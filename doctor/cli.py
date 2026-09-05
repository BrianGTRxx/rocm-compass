"""`rocm-doctor` command-line entry point.

Usage (once installed, see COMO_EJECUTAR.md):
    rocm-doctor check
    rocm-doctor check --json
    rocm-doctor check --package torch --report --outcome worked
    rocm-doctor check --log-file /path/to/rocminfo_error.txt
"""

from __future__ import annotations

import json
from pathlib import Path

import typer

from doctor.detectors import detect_environment, detect_installed_package_version
from doctor.known_issues import match_known_issues
from doctor.resolver import resolve
from shared.schema import EnvironmentReport, EnvironmentSnapshot, PackageVersion, ReportOutcome
from shared.store import DB_PATH, save_report

app = typer.Typer(help="Diagnose a ROCm installation and resolve it towards a known-good configuration.")


@app.callback()
def _main() -> None:
    """Kept even though `check` is the only command: Typer collapses a
    single-command app into a no-subcommand CLI, which would silently break
    every `rocm-doctor check ...` example in the docs. This callback forces
    Typer to keep requiring the subcommand name, so `check` (and any future
    sibling command, e.g. `report`) works the way the docs describe.
    """


@app.command()
def check(
    package: str = typer.Option("torch", help="Package you want to get working, e.g. torch, flash-attn."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON instead of a text report."),
    report: bool = typer.Option(
        False,
        "--report",
        help="Opt-in: save this (anonymized) result to shared/reports.db, feeding the community-wide compatibility matrix.",
    ),
    outcome: str = typer.Option(
        None,
        "--outcome",
        help="Required with --report: did `package` end up working on this environment? worked | failed | partial.",
    ),
    notes: str = typer.Option(
        "",
        "--notes",
        help="Optional free-text context to attach to the report (e.g. what fixed it).",
    ),
    package_version: str = typer.Option(
        None,
        "--package-version",
        help="Version of `package` actually installed, if it can't be auto-detected via pip metadata (e.g. installed from source).",
    ),
    log_file: Path = typer.Option(
        None,
        "--log-file",
        help="Path to a saved error log (e.g. rocminfo/rocm-smi stderr) to scan against known environment issues.",
    ),
) -> None:
    snapshot = detect_environment()
    rocm_not_detected = snapshot.gpu_arch == "unknown" and snapshot.rocm_version == "unknown"
    # Without a detected GPU arch, resolve()'s "closest node" heuristic would still
    # pick *some* node and report it with a misleadingly confident cost (often 0),
    # as if the environment were already known-good. Skip resolution entirely
    # instead of reporting a guess as a finding.
    resolution = None if rocm_not_detected else resolve(snapshot, package)
    known_issues = match_known_issues(log_file.read_text(encoding="utf-8")) if log_file else []

    report_result: dict | None = None
    if report:
        report_result = _submit_report(
            snapshot=snapshot,
            rocm_not_detected=rocm_not_detected,
            package=package,
            outcome=outcome,
            notes=notes,
            package_version_override=package_version,
        )

    if json_output:
        payload = {
            "detected": {
                "gpu_arch": snapshot.gpu_arch,
                "rocm_version": snapshot.rocm_version,
                "kernel_version": snapshot.kernel_version,
            },
            "package": package,
            "rocm_detected": not rocm_not_detected,
            "resolution": None,
            "known_issues": [issue.id for issue in known_issues],
            "report": report_result,
        }
        if resolution is not None:
            payload["resolution"] = {
                "target_rocm_version": resolution.target.rocm_version,
                "target_package_version": resolution.target.package_version,
                "target_amdgpu_driver_version": resolution.target.amdgpu_driver_version,
                "total_cost": resolution.total_cost,
            }
        typer.echo(json.dumps(payload, indent=2))
    else:
        typer.echo(f"Detected: gpu_arch={snapshot.gpu_arch} rocm={snapshot.rocm_version} kernel={snapshot.kernel_version}")
        if rocm_not_detected:
            typer.echo("Could not detect a ROCm installation on this system (rocminfo/rocm-smi not found or unreadable).")
            typer.echo("If ROCm is installed, check that rocminfo/rocm-smi are on PATH and that this user can access /dev/kfd (see --log-file for permission-style errors).")
        elif resolution is None:
            typer.echo(f"No known-good path found yet for '{package}' with this environment.")
            typer.echo("This usually means the compatibility graph doesn't have enough data yet -- consider running with --report once you find a fix.")
        else:
            typer.echo(
                f"Recommendation: move to rocm={resolution.target.rocm_version}, "
                f"{package}={resolution.target.package_version} "
                f"(amdgpu driver {resolution.target.amdgpu_driver_version or 'unspecified'}; "
                f"estimated change cost: {resolution.total_cost})"
            )

        if known_issues:
            typer.echo("")
            typer.echo(f"Known environment issues matched in {log_file}:")
            for issue in known_issues:
                typer.echo(f"  [{issue.severity}] {issue.id}")
                typer.echo(f"    Symptom: {issue.symptom}")
                typer.echo(f"    Cause: {issue.cause}")
                typer.echo(f"    Fix: {issue.fix}")
                if issue.caveats:
                    typer.echo(f"    Caveats: {issue.caveats}")

        if report_result is not None:
            typer.echo("")
            if report_result.get("error"):
                typer.echo(f"Report not saved: {report_result['error']}")
            else:
                typer.echo(
                    f"Report #{report_result['id']} saved: {package}=={report_result['package_version']} "
                    f"-> {report_result['outcome']} (shared/reports.db)"
                )

    if report_result is not None and report_result.get("error"):
        raise typer.Exit(code=1)


def _submit_report(
    *,
    snapshot: EnvironmentSnapshot,
    rocm_not_detected: bool,
    package: str,
    outcome: str | None,
    notes: str,
    package_version_override: str | None,
    db_path: Path = DB_PATH,
) -> dict:
    """Validates and saves one --report submission. Returns a dict describing
    what happened (either {"error": ...} or the saved report's fields) so the
    caller can render it in either text or --json mode. `db_path` defaults to
    the real shared/reports.db but can be overridden (see tests/test_cli_report.py)
    so exercising this doesn't write into the real database.
    """
    if rocm_not_detected:
        return {"error": "no ROCm environment was detected on this system -- nothing to report."}

    if outcome not in {o.value for o in ReportOutcome}:
        return {"error": "--report requires --outcome worked|failed|partial."}

    resolved_version = package_version_override or detect_installed_package_version(package)
    if resolved_version is None:
        return {
            "error": (
                f"could not detect an installed version of '{package}' via pip metadata "
                "-- pass --package-version explicitly."
            )
        }

    report = EnvironmentReport(
        snapshot=snapshot,
        package=PackageVersion(name=package, version=resolved_version),
        outcome=ReportOutcome(outcome),
        notes=notes,
    )
    report_id = save_report(report, db_path=db_path)

    return {
        "id": report_id,
        "package_version": resolved_version,
        "outcome": outcome,
    }


if __name__ == "__main__":
    app()
