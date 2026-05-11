"""
Scheduler Worker
─────────────────
APScheduler AsyncIO scheduler wired to the FastAPI lifespan.

Supports three trigger types:
  cron      – standard cron expression ({"minute": "*/5", "hour": "9", …})
  interval  – every N seconds           ({"seconds": 3600})
  date      – one-shot at a UTC datetime ({"run_date": "2025-01-01T09:00:00"})

Actions:
  chat_prompt   – send a message to JARVIS and store the response in memory
  skill_call    – call a stored skill with given params
  http_request  – perform an outbound HTTP GET/POST

Task state is persisted in SQLite so schedules survive restarts.
"""
from __future__ import annotations

import json
import time
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.logging import get_logger
from app.db.models import ScheduledTask

logger = get_logger(__name__)


class SchedulerWorker:
    _instance: "SchedulerWorker | None" = None

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._scheduler = AsyncIOScheduler(timezone="UTC")
        self._loaded: set[str] = set()

    # ─── Lifecycle ────────────────────────────────────────────────────────────

    @classmethod
    def initialize(cls, session_factory: async_sessionmaker[AsyncSession]) -> "SchedulerWorker":
        cls._instance = cls(session_factory)
        return cls._instance

    @classmethod
    def get(cls) -> "SchedulerWorker":
        if cls._instance is None:
            raise RuntimeError("SchedulerWorker not initialised")
        return cls._instance

    async def start(self) -> None:
        """Start the APScheduler and reload all enabled tasks from DB."""
        self._scheduler.start()
        await self._reload_all()
        logger.info("scheduler_started", jobs=len(self._loaded))

    async def stop(self) -> None:
        self._scheduler.shutdown(wait=False)
        logger.info("scheduler_stopped")

    # ─── CRUD ─────────────────────────────────────────────────────────────────

    async def add_task(self, task_dict: dict[str, Any]) -> dict[str, Any]:
        async with self._session_factory() as db:
            row = ScheduledTask(
                task_id=task_dict["task_id"],
                name=task_dict["name"],
                description=task_dict.get("description", ""),
                trigger_type=task_dict["trigger_type"],
                trigger_config=json.dumps(task_dict["trigger_config"]),
                action_json=json.dumps(task_dict["action"]),
                enabled=task_dict.get("enabled", True),
                status="pending",
                created_at=time.time(),
            )
            db.add(row)
            await db.commit()
        self._schedule_job(task_dict["task_id"], task_dict["trigger_type"],
                           task_dict["trigger_config"], task_dict["action"])
        return task_dict

    async def remove_task(self, task_id: str) -> bool:
        async with self._session_factory() as db:
            result = await db.execute(select(ScheduledTask).where(ScheduledTask.task_id == task_id))
            row = result.scalar_one_or_none()
            if row is None:
                return False
            await db.delete(row)
            await db.commit()
        if self._scheduler.get_job(task_id):
            self._scheduler.remove_job(task_id)
        self._loaded.discard(task_id)
        return True

    async def pause_task(self, task_id: str) -> bool:
        job = self._scheduler.get_job(task_id)
        if job:
            job.pause()
        async with self._session_factory() as db:
            result = await db.execute(select(ScheduledTask).where(ScheduledTask.task_id == task_id))
            row = result.scalar_one_or_none()
            if row:
                row.status = "paused"
                row.enabled = False
                await db.commit()
        return True

    async def resume_task(self, task_id: str) -> bool:
        job = self._scheduler.get_job(task_id)
        if job:
            job.resume()
        async with self._session_factory() as db:
            result = await db.execute(select(ScheduledTask).where(ScheduledTask.task_id == task_id))
            row = result.scalar_one_or_none()
            if row:
                row.status = "pending"
                row.enabled = True
                await db.commit()
        return True

    async def list_tasks(self) -> list[dict[str, Any]]:
        async with self._session_factory() as db:
            result = await db.execute(
                select(ScheduledTask).order_by(ScheduledTask.created_at.desc())
            )
            return [_task_to_dict(r) for r in result.scalars().all()]

    # ─── Internal ─────────────────────────────────────────────────────────────

    async def _reload_all(self) -> None:
        async with self._session_factory() as db:
            result = await db.execute(
                select(ScheduledTask).where(ScheduledTask.enabled.is_(True))
            )
            for row in result.scalars().all():
                try:
                    trigger_config = json.loads(row.trigger_config)
                    action = json.loads(row.action_json)
                    self._schedule_job(row.task_id, row.trigger_type, trigger_config, action)
                except Exception as exc:
                    logger.warning("scheduler_reload_failed", task_id=row.task_id, error=str(exc))

    def _schedule_job(
        self,
        task_id: str,
        trigger_type: str,
        trigger_config: dict,
        action: dict,
    ) -> None:
        if task_id in self._loaded:
            return

        trigger = self._build_trigger(trigger_type, trigger_config)
        self._scheduler.add_job(
            self._execute_task,
            trigger=trigger,
            id=task_id,
            args=[task_id, action],
            replace_existing=True,
            misfire_grace_time=120,
        )
        self._loaded.add(task_id)
        logger.debug("scheduler_job_added", task_id=task_id, trigger_type=trigger_type)

    @staticmethod
    def _build_trigger(trigger_type: str, config: dict):
        if trigger_type == "cron":
            return CronTrigger(**config)
        elif trigger_type == "interval":
            return IntervalTrigger(**config)
        elif trigger_type == "date":
            return DateTrigger(**config)
        else:
            raise ValueError(f"Unknown trigger type: {trigger_type}")

    async def _execute_task(self, task_id: str, action: dict) -> None:
        logger.info("scheduler_task_run", task_id=task_id, action_type=action.get("type"))
        result_data: dict[str, Any] = {}
        status = "done"

        try:
            result_data = await self._dispatch_action(action)
        except Exception as exc:
            logger.error("scheduler_task_failed", task_id=task_id, error=str(exc))
            result_data = {"error": str(exc)}
            status = "failed"

        # Update run metadata
        async with self._session_factory() as db:
            res = await db.execute(select(ScheduledTask).where(ScheduledTask.task_id == task_id))
            row = res.scalar_one_or_none()
            if row:
                row.run_count += 1
                row.last_run_at = time.time()
                row.status = status
                row.last_result_json = json.dumps(result_data)[:4096]
                await db.commit()

    async def _dispatch_action(self, action: dict) -> dict[str, Any]:
        action_type = action.get("type", "")

        if action_type == "chat_prompt":
            return await self._action_chat(action)

        if action_type == "skill_call":
            return await self._action_skill(action)

        if action_type == "http_request":
            return await self._action_http(action)

        return {"note": f"Unknown action type: {action_type}"}

    async def _action_chat(self, action: dict) -> dict[str, Any]:
        from app.providers.router import ProviderRouter

        pr = ProviderRouter.get()
        provider = pr.get_active_provider()
        if provider is None:
            return {"error": "No provider available"}

        prompt = action.get("prompt", "Provide a status update.")
        result = await provider.chat(
            messages=[{"role": "user", "content": prompt}],
            model_id="",
            max_tokens=512,
        )
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")

        # Store in memory
        async with self._session_factory() as db:
            from app.services import memory_service
            await memory_service.store(
                db,
                content=f"[Scheduled] {prompt}\n\nResponse: {content}",
                metadata={"source": "scheduler", "prompt": prompt[:100]},
                memory_type="episodic",
                importance=0.3,
            )
        return {"response": content[:500]}

    async def _action_skill(self, action: dict) -> dict[str, Any]:
        async with self._session_factory() as db:
            from app.services import skill_service
            return await skill_service.execute(
                db,
                skill_id=action.get("skill_id", ""),
                params=action.get("params", {}),
            )

    @staticmethod
    async def _action_http(action: dict) -> dict[str, Any]:
        import httpx

        method = action.get("method", "GET").upper()
        url = action.get("url", "")
        headers = action.get("headers", {})
        body = action.get("body")

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.request(method, url, headers=headers, json=body)
            return {"status_code": resp.status_code, "body": resp.text[:2000]}


# ─── Serialiser ───────────────────────────────────────────────────────────────

def _task_to_dict(row: ScheduledTask) -> dict[str, Any]:
    try:
        trigger_config = json.loads(row.trigger_config)
    except Exception:
        trigger_config = {}
    try:
        action = json.loads(row.action_json)
    except Exception:
        action = {}
    try:
        last_result = json.loads(row.last_result_json)
    except Exception:
        last_result = {}
    return {
        "taskId": row.task_id,
        "name": row.name,
        "description": row.description,
        "triggerType": row.trigger_type,
        "triggerConfig": trigger_config,
        "action": action,
        "enabled": row.enabled,
        "status": row.status,
        "runCount": row.run_count,
        "lastRunAt": row.last_run_at,
        "nextRunAt": row.next_run_at,
        "lastResult": last_result,
        "createdAt": row.created_at,
    }
