"""Generate an Obsidian vault (plain .md notes with [[wikilinks]]) from the
project's own data files: doctor/compatibility_graph.json, doctor/known_issues.json,
and compass/packages.json.

Why a generator instead of hand-written notes: the underlying JSON is the
source of truth and will grow (Fase 0 backlog adds more packages/nodes to the
graph) -- regenerating from data avoids the notes silently going stale.
Uses Obsidian's built-in graph view; no plugin required.

Usage:
    python scripts/generate_obsidian_notes.py
Then open the `obsidian/` folder as a vault in Obsidian (or as a folder
inside an existing vault).
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from shared.versions import version_sort_key

ROOT = Path(__file__).parent.parent
VAULT = ROOT / "obsidian"

ARCH_LABELS = {
    "gfx90a": "gfx90a -- AMD Instinct MI200 series (CDNA2)",
    "gfx942": "gfx942 -- AMD Instinct MI300 series (CDNA3)",
    "gfx1100": "gfx1100 -- AMD Radeon RX 7900 series (RDNA3)",
}

STATUS_LABELS = {
    "official": "Soporte oficial",
    "partial": "Soporte parcial",
    "unsupported": "Sin soporte",
}


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def load_json(relative_path: str) -> dict:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def generate_graph_nodes(graph: dict) -> dict[str, list[str]]:
    """Writes one note per compatibility-graph node. Returns {gpu_arch: [node_id, ...]}
    ordered by rocm_version, for the architecture hub notes.
    """
    nodes_by_id = {n["id"]: n for n in graph["nodes"]}

    successor: dict[str, tuple[str, int]] = {}
    predecessor: dict[str, tuple[str, int]] = {}
    for edge in graph["edges"]:
        successor[edge["from"]] = (edge["to"], edge["cost"])
        predecessor[edge["to"]] = (edge["from"], edge["cost"])

    by_arch: dict[str, list[str]] = {}
    for node in graph["nodes"]:
        by_arch.setdefault(node["gpu_arch"], []).append(node["id"])

    for arch, ids in by_arch.items():
        # Plain string sort would put "6.10.0" before "6.3.2" -- version_sort_key
        # compares the dotted segments numerically instead.
        ids.sort(key=lambda node_id: version_sort_key(nodes_by_id[node_id]["rocm_version"]))

    for node in graph["nodes"]:
        node_id = node["id"]
        lines = [
            f"# {node_id}",
            "",
            f"- **Arquitectura GPU:** [[{node['gpu_arch']}]]",
            f"- **Versión ROCm:** {node['rocm_version']}",
            f"- **Kernel:** {node['kernel_version']}",
            f"- **Driver amdgpu:** {node.get('amdgpu_driver_version', 'no especificado')}",
            f"- **Paquete:** [[{node['package']['name']}]] == {node['package']['version']}",
            f"- **Fuente:** {node.get('source', 'desconocida')}",
            f"- **Verificado:** {node.get('verified_at', 'no especificado')}",
        ]

        if node.get("notes"):
            lines += ["", "## Notas", "", node["notes"]]

        lines += ["", "## Camino de actualización", ""]
        if node_id in predecessor:
            prev_id, cost = predecessor[node_id]
            lines.append(f"- Anterior: [[{prev_id}]] (costo {cost})")
        if node_id in successor:
            next_id, cost = successor[node_id]
            lines.append(f"- Siguiente: [[{next_id}]] (costo {cost})")
        if node_id not in predecessor and node_id not in successor:
            lines.append("- Sin conexiones registradas todavía.")

        _write(VAULT / "Grafo de Compatibilidad" / f"{node_id}.md", "\n".join(lines) + "\n")

    return by_arch


def generate_architecture_hubs(by_arch: dict[str, list[str]]) -> None:
    for arch, node_ids in by_arch.items():
        label = ARCH_LABELS.get(arch, arch)
        lines = [
            f"# {label}",
            "",
            "Nodos de configuración conocidos-buenos para esta arquitectura, en orden de versión de ROCm:",
            "",
        ]
        lines += [f"{i}. [[{node_id}]]" for i, node_id in enumerate(node_ids, start=1)]
        _write(VAULT / "Arquitecturas" / f"{arch}.md", "\n".join(lines) + "\n")


def generate_packages(packages_data: dict, package_has_graph_nodes: set[str]) -> None:
    for package in packages_data["packages"]:
        name = package["name"]
        status_label = STATUS_LABELS.get(package["status"], package["status"])
        lines = [
            f"# {name}",
            "",
            f"- **Estado:** {status_label} (`{package['status']}`)",
            f"- **Última verificación:** {package.get('last_checked', 'no especificado')}",
            f"- **Fuente:** {package.get('source', 'no especificada')}",
            "",
            "## Notas",
            "",
            package.get("notes", "(sin notas)"),
            "",
            "## Nodos en el grafo de compatibilidad",
            "",
        ]
        if name in package_has_graph_nodes:
            lines.append("Este paquete ya tiene nodos reales en el grafo de compatibilidad, agrupados por arquitectura: [[gfx90a]], [[gfx942]], [[gfx1100]].")
        else:
            lines.append("Todavía no tiene nodos en el grafo de compatibilidad (`doctor/compatibility_graph.json`) -- por ahora solo está trackeado aquí, en el Compass. Pendiente para el backlog de Fase 0.")

        _write(VAULT / "Paquetes" / f"{name}.md", "\n".join(lines) + "\n")


def generate_known_issues(issues_data: dict) -> None:
    for issue in issues_data["issues"]:
        lines = [
            f"# {issue['id']}",
            "",
            f"- **Severidad:** {issue['severity']}",
            "",
            "## Síntoma",
            "",
            issue["symptom"],
            "",
            "## Causa",
            "",
            issue["cause"],
            "",
            "## Fix",
            "",
            f"```\n{issue['fix']}\n```",
        ]
        if issue.get("caveats"):
            lines += ["", "## Advertencias", "", issue["caveats"]]
        if issue.get("sources"):
            lines += ["", "## Fuentes", ""]
            lines += [f"- {url}" for url in issue["sources"]]

        _write(VAULT / "Problemas Conocidos" / f"{issue['id']}.md", "\n".join(lines) + "\n")


def generate_index(by_arch: dict, packages_data: dict, issues_data: dict) -> None:
    lines = [
        "# ROCm Compass -- Indice",
        "",
        "Vault generado automáticamente por `scripts/generate_obsidian_notes.py` a partir de",
        "`doctor/compatibility_graph.json`, `compass/packages.json` y `doctor/known_issues.json`.",
        "No edites estas notas a mano -- edita el JSON fuente y vuelve a correr el script.",
        "",
        "## Arquitecturas (grafo de compatibilidad)",
        "",
    ]
    lines += [f"- [[{arch}]]" for arch in sorted(by_arch)]

    lines += ["", "## Paquetes (Compass)", ""]
    for package in packages_data["packages"]:
        lines.append(f"- [[{package['name']}]] -- {STATUS_LABELS.get(package['status'], package['status'])}")

    lines += ["", "## Problemas conocidos (Doctor)", ""]
    for issue in issues_data["issues"]:
        lines.append(f"- [[{issue['id']}]]")

    _write(VAULT / "Indice.md", "\n".join(lines) + "\n")


def main() -> None:
    # Wipe first: without this, renaming/removing an entry in the source JSON
    # (e.g. "xla" -> "torch-xla") left the old note orphaned in the vault
    # forever instead of the vault reflecting only what's in the JSON today.
    if VAULT.exists():
        shutil.rmtree(VAULT)

    graph = load_json("doctor/compatibility_graph.json")
    packages_data = load_json("compass/packages.json")
    issues_data = load_json("doctor/known_issues.json")

    package_has_graph_nodes = {node["package"]["name"] for node in graph["nodes"]}

    by_arch = generate_graph_nodes(graph)
    generate_architecture_hubs(by_arch)
    generate_packages(packages_data, package_has_graph_nodes)
    generate_known_issues(issues_data)
    generate_index(by_arch, packages_data, issues_data)

    note_count = (
        len(graph["nodes"]) + len(by_arch) + len(packages_data["packages"]) + len(issues_data["issues"]) + 1
    )
    print(f"Generated {note_count} notes in {VAULT}")


if __name__ == "__main__":
    main()
