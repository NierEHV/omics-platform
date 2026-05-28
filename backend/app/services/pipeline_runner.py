"""Pipeline runner — execute DAG nodes with SSE status streaming."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import AsyncGenerator

from . import project_store
from .dag_registry import load_template, get_topo_order

logger = logging.getLogger(__name__)

UPLOADS_BASE = Path(__file__).resolve().parent.parent.parent / "uploads"

TOOL_MAP = {
    "qc": "omics_scrna_qc",
    "normalize": "omics_scrna_normalize",
    "reduce": "omics_scrna_reduce",
    "cluster": "omics_scrna_cluster",
    "markers": "omics_scrna_markers",
    "trajectory": "omics_scrna_trajectory",
    "annotate": "omics_scrna_annotate",
    "visualize": "omics_visualize_umap",
    "cell_communication": "omics_scrna_cell_communication",
}


def _run_tool_sync(tool_name: str, args: dict) -> dict:
    from omics.agent.handler import OmicsAgentHandler
    cwd = args.pop("_cwd", ".")
    handler = OmicsAgentHandler(cwd=cwd)
    method = getattr(handler, f"do_{tool_name}", None)
    if method is None:
        return {"status": "error", "msg": f"Unknown tool: {tool_name}"}
    outcome = method(args, None)
    return outcome.data if hasattr(outcome, "data") else {"status": "error", "msg": str(outcome)}


async def _run_tool(tool_name: str, args: dict) -> dict:
    return await asyncio.to_thread(_run_tool_sync, tool_name, args)


class PipelineRunner:
    def __init__(self, project_id: str):
        self.project_id = project_id

    async def execute_node(self, node_id: str, params: dict | None = None) -> AsyncGenerator[dict, None]:
        project = await project_store.get_project(self.project_id)
        if not project:
            yield {"type": "error", "node_id": node_id, "msg": "Project not found"}
            return

        proj_uploads = UPLOADS_BASE / self.project_id
        proj_uploads.mkdir(parents=True, exist_ok=True)

        params = params or {}
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        await project_store.upsert_node_state(self.project_id, node_id, status="running", started_at=now)
        await project_store.add_log(self.project_id, node_id, "info", f"Starting {node_id}")

        yield {"type": "node_status", "node_id": node_id, "status": "running"}

        if node_id == "import":
            await project_store.upsert_node_state(self.project_id, "import",
                status="done", result=json.dumps({"status": "success", "msg": "数据已导入"}, ensure_ascii=False),
                finished_at=time.strftime("%Y-%m-%dT%H:%M:%S"))
            yield {"type": "node_status", "node_id": "import", "status": "done",
                   "result": {"status": "success", "msg": "数据已导入"}}
            return

        try:
            tool_name = TOOL_MAP.get(node_id, f"omics_{node_id}")
            args = dict(params)
            args["_cwd"] = str(proj_uploads)
            if "input" not in args or not args.get("input"):
                args["input"] = self._find_input_file(node_id)

            result = await _run_tool(tool_name, args)
            is_success = result.get("status") == "success"

            await project_store.upsert_node_state(
                self.project_id, node_id,
                status="done" if is_success else "failed",
                result=json.dumps(result, ensure_ascii=False),
                error_msg=result.get("msg") if not is_success else None,
                finished_at=time.strftime("%Y-%m-%dT%H:%M:%S"))
            level = "info" if is_success else "error"
            await project_store.add_log(self.project_id, node_id, level,
                                        str(result.get("msg", ""))[:2000])

            yield {"type": "node_status", "node_id": node_id,
                   "status": "done" if is_success else "failed", "result": result}

        except Exception as e:
            msg = str(e)
            await project_store.upsert_node_state(
                self.project_id, node_id, status="failed", error_msg=msg,
                finished_at=time.strftime("%Y-%m-%dT%H:%M:%S"))
            await project_store.add_log(self.project_id, node_id, "error", msg[:2000])
            yield {"type": "node_status", "node_id": node_id, "status": "failed", "error": msg}

    def _find_input_file(self, node_id: str) -> str:
        proj_uploads = UPLOADS_BASE / self.project_id
        if not proj_uploads.exists():
            return ""
        files = sorted(proj_uploads.glob("*.h5ad"),
                       key=lambda f: f.stat().st_mtime, reverse=True)
        return files[0].name if files else ""

    async def run_all(self, node_params: dict[str, dict] | None = None) -> AsyncGenerator[dict, None]:
        project = await project_store.get_project(self.project_id)
        if not project:
            yield {"type": "error", "msg": "Project not found"}
            return

        template = load_template(project["modality"])
        ordered = get_topo_order(template)
        node_params = node_params or {}

        await project_store.update_project(self.project_id, status="running")
        yield {"type": "pipeline_start", "total_nodes": len(ordered)}

        for i, node in enumerate(ordered):
            nid = node["id"]
            if nid == "import":
                await project_store.upsert_node_state(self.project_id, "import",
                    status="done", result=json.dumps({"status": "success", "msg": "数据已导入"}, ensure_ascii=False),
                    finished_at=time.strftime("%Y-%m-%dT%H:%M:%S"))
                yield {"type": "node_status", "node_id": "import", "status": "done",
                       "result": {"status": "success", "msg": "数据已导入"}}
                continue
            if node.get("type") == "branch_optional":
                existing = await project_store.get_node_states(self.project_id)
                if not any(n["node_id"] == nid and json.loads(n.get("params", "{}"))
                           for n in existing):
                    continue  # skip optional branches unless explicitly triggered

            params = node_params.get(nid, {})
            async for event in self.execute_node(nid, params):
                yield event
                if event.get("status") == "failed":
                    await project_store.update_project(self.project_id, status="failed")
                    yield {"type": "pipeline_stop", "failed_at": nid}
                    return

            yield {"type": "pipeline_progress", "current": i + 1, "total": len(ordered)}

        await project_store.update_project(self.project_id, status="completed")
        yield {"type": "pipeline_complete"}
