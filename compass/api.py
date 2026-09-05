"""FastAPI app serving the public compatibility matrix.

Combines the static per-package research in compass/packages.json with the
live community_reports aggregate from compass/aggregate.py, built from two
sources: shared/reports.db (this machine's own `rocm-doctor check --report`)
and compass/community_reports.jsonl (other people's reports, ingested from
GitHub Issues -- see compass/ingest.py and .github/workflows/ingest-reports.yml).
Kept intentionally thin: no database migrations, no auth -- just a read-only
view until there's real traffic to justify more.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException

from compass.aggregate import aggregate_reports_by_package
from compass.ingest import COMMUNITY_REPORTS_PATH
from shared.store import DB_PATH

app = FastAPI(title="ROCm Compass API", description="Public compatibility matrix for the ROCm Python AI ecosystem.")

PACKAGES_PATH = Path(__file__).parent / "packages.json"


def get_db_path() -> Path:
    """FastAPI dependency for the local reports database location. Overriding
    this (via `app.dependency_overrides`, see tests/test_api.py) lets tests --
    and, later, a real deployment -- point at a different file instead of
    every request silently reading/creating the real shared/reports.db.
    """
    return DB_PATH


def get_community_reports_path() -> Path:
    """Same idea as get_db_path, for the committed community reports file --
    without this, tests would read (and, on a fresh checkout, mkdir/read) the
    real compass/community_reports.jsonl instead of an isolated fixture.
    """
    return COMMUNITY_REPORTS_PATH


def _load_static_packages() -> list[dict]:
    return json.loads(PACKAGES_PATH.read_text(encoding="utf-8"))["packages"]


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/packages")
def list_packages(
    db_path: Path = Depends(get_db_path),
    community_path: Path = Depends(get_community_reports_path),
) -> dict:
    packages = [
        {
            **package,
            "community_reports": aggregate_reports_by_package(package["name"], db_path=db_path, community_path=community_path),
        }
        for package in _load_static_packages()
    ]
    return {"packages": packages}


@app.get("/packages/{name}")
def package_detail(
    name: str,
    db_path: Path = Depends(get_db_path),
    community_path: Path = Depends(get_community_reports_path),
) -> dict:
    static = next((p for p in _load_static_packages() if p["name"] == name), None)
    if static is None:
        raise HTTPException(status_code=404, detail=f"Unknown package: {name}")
    return {**static, "community_reports": aggregate_reports_by_package(name, db_path=db_path, community_path=community_path)}
