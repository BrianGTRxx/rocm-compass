from compass.scraper import fetch_recent_releases, find_new_rocm_mentions, mentions_rocm, run


def test_mentions_rocm_is_case_insensitive():
    assert mentions_rocm("Added support for ROCm 7.0") is True
    assert mentions_rocm("added support for rocm 7.0") is True
    assert mentions_rocm("just a regular CUDA release") is False
    assert mentions_rocm("") is False
    assert mentions_rocm(None) is False


def test_find_new_rocm_mentions_filters_by_date_and_content():
    package = {"name": "torch", "last_checked": "2026-06-01"}
    releases = [
        {"tag_name": "v1.0", "published_at": "2026-05-01T00:00:00Z", "body": "mentions ROCm", "html_url": "u1"},  # too old
        {"tag_name": "v2.0", "published_at": "2026-07-01T00:00:00Z", "body": "just CUDA stuff", "html_url": "u2"},  # no ROCm
        {"tag_name": "v3.0", "published_at": "2026-08-01T00:00:00Z", "body": "adds AMD Instinct support", "html_url": "u3"},  # match
    ]

    matches = find_new_rocm_mentions(package, releases)

    assert len(matches) == 1
    assert matches[0]["tag_name"] == "v3.0"
    assert matches[0]["url"] == "u3"
    assert matches[0]["published_at"] == "2026-08-01"


def test_find_new_rocm_mentions_handles_missing_fields_gracefully():
    package = {"name": "torch", "last_checked": "2020-01-01"}
    releases = [{"tag_name": "v1.0"}]  # no published_at, no body

    assert find_new_rocm_mentions(package, releases) == []


def test_run_skips_packages_without_a_github_repo():
    packages = [{"name": "no-repo-tracked"}]

    findings = run(packages=packages, fetch=lambda repo: (_ for _ in ()).throw(AssertionError("should not fetch")))

    assert findings == {}


def test_run_aggregates_matches_per_package_using_injected_fetch():
    packages = [
        {"name": "torch", "github_repo": "pytorch/pytorch", "last_checked": "2026-01-01"},
        {"name": "xformers", "github_repo": "facebookresearch/xformers", "last_checked": "2026-01-01"},
    ]

    def fake_fetch(github_repo: str):
        if github_repo == "pytorch/pytorch":
            return [{"tag_name": "v2.9.0", "published_at": "2026-02-01T00:00:00Z", "body": "ROCm 7.2 support", "html_url": "u"}]
        return []  # xformers: nothing new

    findings = run(packages=packages, fetch=fake_fetch)

    assert list(findings.keys()) == ["torch"]
    assert findings["torch"][0]["tag_name"] == "v2.9.0"


def test_fetch_recent_releases_returns_empty_list_on_network_failure(monkeypatch):
    import urllib.error

    def fake_urlopen(*args, **kwargs):
        raise urllib.error.URLError("network is down")

    monkeypatch.setattr("compass.scraper.urllib.request.urlopen", fake_urlopen)

    assert fetch_recent_releases("some/repo") == []
