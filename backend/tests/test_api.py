import os
from datetime import date, timedelta

os.environ["DATABASE_URL"] = "sqlite:///./test_price_action.db"
os.environ["SEED_DEMO_DATA"] = "true"

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.database import SessionLocal
from app.main import app
from app.models import DailyBar, MarketSymbol
from app.services.ibkr import ibkr_service


def test_mvp_flow() -> None:
    with TestClient(app) as client:
        assert client.get("/api/health").status_code == 200
        rules = client.get("/api/price-action/rules").json()
        assert len(rules) == 8
        sources = client.get("/api/knowledge/sources").json()
        assert len(sources) == 5
        assert sum(source["pages"] for source in sources) == 7226
        assert all(source["redistributed"] is False for source in sources)
        symbols = client.get("/api/market/symbols").json()
        assert len(symbols) >= 300
        universe = client.get("/api/market/universe/sp500-top300").json()
        assert universe["count"] == 300
        assert universe["registered_count"] == 300
        assert universe["symbols"][0]["symbol"] == "NVDA"
        sync_status = client.get("/api/market/data/sync-status").json()
        assert sync_status["daily_time"] == "15:00"
        assert sync_status["retention_trading_days"] == 300
        job = client.post(
            "/api/scanner/jobs", json={"symbols": [], "rule_ids": [], "min_score": 50}
        )
        assert job.status_code == 201
        assert job.json()["status"] == "completed"
        results = client.get("/api/scanner/results", params={"job_id": job.json()["id"]}).json()
        assert isinstance(results, list)
        bars = client.get("/api/market/data/daily/AAPL").json()["bars"]
        assert len(bars) >= 250


def test_scan_results_are_isolated_by_job() -> None:
    with TestClient(app) as client:
        first = client.post(
            "/api/scanner/jobs",
            json={"symbols": ["AAPL"], "rule_ids": [], "min_score": 50},
        ).json()
        second = client.post(
            "/api/scanner/jobs",
            json={"symbols": ["NVDA"], "rule_ids": [], "min_score": 50},
        ).json()
        first_results = client.get("/api/scanner/results", params={"job_id": first["id"]}).json()
        second_results = client.get("/api/scanner/results", params={"job_id": second["id"]}).json()
        assert first_results and second_results
        assert {item["scan_job_id"] for item in first_results} == {first["id"]}
        assert {item["symbol"] for item in first_results} == {"AAPL"}
        assert {item["scan_job_id"] for item in second_results} == {second["id"]}
        assert {item["symbol"] for item in second_results} == {"NVDA"}


def test_backtest_positions_do_not_overlap_per_symbol() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/backtests",
            json={
                "rule_id": "resistance_breakout_volume",
                "symbols": [],
                "holding_days": 10,
                "target_r": 2,
            },
        )
        assert response.status_code == 201
        trades = response.json()["trades"]
        assert trades
        by_symbol: dict[str, list[dict]] = {}
        for trade in trades:
            by_symbol.setdefault(trade["symbol"], []).append(trade)
            bars = client.get(
                f"/api/market/data/daily/{trade['symbol']}", params={"limit": 1000}
            ).json()["bars"]
            bar_by_date = {bar["bar_date"]: bar for bar in bars}
            assert trade["entry_date"] > trade["signal_date"]
            assert bar_by_date[trade["entry_date"]]["high"] >= trade["entry"]
        for symbol_trades in by_symbol.values():
            ordered = sorted(symbol_trades, key=lambda item: item["entry_date"])
            for previous, current in zip(ordered, ordered[1:], strict=False):
                assert current["entry_date"] > previous["exit_date"]


def test_real_sync_replaces_demo_series(monkeypatch) -> None:
    ticker = "MIXD"
    with SessionLocal() as db:
        symbol = db.scalar(select(MarketSymbol).where(MarketSymbol.symbol == ticker))
        if symbol is None:
            symbol = MarketSymbol(symbol=ticker, name="Mixed data fixture")
            db.add(symbol)
            db.flush()
        db.execute(delete(DailyBar).where(DailyBar.market_symbol_id == symbol.id))
        db.add_all(
            [
                DailyBar(
                    market_symbol_id=symbol.id,
                    bar_date=date(2026, 1, 1),
                    open=10,
                    high=11,
                    low=9,
                    close=10.5,
                    volume=100,
                    source="DEMO",
                ),
                DailyBar(
                    market_symbol_id=symbol.id,
                    bar_date=date(2026, 1, 2),
                    open=10.5,
                    high=12,
                    low=10,
                    close=11.5,
                    volume=120,
                    source="DEMO",
                ),
            ]
        )
        db.commit()

    async def fake_fetch(*_args, **_kwargs):
        start = date(2025, 1, 1)
        return 12345, [
            {
                "date": start + timedelta(days=index),
                "open": 20 + index,
                "high": 22 + index,
                "low": 19 + index,
                "close": 21 + index,
                "volume": 1_000 + index,
            }
            for index in range(305)
        ]

    monkeypatch.setattr(ibkr_service, "fetch_daily_bars", fake_fetch)
    with TestClient(app) as client:
        response = client.post(
            "/api/market/data/sync-daily",
            json={"symbols": [ticker], "duration": "1 Y", "use_rth": True},
        )
        assert response.status_code == 200
        result = response.json()["results"][0]
        assert result["removed_demo"] == 2
        assert result["inserted"] == 305
        assert result["pruned"] == 5
        assert result["retained"] == 300
        bars = client.get(f"/api/market/data/daily/{ticker}").json()["bars"]
        assert len(bars) == 300
        assert bars[0]["bar_date"] == "2025-01-06"
        assert {bar["source"] for bar in bars} == {"IBKR"}
