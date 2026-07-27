from __future__ import annotations

import asyncio
from contextlib import suppress
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, select

from ..config import get_settings
from ..database import SessionLocal
from ..models import DailyBar, MarketSymbol, Watchlist
from ..universe import UNIVERSE_NAME
from .ibkr import ibkr_service
from .market_data import sync_symbol_daily


def _observed(day: date) -> date:
    if day.weekday() == 5:
        return day - timedelta(days=1)
    if day.weekday() == 6:
        return day + timedelta(days=1)
    return day


def _nth_weekday(year: int, month: int, weekday: int, occurrence: int) -> date:
    day = date(year, month, 1)
    offset = (weekday - day.weekday()) % 7
    return day + timedelta(days=offset + 7 * (occurrence - 1))


def _last_weekday(year: int, month: int, weekday: int) -> date:
    next_month = date(year + (month == 12), month % 12 + 1, 1)
    day = next_month - timedelta(days=1)
    return day - timedelta(days=(day.weekday() - weekday) % 7)


def _easter_sunday(year: int) -> date:
    """Gregorian computus, used to derive the NYSE Good Friday closure."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    ell = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * ell) // 451
    month = (h + ell - 7 * m + 114) // 31
    day = (h + ell - 7 * m + 114) % 31 + 1
    return date(year, month, day)


def us_equity_market_holidays(year: int) -> set[date]:
    holidays = {
        _observed(date(year, 1, 1)),
        _nth_weekday(year, 1, 0, 3),  # Martin Luther King Jr. Day
        _nth_weekday(year, 2, 0, 3),  # Washington's Birthday
        _easter_sunday(year) - timedelta(days=2),
        _last_weekday(year, 5, 0),  # Memorial Day
        _observed(date(year, 7, 4)),
        _nth_weekday(year, 9, 0, 1),  # Labor Day
        _nth_weekday(year, 11, 3, 4),  # Thanksgiving
        _observed(date(year, 12, 25)),
    }
    if year >= 2022:
        holidays.add(_observed(date(year, 6, 19)))
    return holidays


def is_us_equity_trading_day(day: date) -> bool:
    if day.weekday() >= 5:
        return False
    holidays = set().union(
        us_equity_market_holidays(day.year - 1),
        us_equity_market_holidays(day.year),
        us_equity_market_holidays(day.year + 1),
    )
    return day not in holidays


def next_sync_time(now: datetime, hour: int = 15, minute: int = 0) -> datetime:
    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= now:
        candidate += timedelta(days=1)
    while not is_us_equity_trading_day(candidate.date()):
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
            "trading_days_only": True,
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
