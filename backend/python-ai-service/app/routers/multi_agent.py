"""
Multi-Agent API Router

Endpoints:
  POST /multi-agent/run          — run task with multi-agent system
  POST /multi-agent/spawn        — spawn a single agent
  POST /multi-agent/spawn-auto   — LLM designs + spawns agent for task
  GET  /multi-agent/agents       — list live agents (session)
  GET  /multi-agent/blackboard/{session_id} — get blackboard snapshot
  GET  /multi-agent/history      — get AgentBus message history
  GET  /multi-agent/status       — system status
  GET  /multi-agent/stream/{session_id} — SSE stream of agent messages
  POST /multi-agent/message      — send a manual message on bus
"""
from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from app.core.envelopes import error, success
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/multi-agent", tags=["multi-agent"])


# ── Request / Response models ─────────────────────────────────────────────────

class RunRequest(BaseModel):
    task: str
    session_id: str | None = None
    pattern: str = "auto"       # auto | parallel | chain | hub_spoke
    max_agents: int = 5
    cleanup: bool = True


class SpawnRequest(BaseModel):
    name: str
    role: str = "orchestrator"
    goal: str
    backstory: str = ""
    tools: list[str] = []
    topics: list[str] = []
    session_id: str = "default"
    max_tokens: int = 1024


class SpawnAutoRequest(BaseModel):
    task: str
    session_id: str = "default"
    auto_run: bool = True


class MessageRequest(BaseModel):
    sender_id: str
    sender_name: str = ""
    topic: str = "general"
    recipient_id: str | None = None
    content: str
    msg_type: str = "message"
    payload: dict = {}


# ── Lazy imports (avoid circular at module load) ──────────────────────────────

def _bus():
    from app.multi_agent.agent_bus import AgentBus
    return AgentBus.get()

def _factory():
    from app.multi_agent.agent_factory import AgentFactory
    return AgentFactory.get()

def _registry():
    from app.multi_agent.agent_factory import AgentRegistry
    return AgentRegistry.get()

def _bb_registry():
    from app.multi_agent.blackboard import BlackboardRegistry
    return BlackboardRegistry.get()


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/run")
async def run_multi_agent(req: RunRequest) -> dict[str, Any]:
    """
    Execute a task using the multi-agent system.
    Automatically decomposes, spawns specialists, and aggregates results.
    """
    try:
        from app.multi_agent.multi_orchestrator import MultiAgentOrchestrator
        orch = MultiAgentOrchestrator(session_id=req.session_id)
        result = await orch.run(
            task=req.task,
            pattern=req.pattern,
            max_agents=req.max_agents,
            cleanup=req.cleanup,
        )
        return success(result.to_dict())
    except Exception as exc:
        logger.warning("multi_agent_run_error", error=str(exc))
        return JSONResponse(status_code=500, content=error("execution_failed", str(exc)))


@router.post("/spawn")
async def spawn_agent(req: SpawnRequest) -> dict[str, Any]:
    """Spawn a single agent from explicit spec."""
    try:
        from app.multi_agent.agent_node import AgentNodeSpec
        spec = AgentNodeSpec(
            name=req.name,
            role=req.role,
            goal=req.goal,
            backstory=req.backstory,
            tools=req.tools,
            topics=req.topics,
            max_tokens=req.max_tokens,
        )
        node = _factory().spawn(spec, session_id=req.session_id)
        return success(node.to_dict())
    except Exception as exc:
        return JSONResponse(status_code=500, content=error("spawn_failed", str(exc)))


@router.post("/spawn-auto")
async def spawn_auto(req: SpawnAutoRequest) -> dict[str, Any]:
    """
    Agent-to-generate-agent: LLM designs + spawns an agent for the given task.
    Optionally runs the task immediately.
    """
    try:
        node, output = await _factory().spawn_for_task(
            task=req.task,
            session_id=req.session_id,
            auto_run=req.auto_run,
        )
        return success({
            "agent": node.to_dict(),
            "output": output,
            "auto_run": req.auto_run,
        })
    except Exception as exc:
        return JSONResponse(status_code=500, content=error("spawn_auto_failed", str(exc)))


@router.get("/agents")
async def list_agents(session_id: str = Query(default="default")) -> dict[str, Any]:
    """List all live agents for a session."""
    agents = _registry().list_agents(session_id)
    return success({"agents": agents, "session_id": session_id})


@router.get("/agents/all")
async def list_all_agents() -> dict[str, Any]:
    """List all live agents across all sessions."""
    return success({"agents": _registry().list_all()})


@router.delete("/agents/{agent_id}")
async def remove_agent(agent_id: str, session_id: str = Query(default="default")) -> dict[str, Any]:
    """Remove and deregister an agent."""
    _registry().remove(agent_id, session_id)
    return success({"removed": agent_id})


@router.get("/blackboard/{session_id}")
async def get_blackboard(session_id: str) -> dict[str, Any]:
    """Get the full blackboard snapshot for a session."""
    board = _bb_registry().get_board(session_id)
    if board is None:
        return JSONResponse(status_code=404, content=error("not_found", f"No board for session {session_id}"))
    return success({
        "session_id": session_id,
        "snapshot": board.snapshot(),
        "changelog": board.changelog(20),
    })


@router.get("/history")
async def get_history(
    topic: str = Query(default=""),
    limit: int = Query(default=50, le=500),
) -> dict[str, Any]:
    """Get AgentBus message history."""
    bus = _bus()
    if topic:
        msgs = bus.get_history(topic, limit)
    else:
        msgs = bus.get_all_history(limit)
    return success({"messages": msgs, "count": len(msgs)})


@router.post("/message")
async def send_message(req: MessageRequest) -> dict[str, Any]:
    """Manually publish a message to the AgentBus."""
    from app.multi_agent.agent_bus import AgentMessage
    msg = AgentMessage(
        sender_id=req.sender_id,
        sender_name=req.sender_name or req.sender_id,
        recipient_id=req.recipient_id,
        topic=req.topic,
        content=req.content,
        payload=req.payload,
        msg_type=req.msg_type,
    )
    await _bus().publish(msg)
    return success(msg.to_dict())


@router.get("/status")
async def get_status() -> dict[str, Any]:
    """Get multi-agent system status."""
    try:
        bus_status = _bus().get_status()
        factory_status = _factory().get_status()
        sessions = _bb_registry().list_sessions()
        return success({
            "bus": bus_status,
            "factory": factory_status,
            "blackboard_sessions": sessions,
        })
    except Exception as exc:
        return JSONResponse(status_code=500, content=error("status_failed", str(exc)))


# ── SSE Stream ────────────────────────────────────────────────────────────────

@router.get("/stream/{session_id}")
async def stream_session(session_id: str) -> StreamingResponse:
    """
    SSE stream of all AgentBus messages for a session.
    Connect from UI to see real-time agent communication log.

    Format: text/event-stream
    Each event: data: <JSON>\\n\\n
    """
    bus = _bus()
    queue: asyncio.Queue = asyncio.Queue(maxsize=200)
    bus.add_sse_queue(queue)

    async def event_generator() -> AsyncIterator[str]:
        try:
            # send connected event
            yield f"data: {json.dumps({'type': 'connected', 'session_id': session_id})}\n\n"

            # send recent history
            history = bus.get_history(f"session_{session_id}", 20)
            for msg in history:
                yield f"data: {json.dumps({'type': 'history', 'message': msg})}\n\n"

            # stream new messages
            while True:
                try:
                    msg_dict = await asyncio.wait_for(queue.get(), timeout=30.0)
                    # filter: only messages in this session or global topics
                    topic = msg_dict.get("topic", "")
                    if session_id in topic or topic in ("general", "blackboard", "*"):
                        yield f"data: {json.dumps({'type': 'message', 'message': msg_dict})}\n\n"
                except asyncio.TimeoutError:
                    yield f"data: {json.dumps({'type': 'ping'})}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            bus.remove_sse_queue(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
