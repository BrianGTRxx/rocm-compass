"""Turns raw shared/reports.db rows into the per-package summary compass/api.py
serves. This is the other half of the Doctor <-> Compass loop: whatever
`rocm-doctor check --report` writes, this reads back out as an aggregate.
"""

from __future__ import annotations

from pathlib import Path

from shared.schema import ReportOutcome
from shared.store import DB_PATH, load_reports


def aggregate_reports_by_package(package_name: str, db_path: Path = DB_PATH) -> dict:
    reports = load_reports(package_name=package_name, db_path=db_path)

    worked = [r for r in reports if r.outcome == ReportOutcome.WORKED]
    failed = [r for r in reports if r.outcome == ReportOutcome.FAILED]
    partial = [r for r in reports if r.outcome == ReportOutcome.PARTIAL]

    known_good_combos = sorted({
        f"{r.snapshot.gpu_arch} + rocm{r.snapshot.rocm_version} + {r.package.name}=={r.package.version}"
        for r in worked
    })

    return {
        "total_reports": len(reports),
        "worked": len(worked),
        "failed": len(failed),
        "partial": len(partial),
        "known_good_combos": known_good_combos,
    }
