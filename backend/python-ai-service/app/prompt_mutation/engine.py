"""
Prompt Mutation Engine — self-improving prompts through evolutionary mutation loops.

Implements: task → evaluate → mutate prompt → retry → compare outputs → store best version.
Mirrors patterns from Prompt-Master and integrates with the existing SelfImprovementLoop.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class PromptTemplate:
    """A prompt template with metadata and performance tracking."""

    id: str
    name: str
    system_prompt: str
    user_template: str
    version: int = 1
    score: float = 0.0
    usage_count: int = 0
    success_rate: float = 0.0
    avg_latency_ms: float = 0.0
    parent_id: str | None = None
    tags: list[str] = field(default_factory=list)
    created_at: float = 0.0
    updated_at: float = 0.0


@dataclass
class MutationRecord:
    """Record of a single mutation operation."""

    id: str
    template_id: str
    mutation_type: str  # rewrite, expand, contract, rephrase, restructure
    before_score: float
    after_score: float
    improved: bool
    created_at: float = 0.0


class PromptMutationEngine:
    """
    Evolutionary prompt mutation engine.

    Each prompt starts as a seed template. The engine generates variants,
    evaluates them, and keeps the best performing versions.
    """

    MUTATION_TYPES = ["rewrite", "expand", "contract", "rephrase", "restructure"]

    def __init__(self):
        self._templates: dict[str, PromptTemplate] = {}
        self._mutations: list[MutationRecord] = []
        self._max_mutations = 500

    async def register_template(
        self,
        name: str,
        system_prompt: str,
        user_template: str,
        tags: list[str] | None = None,
    ) -> PromptTemplate:
        """Register a new prompt template for mutation."""
        template = PromptTemplate(
            id=str(uuid.uuid4()),
            name=name,
            system_prompt=system_prompt,
            user_template=user_template,
            tags=tags or [],
            created_at=time.time(),
            updated_at=time.time(),
        )
        self._templates[template.id] = template
        logger.info("prompt_template_registered", name=name, template_id=template.id)
        return template

    async def mutate(
        self,
        template_id: str,
        mutation_type: str | None = None,
        num_variants: int = 3,
    ) -> list[PromptTemplate]:
        """Generate mutated variants of a prompt template."""
        template = self._templates.get(template_id)
        if not template:
            raise ValueError(f"Template '{template_id}' not found")

        mutation_type = mutation_type or "rewrite"
        if mutation_type not in self.MUTATION_TYPES:
            raise ValueError(f"Invalid mutation type '{mutation_type}'. Options: {self.MUTATION_TYPES}")

        variants: list[PromptTemplate] = []

        for i in range(num_variants):
            variant = await self._apply_mutation(
                template=template,
                mutation_type=mutation_type,
                variant_index=i,
            )
            variants.append(variant)
            self._templates[variant.id] = variant

        logger.info("prompt_mutation_complete", template_id=template_id, mutation=mutation_type, variants=len(variants))
        return variants

    async def _apply_mutation(
        self,
        template: PromptTemplate,
        mutation_type: str,
        variant_index: int,
    ) -> PromptTemplate:
        """Apply a specific mutation to a template."""
        mutation_fns = {
            "rewrite": self._rewrite_prompt,
            "expand": self._expand_prompt,
            "contract": self._contract_prompt,
            "rephrase": self._rephrase_prompt,
            "restructure": self._restructure_prompt,
        }

        fn = mutation_fns.get(mutation_type, self._rewrite_prompt)
        system_prompt, user_template = await fn(template, variant_index)

        return PromptTemplate(
            id=str(uuid.uuid4()),
            name=f"{template.name}-{mutation_type}-{variant_index}",
            system_prompt=system_prompt,
            user_template=user_template,
            version=template.version + 1,
            parent_id=template.id,
            tags=template.tags.copy(),
            created_at=time.time(),
            updated_at=time.time(),
        )

    async def _rewrite_prompt(self, template: PromptTemplate, variant: int) -> tuple[str, str]:
        """Complete rewrite preserving core intent."""
        suffixes = [
            "\n\nBe concise and direct in your response.",
            "\n\nProvide step-by-step reasoning before giving your answer.",
            "\n\nConsider edge cases and alternative perspectives.",
        ]
        suffix = suffixes[variant % len(suffixes)]
        return template.system_prompt + suffix, template.user_template

    async def _expand_prompt(self, template: PromptTemplate, variant: int) -> tuple[str, str]:
        """Expand with more context and examples."""
        expansions = [
            "\n\nAdditional context: The user is working on a production system and needs robust, well-tested solutions.",
            "\n\nAdditional context: Prioritize clarity and maintainability over clever optimizations.",
            "\n\nAdditional context: Consider the full system architecture and how this component fits in.",
        ]
        return template.system_prompt + expansions[variant % len(expansions)], template.user_template

    async def _contract_prompt(self, template: PromptTemplate, variant: int) -> tuple[str, str]:
        """Contract to essential instructions."""
        # Take first 300 chars of system prompt
        contracted = template.system_prompt[:300]
        if contracted != template.system_prompt:
            contracted += "\n\n(Instructions condensed for efficiency)"
        return contracted, template.user_template

    async def _rephrase_prompt(self, template: PromptTemplate, variant: int) -> tuple[str, str]:
        """Rephrase for clarity and different communication styles."""
        rephrasings = [
            template.system_prompt.replace("must", "should").replace("always", "prefer"),
            template.system_prompt + "\n\nUse a friendly, conversational tone.",
            template.system_prompt + "\n\nUse a technical, precise tone with specific terminology.",
        ]
        return rephrasings[variant % len(rephrasings)], template.user_template

    async def _restructure_prompt(self, template: PromptTemplate, variant: int) -> tuple[str, str]:
        """Restructure with explicit sections."""
        structures = [
            "## Role\nYou are an AI assistant.\n\n## Instructions\n{instructions}\n\n## Constraints\n{constraints}".format(
                instructions=template.system_prompt[:200],
                constraints="Be accurate, concise, and helpful.",
            ),
            "## Objective\n{obj}\n\n## Approach\n{approach}\n\n## Output Format\n{fmt}".format(
                obj=template.system_prompt[:150],
                approach="Follow a systematic approach",
                fmt="Provide clear, structured output",
            ),
        ]
        system = structures[variant % len(structures)]
        return system, template.user_template

    async def evaluate(
        self,
        template_id: str,
        test_input: str,
        expected_output_quality: str = "high",
    ) -> dict[str, Any]:
        """Evaluate a prompt template's performance."""
        template = self._templates.get(template_id)
        if not template:
            raise ValueError(f"Template '{template_id}' not found")

        start = time.perf_counter()
        await asyncio.sleep(0.1)  # Simulated evaluation
        latency_ms = (time.perf_counter() - start) * 1000

        # Simulated scoring
        score = min(1.0, (template.version * 0.05) + 0.5)

        # Update template stats
        template.usage_count += 1
        template.avg_latency_ms = (template.avg_latency_ms * (template.usage_count - 1) + latency_ms) / template.usage_count
        template.success_rate = (template.success_rate * (template.usage_count - 1) + (0.9 if score > 0.6 else 0.3)) / template.usage_count
        template.score = score
        template.updated_at = time.time()

        return {
            "templateId": template_id,
            "score": score,
            "latencyMs": round(latency_ms, 1),
            "avgLatencyMs": round(template.avg_latency_ms, 1),
            "successRate": round(template.success_rate, 3),
            "usageCount": template.usage_count,
        }

    async def evolve(
        self,
        template_id: str,
        test_input: str,
        generations: int = 3,
    ) -> list[dict[str, Any]]:
        """
        Full evolutionary loop:
        1. Evaluate current template
        2. Generate mutated variants
        3. Evaluate all variants
        4. Keep best performer
        5. Repeat for N generations
        """
        history: list[dict[str, Any]] = []
        current_id = template_id

        for gen in range(generations):
            logger.info("prompt_evolution_generation", gen=gen + 1, template_id=current_id)

            # Evaluate current
            eval_result = await self.evaluate(current_id, test_input)
            before_score = eval_result["score"]

            # Mutate
            variants = await self.mutate(current_id, num_variants=3)

            # Evaluate variants
            best_variant = None
            best_score = before_score

            for variant in variants:
                v_eval = await self.evaluate(variant.id, test_input)
                if v_eval["score"] > best_score:
                    best_score = v_eval["score"]
                    best_variant = variant

            # Record mutation
            record = MutationRecord(
                id=str(uuid.uuid4()),
                template_id=current_id,
                mutation_type="auto_evolve",
                before_score=before_score,
                after_score=best_score,
                improved=best_score > before_score,
                created_at=time.time(),
            )
            self._mutations.append(record)

            history.append({
                "generation": gen + 1,
                "beforeScore": before_score,
                "afterScore": best_score,
                "improved": best_score > before_score,
                "bestVariantId": best_variant.id if best_variant else None,
                "bestVariantName": best_variant.name if best_variant else None,
            })

            # Move to best variant
            if best_variant and best_score > before_score:
                current_id = best_variant.id

            # Prune mutation history
            if len(self._mutations) > self._max_mutations:
                self._mutations = self._mutations[-self._max_mutations:]

        return history

    async def get_template(self, template_id: str) -> PromptTemplate | None:
        return self._templates.get(template_id)

    async def list_templates(self, limit: int = 50) -> list[dict[str, Any]]:
        templates = sorted(
            self._templates.values(),
            key=lambda t: t.updated_at,
            reverse=True,
        )
        return [
            {
                "id": t.id,
                "name": t.name,
                "version": t.version,
                "score": round(t.score, 3),
                "usageCount": t.usage_count,
                "successRate": round(t.success_rate, 3),
                "tags": t.tags,
                "updatedAt": t.updated_at,
            }
            for t in templates[:limit]
        ]

    async def get_mutation_history(self, limit: int = 50) -> list[dict[str, Any]]:
        records = sorted(self._mutations, key=lambda r: r.created_at, reverse=True)
        return [
            {
                "id": r.id,
                "templateId": r.template_id,
                "mutationType": r.mutation_type,
                "beforeScore": round(r.before_score, 3),
                "afterScore": round(r.after_score, 3),
                "improved": r.improved,
            }
            for r in records[:limit]
        ]


# Singleton
_mutation_engine_instance: PromptMutationEngine | None = None


def get_mutation_engine() -> PromptMutationEngine:
    global _mutation_engine_instance
    if _mutation_engine_instance is None:
        _mutation_engine_instance = PromptMutationEngine()
    return _mutation_engine_instance
