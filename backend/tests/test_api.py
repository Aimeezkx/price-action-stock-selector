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
