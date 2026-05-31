# Multi-Agent Communication System — Task Plan

## Architecture
- AgentBus: central message bus (pub/sub, A2A messaging)
- AgentNode: base class for any agent that can send/receive messages
- AgentFactory: creates new agents dynamically from spec (agent-to-generate-agent)
- SharedBlackboard: shared memory/state for all agents
- MultiAgentOrchestrator: hub-and-spoke + parallel execution + chain support
- Agent-to-agent pipeline: output of one → input of next
- UI log: all messages visible via SSE stream

## Files to create/modify
1. [x] app/multi_agent/agent_bus.py         — message bus (A2A messaging)
2. [x] app/multi_agent/agent_node.py        — base agent node class
3. [x] app/multi_agent/blackboard.py        — shared memory/blackboard
4. [x] app/multi_agent/agent_factory.py     — dynamic agent creation (agent-to-generate-agent)
5. [x] app/multi_agent/multi_orchestrator.py — hub+spoke, parallel, chain, pipeline
6. [x] app/multi_agent/__init__.py
7. [x] app/routers/multi_agent.py           — API + SSE stream endpoint
8. [x] app/main.py                          — register new router

## Phases
- [x] Phase 1: AgentBus + AgentNode + Blackboard
- [x] Phase 2: AgentFactory (generate-agent system)
- [x] Phase 3: MultiAgentOrchestrator (hub+spoke, parallel, chain)
- [x] Phase 4: API router + SSE stream + UI log
- [x] Phase 5: Register + test
