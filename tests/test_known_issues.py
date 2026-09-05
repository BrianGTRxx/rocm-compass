from doctor.known_issues import match_known_issues


def test_matches_real_kfd_permission_error_string():
    # Exact error string reported in https://github.com/ROCm/rocminfo/issues/34
    log = "rocminfo: Unable to open /dev/kfd read-write: Permission denied"

    matches = match_known_issues(log)

    ids = [issue.id for issue in matches]
    assert "kfd-permission-denied" in ids


def test_clean_log_matches_nothing():
    log = "rocminfo\nAgent 1\n  Name: gfx90a\n  Marketing Name: AMD Instinct MI250X"

    assert match_known_issues(log) == []
