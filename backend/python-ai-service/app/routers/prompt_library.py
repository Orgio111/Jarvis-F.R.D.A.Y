"""
Prompt Library API router.

GET    /prompts                       — list templates
POST   /prompts                       — create template
GET    /prompts/{id}                  — get template with versions
PUT    /prompts/{id}                  — update metadata
DELETE /prompts/{id}                  — delete template
POST   /prompts/{id}/versions         — add new version
POST   /prompts/{id}/render           — render template with variables
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.envelopes import success
from app.prompt_library.store import PromptLibraryStore

router = APIRouter(prefix="/prompts", tags=["prompt_library"])


class CreateTemplateRequest(BaseModel):
    name: str
    body: str
    description: str = ""
    category: str = "general"
    tags: list[str] = []
    metadata: dict[str, Any] = {}
    notes: str = ""


class AddVersionRequest(BaseModel):
    body: str
    notes: str = ""


class UpdateTemplateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    category: str | None = None
    tags: list[str] | None = None


class RenderRequest(BaseModel):
    variables: dict[str, str] = {}
    version: int | None = None


@router.get("")
async def list_templates(
    category: str | None = None,
    tag: str | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    store = PromptLibraryStore.get()
    templates = store.list(category=category, tag=tag, search=search, limit=limit, offset=offset)
    return success({"templates": templates, "count": len(templates)})


@router.post("")
async def create_template(body: CreateTemplateRequest):
    store = PromptLibraryStore.get()
    tpl = store.create(
        name=body.name,
        body=body.body,
        description=body.description,
        category=body.category,
        tags=body.tags,
        metadata=body.metadata,
        notes=body.notes,
    )
    return success(tpl.to_dict())


@router.get("/{template_id}")
async def get_template(template_id: str):
    store = PromptLibraryStore.get()
    tpl = store.get(template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    return success(tpl.to_dict())


@router.put("/{template_id}")
async def update_template(template_id: str, body: UpdateTemplateRequest):
    store = PromptLibraryStore.get()
    kwargs = {k: v for k, v in body.model_dump().items() if v is not None}
    ok = store.update(template_id, **kwargs)
    if not ok:
        raise HTTPException(status_code=404, detail="Template not found")
    return success({"updated": True})


@router.delete("/{template_id}")
async def delete_template(template_id: str):
    store = PromptLibraryStore.get()
    ok = store.delete(template_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Template not found")
    return success({"deleted": True})


@router.post("/{template_id}/versions")
async def add_version(template_id: str, body: AddVersionRequest):
    store = PromptLibraryStore.get()
    ok = store.add_version(template_id, body.body, notes=body.notes)
    if not ok:
        raise HTTPException(status_code=404, detail="Template not found")
    tpl = store.get(template_id)
    return success(tpl.to_dict() if tpl else {})


@router.post("/{template_id}/render")
async def render_template(template_id: str, body: RenderRequest):
    store = PromptLibraryStore.get()
    tpl = store.get(template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")

    # Use specific version if requested
    if body.version is not None:
        ver = next((v for v in tpl.versions if v.version == body.version), None)
        if not ver:
            raise HTTPException(status_code=404, detail=f"Version {body.version} not found")
        rendered = ver.render(**body.variables)
        tpl.usage_count += 1
    else:
        rendered = store.render(template_id, **body.variables)

    return success({"rendered": rendered, "template_id": template_id})
