from compass.aggregate import aggregate_reports_by_package
from compass.ingest import append_to_community_reports
from shared.schema import EnvironmentReport, EnvironmentSnapshot, PackageVersion, ReportOutcome
from shared.store import save_report


def test_empty_package_has_zero_reports(tmp_path):
    db_path = tmp_path / "reports.db"
    community_path = tmp_path / "community_reports.jsonl"

    aggregate = aggregate_reports_by_package("torch", db_path=db_path, community_path=community_path)

    assert aggregate == {
        "total_reports": 0,
        "worked": 0,
        "failed": 0,
        "partial": 0,
        "known_good_combos": [],
    }


def test_aggregate_counts_outcomes_and_known_good_combos(tmp_path):
    db_path = tmp_path / "reports.db"
    community_path = tmp_path / "community_reports.jsonl"
    snapshot = EnvironmentSnapshot(gpu_arch="gfx90a", rocm_version="6.4.3", kernel_version="6.8.0")

    save_report(
        EnvironmentReport(
            snapshot=snapshot,
            package=PackageVersion(name="torch", version="2.9.0"),
            outcome=ReportOutcome.WORKED,
        ),
        db_path=db_path,
    )
    save_report(
        EnvironmentReport(
            snapshot=snapshot,
            package=PackageVersion(name="torch", version="2.9.0"),
            outcome=ReportOutcome.FAILED,
        ),
        db_path=db_path,
    )
    save_report(
        EnvironmentReport(
            snapshot=snapshot,
            package=PackageVersion(name="vllm", version="0.14.0"),
            outcome=ReportOutcome.WORKED,
        ),
        db_path=db_path,
    )

    aggregate = aggregate_reports_by_package("torch", db_path=db_path, community_path=community_path)

    assert aggregate["total_reports"] == 2
    assert aggregate["worked"] == 1
    assert aggregate["failed"] == 1
    assert aggregate["known_good_combos"] == ["gfx90a + rocm6.4.3 + torch==2.9.0"]


def test_aggregate_merges_local_db_and_community_jsonl(tmp_path):
    """The two transports (this machine's local --report, and third-party
    reports ingested from GitHub Issues into community_reports.jsonl) must
    both count towards the same package's aggregate.
    """
    db_path = tmp_path / "reports.db"
    community_path = tmp_path / "community_reports.jsonl"
    snapshot = EnvironmentSnapshot(gpu_arch="gfx942", rocm_version="7.0.0", kernel_version="6.8.0")

    save_report(
        EnvironmentReport(
            snapshot=snapshot,
            package=PackageVersion(name="vllm", version="0.14.0"),
            outcome=ReportOutcome.WORKED,
            source="local",
        ),
        db_path=db_path,
    )
    append_to_community_reports(
        EnvironmentReport(
            snapshot=snapshot,
            package=PackageVersion(name="vllm", version="0.14.0"),
            outcome=ReportOutcome.WORKED,
            source="community",
        ),
        path=community_path,
    )

    aggregate = aggregate_reports_by_package("vllm", db_path=db_path, community_path=community_path)

    assert aggregate["total_reports"] == 2
    assert aggregate["worked"] == 2
