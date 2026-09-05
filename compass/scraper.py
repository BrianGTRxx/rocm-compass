"""Complementary data source for the Compass matrix: scans each tracked
package's GitHub releases/issues for ROCm/HIP/AMD mentions.

This is secondary to the Doctor --report loop (docs/rocm-compass-plan.md,
section 4.3) -- it exists to cover packages that don't yet have enough
community reports.
"""

from __future__ import annotations

import json
from pathlib import Path

PACKAGES_PATH = Path(__file__).parent / "packages.json"

ROCM_KEYWORDS = ("rocm", "hip", "amd gpu", "gfx9", "instinct")


def load_packages() -> list[dict]:
    data = json.loads(PACKAGES_PATH.read_text(encoding="utf-8"))
    return data["packages"]


def mentions_rocm(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in ROCM_KEYWORDS)


def scan_release_notes(package_name: str, release_notes: list[str]) -> list[str]:
    """Given a package's raw release note bodies (fetched via the GitHub API
    elsewhere), return the ones that mention ROCm/AMD. Kept as a pure function
    so it's testable without hitting the network -- the actual GitHub API call
    (with auth/rate-limit handling) is Fase 2 work.
    """
    return [note for note in release_notes if mentions_rocm(note)]


if __name__ == "__main__":
    for package in load_packages():
        print(f"{package['name']}: {package['status']}")
