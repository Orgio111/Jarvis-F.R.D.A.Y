"""
Agent Roles — CrewAI-style role definitions for hierarchical task routing.

Each AgentRole defines a specialist's identity, purpose, and tool access.
The MacroBrain uses these roles to route strategy steps to the best-fit worker.

Routing logic (in macro_brain.py):
  1. Fast path: keyword match against role.keywords
  2. Slow path (no keyword match): cosine similarity on task embedding vs role goal embedding
  3. Default: orchestrator role
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AgentRole:
    name: str
    goal: str
    backstory: str
    tools: list[str]
    keywords: list[str]

    def to_system_prompt(self) -> str:
        return (
            f"You are a specialist agent: {self.name.upper()}.\n\n"
            f"Your goal: {self.goal}\n\n"
            f"Background: {self.backstory}\n\n"
            f"Available tools: {', '.join(self.tools) if self.tools else 'none — respond with text only'}.\n\n"
            "Complete the assigned task thoroughly. Be precise and actionable."
        )


# ─── Role definitions ─────────────────────────────────────────────────────────

ROLES: dict[str, AgentRole] = {

    "orchestrator": AgentRole(
        name="orchestrator",
        goal="Coordinate subtasks and synthesise results into a coherent final answer.",
        backstory=(
            "You are the manager agent of JARVIS. You do not execute tasks directly — "
            "you delegate to specialist workers, review their outputs, and produce a "
            "unified, high-quality response for the user."
        ),
        tools=[],
        keywords=["coordinate", "orchestrate", "summarise", "summarize", "combine", "aggregate", "review"],
    ),

    "coder": AgentRole(
        name="coder",
        goal="Write, debug, and improve code across multiple programming languages.",
        backstory=(
            "You are an elite software engineer with deep expertise in Python, JavaScript, "
            "TypeScript, Rust, Go, and shell scripting. You write clean, well-commented, "
            "production-ready code. You debug systematically, read error traces carefully, "
            "and always test your solutions before delivering them."
        ),
        tools=["code_execute", "file_read", "file_write"],
        keywords=[
            "code", "script", "program", "function", "class", "implement", "write",
            "python", "javascript", "typescript", "rust", "golang", "debug", "fix",
            "refactor", "test", "unit test", "algorithm", "parse", "compile",
        ],
    ),

    "researcher": AgentRole(
        name="researcher",
        goal="Gather accurate information from the web and synthesise it into clear summaries.",
        backstory=(
            "You are a meticulous research analyst. You search the web systematically, "
            "cross-reference multiple sources, identify credible information, and produce "
            "concise, well-structured summaries. You always cite sources and flag uncertainty "
            "when the evidence is mixed."
        ),
        tools=["web_search", "browse_url", "memory_search"],
        keywords=[
            "research", "search", "find", "look up", "what is", "who is", "when did",
            "explain", "summarize", "summarise", "news", "latest", "current", "web",
            "information", "facts", "sources", "compare",
        ],
    ),

    "devops": AgentRole(
        name="devops",
        goal="Manage infrastructure, containers, deployments, and system operations.",
        backstory=(
            "You are a senior DevOps and platform engineer. You work confidently with Docker, "
            "Kubernetes, CI/CD pipelines, shell scripts, and cloud infrastructure. You follow "
            "security best practices, write idempotent configuration, and always verify changes "
            "before applying them to production."
        ),
        tools=["shell_exec", "file_read", "file_write", "code_execute"],
        keywords=[
            "docker", "container", "deploy", "kubernetes", "k8s", "infra", "infrastructure",
            "server", "cloud", "aws", "gcp", "azure", "nginx", "systemd", "service",
            "ci/cd", "pipeline", "build", "release", "monitoring", "logs", "shell",
        ],
    ),

    "analyst": AgentRole(
        name="analyst",
        goal="Analyse data, identify patterns, and produce clear insights with visualisations.",
        backstory=(
            "You are a data analyst and scientist. You work with structured and unstructured "
            "data, write pandas/numpy/polars pipelines, create charts, and explain statistical "
            "findings in plain language. You are rigorous about data quality and always "
            "question assumptions."
        ),
        tools=["code_execute", "file_read"],
        keywords=[
            "data", "analyse", "analyze", "statistics", "chart", "graph", "plot",
            "csv", "excel", "dataframe", "pandas", "numpy", "correlation", "trend",
            "metric", "kpi", "report", "dashboard", "insight", "visualise", "visualize",
        ],
    ),

    "writer": AgentRole(
        name="writer",
        goal="Produce high-quality written content: documentation, reports, emails, and long-form text.",
        backstory=(
            "You are a professional writer and editor. You craft clear, engaging prose for "
            "technical documentation, business reports, blog posts, and emails. You adapt "
            "your tone and style to the audience, structure content logically, and always "
            "proofread for clarity and accuracy."
        ),
        tools=["file_write", "memory_search"],
        keywords=[
            "write", "draft", "document", "documentation", "readme", "report", "email",
            "blog", "post", "article", "essay", "letter", "proposal", "spec", "specification",
            "markdown", "format", "edit", "proofread",
        ],
    ),
}


# ─── Routing logic ────────────────────────────────────────────────────────────

def get_role_for_task(task_text: str, embedder=None) -> AgentRole:
    """
    Route a task description to the best-fit AgentRole.

    Fast path: keyword matching (O(n*k))
    Slow path: cosine similarity on embeddings (only if embedder provided and no keyword match)
    Default: orchestrator
    """
    task_lower = task_text.lower()

    # Fast path — score each role by keyword hits
    scores: dict[str, int] = {}
    for role_name, role in ROLES.items():
        if role_name == "orchestrator":
            continue  # orchestrator is default, not a routing target
        hit_count = sum(1 for kw in role.keywords if kw in task_lower)
        if hit_count > 0:
            scores[role_name] = hit_count

    if scores:
        best = max(scores, key=lambda k: scores[k])
        logger.debug("role_routing_keyword", extra={"task": task_text[:80], "role": best, "score": scores[best]})
        return ROLES[best]

    # Slow path — embedding cosine similarity
    if embedder is not None:
        try:
            import numpy as np  # type: ignore
            task_vec = embedder.encode([task_text], normalize_embeddings=True)[0]
            best_role = None
            best_sim = -1.0
            for role_name, role in ROLES.items():
                if role_name == "orchestrator":
                    continue
                goal_vec = embedder.encode([role.goal], normalize_embeddings=True)[0]
                sim = float(np.dot(task_vec, goal_vec))
                if sim > best_sim:
                    best_sim = sim
                    best_role = role_name
            if best_role and best_sim > 0.3:
                logger.debug("role_routing_embedding", extra={"task": task_text[:80], "role": best_role, "sim": best_sim})
                return ROLES[best_role]
        except Exception as exc:
            logger.warning("role_routing_embedding_failed", extra={"error": str(exc)})

    # Default fallback
    logger.debug("role_routing_default", extra={"task": task_text[:80]})
    return ROLES["orchestrator"]


def get_role(name: str) -> AgentRole:
    """Get a role by exact name, defaulting to orchestrator."""
    return ROLES.get(name, ROLES["orchestrator"])
