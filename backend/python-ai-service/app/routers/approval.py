"""
Approval Gates API router.

GET  /approval/pending          — list all pending gates
GET  /approval/history          — resolved gate history
GET  /approval/{id}             — get single request
POST /approval/{id}/respond     — approve or reject
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.envelopes import success, error
from app.approval.gate import ApprovalGate, RiskLevel

router = APIRouter(prefix="/approval", tags=["approval"])


class RespondRequest(BaseModel):
    approved: bool
    reason: str = ""


@router.get("/pending")
async def list_pending():
    gate = ApprovalGate.get()
    return success({"requests": gate.list_pending()})


@router.get("/history")
async def get_history(limit: int = 50):
    gate = ApprovalGate.get()
    return success({"history": gate.history(limit=limit)})


@router.get("/{request_id}")
async def get_request(request_id: str):
    gate = ApprovalGate.get()
    req = gate.get_request(request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Approval request not found")
    return success(req.to_dict())


@router.post("/{request_id}/respond")
async def respond(request_id: str, body: RespondRequest):
    gate = ApprovalGate.get()
    ok = gate.respond(
        request_id=request_id,
        approved=body.approved,
        reason=body.reason,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Approval request not found or already resolved")
    return success({"responded": True, "approved": body.approved})
