from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import delete, desc, select
from sqlalchemy.orm import Session

from ..models import DailyBar, MarketSymbol
from .ibkr import ibkr_service


async def sync_symbol_daily(
    db: Session,
    ticker: str,
    duration: str,
    use_rth: bool = True,
    retention: int = 300,
) -> dict:
    ticker = ticker.strip().upper()
    symbol = db.scalar(select(MarketSymbol).where(MarketSymbol.symbol == ticker))
    if symbol is None:
        symbol = MarketSymbol(symbol=ticker, name=ticker)
        db.add(symbol)
        db.flush()

    contract_id, bars = await ibkr_service.fetch_daily_bars(ticker, duration, use_rth)
    symbol.ibkr_contract_id = contract_id
    removed_demo = db.execute(
        delete(DailyBar).where(
            DailyBar.market_symbol_id == symbol.id,
            DailyBar.source == "DEMO",
        )
    ).rowcount
    inserted = 0
    for bar in bars:
        existing = db.scalar(
            select(DailyBar).where(
                DailyBar.market_symbol_id == symbol.id,
                DailyBar.bar_date == bar["date"],
            )
        )
        if existing:
            for field in ("open", "high", "low", "close", "volume"):
                setattr(existing, field, bar[field])
            existing.source = "IBKR"
        else:
            db.add(
                DailyBar(
                    market_symbol_id=symbol.id,
                    bar_date=bar["date"],
                    source="IBKR",
                    **{key: bar[key] for key in ("open", "high", "low", "close", "volume")},
                )
            )
            inserted += 1

    db.flush()
    ordered_ids = list(
        db.scalars(
            select(DailyBar.id)
            .where(DailyBar.market_symbol_id == symbol.id)
            .order_by(desc(DailyBar.bar_date), desc(DailyBar.id))
        ).all()
    )
    stale_ids = ordered_ids[retention:]
    if stale_ids:
        db.execute(delete(DailyBar).where(DailyBar.id.in_(stale_ids)))
    symbol.last_synced_at = datetime.now(timezone.utc)
    db.commit()
    return {
        "symbol": ticker,
        "status": "ok",
        "received": len(bars),
        "inserted": inserted,
        "removed_demo": removed_demo,
        "pruned": len(stale_ids),
        "retained": min(len(ordered_ids), retention),
    }
