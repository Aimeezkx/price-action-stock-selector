"""Read-only IBKR acceptance probe for TWS / IB Gateway."""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict

from app.services.ibkr import ibkr_service


async def run(symbol: str, duration: str) -> int:
    status = await ibkr_service.connect()
    result: dict = {"connection": asdict(status), "symbol": symbol.upper()}
    if not status.connected:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1
    try:
        contract_id, bars = await ibkr_service.fetch_daily_bars(symbol, duration)
        result.update(
            {
                "contract_id": contract_id,
                "bar_count": len(bars),
                "first_bar": bars[0] if bars else None,
                "last_bar": bars[-1] if bars else None,
                "ohlcv_valid": bool(bars)
                and all(
                    bar["low"] <= min(bar["open"], bar["close"])
                    and bar["high"] >= max(bar["open"], bar["close"])
                    and bar["volume"] >= 0
                    for bar in bars
                ),
            }
        )
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return 0 if bars and result["ohlcv_valid"] else 2
    finally:
        ibkr_service.disconnect()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", default="AAPL")
    parser.add_argument("--duration", default="1 M")
    args = parser.parse_args()
    return asyncio.run(run(args.symbol, args.duration))


if __name__ == "__main__":
    raise SystemExit(main())
