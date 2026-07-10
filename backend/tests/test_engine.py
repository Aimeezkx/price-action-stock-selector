from datetime import date, timedelta

from app.knowledge import RULE_DEFINITIONS
from app.price_action import analyze_rule


def bars_with_breakout() -> list[dict]:
    start = date(2025, 1, 1)
    bars = []
    price = 100.0
    for index in range(60):
        close = price + 0.25
        bars.append(
            {
                "date": start + timedelta(days=index),
                "open": price,
                "high": close + 0.5,
                "low": price - 0.4,
                "close": close,
                "volume": 1_000_000,
            }
        )
        price = close
    bars[-1].update(
        {"open": 115.0, "low": 114.8, "high": 119.0, "close": 118.8, "volume": 2_500_000}
    )
    return bars


def test_breakout_rule_has_trade_plan() -> None:
    rule = next(item for item in RULE_DEFINITIONS if item["id"] == "resistance_breakout_volume")
    signal = analyze_rule(rule, bars_with_breakout())
    assert signal["matched"] is True
    assert signal["score"] >= 80
    assert signal["stop"] < signal["entry"] < signal["target"]
    assert signal["risk_reward"] >= 1.9


def test_all_rules_return_uniform_shape() -> None:
    expected = {
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
    for rule in RULE_DEFINITIONS:
        assert set(analyze_rule(rule, bars_with_breakout())) == expected
