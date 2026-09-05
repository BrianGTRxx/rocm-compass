# Contributing

This project grows mainly from real usage, not manual curation. The most valuable contribution most people can make doesn't require touching code at all.

## Report your environment (the highest-value contribution)

If you run `rocm-doctor check --report` (see `COMO_EJECUTAR.md`), an anonymized snapshot of your GPU architecture, ROCm/kernel versions, the package you tried, and whether it worked gets added to the shared dataset in `shared/`. That dataset is what powers the Compass compatibility matrix -- so every report makes the tool more accurate for the next person, especially for combinations the maintainer has no hardware to test personally (see `docs/rocm-compass-plan.md` section 7).

No report is sent without the `--report` flag, and it never includes anything beyond architecture/version/outcome.

## Contribute compatibility data manually

If you've hit (or solved) a version mismatch that isn't in `doctor/compatibility_graph.json` yet, or know a package's ROCm support status that isn't reflected in `compass/packages.json`, open an issue or a PR with:

- The exact versions involved (GPU arch, ROCm, kernel, package)
- Whether it worked, partially worked, or failed
- A source if you have one (release notes, GitHub issue/PR, your own benchmark)

## Code contributions

- `doctor/` -- detection logic and the compatibility resolver (see `doctor/resolver.py`)
- `compass/` -- the scraper and the API serving the matrix
- `shared/` -- the schema connecting both

Open an issue before large changes so we can check they fit the project's scope (see `docs/rocm-compass-plan.md` section 3 for what this project deliberately does *not* do -- CUDA-to-HIP code migration/translation is out of scope).

## Development setup

See `COMO_EJECUTAR.md`.
