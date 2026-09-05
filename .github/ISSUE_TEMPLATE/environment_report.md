---
name: Environment report
about: Share whether a package worked on your ROCm setup -- feeds the community compatibility matrix
title: "[report] "
labels: report
---

<!--
Easiest way to fill this out: run
    rocm-doctor check --package <package> --report --outcome <worked|failed|partial> --submit
It builds this exact issue for you (via `gh issue create` if you have it, or
a pre-filled link to open in your browser otherwise).

Filling it by hand instead? Replace the block below with valid JSON in the
same shape -- an automated check reads it and adds your report to
compass/community_reports.jsonl within a few minutes, no maintainer needed.
-->

```json
{
  "gpu_arch": "",
  "rocm_version": "",
  "kernel_version": "",
  "amdgpu_driver_version": null,
  "package_name": "",
  "package_version": "",
  "outcome": "worked",
  "notes": "",
  "source": "community",
  "reported_at": "2026-01-01T00:00:00+00:00"
}
```
