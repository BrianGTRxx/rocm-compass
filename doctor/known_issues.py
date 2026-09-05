"""Matches raw log/error text against doctor/known_issues.json.

Complements the compatibility resolver (doctor/resolver.py): the resolver
handles "which versions should I install", this handles "my versions are
fine but something else about the environment is broken" (permissions,
env vars, upstream ABI regressions) -- issues that aren't a point in the
compatibility graph.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

ISSUES_PATH = Path(__file__).parent / "known_issues.json"


@dataclass(frozen=True)
class KnownIssue:
    id: str
    symptom: str
    cause: str
    fix: str
    severity: str
    sources: tuple[str, ...]
    caveats: str = ""


def load_known_issues(path: Path = ISSUES_PATH) -> list[tuple[re.Pattern, KnownIssue]]:
    data = json.loads(path.read_text(encoding="utf-8"))

    compiled: list[tuple[re.Pattern, KnownIssue]] = []
    for raw in data["issues"]:
        pattern = re.compile(raw["match_pattern"])
        issue = KnownIssue(
            id=raw["id"],
            symptom=raw["symptom"],
            cause=raw["cause"],
            fix=raw["fix"],
            severity=raw["severity"],
            sources=tuple(raw.get("sources", [])),
            caveats=raw.get("caveats", ""),
        )
        compiled.append((pattern, issue))

    return compiled


def match_known_issues(log_text: str) -> list[KnownIssue]:
    """Return every known issue whose pattern is found in the given log text."""
    matches = []
    for pattern, issue in load_known_issues():
        if pattern.search(log_text):
            matches.append(issue)
    return matches
