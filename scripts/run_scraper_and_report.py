"""Run weekly by .github/workflows/scrape-rocm-mentions.yml: scans every
tracked package for new ROCm-mentioning releases and prints a Markdown
summary to stdout. Empty output means nothing new was found -- the workflow
skips opening an issue in that case.

A human still has to look at the summary and decide whether to update
compass/packages.json: a release mentioning ROCm doesn't by itself tell you
whether support actually improved (see how much research the current
entries needed) -- this script's job stops at "here's something to check."
"""

from __future__ import annotations

from compass.scraper import run


def main() -> None:
    findings = run()
    if not findings:
        return

    print("New releases mentioning ROCm/AMD since each package's `last_checked` date:")
    print()
    for name, matches in findings.items():
        print(f"### {name}")
        for match in matches:
            print(f"- [{match['tag_name']}]({match['url']}) -- {match['published_at']}")
        print()
    print("Update `compass/packages.json` (status/notes/last_checked) if any of these actually change the picture.")


if __name__ == "__main__":
    main()
