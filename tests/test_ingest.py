import pytest

from compass.ingest import append_to_community_reports, load_community_reports, parse_report_issue_body
from shared.schema import EnvironmentReport, EnvironmentSnapshot, PackageVersion, ReportOutcome

VALID_BODY = """
Some human-written preamble the reporter added.

```json
{
  "gpu_arch": "gfx942",
  "rocm_version": "7.0.0",
  "kernel_version": "6.8.0-generic",
  "amdgpu_driver_version": "30.10.1",
  "package_name": "vllm",
  "package_version": "0.14.0",
  "outcome": "worked",
  "notes": "official wheel, no issues",
  "source": "community",
  "reported_at": "2026-09-05T12:00:00+00:00"
}
```

Thanks!
"""


def test_parses_a_valid_issue_body():
    report = parse_report_issue_body(VALID_BODY)

    assert report.snapshot.gpu_arch == "gfx942"
    assert report.package.name == "vllm"
    assert report.outcome == ReportOutcome.WORKED


def test_rejects_a_body_with_no_json_block():
    with pytest.raises(ValueError, match="No ```json code block"):
        parse_report_issue_body("just some text, no code block here")


def test_rejects_malformed_json():
    # Brace-balanced (so the regex finds a block) but invalid JSON (trailing comma).
    body = '```json\n{"gpu_arch": "gfx90a",}\n```'
    with pytest.raises(ValueError, match="isn't valid JSON"):
        parse_report_issue_body(body)


def test_rejects_a_report_missing_a_required_field():
    body = '```json\n{"gpu_arch": "gfx90a"}\n```'
    with pytest.raises(ValueError, match="missing a field or has an invalid value"):
        parse_report_issue_body(body)


def test_rejects_an_invalid_outcome_value():
    body = VALID_BODY.replace('"outcome": "worked"', '"outcome": "sort_of_worked_i_guess"')
    with pytest.raises(ValueError, match="missing a field or has an invalid value"):
        parse_report_issue_body(body)


def test_append_and_load_round_trip(tmp_path):
    path = tmp_path / "community_reports.jsonl"
    report = EnvironmentReport(
        snapshot=EnvironmentSnapshot(gpu_arch="gfx90a", rocm_version="6.4.3", kernel_version="6.8.0"),
        package=PackageVersion(name="torch", version="2.9.0"),
        outcome=ReportOutcome.WORKED,
    )

    append_to_community_reports(report, path=path)
    append_to_community_reports(report, path=path)

    loaded = load_community_reports(path=path)
    assert len(loaded) == 2
    assert loaded[0].package.name == "torch"


def test_load_missing_file_returns_empty_list(tmp_path):
    assert load_community_reports(path=tmp_path / "does-not-exist.jsonl") == []
