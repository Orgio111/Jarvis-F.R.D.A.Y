"""Prompt Mutation Engine API router."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.prompt_mutation.engine import get_mutation_engine

router = APIRouter(prefix="/prompt-mutation", tags=["prompt-mutation"])


class RegisterTemplateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    system_prompt: str = Field(min_length=1)
    user_template: str = ""
    tags: list[str] = []


class MutateRequest(BaseModel):
    template_id: str
    mutation_type: str = "rewrite"
    num_variants: int = 3


class EvolveRequest(BaseModel):
    template_id: str
    test_input: str = "test query"
    generations: int = 3


@router.post("/templates")
async def register_template(req: RegisterTemplateRequest):
    """Register a new prompt template for mutation."""
    engine = get_mutation_engine()
    template = await engine.register_template(
        name=req.name,
        system_prompt=req.system_prompt,
        user_template=req.user_template,
        tags=req.tags,
    )
    return {
        "id": template.id,
        "name": template.name,
        "version": template.version,
    }


@router.post("/mutate")
async def mutate(req: MutateRequest):
    """Generate mutated variants of a prompt template."""
    engine = get_mutation_engine()
    try:
        variants = await engine.mutate(
            template_id=req.template_id,
            mutation_type=req.mutation_type,
            num_variants=req.num_variants,
        )
        return {
            "variants": [
                {"id": v.id, "name": v.name, "version": v.version}
                for v in variants
            ],
            "count": len(variants),
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/evolve")
async def evolve(req: EvolveRequest):
    """Run evolutionary prompt improvement loop."""
    engine = get_mutation_engine()
    try:
        history = await engine.evolve(
            template_id=req.template_id,
            test_input=req.test_input,
            generations=req.generations,
        )
        return {"history": history, "generations": len(history)}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/evaluate/{template_id}")
async def evaluate(template_id: str, test_input: str = "test query"):
    """Evaluate a prompt template's performance."""
    engine = get_mutation_engine()
    try:
        return await engine.evaluate(template_id, test_input)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/templates")
async def list_templates(limit: int = 50):
    """List all registered prompt templates."""
    engine = get_mutation_engine()
    return {"templates": await engine.list_templates(limit=limit)}


@router.get("/mutations")
async def mutation_history(limit: int = 50):
    """Get mutation history records."""
    engine = get_mutation_engine()
    return {"mutations": await engine.get_mutation_history(limit=limit)}
