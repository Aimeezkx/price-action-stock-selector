from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MarketSymbol(Base):
    __tablename__ = "market_symbols"

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160), default="")
    exchange: Mapped[str] = mapped_column(String(32), default="SMART")
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    ibkr_contract_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sector: Mapped[str | None] = mapped_column(String(80), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    min_average_volume: Mapped[float] = mapped_column(Float, default=500_000)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    bars: Mapped[list[DailyBar]] = relationship(
        back_populates="market_symbol", cascade="all, delete-orphan"
    )


class DailyBar(Base):
    __tablename__ = "daily_bars"
    __table_args__ = (UniqueConstraint("market_symbol_id", "bar_date", name="uq_symbol_bar_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    market_symbol_id: Mapped[int] = mapped_column(
        ForeignKey("market_symbols.id", ondelete="CASCADE"), index=True
    )
    bar_date: Mapped[date] = mapped_column(Date, index=True)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(24), default="IBKR")
    adjusted: Mapped[bool] = mapped_column(Boolean, default=False)

    market_symbol: Mapped[MarketSymbol] = relationship(back_populates="bars")


class PriceActionRule(Base):
    __tablename__ = "price_action_rules"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(48), index=True)
    description: Mapped[str] = mapped_column(Text)
    direction: Mapped[str] = mapped_column(String(16), default="long")
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    source_references: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class ScanJob(Base):
    __tablename__ = "scan_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[str] = mapped_column(String(24), default="queued", index=True)
    symbols: Mapped[list[str]] = mapped_column(JSON, default=list)
    rule_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    min_score: Mapped[float] = mapped_column(Float, default=60)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ScanResult(Base):
    __tablename__ = "scan_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    scan_job_id: Mapped[int] = mapped_column(
        ForeignKey("scan_jobs.id", ondelete="CASCADE"), index=True
    )
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    signal_date: Mapped[date] = mapped_column(Date, index=True)
    rule_id: Mapped[str] = mapped_column(String(64), index=True)
    rule_name: Mapped[str] = mapped_column(String(120))
    score: Mapped[float] = mapped_column(Float, index=True)
    direction: Mapped[str] = mapped_column(String(16))
    entry: Mapped[float] = mapped_column(Float)
    stop: Mapped[float] = mapped_column(Float)
    target: Mapped[float] = mapped_column(Float)
    risk_reward: Mapped[float] = mapped_column(Float)
    explanation: Mapped[list[str]] = mapped_column(JSON, default=list)
    annotations: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Watchlist(Base):
    __tablename__ = "watchlists"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    symbols: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class BacktestRun(Base):
    __tablename__ = "backtest_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    rule_id: Mapped[str] = mapped_column(String(64), index=True)
    symbols: Mapped[list[str]] = mapped_column(JSON, default=list)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    trades: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
