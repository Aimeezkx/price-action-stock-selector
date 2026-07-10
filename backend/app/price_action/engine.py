from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from statistics import fmean
from typing import Any


@dataclass(slots=True)
class Bar:
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: float
    atr: float = 0
    avg_volume: float = 0
    ema20: float = 0

    @property
    def body(self) -> float:
        return abs(self.close - self.open)

    @property
    def range(self) -> float:
        return max(self.high - self.low, 1e-9)

    @property
    def upper_wick(self) -> float:
        return self.high - max(self.open, self.close)

    @property
    def lower_wick(self) -> float:
        return min(self.open, self.close) - self.low

    @property
    def close_location(self) -> float:
        return (self.close - self.low) / self.range

    @property
    def volume_ratio(self) -> float:
        return self.volume / self.avg_volume if self.avg_volume else 0


def enrich_bars(rows: list[Any]) -> list[Bar]:
    bars = [
        Bar(
            date=getattr(row, "bar_date", row.get("date") if isinstance(row, dict) else None),
            open=float(getattr(row, "open", row.get("open") if isinstance(row, dict) else 0)),
            high=float(getattr(row, "high", row.get("high") if isinstance(row, dict) else 0)),
            low=float(getattr(row, "low", row.get("low") if isinstance(row, dict) else 0)),
            close=float(getattr(row, "close", row.get("close") if isinstance(row, dict) else 0)),
            volume=float(getattr(row, "volume", row.get("volume") if isinstance(row, dict) else 0)),
        )
        for row in rows
    ]
    if not bars:
        return bars
    alpha = 2 / 21
    ema = bars[0].close
    true_ranges: list[float] = []
    volumes: list[float] = []
    for index, bar in enumerate(bars):
        previous_close = bars[index - 1].close if index else bar.close
        true_range = max(
            bar.high - bar.low, abs(bar.high - previous_close), abs(bar.low - previous_close)
        )
        true_ranges.append(true_range)
        volumes.append(bar.volume)
        ema = bar.close * alpha + ema * (1 - alpha)
        bar.ema20 = ema
        bar.atr = fmean(true_ranges[max(0, index - 13) : index + 1])
        bar.avg_volume = fmean(volumes[max(0, index - 19) : index + 1])
    return bars


def _signal(
    rule: dict[str, Any],
    bar: Bar,
    score: float,
    entry: float,
    stop: float,
    explanations: list[str],
    annotations: list[dict[str, Any]],
) -> dict[str, Any]:
    risk = max(entry - stop, bar.atr * 0.25, 0.01)
    target = entry + risk * float(rule.get("parameters", {}).get("minimum_rr", 2.0))
    return {
        "matched": score >= 50,
        "score": round(max(0, min(score, 100)), 1),
        "direction": rule["direction"],
        "entry": round(entry, 2),
        "stop": round(stop, 2),
        "target": round(target, 2),
        "risk_reward": round((target - entry) / risk, 2),
        "explanation": explanations,
        "annotations": annotations,
    }


def analyze_rule(rule: dict[str, Any], rows: list[Any]) -> dict[str, Any]:
    bars = enrich_bars(rows)
    if len(bars) < 45:
        return {
            "matched": False,
            "score": 0,
            "direction": rule["direction"],
            "entry": 0,
            "stop": 0,
            "target": 0,
            "risk_reward": 0,
            "explanation": ["至少需要 45 根日线 K 线"],
            "annotations": [],
        }

    current, previous = bars[-1], bars[-2]
    params = rule.get("parameters", {})
    rule_id = rule["id"]
    score = 0.0
    explanations: list[str] = []
    annotations: list[dict[str, Any]] = []
    entry = current.high + max(current.atr * 0.05, 0.01)
    stop = current.low - max(current.atr * 0.1, 0.01)

    prior20 = bars[-21:-1]
    prior40 = bars[-41:-1]
    support20 = min(item.low for item in prior20)
    resistance40 = max(item.high for item in prior40)
    rising_structure = current.ema20 > bars[-11].ema20 and current.close > current.ema20

    if rule_id == "trend_continuation_pullback":
        near_ema = current.low <= current.ema20 + current.atr * params.get("pullback_atr", 0.8)
        strong_close = current.close_location >= 0.65 and current.close > current.open
        score = (
            35 * rising_structure
            + 30 * near_ema
            + 25 * strong_close
            + min(current.volume_ratio, 1.5) / 1.5 * 10
        )
        if rising_structure:
            explanations.append("20 日 EMA 上行且收盘保持其上，趋势结构偏多")
        if near_ema:
            explanations.append("回踩进入均线/动态支撑的 ATR 容差区")
        if strong_close:
            explanations.append("信号 K 线收在区间上部，出现买方跟随确认")
        stop = min(current.low, current.ema20 - current.atr * 0.35)
        annotations.append(
            {"type": "line", "price": round(current.ema20, 2), "label": "EMA20 / 回踩区"}
        )

    elif rule_id == "resistance_breakout_volume":
        breakout = current.close > resistance40
        volume_ok = current.volume_ratio >= params.get("volume_ratio", 1.4)
        strong_close = current.close_location >= 0.7
        score = 45 * breakout + 30 * volume_ok + 15 * strong_close + 10 * rising_structure
        if breakout:
            explanations.append(f"收盘突破过去 40 日阻力 {resistance40:.2f}")
        if volume_ok:
            explanations.append(f"成交量为 20 日均量的 {current.volume_ratio:.2f} 倍")
        if strong_close:
            explanations.append("突破 K 线接近最高位收盘，跟随质量较高")
        stop = max(resistance40 - current.atr * 0.35, current.low - current.atr * 0.1)
        annotations.append({"type": "line", "price": round(resistance40, 2), "label": "40 日阻力"})

    elif rule_id == "breakout_pullback_support":
        breakout_candidates = bars[-16:-3]
        breakout_level = max(item.high for item in bars[-56:-16])
        broke = any(item.close > breakout_level for item in breakout_candidates)
        held = current.low >= breakout_level - current.atr * params.get("tolerance_atr", 0.35)
        rejection = current.close_location >= 0.65 and current.lower_wick > current.body
        score = 40 * broke + 30 * held + 20 * rejection + 10 * rising_structure
        if broke:
            explanations.append(f"最近 10 日内曾有效突破结构位 {breakout_level:.2f}")
        if held:
            explanations.append("当前回踩仍守住突破位容差区")
        if rejection:
            explanations.append("下影线与高位收盘显示支撑承接")
        stop = breakout_level - current.atr * 0.45
        annotations.append(
            {"type": "line", "price": round(breakout_level, 2), "label": "突破回踩位"}
        )

    elif rule_id == "tight_range_breakout":
        range_days = int(params.get("range_days", 7))
        compression = bars[-(range_days + 1) : -1]
        compressed_range = max(item.high for item in compression) - min(
            item.low for item in compression
        )
        baseline = fmean(item.atr for item in bars[-21:-1]) * range_days**0.5
        tight = compressed_range <= baseline * params.get("compression_ratio", 0.65)
        level = max(item.high for item in compression)
        breakout = current.close > level and current.close_location >= 0.7
        volume_ok = current.volume_ratio >= params.get("volume_ratio", 1.2)
        score = 35 * tight + 40 * breakout + 20 * volume_ok + 5 * rising_structure
        if tight:
            explanations.append(f"过去 {range_days} 日波幅显著压缩，形成紧密交易区间")
        if breakout:
            explanations.append(f"强势收盘突破区间上沿 {level:.2f}")
        if volume_ok:
            explanations.append(f"扩张日成交量达到均量 {current.volume_ratio:.2f} 倍")
        stop = min(item.low for item in compression)
        annotations.append(
            {"type": "zone", "low": round(stop, 2), "high": round(level, 2), "label": "压缩区"}
        )

    elif rule_id == "pin_bar_key_level":
        body = max(current.body, current.range * 0.08)
        pin = current.lower_wick / body >= params.get(
            "wick_body_ratio", 2
        ) and current.close_location >= params.get("close_location", 0.65)
        near_support = current.low <= support20 + current.atr * 0.3
        follow = current.close > previous.close
        score = 45 * pin + 30 * near_support + 15 * follow + 10 * (current.volume_ratio >= 1)
        if pin:
            explanations.append("长下影超过实体两倍且收在 K 线高位，形成拒绝形态")
        if near_support:
            explanations.append(f"拒绝发生在 20 日关键支撑 {support20:.2f} 附近")
        if follow:
            explanations.append("收盘高于前一日，具备初步跟随确认")
        stop = current.low - current.atr * 0.15
        annotations.append({"type": "line", "price": round(support20, 2), "label": "20 日支撑"})

    elif rule_id == "inside_bar_breakout":
        mother = bars[-3]
        inside = previous.high < mother.high and previous.low > mother.low
        breakout = current.close > mother.high and current.close_location >= 0.65
        volume_ok = current.volume_ratio >= params.get("volume_ratio", 1)
        score = 40 * inside + 40 * breakout + 15 * volume_ok + 5 * rising_structure
        if inside:
            explanations.append("前一日完全位于母 K 线内部，波动收缩")
        if breakout:
            explanations.append(f"当前收盘突破母 K 高点 {mother.high:.2f}")
        if volume_ok:
            explanations.append("突破量能不低于 20 日均量")
        stop = mother.low - current.atr * 0.1
        annotations.append(
            {
                "type": "zone",
                "low": round(mother.low, 2),
                "high": round(mother.high, 2),
                "label": "母 K 区间",
            }
        )

    elif rule_id == "false_breakdown_reclaim":
        broke_support = current.low < support20
        reclaimed = current.close > support20 and current.close_location >= params.get(
            "close_location", 0.6
        )
        follow = current.close > previous.close
        score = 45 * broke_support + 35 * reclaimed + 10 * follow + 10 * (current.volume_ratio >= 1)
        if broke_support:
            explanations.append(f"盘中跌破过去 20 日支撑 {support20:.2f}")
        if reclaimed:
            explanations.append("收盘重新站回支撑上方，空头突破失败")
        if follow:
            explanations.append("收盘改善，可能存在被困空头回补")
        stop = current.low - current.atr * 0.15
        annotations.append({"type": "line", "price": round(support20, 2), "label": "假跌破支撑"})

    elif rule_id == "high_volume_upper_wick_risk":
        body = max(current.body, current.range * 0.08)
        wick_risk = current.upper_wick / body >= params.get("wick_body_ratio", 1.8)
        volume_risk = current.volume_ratio >= params.get("volume_ratio", 1.6)
        extended = (current.close - current.ema20) / max(current.atr, 0.01) >= params.get(
            "extended_atr", 2.5
        )
        oversized = current.range >= current.atr * 1.8
        score = 35 * wick_risk + 30 * volume_risk + 20 * extended + 15 * oversized
        if wick_risk:
            explanations.append("高位长上影显示买盘被明显拒绝")
        if volume_risk:
            explanations.append(f"成交量放大至均量 {current.volume_ratio:.2f} 倍，需防范派发")
        if extended:
            explanations.append("价格距离 EMA20 过远，追涨风险上升")
        if oversized:
            explanations.append("信号 K 线过大，结构止损距离偏远")
        entry, stop = current.close, current.high + current.atr * 0.1
        result = _signal(
            rule, current, score, entry, min(entry - 0.01, current.low), explanations, annotations
        )
        result["direction"] = "risk"
        result["target"] = 0
        result["risk_reward"] = 0
        return result

    else:
        raise ValueError(f"Unknown rule: {rule_id}")

    return _signal(rule, current, score, entry, stop, explanations, annotations)
