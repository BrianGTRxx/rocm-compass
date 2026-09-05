# Contributing

This project grows mainly from real usage, not manual curation. The most valuable contribution most people can make doesn't require touching code at all.

## Report your environment (the highest-value contribution)

```bash
rocm-doctor check --package torch --report --outcome worked --submit
```

`--report` saves an anonymized snapshot (GPU arch, ROCm/kernel versions, the package + version, and whether it worked) locally to `shared/reports.db`. Adding `--submit` shares it with everyone else too: it opens a GitHub issue on this repo (via `gh issue create` if you have the CLI, or a pre-filled link if you don't) with the report embedded as JSON. A GitHub Action reads that issue automatically, appends the report to [`compass/community_reports.jsonl`](compass/community_reports.jsonl), comments back, and closes it -- no maintainer has to do anything by hand. That file is what `compass/api.py` reads to compute each package's `community_reports` aggregate, so every submitted report makes the matrix more accurate, especially for combinations the maintainer has no hardware to test personally (see `docs/rocm-compass-plan.md` section 7).

Prefer not to install anything? Open an issue by hand using the "Environment report" template -- same JSON shape, same automatic ingestion.

Nothing beyond architecture/version/outcome/notes is ever included, and nothing is shared unless you explicitly pass `--submit` (or open the issue yourself).

## Contribute compatibility data manually

If you've hit (or solved) a version mismatch that isn't in `doctor/compatibility_graph.json` yet, or know a package's ROCm support status that isn't reflected in `compass/packages.json`, open an issue or a PR with:

- The exact versions involved (GPU arch, ROCm, kernel, package)
- Whether it worked, partially worked, or failed
- A source if you have one (release notes, GitHub issue/PR, your own benchmark)

## Code contributions

- `doctor/` -- detection logic and the compatibility resolver (see `doctor/resolver.py`)
- `compass/` -- the scraper, the report-ingestion parser (`compass/ingest.py`), and the API serving the matrix
- `shared/` -- the schema, local storage, and the shared GitHub-issue format connecting both

Open an issue before large changes so we can check they fit the project's scope (see `docs/rocm-compass-plan.md` section 3 for what this project deliberately does *not* do -- CUDA-to-HIP code migration/translation is out of scope).

## Development setup

See `COMO_EJECUTAR.md`.
