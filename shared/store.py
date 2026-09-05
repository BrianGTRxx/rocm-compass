"""Local SQLite-backed store for EnvironmentReport rows -- the one dataset
`rocm-doctor check --report` writes to and `compass/aggregate.py` reads from.

Deliberately just a file (docs/rocm-compass-plan.md section 6: "SQLite al
inicio -- nada de bases de datos complejas hasta que haya tracción real").
How reports from OTHER people's machines eventually reach this store once the
project is public (a PR/issue bot? a real HTTP endpoint?) is still an open
question (see plan section 10) -- this module only defines the local
read/write contract both the Doctor and the Compass share today.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from shared.schema import EnvironmentReport

DB_PATH = Path(__file__).parent / "reports.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS environment_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gpu_arch TEXT NOT NULL,
    rocm_version TEXT NOT NULL,
    kernel_version TEXT NOT NULL,
    amdgpu_driver_version TEXT,
    package_name TEXT NOT NULL,
    package_version TEXT NOT NULL,
    outcome TEXT NOT NULL,
    notes TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT 'community',
    reported_at TEXT NOT NULL
);
"""

_COLUMNS = [
    "id", "gpu_arch", "rocm_version", "kernel_version", "amdgpu_driver_version",
    "package_name", "package_version", "outcome", "notes", "source", "reported_at",
]


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute(_SCHEMA)
    return conn


def save_report(report: EnvironmentReport, db_path: Path = DB_PATH) -> int:
    """Persists one report, returns its new row id."""
    data = report.to_dict()
    # `with conn:` alone only commits/rolls back the transaction -- per the
    # sqlite3 docs it does NOT close the connection, which leaked one file
    # handle per call (verified: a long-lived caller like compass/api.py would
    # leak 12 of these per /packages request). `closing()` guarantees close().
    with closing(_connect(db_path)) as conn:
        with conn:
            cursor = conn.execute(
                """
                INSERT INTO environment_reports
                    (gpu_arch, rocm_version, kernel_version, amdgpu_driver_version,
                     package_name, package_version, outcome, notes, source, reported_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["gpu_arch"], data["rocm_version"], data["kernel_version"],
                    data["amdgpu_driver_version"], data["package_name"], data["package_version"],
                    data["outcome"], data["notes"], data["source"], data["reported_at"],
                ),
            )
        return cursor.lastrowid


def load_reports(package_name: str | None = None, db_path: Path = DB_PATH) -> list[EnvironmentReport]:
    """All reports, optionally filtered to one package, oldest first."""
    with closing(_connect(db_path)) as conn:
        if package_name is None:
            rows = conn.execute("SELECT * FROM environment_reports ORDER BY reported_at").fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM environment_reports WHERE package_name = ? ORDER BY reported_at",
                (package_name,),
            ).fetchall()

    return [EnvironmentReport.from_dict(dict(zip(_COLUMNS, row))) for row in rows]
