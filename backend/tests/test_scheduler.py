from datetime import datetime
from zoneinfo import ZoneInfo

from app.services.scheduler import next_sync_time


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
