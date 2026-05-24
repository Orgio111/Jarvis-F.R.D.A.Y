"""Image Generation API router."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.image_generation.engine import get_generator

router = APIRouter(prefix="/image", tags=["image-generation"])


class GenerateImageRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=2000)
    negative_prompt: str = ""
    width: int = 1024
    height: int = 1024
    num_images: int = Field(default=1, ge=1, le=4)
    guidance_scale: float = Field(default=7.5, ge=1.0, le=15.0)
    num_inference_steps: int = Field(default=4, ge=1, le=64)


@router.post("/generate")
async def generate_image(req: GenerateImageRequest):
    """Generate images from a text prompt."""
    generator = get_generator()
    result = await generator.generate(
        prompt=req.prompt,
        negative_prompt=req.negative_prompt,
        width=req.width,
        height=req.height,
        num_images=req.num_images,
        guidance_scale=req.guidance_scale,
        num_inference_steps=req.num_inference_steps,
    )
    return result


@router.get("/history")
async def image_history(limit: int = 20):
    """Get image generation history."""
    generator = get_generator()
    return {"generations": await generator.get_history(limit=limit)}
