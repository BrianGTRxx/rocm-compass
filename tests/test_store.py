from shared.schema import EnvironmentReport, EnvironmentSnapshot, PackageVersion, ReportOutcome
from shared.store import load_reports, save_report


def _make_report(**overrides) -> EnvironmentReport:
    defaults = dict(
        snapshot=EnvironmentSnapshot(gpu_arch="gfx90a", rocm_version="6.4.3", kernel_version="6.8.0"),
        package=PackageVersion(name="torch", version="2.9.0"),
        outcome=ReportOutcome.WORKED,
    )
    defaults.update(overrides)
    return EnvironmentReport(**defaults)


def test_save_and_load_round_trip(tmp_path):
    db_path = tmp_path / "reports.db"
    report = _make_report(notes="worked out of the box")

    report_id = save_report(report, db_path=db_path)
    assert report_id == 1

    loaded = load_reports(db_path=db_path)
    assert len(loaded) == 1
    assert loaded[0].snapshot.gpu_arch == "gfx90a"
    assert loaded[0].package.name == "torch"
    assert loaded[0].outcome == ReportOutcome.WORKED
    assert loaded[0].notes == "worked out of the box"


def test_load_filters_by_package(tmp_path):
    db_path = tmp_path / "reports.db"
    save_report(_make_report(package=PackageVersion(name="torch", version="2.9.0")), db_path=db_path)
    save_report(_make_report(package=PackageVersion(name="vllm", version="0.14.0")), db_path=db_path)

    torch_reports = load_reports(package_name="torch", db_path=db_path)
    assert len(torch_reports) == 1
    assert torch_reports[0].package.name == "torch"


def test_load_empty_db_returns_empty_list(tmp_path):
    db_path = tmp_path / "reports.db"
    assert load_reports(db_path=db_path) == []
