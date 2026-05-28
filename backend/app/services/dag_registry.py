"""DAG template registry — load modality-specific pipeline definitions."""

import json
from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


def load_template(modality: str) -> dict:
    path = TEMPLATES_DIR / f"{modality}.json"
    if not path.exists():
        return {
            "modality": modality, "name": modality, "nodes": [
                {"id": "import", "label": "数据导入", "type": "import",
                 "params": [{"key": "file", "label": "数据文件", "type": "file_select", "required": True}]}
            ], "edges": []
        }
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def list_modalities() -> list[dict]:
    result = []
    for f in sorted(TEMPLATES_DIR.glob("*.json")):
        try:
            t = json.loads(f.read_text(encoding="utf-8"))
            result.append({
                "modality": t["modality"], "name": t.get("name", t["modality"]),
                "node_count": len(t.get("nodes", []))})
        except Exception:
            pass
    return result


def get_topo_order(template: dict) -> list[dict]:
    nodes = {n["id"]: n for n in template["nodes"]}
    in_degree: dict[str, int] = {n["id"]: 0 for n in template["nodes"]}
    adj: dict[str, list[str]] = {n["id"]: [] for n in template["nodes"]}

    for n in template["nodes"]:
        deps = n.get("depends_on", [])
        if isinstance(deps, str):
            deps = [deps]
        for dep in deps:
            if dep in adj:
                adj[dep].append(n["id"])
                in_degree[n["id"]] += 1

    queue = [nid for nid, deg in in_degree.items() if deg == 0]
    result = []
    while queue:
        nid = queue.pop(0)
        result.append(nodes[nid])
        for downstream in adj.get(nid, []):
            in_degree[downstream] -= 1
            if in_degree[downstream] == 0:
                queue.append(downstream)
    return result
