"""End-to-end HTTP acceptance test against a running backend."""

from __future__ import annotations

import argparse
import json

import httpx


def require(response: httpx.Response) -> dict | list:
    response.raise_for_status()
    return response.json()


def run(base_url: str, symbol: str) -> dict:
    ticker = symbol.upper()
    with httpx.Client(base_url=base_url, timeout=120) as client:
        health = require(client.get("/api/health"))
        connection = require(client.post("/api/market/ibkr/connect"))
        if not connection["connected"]:
            raise AssertionError(connection["message"])

        first_sync = require(
            client.post(
                "/api/market/data/sync-daily",
                json={"symbols": [ticker], "duration": "1 Y", "use_rth": True},
            )
        )["results"][0]
        if first_sync["status"] != "ok" or first_sync["received"] < 200:
            raise AssertionError(first_sync)

        second_sync = require(
            client.post(
                "/api/market/data/sync-daily",
                json={"symbols": [ticker], "duration": "1 Y", "use_rth": True},
            )
        )["results"][0]
        if second_sync["status"] != "ok" or second_sync["inserted"] != 0:
            raise AssertionError({"idempotency_failed": second_sync})

        daily = require(client.get(f"/api/market/data/daily/{ticker}", params={"limit": 400}))
        bars = daily["bars"]
        dates = [bar["bar_date"] for bar in bars]
        if len(bars) < 200 or dates != sorted(set(dates)):
            raise AssertionError("Daily bars are missing, duplicated, or out of order")
        if not all(
            bar["low"] <= min(bar["open"], bar["close"])
            and bar["high"] >= max(bar["open"], bar["close"])
            and bar["volume"] >= 0
            for bar in bars
        ):
            raise AssertionError("Invalid OHLCV relationship")

        scan_job = require(
            client.post(
                "/api/scanner/jobs",
                json={"symbols": [ticker], "rule_ids": [], "min_score": 50},
            )
        )
        if scan_job["status"] != "completed":
            raise AssertionError(scan_job)
        scan_results = require(
            client.get("/api/scanner/results", params={"job_id": scan_job["id"]})
        )
        if not scan_results:
            raise AssertionError("Scanner completed without a candidate")
        if any(result["scan_job_id"] != scan_job["id"] for result in scan_results):
            raise AssertionError("Scanner returned results from another job")

        rule_test = require(
            client.post(
                "/api/price-action/rules/trend_continuation_pullback/test",
                json={"symbol": ticker},
            )
        )
        expected_signal_keys = {
            "matched",
            "score",
            "direction",
            "entry",
            "stop",
            "target",
            "risk_reward",
            "explanation",
            "annotations",
        }
        if set(rule_test["signal"]) != expected_signal_keys:
            raise AssertionError("Rule-test response shape changed")

        backtest = require(
            client.post(
                "/api/backtests",
                json={
                    "rule_id": "trend_continuation_pullback",
                    "symbols": [ticker],
                    "holding_days": 10,
                    "entry_expiry_days": 3,
                    "target_r": 2,
                },
            )
        )
        trades = sorted(backtest["trades"], key=lambda trade: trade["entry_date"])
        if not trades:
            raise AssertionError("Backtest completed without a triggered entry")
        for previous, current in zip(trades, trades[1:], strict=False):
            if current["entry_date"] <= previous["exit_date"]:
                raise AssertionError("Backtest positions overlap")

        return {
            "health": health,
            "ibkr": connection,
            "symbol": daily["symbol"],
            "first_sync": first_sync,
            "second_sync": second_sync,
            "daily_bar_count": len(bars),
            "daily_range": [dates[0], dates[-1]],
            "scan_job_id": scan_job["id"],
            "scan_result_count": len(scan_results),
            "rule_test_score": rule_test["signal"]["score"],
            "backtest_id": backtest["id"],
            "backtest_metrics": backtest["metrics"],
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--symbol", default="AAPL")
    args = parser.parse_args()
    print(json.dumps(run(args.base_url, args.symbol), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
