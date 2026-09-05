"""Compares dotted version strings (ROCm/package versions) numerically
instead of lexicographically. Plain string comparison breaks the moment a
segment reaches two digits: "6.10.0" sorts *before* "6.3.2" as text even
though it's the newer version -- this showed up both in the resolver's
"how close is this node to what I detected" heuristic (doctor/resolver.py)
and in the Obsidian generator's node ordering (scripts/generate_obsidian_notes.py).
"""

from __future__ import annotations


def parse_version(version: str) -> tuple[int, ...] | None:
    """"6.3.2" -> (6, 3, 2). None if it isn't a plain dotted-integer version
    (free-form strings like "unknown" or a kernel description aren't versions
    in this sense, and shouldn't be silently mis-parsed).
    """
    try:
        return tuple(int(part) for part in version.split("."))
    except ValueError:
        return None


def version_sort_key(version: str) -> tuple:
    """Sort key that orders dotted versions numerically. Unparseable values
    sort after every numeric one (grouped together, order among themselves
    doesn't matter here) so sorting still terminates instead of raising.
    """
    parsed = parse_version(version)
    return (0, parsed) if parsed is not None else (1, version)


def version_distance(a: str, b: str, weights: tuple[int, ...] = (3, 1, 1)) -> int:
    """A small, capped numeric distance between two dotted versions, weighted
    so a major-version difference matters more than a patch difference.
    Falls back to a flat penalty of 1 if either string doesn't parse as a
    plain dotted-integer version (e.g. comparing kernel_version strings) --
    not a general semver comparator, just enough for the resolver's heuristic.
    """
    if a == b:
        return 0

    parsed_a, parsed_b = parse_version(a), parse_version(b)
    if parsed_a is None or parsed_b is None:
        return 1

    length = max(len(parsed_a), len(parsed_b), len(weights))
    padded_a = parsed_a + (0,) * (length - len(parsed_a))
    padded_b = parsed_b + (0,) * (length - len(parsed_b))
    padded_weights = weights + (1,) * (length - len(weights))

    distance = sum(abs(x - y) * w for x, y, w in zip(padded_a, padded_b, padded_weights))
    return min(distance, 5)
