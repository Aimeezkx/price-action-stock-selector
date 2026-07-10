from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..models import DailyBar, MarketSymbol, PriceActionRule, ScanJob, ScanResult
from ..price_action import analyze_rule


def rule_to_dict(rule: PriceActionRule) -> dict:
    return {
        "id": rule.id,
        "name": rule.name,
        "category": rule.category,
        "description": rule.description,
        "direction": rule.direction,
        "parameters": rule.parameters,
        "source_references": rule.source_references,
        "enabled": rule.enabled,
    }


def run_scan(db: Session, job: ScanJob) -> ScanJob:
    job.status = "running"
    job.started_at = datetime.now(timezone.utc)
    db.commit()
    try:
        db.execute(delete(ScanResult).where(ScanResult.scan_job_id == job.id))
        symbol_query = select(MarketSymbol).where(MarketSymbol.enabled.is_(True))
        if job.symbols:
            symbol_query = symbol_query.where(MarketSymbol.symbol.in_(job.symbols))
        symbols = db.scalars(symbol_query.order_by(MarketSymbol.symbol)).all()

        rule_query = select(PriceActionRule).where(PriceActionRule.enabled.is_(True))
        if job.rule_ids:
            rule_query = rule_query.where(PriceActionRule.id.in_(job.rule_ids))
        rules = db.scalars(rule_query.order_by(PriceActionRule.id)).all()

        for symbol in symbols:
            bars = db.scalars(
                select(DailyBar)
                .where(DailyBar.market_symbol_id == symbol.id)
                .order_by(DailyBar.bar_date)
            ).all()
            for rule in rules:
                signal = analyze_rule(rule_to_dict(rule), list(bars))
                if not signal["matched"] or signal["score"] < job.min_score:
                    continue
                db.add(
                    ScanResult(
                        scan_job_id=job.id,
                        symbol=symbol.symbol,
                        signal_date=bars[-1].bar_date,
                        rule_id=rule.id,
                        rule_name=rule.name,
                        score=signal["score"],
                        direction=signal["direction"],
                        entry=signal["entry"],
                        stop=signal["stop"],
                        target=signal["target"],
                        risk_reward=signal["risk_reward"],
                        explanation=signal["explanation"],
                        annotations=signal["annotations"],
                    )
                )
        job.status = "completed"
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
    except Exception as exc:
        job.status = "failed"
        job.error = str(exc)
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
        raise
    return job
