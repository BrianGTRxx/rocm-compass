import pytest
from fastapi.testclient import TestClient

from compass.api import app, get_db_path


@pytest.fixture
def client(tmp_path):
    # Without this override, every test here would silently read (and create,
    # via CREATE TABLE IF NOT EXISTS) the real shared/reports.db -- verified:
    # running just this file used to leave that file behind in the repo.
    app.dependency_overrides[get_db_path] = lambda: tmp_path / "reports.db"
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_packages_includes_community_reports_aggregate(client):
    response = client.get("/packages")
    assert response.status_code == 200

    packages = response.json()["packages"]
    assert len(packages) == 12

    torch_entry = next(p for p in packages if p["name"] == "torch")
    assert torch_entry["status"] == "official"
    assert torch_entry["community_reports"] == {
        "total_reports": 0, "worked": 0, "failed": 0, "partial": 0, "known_good_combos": [],
    }


def test_package_detail_404_for_unknown_package(client):
    response = client.get("/packages/definitely-not-a-tracked-package")
    assert response.status_code == 404
