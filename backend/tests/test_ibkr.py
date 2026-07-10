import asyncio

from app.services import ibkr as ibkr_module


def test_ibkr_uses_active_asgi_event_loop(monkeypatch) -> None:
    class FakeIB:
        def __init__(self) -> None:
            self.connected = False

        def isConnected(self) -> bool:
            return self.connected

        async def connectAsync(self, *_args, **_kwargs) -> None:
            policy_loop = asyncio.get_event_loop_policy().get_event_loop()
            assert policy_loop is asyncio.get_running_loop()
            self.connected = True

        def reqMarketDataType(self, _market_data_type: int) -> None:
            return None

    monkeypatch.setattr(ibkr_module, "IB", FakeIB)
    service = ibkr_module.IBKRService()
    status = asyncio.run(service.connect())

    assert status.connected is True
    assert status.message == "已连接 TWS / IB Gateway"
