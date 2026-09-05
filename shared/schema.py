"""Shared data schema for the Doctor <-> Compass feedback loop.

An EnvironmentReport is the atomic unit both modules revolve around:
- doctor/resolver.py reads existing reports to find known-good neighbors.
- doctor/cli.py writes a new report when the user opts in via `--report`.
- compass/api.py aggregates reports into the public compatibility matrix.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class ReportOutcome(str, Enum):
    WORKED = "worked"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass(frozen=True)
class EnvironmentSnapshot:
    """The versions that together define a point in the compatibility graph."""

    gpu_arch: str  # e.g. "gfx90a", "gfx942"
    rocm_version: str  # e.g. "6.1.2"
    kernel_version: str  # e.g. "5.15.0-91-generic"
    amdgpu_driver_version: str | None = None


@dataclass(frozen=True)
class PackageVersion:
    name: str  # e.g. "torch", "flash-attn"
    version: str  # e.g. "2.3.0"


@dataclass(frozen=True)
class EnvironmentReport:
    """One anonymized submission from `rocm-doctor check --report`."""

    snapshot: EnvironmentSnapshot
    package: PackageVersion
    outcome: ReportOutcome
    notes: str = ""
    source: str = "community"  # "community" | "release_notes" | "github_issue" | "benchmark"
    reported_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "gpu_arch": self.snapshot.gpu_arch,
            "rocm_version": self.snapshot.rocm_version,
            "kernel_version": self.snapshot.kernel_version,
            "amdgpu_driver_version": self.snapshot.amdgpu_driver_version,
            "package_name": self.package.name,
            "package_version": self.package.version,
            "outcome": self.outcome.value,
            "notes": self.notes,
            "source": self.source,
            "reported_at": self.reported_at.isoformat(),
        }

    @staticmethod
    def from_dict(data: dict) -> "EnvironmentReport":
        return EnvironmentReport(
            snapshot=EnvironmentSnapshot(
                gpu_arch=data["gpu_arch"],
                rocm_version=data["rocm_version"],
                kernel_version=data["kernel_version"],
                amdgpu_driver_version=data.get("amdgpu_driver_version"),
            ),
            package=PackageVersion(
                name=data["package_name"],
                version=data["package_version"],
            ),
            outcome=ReportOutcome(data["outcome"]),
            notes=data.get("notes", ""),
            source=data.get("source", "community"),
            reported_at=datetime.fromisoformat(data["reported_at"]),
        )
