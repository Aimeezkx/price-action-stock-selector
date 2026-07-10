from __future__ import annotations

from datetime import date
from math import sqrt
from statistics import fmean

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import BacktestRun, DailyBar, MarketSymbol, PriceActionRule
from ..price_action import analyze_rule
from .scanner import rule_to_dict


def run_backtest(
    db: Session,
    rule: PriceActionRule,
    symbols: list[str],
    start_date: date | None,
    end_date: date | None,
    holding_days: int,
    target_r: float,
) -> BacktestRun:
    query = select(MarketSymbol)
    if symbols:
        query = query.where(MarketSymbol.symbol.in_(symbols))
    market_symbols = db.scalars(query.order_by(MarketSymbol.symbol)).all()
    trades: list[dict] = []

    for market_symbol in market_symbols:
        bars = list(
            db.scalars(
                select(DailyBar)
                .where(DailyBar.market_symbol_id == market_symbol.id)
                .order_by(DailyBar.bar_date)
            ).all()
        )
        index = 44
        while index < len(bars) - holding_days:
            signal_date = bars[index].bar_date
            if start_date and signal_date < start_date:
                index += 1
                continue
            if end_date and signal_date > end_date:
                break
            signal = analyze_rule(rule_to_dict(rule), bars[: index + 1])
            if not signal["matched"] or signal["direction"] != "long" or signal["score"] < 60:
                index += 1
                continue
            risk = max(signal["entry"] - signal["stop"], 0.01)
            target = signal["entry"] + risk * target_r
            outcome_r = None
            exit_price = bars[index + holding_days].close
            exit_date = bars[index + holding_days].bar_date
            exit_index = index + holding_days
            for future_index, future in enumerate(
                bars[index + 1 : index + holding_days + 1], start=index + 1
            ):
                if future.low <= signal["stop"]:
                    outcome_r, exit_price, exit_date = -1.0, signal["stop"], future.bar_date
                    exit_index = future_index
                    break
                if future.high >= target:
                    outcome_r, exit_price, exit_date = target_r, target, future.bar_date
                    exit_index = future_index
                    break
            if outcome_r is None:
                outcome_r = (exit_price - signal["entry"]) / risk
            trades.append(
                {
                    "symbol": market_symbol.symbol,
                    "entry_date": signal_date.isoformat(),
                    "exit_date": exit_date.isoformat(),
                    "entry": signal["entry"],
                    "exit": round(exit_price, 2),
                    "score": signal["score"],
                    "r": round(outcome_r, 3),
                }
            )
            # Resume signal evaluation only after the simulated position exits.
            index = exit_index + 1

    returns = [trade["r"] for trade in trades]
    equity = peak = 0.0
    max_drawdown = 0.0
    for value in returns:
        equity += value
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, peak - equity)
    wins = [value for value in returns if value > 0]
    losses = [value for value in returns if value <= 0]
    mean_r = fmean(returns) if returns else 0
    stdev = sqrt(fmean([(value - mean_r) ** 2 for value in returns])) if returns else 0
    metrics = {
        "sample_size": len(trades),
        "win_rate": round(len(wins) / len(returns) * 100, 1) if returns else 0,
        "average_r": round(mean_r, 3),
        "profit_factor": round(sum(wins) / abs(sum(losses)), 2) if losses and sum(losses) else 0,
        "max_drawdown_r": round(max_drawdown, 2),
        "expectancy_r": round(mean_r, 3),
        "sharpe_like": round(mean_r / stdev * sqrt(len(returns)), 2) if stdev else 0,
    }
    run = BacktestRun(
        rule_id=rule.id,
        symbols=[item.symbol for item in market_symbols],
        start_date=start_date,
        end_date=end_date,
        config={"holding_days": holding_days, "target_r": target_r, "signal_score_min": 60},
        metrics=metrics,
        trades=trades[-250:],
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run
