"""Compatibility resolver: given a detected (likely broken) environment,
find the nearest known-good node in the compatibility graph and the
minimum-cost path of changes to reach it.

This is the module's core differentiator (see docs/rocm-compass-plan.md,
section 4.1): a small weighted graph-search problem instead of a flat
rules table.
"""

from __future__ import annotations

import heapq
import json
from dataclasses import dataclass
from pathlib import Path

from shared.schema import EnvironmentSnapshot
from shared.versions import version_distance

GRAPH_PATH = Path(__file__).parent / "compatibility_graph.json"


@dataclass(frozen=True)
class GraphNode:
    id: str
    gpu_arch: str
    rocm_version: str
    kernel_version: str
    package_name: str
    package_version: str
    source: str
    amdgpu_driver_version: str | None = None


@dataclass(frozen=True)
class ResolutionStep:
    target: GraphNode
    total_cost: int


def load_graph(path: Path = GRAPH_PATH) -> tuple[dict[str, GraphNode], dict[str, list[tuple[str, int]]]]:
    """Returns (nodes_by_id, adjacency) where adjacency maps node_id -> [(neighbor_id, cost), ...].
    Edges are treated as undirected: moving a config in either direction is possible,
    though a future version could weight directions differently (e.g. downgrading a
    package is cheaper than upgrading one that isn't released yet).
    """
    data = json.loads(path.read_text(encoding="utf-8"))

    nodes: dict[str, GraphNode] = {}
    for raw in data["nodes"]:
        nodes[raw["id"]] = GraphNode(
            id=raw["id"],
            gpu_arch=raw["gpu_arch"],
            rocm_version=raw["rocm_version"],
            kernel_version=raw["kernel_version"],
            package_name=raw["package"]["name"],
            package_version=raw["package"]["version"],
            source=raw.get("source", "unknown"),
            amdgpu_driver_version=raw.get("amdgpu_driver_version"),
        )

    adjacency: dict[str, list[tuple[str, int]]] = {node_id: [] for node_id in nodes}
    for edge in data["edges"]:
        adjacency[edge["from"]].append((edge["to"], edge["cost"]))
        adjacency[edge["to"]].append((edge["from"], edge["cost"]))

    return nodes, adjacency


def _distance_to_snapshot(node: GraphNode, snapshot: EnvironmentSnapshot, package_name: str) -> int:
    """Heuristic distance from a detected (possibly imperfect) snapshot to a graph
    node -- how much this node's own configuration differs from what was actually
    detected. Used as the *entry cost* for that node in `_dijkstra_multi_source`,
    not discarded once an "entry point" is picked (see that function's docstring
    for why that distinction matters).
    """
    distance = 0
    distance += 0 if node.gpu_arch == snapshot.gpu_arch else 5
    distance += version_distance(node.rocm_version, snapshot.rocm_version)
    distance += 0 if node.kernel_version == snapshot.kernel_version else 1
    distance += 0 if node.package_name == package_name else 3
    return distance


def _dijkstra_multi_source(adjacency: dict[str, list[tuple[str, int]]], entry_costs: dict[str, int]) -> dict[str, int]:
    """Dijkstra seeded from EVERY node at once, each starting at its own
    `entry_costs[node]` instead of a single node starting at 0.

    This used to pick one "closest" node via `_distance_to_snapshot` and run
    Dijkstra from it at cost 0 -- which silently threw away that node's own
    distance from the snapshot. An environment that didn't exactly match any
    graph node (the common case: real ROCm patch versions vary continuously)
    could still get told "cost 0, you're already on a known-good config",
    which is false. Seeding every node with its real entry cost fixes that:
    the reported total_cost now reflects "how different is my real environment
    from a known-good one", not just "how many edges are between two graph
    nodes that both assume perfect detection".
    """
    costs = dict(entry_costs)
    queue: list[tuple[int, str]] = [(cost, node_id) for node_id, cost in entry_costs.items()]
    heapq.heapify(queue)
    visited: set[str] = set()

    while queue:
        cost, current = heapq.heappop(queue)
        if current in visited:
            continue
        visited.add(current)

        for neighbor, edge_cost in adjacency.get(current, []):
            new_cost = cost + edge_cost
            if new_cost < costs.get(neighbor, float("inf")):
                costs[neighbor] = new_cost
                heapq.heappush(queue, (new_cost, neighbor))

    return costs


def resolve(snapshot: EnvironmentSnapshot, package_name: str) -> ResolutionStep | None:
    """Find the best reachable known-good node for the given environment + package.

    Every node is a potential entry point, seeded with its own distance from
    the detected snapshot; Dijkstra then finds, for each node, the cheapest
    combination of "how far is this from what I detected" plus "how many
    edges to get there from a plausible entry point". The returned cost is
    the minimum of that over every node matching `package_name`.
    """
    nodes, adjacency = load_graph()
    if not nodes:
        return None

    entry_costs = {
        node_id: _distance_to_snapshot(node, snapshot, package_name)
        for node_id, node in nodes.items()
    }
    reachable_costs = _dijkstra_multi_source(adjacency, entry_costs)

    candidates = [
        (node_id, cost)
        for node_id, cost in reachable_costs.items()
        if nodes[node_id].package_name == package_name
    ]
    if not candidates:
        return None

    best_id, best_cost = min(candidates, key=lambda pair: pair[1])
    return ResolutionStep(target=nodes[best_id], total_cost=best_cost)
