import os

os.environ["DATABASE_URL"] = "sqlite:///./test_price_action.db"
os.environ["SEED_DEMO_DATA"] = "true"

from fastapi.testclient import TestClient

from app.main import app


def test_mvp_flow() -> None:
    with TestClient(app) as client:
        assert client.get("/api/health").status_code == 200
        rules = client.get("/api/price-action/rules").json()
        assert len(rules) == 8
        symbols = client.get("/api/market/symbols").json()
        assert len(symbols) >= 6
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
        for symbol_trades in by_symbol.values():
            ordered = sorted(symbol_trades, key=lambda item: item["entry_date"])
            for previous, current in zip(ordered, ordered[1:], strict=False):
                assert current["entry_date"] > previous["exit_date"]
