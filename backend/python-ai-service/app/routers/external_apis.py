from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from app.core.envelopes import error, success
from app.core.logging import get_logger
from app.services.api_registry_service import ApiRegistryService

logger = get_logger(__name__)
router = APIRouter()


@router.get("/external-apis/providers")
async def list_external_api_providers(request: Request) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    try:
        svc = ApiRegistryService.get()
        providers = await svc.list_providers()
        return success(providers, correlation_id)
    except Exception as exc:
        logger.error("list_external_apis_failed", error=str(exc))
        return success([], correlation_id)


@router.get("/external-apis/health")
async def external_api_health(request: Request) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    try:
        svc = ApiRegistryService.get()
        statuses = await svc.check_health()
        return success(statuses, correlation_id)
    except Exception as exc:
        logger.error("external_api_health_failed", error=str(exc))
        return error("health_check_failed", str(exc), correlation_id=correlation_id)


@router.post("/external-apis/call")
async def call_external_api(request: Request, body: dict[str, Any]) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    try:
        endpoint = body.get("endpoint", "")
        strategy = body.get("strategy", "fastest")
        path_params = body.get("pathParams")
        query_params = body.get("queryParams")
        req_body = body.get("body")
        auth_token = body.get("authToken")
        task = body.get("task", "")

        if not endpoint:
            return error("missing_endpoint", "endpoint name is required", correlation_id=correlation_id)

        svc = ApiRegistryService.get()
        result = await svc.call_api(
            endpoint_name=endpoint,
            strategy=strategy,
            path_params=path_params,
            query_params=query_params,
            body=req_body,
            auth_token=auth_token,
            task_description=task,
        )
        return success(result, correlation_id)
    except Exception as exc:
        logger.error("external_api_call_failed", endpoint=body.get("endpoint"), error=str(exc))
        return error("api_call_failed", str(exc), correlation_id=correlation_id)
