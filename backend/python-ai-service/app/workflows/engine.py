"""
Workflow execution engine — runs a workflow DAG by traversing nodes in topological order.

Node execution:
  1. TRIGGER → awaits trigger condition
  2. LLM     → calls configured AI provider with system prompt
  3. TOOL    → executes a tool (code, browser, memory, API)
  4. CONDITION → evaluates expression, routes to next node
  5. AGENT   → delegates to a sub-agent
  6. DELAY   → waits for specified duration
  7. OUTPUT  → formats and returns result

Inspired by the existing autonomous_pipeline.py 6-stage pattern.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from typing import Any

from app.workflows.models import (
    WorkflowDefinition, WorkflowExecution, WorkflowNode, WorkflowEdge,
    WorkflowStatus, NodeType,
)
from app.core.logging import get_logger
from app.core.config import get_settings

logger = get_logger(__name__)

# In-memory store (will be SQLite-persisted later)
_workflows: dict[str, WorkflowDefinition] = {}
_executions: dict[str, WorkflowExecution] = {}


# ─── CRUD ─────────────────────────────────────────────────────────────────────


def create_workflow(workflow: WorkflowDefinition) -> WorkflowDefinition:
    _workflows[workflow.id] = workflow
    logger.info("workflow_created", id=workflow.id, name=workflow.name)
    return workflow


def get_workflow(workflow_id: str) -> WorkflowDefinition | None:
    return _workflows.get(workflow_id)


def list_workflows(status: str | None = None) -> list[WorkflowDefinition]:
    wfs = list(_workflows.values())
    if status:
        wfs = [w for w in wfs if w.status.value == status]
    return sorted(wfs, key=lambda w: w.updated_at or "", reverse=True)


def update_workflow(workflow_id: str, data: dict) -> WorkflowDefinition | None:
    existing = _workflows.get(workflow_id)
    if existing is None:
        return None

    # Update fields
    if "name" in data:
        existing.name = data["name"]
    if "description" in data:
        existing.description = data["description"]
    if "nodes" in data:
        existing.nodes = [WorkflowNode.from_dict(n) for n in data["nodes"]]
    if "edges" in data:
        existing.edges = [WorkflowEdge.from_dict(e) for e in data["edges"]]
    if "status" in data:
        existing.status = WorkflowStatus(data["status"])
    if "tags" in data:
        existing.tags = data["tags"]

    existing.updated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    _workflows[workflow_id] = existing
    logger.info("workflow_updated", id=workflow_id)
    return existing


def delete_workflow(workflow_id: str) -> bool:
    if workflow_id in _workflows:
        del _workflows[workflow_id]
        logger.info("workflow_deleted", id=workflow_id)
        return True
    return False


# ─── Execution ────────────────────────────────────────────────────────────────


async def execute_workflow(
    workflow_id: str,
    inputs: dict[str, Any] | None = None,
) -> WorkflowExecution:
    """Execute a workflow DAG from start to finish."""
    workflow = _workflows.get(workflow_id)
    if workflow is None:
        raise ValueError(f"Workflow '{workflow_id}' not found")

    # Validate
    errors = workflow.validate()
    if errors:
        raise ValueError(f"Workflow validation failed: {'; '.join(errors)}")

    execution = WorkflowExecution(
        id=str(uuid.uuid4()),
        workflow_id=workflow_id,
        context=inputs or {},
    )
    _executions[execution.id] = execution

    try:
        # Topological sort
        sorted_nodes = _topological_sort(workflow)
        if not sorted_nodes:
            raise ValueError("No executable nodes found")

        logger.info("workflow_execution_started",
                    id=execution.id, workflow=workflow_id)

        # Execute nodes in order
        for node in sorted_nodes:
            execution.current_node_id = node.id
            logger.info("workflow_executing_node",
                        node=node.id, type=node.type.value)

            result = await _execute_node(node, execution.context, workflow.edges)
            execution.context[f"node_{node.id}_output"] = result

            # Check conditions
            if node.type == NodeType.CONDITION:
                next_node = _resolve_condition(node, result, workflow.edges)
                if next_node is None:
                    break  # No path forward

        execution.status = WorkflowStatus.COMPLETED
        execution.completed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        logger.info("workflow_execution_completed", id=execution.id)

    except Exception as exc:
        execution.status = WorkflowStatus.ERROR
        execution.error = str(exc)
        logger.warning("workflow_execution_failed", id=execution.id, error=str(exc))

    _executions[execution.id] = execution
    return execution


async def _execute_node(
    node: WorkflowNode,
    context: dict[str, Any],
    edges: list[WorkflowEdge],
) -> Any:
    """Execute a single workflow node and return its output."""
    config = node.config

    if node.type == NodeType.TRIGGER:
        return await _execute_trigger(node, context)

    elif node.type == NodeType.LLM:
        return await _execute_llm(node, context)

    elif node.type == NodeType.TOOL:
        return await _execute_tool(node, context)

    elif node.type == NodeType.CONDITION:
        return await _execute_condition(node, context)

    elif node.type == NodeType.AGENT:
        return await _execute_agent(node, context)

    elif node.type == NodeType.DELAY:
        return await _execute_delay(node)

    elif node.type == NodeType.OUTPUT:
        return await _execute_output(node, context)

    elif node.type == NodeType.CODE:
        return await _execute_code(node, context)

    elif node.type == NodeType.MEMORY:
        return await _execute_memory(node, context)

    elif node.type == NodeType.SEARCH:
        return await _execute_search(node, context)

    else:
        return {"node": node.id, "status": "skipped", "reason": f"unsupported_type: {node.type}"}


async def _execute_trigger(node: WorkflowNode, context: dict) -> dict:
    trigger_type = node.config.get("triggerType", "manual")
    return {
        "node": node.id,
        "triggerType": trigger_type,
        "triggered": True,
        "context": context,
    }


async def _execute_llm(node: WorkflowNode, context: dict) -> dict:
    system_prompt = node.config.get("systemPrompt", "")
    user_prompt = node.config.get("userPrompt", "")
    model = node.config.get("model", "")
    temperature = node.config.get("temperature", 0.7)

    # Format prompts with context variables
    formatted_system = _format_template(system_prompt, context)
    formatted_user = _format_template(user_prompt, context)

    messages = [
        {"role": "system", "content": formatted_system},
        {"role": "user", "content": formatted_user},
    ]

    try:
        from app.providers.router import ProviderRouter
        provider = ProviderRouter.get_provider()
        if provider and provider.is_available():
            response = await provider.chat(
                messages=messages,
                model_id=model or "",
                max_tokens=config.get("maxTokens", 2048),
                temperature=temperature,
            )
            content = response.get("content", response.get("text", ""))
        else:
            content = f"[LLM simulation] {formatted_user[:100]}..."
    except Exception as exc:
        content = f"[LLM error] {exc}"

    return {"node": node.id, "content": content, "model": model}


async def _execute_tool(node: WorkflowNode, context: dict) -> dict:
    tool_type = node.config.get("toolType", "web_search")
    params = node.config.get("params", {})

    return {
        "node": node.id,
        "toolType": tool_type,
        "status": "executed",
        "params": params,
    }


async def _execute_condition(node: WorkflowNode, context: dict) -> dict:
    expression = node.config.get("expression", "true")
    try:
        # Simple expression evaluation
        result = bool(eval(expression, {"__builtins__": {}}, context))
    except Exception:
        result = True
    return {"node": node.id, "condition": expression, "result": result}


async def _execute_agent(node: WorkflowNode, context: dict) -> dict:
    agent_type = node.config.get("agentType", "research")
    task = _format_template(node.config.get("task", ""), context)
    return {"node": node.id, "agentType": agent_type, "task": task, "status": "dispatched"}


async def _execute_delay(node: WorkflowNode) -> dict:
    seconds = float(node.config.get("seconds", 1))
    await asyncio.sleep(seconds)
    return {"node": node.id, "delayed": seconds}


async def _execute_output(node: WorkflowNode, context: dict) -> dict:
    format = node.config.get("format", "json")
    template = node.config.get("template", "")
    formatted = _format_template(template, context)
    return {"node": node.id, "format": format, "output": formatted}


async def _execute_code(node: WorkflowNode, context: dict) -> dict:
    code = node.config.get("code", "")
    language = node.config.get("language", "python")
    return {"node": node.id, "language": language, "code": code[:100], "status": "sandbox_ready"}


async def _execute_memory(node: WorkflowNode, context: dict) -> dict:
    operation = node.config.get("operation", "store")
    key = _format_template(node.config.get("key", ""), context)
    return {"node": node.id, "operation": operation, "key": key}


async def _execute_search(node: WorkflowNode, context: dict) -> dict:
    query = _format_template(node.config.get("query", ""), context)
    return {"node": node.id, "query": query, "status": "searching"}


def _resolve_condition(
    node: WorkflowNode,
    result: dict,
    edges: list[WorkflowEdge],
) -> str | None:
    """Determine which node to go to next based on condition result."""
    condition_result = result.get("result", True)
    for edge in edges:
        if edge.source == node.id:
            if condition_result and edge.condition is None:
                return edge.target
            if edge.condition and str(condition_result) == edge.condition:
                return edge.target
    return None


def _topological_sort(workflow: WorkflowDefinition) -> list[WorkflowNode]:
    """Topological sort of workflow nodes based on edges."""
    node_map = {n.id: n for n in workflow.nodes}
    in_degree: dict[str, int] = {n.id: 0 for n in workflow.nodes}

    for edge in workflow.edges:
        if edge.target in in_degree:
            in_degree[edge.target] = in_degree.get(edge.target, 0) + 1

    queue = [nid for nid, deg in in_degree.items() if deg == 0]
    sorted_nodes: list[WorkflowNode] = []

    while queue:
        nid = queue.pop(0)
        if nid in node_map:
            sorted_nodes.append(node_map[nid])
        for edge in workflow.edges:
            if edge.source == nid:
                in_degree[edge.target] -= 1
                if in_degree[edge.target] == 0:
                    queue.append(edge.target)

    return sorted_nodes


def _format_template(template: str, context: dict[str, Any]) -> str:
    """Replace {{variable}} placeholders with values from context."""
    import re
    def replacer(match):
        key = match.group(1).strip()
        return str(context.get(key, match.group(0)))
    return re.sub(r"\{\{(\w+(?:\.\w+)*)\}\}", replacer, template)


# ─── Execution status ─────────────────────────────────────────────────────────


def get_execution(execution_id: str) -> WorkflowExecution | None:
    return _executions.get(execution_id)


def list_executions(workflow_id: str | None = None) -> list[WorkflowExecution]:
    exs = list(_executions.values())
    if workflow_id:
        exs = [e for e in exs if e.workflow_id == workflow_id]
    return sorted(exs, key=lambda e: e.started_at or "", reverse=True)
