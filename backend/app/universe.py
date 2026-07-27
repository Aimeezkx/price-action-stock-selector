from __future__ import annotations

import json
from functools import lru_cache
from importlib.resources import files

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import MarketSymbol, Watchlist


UNIVERSE_NAME = "S&P 500 Top 300"


def load_sp500_top300() -> dict:
    resource = files("app.data").joinpath("sp500_top300.json")
    return json.loads(resource.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def sp500_holding_lookup() -> dict[str, dict]:
    return {item["symbol"]: item for item in load_sp500_top300()["symbols"]}


def seed_sp500_top300(db: Session) -> dict:
    payload = load_sp500_top300()
    created = 0
    watchlist = db.scalar(select(Watchlist).where(Watchlist.name == UNIVERSE_NAME))
    previous_symbols = set(watchlist.symbols if watchlist else [])
    symbols = [holding["symbol"] for holding in payload["symbols"]]
    for stale_symbol in previous_symbols - set(symbols):
        stale = db.scalar(select(MarketSymbol).where(MarketSymbol.symbol == stale_symbol))
        if stale is not None:
            stale.enabled = False
    for holding in payload["symbols"]:
        item = db.scalar(select(MarketSymbol).where(MarketSymbol.symbol == holding["symbol"]))
        if item is None:
            item = MarketSymbol(symbol=holding["symbol"], name=holding["name"])
            db.add(item)
            created += 1
        elif not item.name or item.name == item.symbol:
            item.name = holding["name"]
        item.enabled = True

    if watchlist is None:
        db.add(Watchlist(name=UNIVERSE_NAME, symbols=symbols))
    else:
        watchlist.symbols = symbols
    db.commit()
    return {**payload, "created": created}
