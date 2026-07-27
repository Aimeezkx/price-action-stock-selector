"""RQ entry point for production deployments.

The API executes small scans inline for a zero-configuration MVP. Deployments can enqueue
``run_scan_job`` through RQ to process larger watchlists without changing the rule engine.
"""

from .database import SessionLocal
from .models import ScanJob
from .services.scanner import run_scan


def run_scan_job(job_id: int) -> None:
    with SessionLocal() as db:
        job = db.get(ScanJob, job_id)
        if job is None:
            raise ValueError(f"Unknown scan job {job_id}")
        run_scan(db, job)
