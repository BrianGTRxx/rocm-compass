# Security Policy

## Reporting a vulnerability

Please report security issues privately using GitHub's [private vulnerability reporting](https://github.com/BrianGTRxx/rocm-compass/security/advisories/new) (Security tab -> Report a vulnerability) instead of opening a public issue. If that's not available, open an issue that describes the impact without exploit details and mention you'd like to disclose privately.

Please include:
- What's affected and how (a proof of concept, if you have one)
- Impact you'd expect (e.g. what an attacker could actually do)

This is a small open-source project maintained in spare time -- there's no bug bounty, but reports are taken seriously and credited in the fix.

## Supported versions

There's a single rolling `master` branch, no maintained older releases. Fixes land there.

## Scope notes

- `compass/api.py` is intentionally unauthenticated and read-only by design -- it's not a bug that it has no login.
- `rocm-doctor check --report --submit` and the GitHub Issue ingestion pipeline (`.github/workflows/ingest-reports.yml`, `compass/ingest.py`) accept free-text input from anyone who can open an issue. That data is treated as untrusted throughout -- if you find a way to turn a submitted report into code execution, a git history rewrite, or anything beyond an entry in `compass/community_reports.jsonl`, that's exactly the kind of thing to report here.
