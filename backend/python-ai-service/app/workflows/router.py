"""FastAPI router for workflow CRUD and execution endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.workflows.models import WorkflowDefinition, WorkflowNode, WorkflowEdge
from app.workflows.engine import (
    create_workflow, get_workflow, list_workflows,
    update_workflow, delete_workflow, execute_workflow,
    get_execution, list_executions,
)
from app.core.envelopes import error, success

router = APIRouter(prefix="/workflows")


@router.post("")
async def create_workflow_endpoint(request: Request) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content=error("invalid_request", "Invalid JSON", correlation_id))

    workflow = WorkflowDefinition(
        id=str(uuid.uuid4()),
        name=body.get("name", "Untitled Workflow"),
        description=body.get("description", ""),
        nodes=[WorkflowNode.from_dict(n) for n in body.get("nodes", [])],
        edges=[WorkflowEdge.from_dict(e) for e in body.get("edges", [])],
        tags=body.get("tags", []),
    )

    validation_errors = workflow.validate()
    if validation_errors:
        return JSONResponse(status_code=400, content=error("validation_error", "; ".join(validation_errors), correlation_id))

    created = create_workflow(workflow)
    return success(created.to_dict(), correlation_id)


@router.get("")
async def list_workflows_endpoint(request: Request) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    status = request.query_params.get("status")
    wfs = list_workflows(status=status)
    return success({"workflows": [w.to_dict() for w in wfs], "total": len(wfs)}, correlation_id)


@router.get("/{workflow_id}")
async def get_workflow_endpoint(workflow_id: str, request: Request) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    wf = get_workflow(workflow_id)
    if wf is None:
        return JSONResponse(status_code=404, content=error("not_found", f"Workflow '{workflow_id}' not found", correlation_id))
    return success(wf.to_dict(), correlation_id)


@router.put("/{workflow_id}")
async def update_workflow_endpoint(workflow_id: str, request: Request) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content=error("invalid_request", "Invalid JSON", correlation_id))

    updated = update_workflow(workflow_id, body)
    if updated is None:
        return JSONResponse(status_code=404, content=error("not_found", f"Workflow '{workflow_id}' not found", correlation_id))
    return success(updated.to_dict(), correlation_id)


@router.delete("/{workflow_id}")
async def delete_workflow_endpoint(workflow_id: str, request: Request) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    deleted = delete_workflow(workflow_id)
    if not deleted:
        return JSONResponse(status_code=404, content=error("not_found", f"Workflow '{workflow_id}' not found", correlation_id))
    return success({"deleted": True}, correlation_id)


@router.post("/{workflow_id}/execute")
async def execute_workflow_endpoint(workflow_id: str, request: Request) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    try:
        body = await request.json()
    except Exception:
        body = {}

    try:
        execution = await execute_workflow(workflow_id, inputs=body.get("inputs"))
        return success(execution.to_dict(), correlation_id)
    except ValueError as ve:
        return JSONResponse(status_code=400, content=error("execution_error", str(ve), correlation_id))
    except Exception as exc:
        return JSONResponse(status_code=500, content=error("execution_failed", str(exc), correlation_id))


@router.get("/executions/{execution_id}")
async def get_execution_endpoint(execution_id: str, request: Request) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    ex = get_execution(execution_id)
    if ex is None:
        return JSONResponse(status_code=404, content=error("not_found", f"Execution '{execution_id}' not found", correlation_id))
    return success(ex.to_dict(), correlation_id)


@router.get("/executions")
async def list_executions_endpoint(request: Request) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    workflow_id = request.query_params.get("workflowId")
    exs = list_executions(workflow_id=workflow_id)
    return success({"executions": [e.to_dict() for e in exs], "total": len(exs)}, correlation_id)
