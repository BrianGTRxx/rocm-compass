"""The one shared definition of what a `--submit` GitHub issue looks like:
doctor/cli.py builds this exact format, compass/ingest.py's regex-based
parser expects it. Kept in shared/ (not doctor/ or compass/) so neither
module has to import the other just to agree on this shape.
"""

from __future__ import annotations

import json

from shared.schema import EnvironmentReport

GITHUB_REPO = "BrianGTRxx/rocm-compass"


def build_issue_title(report: EnvironmentReport) -> str:
    return f"[report] {report.package.name}=={report.package.version} on {report.snapshot.gpu_arch} -> {report.outcome.value}"


def build_issue_body(report: EnvironmentReport) -> str:
    payload = json.dumps(report.to_dict(), indent=2)
    return f"Submitted via `rocm-doctor check --report --submit`.\n\n```json\n{payload}\n```\n"
