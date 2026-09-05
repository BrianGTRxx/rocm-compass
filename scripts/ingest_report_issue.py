"""Run by .github/workflows/ingest-reports.yml whenever an issue labeled
`report` is opened/edited/labeled: reads the issue body from stdin, parses it
(compass/ingest.py), and either appends it to compass/community_reports.jsonl
or reports why it couldn't.

Usage: echo "$ISSUE_BODY" | python scripts/ingest_report_issue.py
Prints "OK: ..." and exits 0 on success, "REJECTED: <reason>" and exits 1
otherwise -- the workflow greps this to decide what to comment back.
"""

from __future__ import annotations

import sys

from compass.ingest import append_to_community_reports, parse_report_issue_body


def main() -> None:
    body = sys.stdin.read()

    try:
        report = parse_report_issue_body(body)
    except ValueError as exc:
        print(f"REJECTED: {exc}")
        sys.exit(1)

    append_to_community_reports(report)
    print(
        f"OK: {report.package.name}=={report.package.version} on {report.snapshot.gpu_arch} "
        f"-> {report.outcome.value}"
    )


if __name__ == "__main__":
    main()
