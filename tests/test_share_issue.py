"""IMPORTANT: `gh` is genuinely installed and authenticated on the dev
machine this was written on. Every test here mocks `shutil.which` and
`subprocess.run` at the `doctor.cli` import site -- none of them may ever
invoke the real `gh` binary, or running the test suite would file real
issues against the live repo.
"""

from doctor.cli import _share_via_github_issue
from shared.issue_format import GITHUB_REPO
from shared.schema import EnvironmentReport, EnvironmentSnapshot, PackageVersion, ReportOutcome


def _sample_report() -> EnvironmentReport:
    return EnvironmentReport(
        snapshot=EnvironmentSnapshot(gpu_arch="gfx90a", rocm_version="6.4.3", kernel_version="6.8.0"),
        package=PackageVersion(name="torch", version="2.9.0"),
        outcome=ReportOutcome.WORKED,
    )


def test_falls_back_to_a_prefilled_url_when_gh_is_not_installed(monkeypatch):
    monkeypatch.setattr("doctor.cli.shutil.which", lambda name: None)

    message = _share_via_github_issue(_sample_report())

    assert "Open this URL" in message
    assert f"github.com/{GITHUB_REPO}/issues/new" in message


def test_uses_gh_issue_create_when_available(monkeypatch):
    captured_args = {}

    class FakeCompletedProcess:
        returncode = 0
        stdout = "https://github.com/BrianGTRxx/rocm-compass/issues/42\n"

    def fake_run(args, **kwargs):
        captured_args["args"] = args
        return FakeCompletedProcess()

    monkeypatch.setattr("doctor.cli.shutil.which", lambda name: "/usr/bin/gh")
    monkeypatch.setattr("doctor.cli.subprocess.run", fake_run)

    message = _share_via_github_issue(_sample_report())

    assert "Issue created" in message
    assert "issues/42" in message
    assert captured_args["args"][0] == "/usr/bin/gh"
    assert "--repo" in captured_args["args"]
    assert GITHUB_REPO in captured_args["args"]


def test_falls_back_to_url_when_gh_command_fails(monkeypatch):
    class FakeCompletedProcess:
        returncode = 1
        stdout = ""

    monkeypatch.setattr("doctor.cli.shutil.which", lambda name: "/usr/bin/gh")
    monkeypatch.setattr("doctor.cli.subprocess.run", lambda *a, **k: FakeCompletedProcess())

    message = _share_via_github_issue(_sample_report())

    assert "Open this URL" in message
