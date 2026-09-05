"""Complementary data source for the Compass matrix: scans each tracked
package's GitHub releases for ROCm/HIP/AMD mentions published since that
package's last_checked date.

This is secondary to the Doctor --report loop -- it exists to surface a
signal ("hey, torch's release notes just mentioned ROCm again, go check if
anything changed") for a maintainer to act on, not to auto-update
compass/packages.json's status/notes fields itself. Deciding whether a
release actually changes a package's ROCm support status needs human
judgment (see how much research went into the current entries) -- the
scraper's job stops at "here's something worth looking at."
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

PACKAGES_PATH = Path(__file__).parent / "packages.json"
GITHUB_API = "https://api.github.com"

ROCM_KEYWORDS = ("rocm", "hip", "amd gpu", "gfx9", "instinct")


def load_packages() -> list[dict]:
    data = json.loads(PACKAGES_PATH.read_text(encoding="utf-8"))
    return data["packages"]


def mentions_rocm(text: str) -> bool:
    lowered = (text or "").lower()
    return any(keyword in lowered for keyword in ROCM_KEYWORDS)


def fetch_recent_releases(github_repo: str, limit: int = 5) -> list[dict]:
    """Real (unauthenticated) call to GitHub's releases API -- 60 req/hour is
    enough for a weekly scan of a dozen packages. Returns [] on any failure
    (rate limit, repo renamed/private, network hiccup) instead of raising,
    since one package failing to fetch shouldn't crash the whole scan.
    """
    url = f"{GITHUB_API}/repos/{github_repo}/releases?per_page={limit}"
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "rocm-compass-scraper"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read())
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
        return []


def find_new_rocm_mentions(package: dict, releases: list[dict]) -> list[dict]:
    """Pure and testable: given already-fetched releases, returns the ones
    published after `package["last_checked"]` whose body mentions ROCm.
    Filtering by date matters -- without it, the same old release (e.g. the
    one that's already the cited `source` for a package) would resurface as
    a "new" finding every single week.
    """
    last_checked = package.get("last_checked", "1970-01-01")

    matches = []
    for release in releases:
        published_at = (release.get("published_at") or "")[:10]
        if not published_at or published_at <= last_checked:
            continue
        if mentions_rocm(release.get("body", "")):
            matches.append({
                "tag_name": release.get("tag_name"),
                "url": release.get("html_url"),
                "published_at": published_at,
            })
    return matches


def run(packages: list[dict] | None = None, fetch=fetch_recent_releases) -> dict[str, list[dict]]:
    """Scans every tracked package that has a `github_repo`. Returns
    {package_name: [matches]} for packages with at least one new
    ROCm-mentioning release. `fetch` is injectable so tests don't hit the
    real network (see tests/test_scraper.py).
    """
    packages = packages if packages is not None else load_packages()

    findings: dict[str, list[dict]] = {}
    for package in packages:
        github_repo = package.get("github_repo")
        if not github_repo:
            continue
        releases = fetch(github_repo)
        matches = find_new_rocm_mentions(package, releases)
        if matches:
            findings[package["name"]] = matches
    return findings


if __name__ == "__main__":
    findings = run()
    if not findings:
        print("No new ROCm-mentioning releases since each package's last_checked date.")
    for name, matches in findings.items():
        print(f"{name}:")
        for match in matches:
            print(f"  {match['tag_name']} ({match['published_at']}) -- {match['url']}")
