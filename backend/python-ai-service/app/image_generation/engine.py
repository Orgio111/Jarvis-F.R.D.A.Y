"""
Image Generation Engine — Sana integration for ultra-fast local image synthesis.

Provides a unified interface for text-to-image generation with local model
inference (Sana) and API-based fallback providers.
"""

from __future__ import annotations

import asyncio
import base64
import io
import time
import uuid
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


class ImageGenerator:
    """
    Multi-backend image generation engine.

    Primary: Local Sana model (ultra-fast)
    Fallback: API-based providers (OpenAI DALL-E, Stability AI, etc.)
    """

    def __init__(self):
        self.id = str(uuid.uuid4())[:8]
        self._sana_model = None
        self._sana_pipeline = None
        self._generations: list[dict[str, Any]] = []
        self._max_generations = 100

    async def generate(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 1024,
        height: int = 1024,
        num_images: int = 1,
        guidance_scale: float = 7.5,
        num_inference_steps: int = 4,  # Sana is fast — 4-8 steps typical
        use_local: bool = True,
    ) -> dict[str, Any]:
        """
        Generate images from a text prompt.

        Args:
            prompt: Text description of the image
            negative_prompt: Things to avoid in the image
            width/height: Image dimensions (Sana supports 1024x1024 natively)
            num_images: Number of images to generate
            guidance_scale: How closely to follow the prompt (1-15)
            num_inference_steps: Diffusion steps (Sana: 4-8 for fast, 16-32 for quality)
            use_local: Try local Sana inference first, fallback to API
        """
        gen_id = str(uuid.uuid4())
        start = time.perf_counter()
        logger.info("image_generation_start", gen_id=gen_id, prompt=prompt[:80])

        try:
            if use_local:
                result = await self._generate_local(
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    width=width,
                    height=height,
                    num_images=num_images,
                    guidance_scale=guidance_scale,
                    num_inference_steps=num_inference_steps,
                )
            else:
                result = await self._generate_api(prompt, num_images)

        except Exception as exc:
            logger.warning("image_generation_api_fallback", gen_id=gen_id, error=str(exc))
            result = await self._generate_api(prompt, num_images)

        duration_ms = (time.perf_counter() - start) * 1000
        result["genId"] = gen_id
        result["durationMs"] = round(duration_ms, 1)
        result["prompt"] = prompt

        # Store generation record
        record = {
            "id": gen_id,
            "prompt": prompt[:200],
            "width": width,
            "height": height,
            "durationMs": duration_ms,
            "numImages": num_images,
            "createdAt": time.time(),
        }
        self._generations.append(record)
        if len(self._generations) > self._max_generations:
            self._generations = self._generations[-self._max_generations:]

        logger.info("image_generation_complete", gen_id=gen_id, duration_ms=f"{duration_ms:.0f}ms")
        return result

    async def _generate_local(
        self,
        prompt: str,
        negative_prompt: str,
        width: int,
        height: int,
        num_images: int,
        guidance_scale: float,
        num_inference_steps: int,
    ) -> dict[str, Any]:
        """Generate using local Sana model via diffusers."""
        try:
            import torch
            from diffusers import SanaPipeline

            if self._sana_pipeline is None:
                logger.info("loading_sana_model")
                self._sana_pipeline = SanaPipeline.from_pretrained(
                    "Efficient-Large-Model/Sana_600M_1024px",
                    torch_dtype=torch.bfloat16,
                    variant="bf16",
                )
                self._sana_pipeline.to("cuda" if torch.cuda.is_available() else "cpu")
                logger.info("sana_model_loaded")

            # Generate
            images = self._sana_pipeline(
                prompt=prompt,
                negative_prompt=negative_prompt or None,
                width=width,
                height=height,
                num_images_per_prompt=num_images,
                guidance_scale=guidance_scale,
                num_inference_steps=num_inference_steps,
            ).images

            # Encode to base64
            encoded_images = []
            for img in images:
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                encoded = base64.b64encode(buf.getvalue()).decode("utf-8")
                encoded_images.append(f"data:image/png;base64,{encoded[:50]}...")

            return {
                "status": "local",
                "images": encoded_images,
                "count": len(encoded_images),
                "model": "Sana_600M_1024px",
                "steps": num_inference_steps,
            }

        except ImportError as exc:
            logger.warning("sana_not_available", error=str(exc))
            raise RuntimeError("Sana/diffusers not installed. Run: pip install diffusers torch")
        except Exception as exc:
            logger.warning("sana_generation_failed", error=str(exc))
            raise

    async def _generate_api(self, prompt: str, num_images: int) -> dict[str, Any]:
        """Generate using API-based provider (simulated for now)."""
        # Simulate API generation
        await asyncio.sleep(0.5)
        return {
            "status": "api_simulated",
            "images": [f"data:image/png;base64,simulated_{i}" for i in range(num_images)],
            "count": num_images,
            "model": "api_fallback",
        }

    async def get_history(self, limit: int = 20) -> list[dict[str, Any]]:
        return list(reversed(self._generations[-limit:]))


# Singleton
_generator_instance: ImageGenerator | None = None


def get_generator() -> ImageGenerator:
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = ImageGenerator()
    return _generator_instance
