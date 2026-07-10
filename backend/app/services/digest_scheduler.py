from __future__ import annotations

import asyncio
from contextlib import suppress
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select

from ..config import get_settings
from ..database import SessionLocal
from ..models import ScanJob, ScanResult
from .email_digest import email_digest_service
from .scanner import run_scan, scan_result_sort_key
from .scheduler import next_sync_time


class DailyDigestScheduler:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.timezone = ZoneInfo(self.settings.market_sync_timezone)
        self._loop_task: asyncio.Task | None = None
        self._run_task: asyncio.Task | None = None
        self.next_run_at: datetime | None = None
        self.last_started_at: datetime | None = None
        self.last_finished_at: datetime | None = None
        self.last_error: str | None = None
        self.last_job_id: int | None = None
        self.last_candidate_count = 0

    def start(self) -> None:
        if self.settings.email_digest_enabled and self._loop_task is None:
            self._loop_task = asyncio.create_task(self._loop(), name="daily-email-digest-scheduler")

    async def stop(self) -> None:
        for task in (self._loop_task, self._run_task):
            if task and not task.done():
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task
        self._loop_task = self._run_task = None

    async def _loop(self) -> None:
        while True:
            now = datetime.now(self.timezone)
            self.next_run_at = next_sync_time(
                now,
                self.settings.email_digest_hour,
                self.settings.email_digest_minute,
            )
            await asyncio.sleep((self.next_run_at - now).total_seconds())
            await self.trigger(wait=True)

    async def trigger(self, wait: bool = False) -> bool:
        if self._run_task and not self._run_task.done():
            return False
        self._run_task = asyncio.create_task(asyncio.to_thread(self._build_and_send))
        if wait:
            await self._run_task
        return True

    def _build_and_send(self) -> None:
        self.last_started_at = datetime.now(timezone.utc)
        self.last_finished_at = None
        self.last_error = None
        try:
            with SessionLocal() as db:
                job = ScanJob(
                    symbols=[],
                    rule_ids=[],
                    min_score=self.settings.email_digest_min_score,
                )
                db.add(job)
                db.commit()
                db.refresh(job)
                run_scan(db, job, self.settings.email_digest_target_r)
                candidates = sorted(
                    db.scalars(
                        select(ScanResult).where(ScanResult.scan_job_id == job.id)
                    ).all(),
                    key=scan_result_sort_key,
                )
                unique_results: list[ScanResult] = []
                seen_symbols: set[str] = set()
                for candidate in candidates:
                    if candidate.symbol in seen_symbols:
                        continue
                    unique_results.append(candidate)
                    seen_symbols.add(candidate.symbol)
                    if len(unique_results) == 20:
                        break
                self.last_job_id = job.id
                self.last_candidate_count = len(unique_results)
                email_digest_service.send(unique_results)
        except Exception as exc:
            self.last_error = str(exc)
        finally:
            self.last_finished_at = datetime.now(timezone.utc)

    def status(self) -> dict:
        return {
            "enabled": self.settings.email_digest_enabled,
            "configured": email_digest_service.configured,
            "running": bool(self._run_task and not self._run_task.done()),
            "timezone": self.settings.market_sync_timezone,
            "daily_time": f"{self.settings.email_digest_hour:02d}:{self.settings.email_digest_minute:02d}",
            "recipient": self.settings.email_digest_recipient,
            "next_run_at": self.next_run_at.isoformat() if self.next_run_at else None,
            "last_started_at": self.last_started_at.isoformat() if self.last_started_at else None,
            "last_finished_at": self.last_finished_at.isoformat() if self.last_finished_at else None,
            "last_error": self.last_error,
            "last_job_id": self.last_job_id,
            "last_candidate_count": self.last_candidate_count,
        }


digest_scheduler = DailyDigestScheduler()
