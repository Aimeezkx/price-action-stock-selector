from __future__ import annotations

import math
import random
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .knowledge import RULE_DEFINITIONS
from .models import DailyBar, MarketSymbol, PriceActionRule, Watchlist


DEMO_SYMBOLS = [
    ("AAPL", "Apple", "Technology", 182.0),
    ("MSFT", "Microsoft", "Technology", 418.0),
    ("NVDA", "NVIDIA", "Technology", 152.0),
    ("AMZN", "Amazon", "Consumer Cyclical", 221.0),
    ("META", "Meta Platforms", "Communication", 627.0),
    ("TSLA", "Tesla", "Consumer Cyclical", 318.0),
]


def seed_rules(db: Session) -> None:
    for definition in RULE_DEFINITIONS:
        existing = db.get(PriceActionRule, definition["id"])
        if existing:
            existing.name = definition["name"]
            existing.category = definition["category"]
            existing.description = definition["description"]
            existing.direction = definition["direction"]
            existing.source_references = definition["source_references"]
            continue
        db.add(PriceActionRule(**definition))
    db.commit()


def _trading_dates(count: int) -> list[date]:
    cursor = date.today() - timedelta(days=count * 2)
    dates: list[date] = []
    while len(dates) < count:
        if cursor.weekday() < 5:
            dates.append(cursor)
        cursor += timedelta(days=1)
    return dates


def seed_demo_market(db: Session) -> None:
    if db.scalar(select(MarketSymbol.id).limit(1)) is not None:
        return
    dates = _trading_dates(280)
    for symbol_index, (ticker, name, sector, initial) in enumerate(DEMO_SYMBOLS):
        market_symbol = MarketSymbol(
            symbol=ticker, name=name, sector=sector, last_synced_at=datetime.now(timezone.utc)
        )
        db.add(market_symbol)
        db.flush()
        rng = random.Random(20260 + symbol_index)
        price = initial * 0.72
        for index, bar_date in enumerate(dates):
            drift = 0.0010 + math.sin(index / 22 + symbol_index) * 0.0014
            shock = rng.gauss(0, 0.012)
            if index > 260:
                drift += 0.003 + symbol_index * 0.0002
            open_price = price * (1 + rng.gauss(0, 0.004))
            close = max(5, price * (1 + drift + shock))
            spread = abs(rng.gauss(0.012, 0.004))
            high = max(open_price, close) * (1 + spread)
            low = min(open_price, close) * (1 - spread * 0.85)
            volume = 18_000_000 * (1 + rng.random() * 1.6)
            if index == len(dates) - 1 and ticker in {"AAPL", "NVDA", "META"}:
                close = max(close, max(open_price, price) * 1.035)
                high = close * 1.008
                low = min(open_price, price) * 0.995
                volume *= 2.1
            db.add(
                DailyBar(
                    market_symbol_id=market_symbol.id,
                    bar_date=bar_date,
                    open=round(open_price, 2),
                    high=round(high, 2),
                    low=round(low, 2),
                    close=round(close, 2),
                    volume=round(volume),
                    source="DEMO",
                )
            )
            price = close
    db.add(Watchlist(name="MVP Watchlist", symbols=[item[0] for item in DEMO_SYMBOLS]))
    db.commit()
