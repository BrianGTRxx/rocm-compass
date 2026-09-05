"""Turns raw environment reports into the per-package summary compass/api.py
serves. Reports come from two places: shared/reports.db (local -- whatever
this machine's `rocm-doctor check --report` wrote) and
compass/community_reports.jsonl (reports from other people's machines,
ingested from GitHub Issues -- see compass/ingest.py). Both feed the same
aggregate so the API doesn't care which transport a given report arrived by.
"""

from __future__ import annotations

from pathlib import Path

from compass.ingest import COMMUNITY_REPORTS_PATH, load_community_reports
from shared.schema import ReportOutcome
from shared.store import DB_PATH, load_reports


def aggregate_reports_by_package(
    package_name: str,
    db_path: Path = DB_PATH,
    community_path: Path = COMMUNITY_REPORTS_PATH,
) -> dict:
    reports = load_reports(package_name=package_name, db_path=db_path)
    reports += [r for r in load_community_reports(community_path) if r.package.name == package_name]

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
