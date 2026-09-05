# ROCm Compass

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)

> Working name -- open to a better one. See `docs/rocm-compass-plan.md` section 10.

Environment diagnostics, a compatibility resolver, and a live-tracked map of the Python AI ecosystem on AMD ROCm -- built from real, community-sourced installs instead of a manually maintained table.

## Why this exists

NVIDIA/CUDA dominates AI tooling. AMD's ROCm is a real open alternative, but two things keep people from adopting it: broken installs (version mismatches between kernel, `amdgpu` driver, ROCm, and Python packages), and not knowing in advance whether the packages they rely on (`torch`, `flash-attn`, `vllm`, ...) actually work on ROCm today.

Several projects already tackle CUDA-to-HIP *code* migration (see `docs/rocm-compass-plan.md` section 3). This project deliberately does **not** compete there. Instead it covers the two things nobody maintains publicly and continuously: **environment diagnosis + compatibility resolution**, and **ecosystem-wide visibility**, tied together by a shared feedback loop.

## What it's made of

- **`doctor/`** -- a CLI (`rocm-doctor check`) that detects your installed environment (GPU arch, ROCm version, kernel, driver) and runs it through a **compatibility resolver**: a small weighted graph search (Dijkstra) over known-good configurations, returning the minimum set of version changes to reach a working state -- not just "this is broken."
- **`compass/`** -- the public compatibility matrix (which package + version combos are known to work, on which GPU arch / ROCm version). Served as a JSON API (`compass/api.py`) and, early on, as a generated table in this README.
- **`shared/`** -- the schema both modules read and write. When someone runs `rocm-doctor check --report`, an anonymized result feeds directly into the same dataset that powers the Compass matrix. The tool gets more accurate the more it's used, without relying on manual upkeep.

Full rationale, what was deliberately *not* built, and the phased plan: [`docs/rocm-compass-plan.md`](docs/rocm-compass-plan.md).

## Status

Fase 0 and Fase 1 done: the compatibility graph (`torch` only so far) and the 12-package Compass matrix hold real, sourced data, and the Doctor CLI + resolver run end-to-end. Fase 2's data loop (`--report` -> `shared/reports.db` -> `compass/api.py`'s live `community_reports` aggregate) is now wired up too, verified with a dedicated end-to-end test (`tests/test_loop_end_to_end.py`). Still missing: a way for reports from *other people's* machines to reach that dataset once this is public (see `docs/rocm-compass-plan.md` section 10), and graph coverage beyond `torch`. See `bitacora.md` for the full history.

## Quickstart

```bash
git clone https://github.com/BrianGTRxx/rocm-compass.git
cd rocm-compass
pip install -e ".[dev]"

rocm-doctor check                 # detect + resolve towards a known-good config
rocm-doctor check --package torch --json

uvicorn compass.api:app --reload  # serve the compatibility matrix at /packages
```

Full setup (venv, tests, the `--report` data loop, the generated Obsidian vault): [`COMO_EJECUTAR.md`](COMO_EJECUTAR.md) (in Spanish -- the maintainer's working language; issues and PRs in English are equally welcome).

## Contributing

Community-reported environment results are what make the Compass matrix real data instead of a guess. See [`CONTRIBUTING.md`](CONTRIBUTING.md).

## License

[MIT](LICENSE)
