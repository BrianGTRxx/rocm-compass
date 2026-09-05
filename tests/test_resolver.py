"""Sanity checks for the resolver against the real compatibility graph
(sourced from AMD's official ROCm docs, see doctor/compatibility_graph.json
'sources'). If AMD ships a new ROCm/torch pairing and the graph gets updated,
these expectations should move with it.
"""

from shared.schema import EnvironmentSnapshot
from doctor.resolver import resolve


def test_exact_match_has_zero_cost():
    snapshot = EnvironmentSnapshot(
        gpu_arch="gfx90a",
        rocm_version="6.3.2",
        kernel_version="5.15.x / 6.8.x (Ubuntu 22.04.5) or 6.1.0 (Debian 12)",
    )

    resolution = resolve(snapshot, "torch")

    assert resolution is not None
    assert resolution.target.id == "rocm6.3.2-gfx90a-torch2.4.0"
    assert resolution.total_cost == 0


def test_older_rocm_resolves_towards_a_newer_known_good_node():
    snapshot = EnvironmentSnapshot(
        gpu_arch="gfx942",
        rocm_version="6.3.2",
        kernel_version="unknown",
    )

    resolution = resolve(snapshot, "torch")

    assert resolution is not None
    assert resolution.target.gpu_arch == "gfx942"
    assert resolution.target.rocm_version == "6.3.2"
    # rocm_version matches exactly, but kernel_version doesn't (we only know
    # "unknown", not the real string) -- that residual mismatch must show up
    # as cost, not get silently discarded (see test below for why that matters).
    assert resolution.total_cost == 1


def test_unknown_package_has_no_resolution():
    snapshot = EnvironmentSnapshot(gpu_arch="gfx90a", rocm_version="6.3.2", kernel_version="unknown")

    resolution = resolve(snapshot, "some-package-not-in-the-graph")

    assert resolution is None


def test_a_rocm_version_absent_from_the_graph_never_reports_zero_cost():
    """Regression test: the old single-entry-point algorithm picked whichever
    node was "closest" by a flat heuristic and then ran Dijkstra from it at
    cost 0, discarding that node's own distance from the real snapshot. A
    real environment on a ROCm version nowhere near the graph (simulated here
    with a made-up 7.9.9) could get told "cost 0, you're already fine" while
    pointing at the graph's *oldest* node -- false in both the cost and the
    implied "no changes needed". Verified failing before the multi-source
    Dijkstra fix in doctor/resolver.py.
    """
    snapshot = EnvironmentSnapshot(gpu_arch="gfx1100", rocm_version="7.9.9", kernel_version="does-not-matter")

    resolution = resolve(snapshot, "torch")

    assert resolution is not None
    assert resolution.total_cost > 0


def test_a_nearby_untracked_version_costs_less_than_a_distant_one():
    """rocm 6.3.5 (a patch version one step from the graph's 6.3.2) should be
    reported as closer to a known-good config than rocm 7.9.9 -- proving the
    resolver compares versions numerically, not as an exact-match-or-not flag.
    """
    close = resolve(EnvironmentSnapshot(gpu_arch="gfx1100", rocm_version="6.3.5", kernel_version="?"), "torch")
    far = resolve(EnvironmentSnapshot(gpu_arch="gfx1100", rocm_version="7.9.9", kernel_version="?"), "torch")

    assert close is not None and far is not None
    assert close.total_cost < far.total_cost
