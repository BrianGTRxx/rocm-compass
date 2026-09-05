# ROCm Compass

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)

Environment diagnostics, a compatibility resolver, and a live-tracked map of the Python AI ecosystem on AMD ROCm -- built from real, community-sourced installs instead of a manually maintained table.

## Why this exists

NVIDIA/CUDA dominates AI tooling. AMD's ROCm is a real open alternative, but two things keep people from adopting it: broken installs (version mismatches between kernel, `amdgpu` driver, ROCm, and Python packages), and not knowing in advance whether the packages they rely on (`torch`, `flash-attn`, `vllm`, ...) actually work on ROCm today.

Several projects already tackle CUDA-to-HIP *code* migration (HIPify and a handful of AI-assisted porting tools). This project deliberately does **not** compete there. Instead it covers the two things nobody maintains publicly and continuously: **environment diagnosis + compatibility resolution**, and **ecosystem-wide visibility**, tied together by a shared feedback loop.

## What it's made of

- **`doctor/`** -- a CLI (`rocm-doctor check`) that detects your installed environment (GPU arch, ROCm version, kernel, driver) and runs it through a **compatibility resolver**: a small weighted graph search (Dijkstra) over known-good configurations, returning the minimum set of version changes to reach a working state -- not just "this is broken."
- **`compass/`** -- the public compatibility matrix (which package + version combos are known to work, on which GPU arch / ROCm version). Served as a JSON API (`compass/api.py`) and, early on, as a generated table in this README.
- **`shared/`** -- the schema both modules read and write. When someone runs `rocm-doctor check --report`, an anonymized result feeds directly into the dataset that powers the Compass matrix. Adding `--submit` shares it beyond your own machine too: it opens a GitHub issue, which a GitHub Action automatically validates and merges into [`compass/community_reports.jsonl`](compass/community_reports.jsonl) -- no server, no manual review. The tool gets more accurate the more it's used, without relying on manual upkeep.

## Status

The compatibility graph (`torch`, `vllm`) and the 12-package Compass matrix hold real, sourced data; the Doctor CLI + resolver run end-to-end; and the full data loop works, including third-party submissions -- `rocm-doctor check --report --submit` opens a GitHub issue, `.github/workflows/ingest-reports.yml` validates and merges it into `compass/community_reports.jsonl` automatically, and `compass/api.py` serves the combined result. A weekly scraper (`.github/workflows/scrape-rocm-mentions.yml`) also flags new ROCm-mentioning releases across all 12 tracked packages for manual review. Still ahead: broader graph coverage (`flash-attn` deliberately skipped so far -- no single citable official version pin exists yet across the mainline package or its various ROCm forks/wheels).

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

## Security

Found a vulnerability? See [`SECURITY.md`](SECURITY.md) for how to report it privately.

## License

[MIT](LICENSE)

## About this project and how it was built

I'm an electronics engineer, not a software engineer by trade -- AMD and ROCm are a personal interest of mine, not my day job. The code in this repo was written with AI assistance, working alongside Claude Code (Anthropic's coding agent) for the implementation, the research verification behind the compatibility data, and most of the day-to-day engineering decisions.

What I brought to it myself: the domain grounding from my electronics engineering degree, and the rest self-taught and hands-on -- reading AMD's actual documentation, deciding what was worth building and what wasn't, and enough autonomous learning in software development to push back when something looked wrong instead of accepting it at face value.

I'm saying this openly because I think transparency matters as much as the tool itself, especially in a community that's going to look closely at the code. If that changes how you weigh a bug report or a design decision here, that's fair, and if you think this approach produced something genuinely useful anyway, that's worth knowing too.

One more thing worth being upfront about, since it tends to come up. I'm not collecting anyone's data quietly, and having an NVIDIA card in my current laptop doesn't mean I'm against AMD. I've always chosen AMD for CPUs, my machine right now runs a Ryzen 7 7735HS, and a high-end dedicated AMD GPU is genuinely on my wishlist. What I actually have today is a laptop with that Ryzen 7 7735HS paired with an NVIDIA RTX 4050, no dedicated AMD GPU. That gap is the whole reason the community-reporting loop exists in the first place, and everything it sends is opt-in, minimal, and readable before it's ever submitted (see Contributing and Security above).
