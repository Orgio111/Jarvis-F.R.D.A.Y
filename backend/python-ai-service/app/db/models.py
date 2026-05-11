"""
SQLAlchemy ORM models.

Four domains:
  MemoryEntry  – every stored memory chunk (episodic + semantic)
  UserProfile  – single growing JSON document per user
  Skill        – LLM-generated reusable callable
  ScheduledTask– cron / one-shot background jobs
"""
from __future__ import annotations

import time
from typing import Any

from sqlalchemy import Boolean, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


# ─── Memory ───────────────────────────────────────────────────────────────────

class MemoryEntry(Base):
    __tablename__ = "memory_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # JSON blob: {"session_id": "…", "role": "user"|"assistant", "tags": […], …}
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    memory_type: Mapped[str] = mapped_column(String(32), default="episodic")
    # FAISS vector index position (populated after embedding)
    faiss_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    importance: Mapped[float] = mapped_column(Float, default=0.5)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)
    last_accessed: Mapped[float] = mapped_column(Float, default=time.time)
    access_count: Mapped[int] = mapped_column(Integer, default=0)


# ─── User Profile ─────────────────────────────────────────────────────────────

class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    # Full profile as JSON: preferences, goals, habits, personality signals
    profile_json: Mapped[str] = mapped_column(Text, default="{}")
    # Lightweight counters
    total_interactions: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)
    updated_at: Mapped[float] = mapped_column(Float, default=time.time)


# ─── Skills ───────────────────────────────────────────────────────────────────

class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    skill_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    # The Python source code of the skill function
    source_code: Mapped[str] = mapped_column(Text, nullable=False)
    # JSON array of {"name": str, "type": str, "required": bool, "description": str}
    parameters_json: Mapped[str] = mapped_column(Text, default="[]")
    version: Mapped[int] = mapped_column(Integer, default=1)
    category: Mapped[str] = mapped_column(String(64), default="general")
    # Origin: "user", "generated", "builtin"
    origin: Mapped[str] = mapped_column(String(32), default="generated")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    # Aggregate quality score 0.0–1.0 updated after each execution
    quality_score: Mapped[float] = mapped_column(Float, default=0.5)
    execution_count: Mapped[int] = mapped_column(Integer, default=0)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)
    updated_at: Mapped[float] = mapped_column(Float, default=time.time)


# ─── Scheduled Tasks ──────────────────────────────────────────────────────────

class ScheduledTask(Base):
    __tablename__ = "scheduled_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    # "cron" | "interval" | "date" (one-shot)
    trigger_type: Mapped[str] = mapped_column(String(16), nullable=False)
    # Serialised trigger config JSON (cron fields, interval seconds, run_date)
    trigger_config: Mapped[str] = mapped_column(Text, nullable=False)
    # What to do: {"type": "chat_prompt"|"skill_call"|"http_request", …}
    action_json: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    # "pending" | "running" | "done" | "failed" | "paused"
    status: Mapped[str] = mapped_column(String(16), default="pending")
    run_count: Mapped[int] = mapped_column(Integer, default=0)
    last_run_at: Mapped[float | None] = mapped_column(Float, nullable=True)
    next_run_at: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_result_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[float] = mapped_column(Float, default=time.time)
