from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class SymbolCreate(BaseModel):
    symbol: str = Field(min_length=1, max_length=16)
    name: str = ""
    exchange: str = "SMART"
    currency: str = "USD"
    sector: str | None = None


class SyncRequest(BaseModel):
    symbols: list[str]
    duration: str = "1 Y"
    use_rth: bool = True


class ScanRequest(BaseModel):
    symbols: list[str] = []
    rule_ids: list[str] = []
    min_score: float = Field(default=60, ge=0, le=100)


class RuleUpdate(BaseModel):
    enabled: bool | None = None
    parameters: dict[str, Any] | None = None


class RuleTestRequest(BaseModel):
    symbol: str


class BacktestRequest(BaseModel):
    rule_id: str
    symbols: list[str] = []
    start_date: date | None = None
    end_date: date | None = None
    holding_days: int = Field(default=10, ge=1, le=120)
    entry_expiry_days: int = Field(default=3, ge=1, le=10)
    target_r: float = Field(default=2, ge=0.25, le=10)
