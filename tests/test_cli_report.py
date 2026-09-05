from doctor.cli import _submit_report
from shared.schema import EnvironmentSnapshot
from shared.store import load_reports


def test_submit_report_saves_when_valid(tmp_path):
    db_path = tmp_path / "reports.db"
    snapshot = EnvironmentSnapshot(gpu_arch="gfx90a", rocm_version="6.4.3", kernel_version="6.8.0")

    result = _submit_report(
        snapshot=snapshot,
        rocm_not_detected=False,
        package="torch",
        outcome="worked",
        notes="fresh install, worked first try",
        package_version_override="2.9.0",
        db_path=db_path,
    )

    assert "error" not in result
    assert result["package_version"] == "2.9.0"
    assert result["outcome"] == "worked"

    saved = load_reports(db_path=db_path)
    assert len(saved) == 1
    assert saved[0].notes == "fresh install, worked first try"


def test_submit_report_rejects_missing_outcome(tmp_path):
    db_path = tmp_path / "reports.db"
    snapshot = EnvironmentSnapshot(gpu_arch="gfx90a", rocm_version="6.4.3", kernel_version="6.8.0")

    result = _submit_report(
        snapshot=snapshot,
        rocm_not_detected=False,
        package="torch",
        outcome=None,
        notes="",
        package_version_override="2.9.0",
        db_path=db_path,
    )

    assert "error" in result
    assert load_reports(db_path=db_path) == []


def test_submit_report_rejects_when_rocm_not_detected(tmp_path):
    db_path = tmp_path / "reports.db"
    snapshot = EnvironmentSnapshot(gpu_arch="unknown", rocm_version="unknown", kernel_version="10")

    result = _submit_report(
        snapshot=snapshot,
        rocm_not_detected=True,
        package="torch",
        outcome="worked",
        notes="",
        package_version_override="2.9.0",
        db_path=db_path,
    )

    assert "error" in result
    assert load_reports(db_path=db_path) == []


def test_submit_report_rejects_undetectable_package_version(tmp_path):
    db_path = tmp_path / "reports.db"
    snapshot = EnvironmentSnapshot(gpu_arch="gfx90a", rocm_version="6.4.3", kernel_version="6.8.0")

    result = _submit_report(
        snapshot=snapshot,
        rocm_not_detected=False,
        package="a-package-that-is-definitely-not-installed",
        outcome="worked",
        notes="",
        package_version_override=None,
        db_path=db_path,
    )

    assert "error" in result
    assert load_reports(db_path=db_path) == []
