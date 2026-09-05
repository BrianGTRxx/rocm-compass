"""Environment detection: turns raw system output into an EnvironmentSnapshot.

Each detector wraps a subprocess call (rocminfo, rocm-smi, uname, etc.) and
parses its output. During development (no AMD GPU available), detectors can
be pointed at a saved log file via `from_log_text` instead of calling the
real subprocess, so the resolver and CLI can be built and tested without
ROCm hardware.
"""

from __future__ import annotations

import platform
import re
import subprocess
from importlib import metadata

from shared.schema import EnvironmentSnapshot


def _run(cmd: list[str]) -> str:
    """Run a ROCm tool and return its stdout, or '' if it isn't installed/on PATH.
    A missing binary (no ROCm installed at all, or a non-Linux dev machine like
    this one) is the single most common first-run scenario for this tool, so it
    must degrade to an 'unknown' reading instead of crashing with a traceback.
    """
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except (FileNotFoundError, OSError):
        return ""
    return result.stdout


def detect_kernel_version() -> str:
    return platform.release()


def detect_installed_package_version(package_name: str) -> str | None:
    """The version of `package_name` actually installed in this Python
    environment, via pip metadata -- used by `--report` so a submitted report
    reflects what's really installed, not the resolver's suggested target.
    """
    try:
        return metadata.version(package_name)
    except metadata.PackageNotFoundError:
        return None


def parse_rocminfo(rocminfo_output: str) -> str | None:
    """Extract the GPU architecture (e.g. 'gfx90a') from `rocminfo` output."""
    match = re.search(r"gfx[0-9a-fA-F]+", rocminfo_output)
    return match.group(0) if match else None


def parse_rocm_version(rocm_smi_output: str) -> str | None:
    """Extract the installed ROCm version from `rocm-smi --showdriverversion` output."""
    match = re.search(r"ROCm version:\s*([\d.]+)", rocm_smi_output)
    return match.group(1) if match else None


def detect_environment(rocminfo_text: str | None = None, rocm_smi_text: str | None = None) -> EnvironmentSnapshot:
    """Build a full snapshot. Pass `*_text` explicitly to test against saved logs
    instead of the live subprocess output (used until we have real AMD hardware).
    """
    rocminfo_out = rocminfo_text if rocminfo_text is not None else _run(["rocminfo"])
    rocm_smi_out = rocm_smi_text if rocm_smi_text is not None else _run(["rocm-smi", "--showdriverversion"])

    gpu_arch = parse_rocminfo(rocminfo_out)
    rocm_version = parse_rocm_version(rocm_smi_out)

    return EnvironmentSnapshot(
        gpu_arch=gpu_arch or "unknown",
        rocm_version=rocm_version or "unknown",
        kernel_version=detect_kernel_version(),
    )
