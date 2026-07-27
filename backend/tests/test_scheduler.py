from datetime import datetime
from zoneinfo import ZoneInfo

from app.services.scheduler import is_us_equity_trading_day, next_sync_time


def test_next_sync_time_uses_weekday_chicago_schedule() -> None:
    timezone = ZoneInfo("America/Chicago")
    friday_before_close = datetime(2026, 7, 10, 14, 0, tzinfo=timezone)
    friday_after_close = datetime(2026, 7, 10, 16, 0, tzinfo=timezone)

    assert next_sync_time(friday_before_close) == datetime(
        2026, 7, 10, 15, 0, tzinfo=timezone
    )
    assert next_sync_time(friday_after_close) == datetime(
        2026, 7, 13, 15, 0, tzinfo=timezone
    )


def test_next_sync_time_skips_us_market_holidays() -> None:
    timezone = ZoneInfo("America/Chicago")
    before_independence_observed = datetime(2026, 7, 2, 16, 0, tzinfo=timezone)
    before_thanksgiving = datetime(2026, 11, 25, 16, 0, tzinfo=timezone)

    assert is_us_equity_trading_day(datetime(2026, 7, 3).date()) is False
    assert next_sync_time(before_independence_observed) == datetime(
        2026, 7, 6, 15, 0, tzinfo=timezone
    )
    assert next_sync_time(before_thanksgiving) == datetime(
        2026, 11, 27, 15, 0, tzinfo=timezone
    )
