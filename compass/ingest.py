"""Parses environment reports submitted as GitHub Issues -- the
zero-infrastructure transport for third-party `--report` submissions.

An issue body is expected to contain exactly one fenced ```json code block
holding the same shape `EnvironmentReport.to_dict()` produces. `rocm-doctor
check --report --submit` (see doctor/cli.py) generates that block
automatically; .github/ISSUE_TEMPLATE/environment_report.md carries the same
shape for someone filling it in by hand.

Ingested reports land in compass/community_reports.jsonl -- a file committed
to the repo (unlike shared/reports.db), so the community dataset is visible
on GitHub even before compass/api.py is deployed anywhere live.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from shared.schema import EnvironmentReport

COMMUNITY_REPORTS_PATH = Path(__file__).parent / "community_reports.jsonl"

_JSON_BLOCK = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)


def parse_report_issue_body(body: str) -> EnvironmentReport:
    """Raises ValueError with a human-readable reason on anything invalid.
    The ingestion workflow posts that message back as an issue comment, so a
    bad submission gets concrete feedback instead of silently vanishing.
    """
    match = _JSON_BLOCK.search(body or "")
    if not match:
        raise ValueError("No ```json code block found in the issue body.")

    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise ValueError(f"The json block isn't valid JSON: {exc}") from exc

    try:
        return EnvironmentReport.from_dict(data)
    except (KeyError, ValueError) as exc:
        raise ValueError(f"Report is missing a field or has an invalid value: {exc}") from exc


def append_to_community_reports(report: EnvironmentReport, path: Path = COMMUNITY_REPORTS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(report.to_dict()) + "\n")


def load_community_reports(path: Path = COMMUNITY_REPORTS_PATH) -> list[EnvironmentReport]:
    if not path.exists():
        return []

    reports = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                reports.append(EnvironmentReport.from_dict(json.loads(line)))
    return reports
