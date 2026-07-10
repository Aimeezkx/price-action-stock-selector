from __future__ import annotations

import asyncio
from contextlib import suppress
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, select

from ..config import get_settings
from ..database import SessionLocal
from ..models import DailyBar, MarketSymbol, Watchlist
from ..universe import UNIVERSE_NAME
from .ibkr import ibkr_service
from .market_data import sync_symbol_daily


def next_sync_time(now: datetime, hour: int = 15, minute: int = 0) -> datetime:
    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= now:
        candidate += timedelta(days=1)
    while candidate.weekday() >= 5:
        candidate += timedelta(days=1)
    return candidate


class DailyMarketScheduler:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.timezone = ZoneInfo(self.settings.market_sync_timezone)
        self._loop_task: asyncio.Task | None = None
        self._run_task: asyncio.Task | None = None
        self.next_run_at: datetime | None = None
        self.last_started_at: datetime | None = None
        self.last_finished_at: datetime | None = None
        self.last_error: str | None = None
        self.processed = 0
        self.total = 0
        self.succeeded = 0
        self.failed = 0

    def start(self) -> None:
        if self.settings.market_sync_enabled and self._loop_task is None:
            self._loop_task = asyncio.create_task(self._loop(), name="daily-market-sync-scheduler")

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
                self.settings.market_sync_hour,
                self.settings.market_sync_minute,
            )
            await asyncio.sleep((self.next_run_at - now).total_seconds())
            await self.trigger(wait=True)

    async def trigger(self, wait: bool = False) -> bool:
        if self._run_task and not self._run_task.done():
            return False
        self._run_task = asyncio.create_task(self._run(), name="daily-market-sync-run")
        if wait:
            await self._run_task
        return True

    async def _run(self) -> None:
        self.last_started_at = datetime.now(timezone.utc)
        self.last_finished_at = None
        self.last_error = None
        self.processed = self.succeeded = self.failed = 0
        try:
            status = await ibkr_service.connect()
            if not status.connected:
                raise ConnectionError(status.message)
            with SessionLocal() as db:
                watchlist = db.scalar(select(Watchlist).where(Watchlist.name == UNIVERSE_NAME))
                symbols = list(watchlist.symbols if watchlist else [])
            self.total = len(symbols)
            for ticker in symbols:
                try:
                    with SessionLocal() as db:
                        market_symbol = db.scalar(
                            select(MarketSymbol).where(MarketSymbol.symbol == ticker)
                        )
                        count = (
                            db.scalar(
                                select(func.count(DailyBar.id)).where(
                                    DailyBar.market_symbol_id == market_symbol.id
                                )
                            )
                            if market_symbol
                            else 0
                        ) or 0
                        duration = "2 Y" if count < self.settings.market_bar_retention else "10 D"
                        await sync_symbol_daily(
                            db,
                            ticker,
                            duration,
                            retention=self.settings.market_bar_retention,
                        )
                    self.succeeded += 1
                except Exception:
                    self.failed += 1
                finally:
                    self.processed += 1
        except Exception as exc:
            self.last_error = str(exc)
        finally:
            self.last_finished_at = datetime.now(timezone.utc)

    def status(self) -> dict:
        running = bool(self._run_task and not self._run_task.done())
        return {
            "enabled": self.settings.market_sync_enabled,
            "running": running,
            "timezone": self.settings.market_sync_timezone,
            "daily_time": f"{self.settings.market_sync_hour:02d}:{self.settings.market_sync_minute:02d}",
            "weekdays_only": True,
            "retention_trading_days": self.settings.market_bar_retention,
            "next_run_at": self.next_run_at.isoformat() if self.next_run_at else None,
            "last_started_at": self.last_started_at.isoformat() if self.last_started_at else None,
            "last_finished_at": self.last_finished_at.isoformat() if self.last_finished_at else None,
            "last_error": self.last_error,
            "processed": self.processed,
            "total": self.total,
            "succeeded": self.succeeded,
            "failed": self.failed,
        }


market_scheduler = DailyMarketScheduler()
