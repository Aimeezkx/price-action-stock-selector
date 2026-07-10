from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date
from typing import Any

from ..config import get_settings

try:
    from ib_insync import IB, Stock, util
except ImportError:  # pragma: no cover - allows tests without optional broker package
    IB = Stock = util = None


@dataclass(slots=True)
class IBKRStatus:
    connected: bool
    host: str
    port: int
    client_id: int
    readonly: bool
    market_data_type: int
    message: str


class IBKRService:
    def __init__(self) -> None:
        self.settings = get_settings()
        # Create the IB client lazily inside the active ASGI event loop. Creating
        # it at module import can bind internal futures to a different loop than
        # Uvicorn/uvloop and makes the first HTTP connection fail.
        self.ib: Any = None
        self._lock = asyncio.Lock()

    async def connect(self) -> IBKRStatus:
        if IB is None:
            return self.status("ib-insync 未安装")
        # ib-insync 0.9.x asks the event-loop policy for a loop instead of
        # using get_running_loop(). Python 3.13/Uvicorn can therefore hand it
        # a stale policy loop. Register the active ASGI loop before the client
        # opens its socket so every future belongs to the request loop.
        asyncio.set_event_loop(asyncio.get_running_loop())
        if self.ib is None:
            self.ib = IB()
        if not self.ib.isConnected():
            try:
                await self.ib.connectAsync(
                    self.settings.ibkr_host,
                    self.settings.ibkr_port,
                    clientId=self.settings.ibkr_client_id,
                    readonly=self.settings.ibkr_readonly,
                    timeout=4,
                )
                self.ib.reqMarketDataType(self.settings.ibkr_market_data_type)
            except Exception as exc:
                return self.status(f"连接失败: {exc}")
        return self.status("已连接 TWS / IB Gateway")

    def status(self, message: str | None = None) -> IBKRStatus:
        connected = bool(self.ib and self.ib.isConnected())
        return IBKRStatus(
            connected=connected,
            host=self.settings.ibkr_host,
            port=self.settings.ibkr_port,
            client_id=self.settings.ibkr_client_id,
            readonly=self.settings.ibkr_readonly,
            market_data_type=self.settings.ibkr_market_data_type,
            message=message
            or ("已连接" if connected else "未连接；启动 TWS/IB Gateway 后点击连接"),
        )

    def disconnect(self) -> None:
        """Close the broker socket while the owning event loop is still alive."""
        if self.ib and self.ib.isConnected():
            self.ib.disconnect()

    async def fetch_daily_bars(
        self, symbol: str, duration: str = "1 Y", use_rth: bool = True
    ) -> tuple[int | None, list[dict[str, Any]]]:
        async with self._lock:
            status = await self.connect()
            if not status.connected:
                raise ConnectionError(status.message)
            contract = Stock(symbol.upper(), "SMART", "USD")
            qualified = await self.ib.qualifyContractsAsync(contract)
            if not qualified:
                raise ValueError(f"IBKR 无法解析合约 {symbol}")
            bars = await self.ib.reqHistoricalDataAsync(
                qualified[0],
                endDateTime="",
                durationStr=duration,
                barSizeSetting="1 day",
                whatToShow="TRADES",
                useRTH=use_rth,
                formatDate=1,
                keepUpToDate=False,
            )
            await asyncio.sleep(self.settings.ibkr_request_delay_seconds)
            normalized = [
                {
                    "date": item.date
                    if isinstance(item.date, date)
                    else util.parseIBDatetime(item.date).date(),
                    "open": float(item.open),
                    "high": float(item.high),
                    "low": float(item.low),
                    "close": float(item.close),
                    "volume": float(item.volume),
                }
                for item in bars
            ]
            return qualified[0].conId, normalized


ibkr_service = IBKRService()
