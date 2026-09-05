"""Fase 2 checklist item, made concrete as a test: "Verificar que un reporte
nuevo del Doctor efectivamente actualiza la matriz del Compass" (see
docs/rocm-compass-plan.md section 8). Drives the Doctor side (`_submit_report`,
what `rocm-doctor check --report` calls) and the Compass side
(`aggregate_reports_by_package`, what compass/api.py serves) against the same
database, proving they're actually the same loop and not two disconnected
pieces that happen to share a schema.
"""

from compass.aggregate import aggregate_reports_by_package
from doctor.cli import _submit_report
from shared.schema import EnvironmentSnapshot


def test_a_doctor_report_shows_up_in_the_compass_matrix(tmp_path):
    db_path = tmp_path / "reports.db"
    snapshot = EnvironmentSnapshot(gpu_arch="gfx942", rocm_version="7.1.1", kernel_version="6.8.0")

    before = aggregate_reports_by_package("vllm", db_path=db_path)
    assert before["total_reports"] == 0

    result = _submit_report(
        snapshot=snapshot,
        rocm_not_detected=False,
        package="vllm",
        outcome="worked",
        notes="ran the official rocm700 wheel, worked out of the box",
        package_version_override="0.14.0",
        db_path=db_path,
    )
    assert "error" not in result

    after = aggregate_reports_by_package("vllm", db_path=db_path)
    assert after["total_reports"] == 1
    assert after["worked"] == 1
    assert after["known_good_combos"] == ["gfx942 + rocm7.1.1 + vllm==0.14.0"]

    # A different package's aggregate is unaffected by this report.
    unrelated = aggregate_reports_by_package("torch", db_path=db_path)
    assert unrelated["total_reports"] == 0
