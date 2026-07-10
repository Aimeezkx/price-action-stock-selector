from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import asdict
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from .config import get_settings
from .database import SessionLocal, create_tables, get_db
from .models import (
    BacktestRun,
    DailyBar,
    MarketSymbol,
    PriceActionRule,
    ScanJob,
    ScanResult,
    Watchlist,
)
from .knowledge import local_knowledge_sources
from .price_action import analyze_rule
from .schemas import (
    BacktestRequest,
    RuleTestRequest,
    RuleUpdate,
    ScanRequest,
    SymbolCreate,
    SyncRequest,
)
from .seed import seed_demo_market, seed_rules
from .services.backtest import run_backtest
from .services.ibkr import ibkr_service
from .services.market_data import sync_symbol_daily
from .services.scheduler import market_scheduler
from .services.scanner import rule_to_dict, run_scan
from .universe import (
    UNIVERSE_NAME,
    load_sp500_top300,
    seed_sp500_top300,
    sp500_holding_lookup,
)


settings = get_settings()


def model_dict(item: Any, fields: list[str]) -> dict[str, Any]:
    result = {}
    for field in fields:
        value = getattr(item, field)
        result[field] = value.isoformat() if hasattr(value, "isoformat") else value
    return result


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_tables()
    with SessionLocal() as db:
        seed_rules(db)
        if settings.seed_demo_data:
            seed_demo_market(db)
        seed_sp500_top300(db)
    market_scheduler.start()
    try:
        yield
    finally:
        await market_scheduler.stop()
        ibkr_service.disconnect()


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Daily price-action scanning, IBKR historical data, explanations and backtesting.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict:
    return {"name": settings.app_name, "version": "1.0.0", "docs": "/docs"}


@app.get("/api/health")
def health(db: Session = Depends(get_db)) -> dict:
    return {
        "status": "healthy",
        "database": db.scalar(select(func.count(MarketSymbol.id))) is not None,
    }


@app.get("/api/dashboard")
def dashboard(db: Session = Depends(get_db)) -> dict:
    latest_job = db.scalar(select(ScanJob).order_by(desc(ScanJob.id)).limit(1))
    result_count = db.scalar(select(func.count(ScanResult.id))) or 0
    high_score_count = (
        db.scalar(select(func.count(ScanResult.id)).where(ScanResult.score >= 80)) or 0
    )
    latest_result_query = select(ScanResult)
    if latest_job is not None:
        latest_result_query = latest_result_query.where(ScanResult.scan_job_id == latest_job.id)
    latest_results = sorted(
        db.scalars(latest_result_query).all(), key=scan_result_sort_key
    )[:6]
    return {
        "symbol_count": db.scalar(
            select(func.count(MarketSymbol.id)).where(MarketSymbol.enabled.is_(True))
        ) or 0,
        "active_rule_count": db.scalar(
            select(func.count(PriceActionRule.id)).where(PriceActionRule.enabled.is_(True))
        )
        or 0,
        "signal_count": result_count,
        "high_score_count": high_score_count,
        "latest_job": model_dict(latest_job, ["id", "status", "completed_at"])
        if latest_job
        else None,
        "top_results": [serialize_result(item) for item in latest_results],
        "ibkr": asdict(ibkr_service.status()),
        "sync": market_scheduler.status(),
    }


@app.get("/api/market/ibkr/status")
def ibkr_status() -> dict:
    return asdict(ibkr_service.status())


@app.post("/api/market/ibkr/connect")
async def ibkr_connect() -> dict:
    return asdict(await ibkr_service.connect())


@app.post("/api/market/symbols", status_code=201)
def add_symbol(payload: SymbolCreate, db: Session = Depends(get_db)) -> dict:
    symbol = payload.symbol.strip().upper()
    existing = db.scalar(select(MarketSymbol).where(MarketSymbol.symbol == symbol))
    if existing:
        raise HTTPException(409, "Symbol already exists")
    item = MarketSymbol(
        symbol=symbol,
        name=payload.name,
        exchange=payload.exchange,
        currency=payload.currency,
        sector=payload.sector,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return serialize_symbol(item)


@app.get("/api/market/symbols")
def list_symbols(db: Session = Depends(get_db)) -> list[dict]:
    return [
        serialize_symbol(item)
        for item in db.scalars(
            select(MarketSymbol)
            .where(MarketSymbol.enabled.is_(True))
            .order_by(MarketSymbol.symbol)
        ).all()
    ]


@app.get("/api/market/universe/sp500-top300")
def sp500_top300_universe(db: Session = Depends(get_db)) -> dict:
    payload = load_sp500_top300()
    symbols = [item["symbol"] for item in payload["symbols"]]
    registered = db.scalar(
        select(func.count(MarketSymbol.id)).where(MarketSymbol.symbol.in_(symbols))
    ) or 0
    with_data = db.scalar(
        select(func.count(func.distinct(DailyBar.market_symbol_id)))
        .join(MarketSymbol, DailyBar.market_symbol_id == MarketSymbol.id)
        .where(MarketSymbol.symbol.in_(symbols))
    ) or 0
    return {
        **payload,
        "registered_count": registered,
        "with_data_count": with_data,
        "watchlist": UNIVERSE_NAME,
    }


@app.get("/api/market/data/sync-status")
def scheduled_sync_status() -> dict:
    return market_scheduler.status()


@app.post("/api/market/data/sync-scheduled", status_code=202)
async def trigger_scheduled_sync() -> dict:
    accepted = await market_scheduler.trigger()
    return {"accepted": accepted, **market_scheduler.status()}


@app.post("/api/market/data/sync-daily")
async def sync_daily(payload: SyncRequest, db: Session = Depends(get_db)) -> dict:
    summary: list[dict] = []
    for raw_symbol in payload.symbols:
        ticker = raw_symbol.strip().upper()
        try:
            summary.append(
                await sync_symbol_daily(
                    db,
                    ticker,
                    payload.duration,
                    payload.use_rth,
                    settings.market_bar_retention,
                )
            )
        except Exception as exc:
            db.rollback()
            summary.append({"symbol": ticker, "status": "failed", "error": str(exc)})
    return {"results": summary}


@app.get("/api/market/data/daily/{symbol}")
def daily_bars(
    symbol: str, limit: int = Query(default=300, ge=45, le=2000), db: Session = Depends(get_db)
) -> dict:
    market_symbol = db.scalar(select(MarketSymbol).where(MarketSymbol.symbol == symbol.upper()))
    if not market_symbol:
        raise HTTPException(404, "Symbol not found")
    rows = list(
        db.scalars(
            select(DailyBar)
            .where(DailyBar.market_symbol_id == market_symbol.id)
            .order_by(desc(DailyBar.bar_date))
            .limit(limit)
        ).all()
    )
    rows.reverse()
    return {
        "symbol": serialize_symbol(market_symbol),
        "bars": [
            model_dict(item, ["bar_date", "open", "high", "low", "close", "volume", "source"])
            for item in rows
        ],
    }


@app.get("/api/watchlists")
def watchlists(db: Session = Depends(get_db)) -> list[dict]:
    return [
        model_dict(item, ["id", "name", "symbols", "created_at"])
        for item in db.scalars(select(Watchlist).order_by(Watchlist.name)).all()
    ]


@app.post("/api/scanner/jobs", status_code=201)
def create_scan(payload: ScanRequest, db: Session = Depends(get_db)) -> dict:
    job = ScanJob(
        symbols=[item.upper() for item in payload.symbols],
        rule_ids=payload.rule_ids,
        min_score=payload.min_score,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    run_scan(db, job)
    return serialize_job(job)


@app.get("/api/scanner/jobs/{job_id}")
def get_scan_job(job_id: int, db: Session = Depends(get_db)) -> dict:
    job = db.get(ScanJob, job_id)
    if not job:
        raise HTTPException(404, "Scan job not found")
    result_count = (
        db.scalar(select(func.count(ScanResult.id)).where(ScanResult.scan_job_id == job.id)) or 0
    )
    return {**serialize_job(job), "result_count": result_count}


@app.get("/api/scanner/results")
def scan_results(
    job_id: int | None = None,
    symbol: str | None = None,
    min_score: float = 0,
    db: Session = Depends(get_db),
) -> list[dict]:
    query = select(ScanResult).where(ScanResult.score >= min_score)
    if job_id is not None:
        query = query.where(ScanResult.scan_job_id == job_id)
    else:
        latest_job_id = db.scalar(
            select(ScanJob.id)
            .where(ScanJob.status == "completed")
            .order_by(desc(ScanJob.id))
            .limit(1)
        )
        if latest_job_id is None:
            return []
        query = query.where(ScanResult.scan_job_id == latest_job_id)
    if symbol:
        query = query.where(ScanResult.symbol == symbol.upper())
    items = sorted(db.scalars(query).all(), key=scan_result_sort_key)[:500]
    return [serialize_result(item) for item in items]


@app.get("/api/scanner/results/{result_id}")
def scan_result_detail(result_id: int, db: Session = Depends(get_db)) -> dict:
    item = db.get(ScanResult, result_id)
    if not item:
        raise HTTPException(404, "Scan result not found")
    return serialize_result(item)


@app.get("/api/price-action/rules")
def list_rules(db: Session = Depends(get_db)) -> list[dict]:
    return [
        rule_to_dict(item)
        for item in db.scalars(
            select(PriceActionRule).order_by(PriceActionRule.category, PriceActionRule.name)
        ).all()
    ]


@app.get("/api/knowledge/sources")
def knowledge_sources() -> list[dict]:
    return local_knowledge_sources()


@app.get("/api/price-action/rules/{rule_id}")
def get_rule(rule_id: str, db: Session = Depends(get_db)) -> dict:
    rule = db.get(PriceActionRule, rule_id)
    if not rule:
        raise HTTPException(404, "Rule not found")
    return rule_to_dict(rule)


@app.patch("/api/price-action/rules/{rule_id}")
def update_rule(rule_id: str, payload: RuleUpdate, db: Session = Depends(get_db)) -> dict:
    rule = db.get(PriceActionRule, rule_id)
    if not rule:
        raise HTTPException(404, "Rule not found")
    if payload.enabled is not None:
        rule.enabled = payload.enabled
    if payload.parameters is not None:
        rule.parameters = {**rule.parameters, **payload.parameters}
    db.commit()
    return rule_to_dict(rule)


@app.post("/api/price-action/rules/{rule_id}/test")
def test_rule(rule_id: str, payload: RuleTestRequest, db: Session = Depends(get_db)) -> dict:
    rule = db.get(PriceActionRule, rule_id)
    market_symbol = db.scalar(
        select(MarketSymbol).where(MarketSymbol.symbol == payload.symbol.upper())
    )
    if not rule or not market_symbol:
        raise HTTPException(404, "Rule or symbol not found")
    bars = db.scalars(
        select(DailyBar)
        .where(DailyBar.market_symbol_id == market_symbol.id)
        .order_by(DailyBar.bar_date)
    ).all()
    return {
        "symbol": market_symbol.symbol,
        "rule": rule_to_dict(rule),
        "signal": analyze_rule(rule_to_dict(rule), list(bars)),
    }


@app.post("/api/backtests", status_code=201)
def create_backtest(payload: BacktestRequest, db: Session = Depends(get_db)) -> dict:
    rule = db.get(PriceActionRule, payload.rule_id)
    if not rule:
        raise HTTPException(404, "Rule not found")
    run = run_backtest(
        db,
        rule,
        [item.upper() for item in payload.symbols],
        payload.start_date,
        payload.end_date,
        payload.holding_days,
        payload.entry_expiry_days,
        payload.target_r,
    )
    return serialize_backtest(run)


@app.get("/api/backtests/{backtest_id}")
def get_backtest(backtest_id: int, db: Session = Depends(get_db)) -> dict:
    run = db.get(BacktestRun, backtest_id)
    if not run:
        raise HTTPException(404, "Backtest not found")
    return serialize_backtest(run)


def serialize_symbol(item: MarketSymbol) -> dict:
    return model_dict(
        item,
        [
            "id",
            "symbol",
            "name",
            "exchange",
            "currency",
            "sector",
            "enabled",
            "min_average_volume",
            "ibkr_contract_id",
            "last_synced_at",
        ],
    )


def serialize_job(item: ScanJob) -> dict:
    return model_dict(
        item,
        [
            "id",
            "status",
            "symbols",
            "rule_ids",
            "min_score",
            "error",
            "created_at",
            "started_at",
            "completed_at",
        ],
    )


def serialize_result(item: ScanResult) -> dict:
    holding = sp500_holding_lookup().get(item.symbol)
    return {
        **model_dict(
        item,
        [
            "id",
            "scan_job_id",
            "symbol",
            "signal_date",
            "rule_id",
            "rule_name",
            "score",
            "direction",
            "entry",
            "stop",
            "target",
            "risk_reward",
            "explanation",
            "annotations",
            "created_at",
        ],
        ),
        "market_cap_rank": holding["rank"] if holding else None,
        "index_weight": holding["weight"] if holding else None,
    }


def scan_result_sort_key(item: ScanResult) -> tuple[float, int, int]:
    holding = sp500_holding_lookup().get(item.symbol)
    market_cap_rank = holding["rank"] if holding else 10_000
    return (-item.score, market_cap_rank, -item.id)


def serialize_backtest(item: BacktestRun) -> dict:
    return model_dict(
        item,
        [
            "id",
            "rule_id",
            "symbols",
            "start_date",
            "end_date",
            "config",
            "metrics",
            "trades",
            "created_at",
        ],
    )
