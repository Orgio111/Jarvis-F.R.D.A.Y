from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from app.core.envelopes import error, success
from app.core.logging import get_logger
from app.services.workflow_service import WorkflowService

logger = get_logger(__name__)
router = APIRouter()


@router.post("/workflows/engine/create")
async def create_workflow(request: Request, body: dict[str, Any]) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    try:
        name = body.get("name", "unnamed")
        task_specs = body.get("steps", [])
        description = body.get("description", "")
        context = body.get("context")

        if not task_specs:
            return error("missing_steps", "workflow steps are required", correlation_id=correlation_id)

        svc = WorkflowService.get()
        result = await svc.create_workflow(
            name=name,
            task_specs=task_specs,
            description=description,
            context=context,
        )
        return success(result, correlation_id)
    except Exception as exc:
        logger.error("create_workflow_failed", error=str(exc))
        return error("workflow_create_failed", str(exc), correlation_id=correlation_id)


@router.post("/workflows/engine/run")
async def run_workflow(request: Request, body: dict[str, Any]) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    try:
        workflow_id = body.get("workflowId", "")
        context = body.get("context")

        if not workflow_id:
            return error("missing_workflow_id", "workflowId is required", correlation_id=correlation_id)

        svc = WorkflowService.get()
        result = await svc.run_workflow(workflow_id, context)
        return success(result, correlation_id)
    except Exception as exc:
        logger.error("run_workflow_failed", error=str(exc))
        return error("workflow_run_failed", str(exc), correlation_id=correlation_id)


@router.post("/workflows/engine/pipeline")
async def run_pipeline(request: Request, body: dict[str, Any]) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    try:
        task_specs = body.get("steps", [])
        name = body.get("name", "pipeline")
        context = body.get("context")

        if not task_specs:
            return error("missing_steps", "pipeline steps are required", correlation_id=correlation_id)

        svc = WorkflowService.get()
        result = await svc.run_pipeline(
            task_specs=task_specs,
            name=name,
            context=context,
        )
        return success(result, correlation_id)
    except Exception as exc:
        logger.error("run_pipeline_failed", error=str(exc))
        return error("pipeline_run_failed", str(exc), correlation_id=correlation_id)


@router.get("/workflows/engine/list")
async def list_workflows(request: Request) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    try:
        svc = WorkflowService.get()
        workflows = await svc.list_workflows()
        return success(workflows, correlation_id)
    except Exception as exc:
        logger.error("list_workflows_failed", error=str(exc))
        return success([], correlation_id)


@router.get("/workflows/engine/{workflow_id}")
async def get_workflow(workflow_id: str, request: Request) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    try:
        svc = WorkflowService.get()
        wf = await svc.get_workflow(workflow_id)
        if wf is None:
            raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")
        return success(wf, correlation_id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("get_workflow_failed", workflow_id=workflow_id, error=str(exc))
        return error("workflow_fetch_failed", str(exc), correlation_id=correlation_id)
