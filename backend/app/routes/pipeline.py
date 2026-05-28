"""Pipeline execution routes — DAG templates, node states, SSE execution."""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from ..services import project_store, dag_registry
from ..services.pipeline_runner import PipelineRunner

router = APIRouter(tags=["pipeline"])


# ── DAG Templates ──

@router.get("/dag/templates")
async def list_templates():
    return dag_registry.list_modalities()


@router.get("/dag/templates/{modality}")
async def get_template(modality: str):
    try:
        return dag_registry.load_template(modality)
    except Exception:
        raise HTTPException(404, f"Template not found for modality: {modality}")


# ── Node States ──

@router.get("/projects/{project_id}/nodes")
async def get_node_states(project_id: str):
    return await project_store.get_node_states(project_id)


@router.put("/projects/{project_id}/nodes/{node_id}")
async def update_node_params(project_id: str, node_id: str, req: dict):
    params = req.get("params", {})
    if isinstance(params, dict):
        params = json.dumps(params)
    result = await project_store.upsert_node_state(project_id, node_id, params=params)
    if req.get("reset_downstream", False):
        project = await project_store.get_project(project_id)
        if project:
            template = dag_registry.load_template(project["modality"])
            await project_store.reset_downstream_nodes(project_id, node_id, template["nodes"])
    return result


# ── Node Execution (SSE) ──

@router.post("/projects/{project_id}/nodes/{node_id}/run")
async def run_node(project_id: str, node_id: str, params: dict | None = None):
    project = await project_store.get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    runner = PipelineRunner(project_id)

    async def generate():
        async for event in runner.execute_node(node_id, params or {}):
            yield f"event: {event['type']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.post("/projects/{project_id}/run")
async def run_pipeline(project_id: str, params: dict | None = None):
    project = await project_store.get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    runner = PipelineRunner(project_id)

    async def generate():
        async for event in runner.run_all():
            yield f"event: {event['type']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ── System ──

@router.get("/system/capacity")
async def system_capacity():
    import os
    cpu = os.cpu_count() or 1
    try:
        import psutil
        mem = psutil.virtual_memory()
        ram_gb = mem.total / (1024 ** 3)
    except Exception:
        ram_gb = 8.0
    gpu_count = 0
    gpu_vram_gb = 0.0
    try:
        import subprocess
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            encoding="utf-8", timeout=5)
        for line in out.strip().split("\n"):
            if line.strip():
                gpu_count += 1
                gpu_vram_gb += float(line.strip()) / 1024
    except Exception:
        pass
    max_parallel = max(1, min(int(cpu / 2), int(ram_gb / 4)))
    if gpu_count > 0:
        max_parallel = max(1, min(max_parallel, int(gpu_vram_gb / 2)))
    return {
        "cpu_cores": cpu, "ram_gb": round(ram_gb, 1),
        "gpu_count": gpu_count, "gpu_vram_gb": round(gpu_vram_gb, 1),
        "recommended_max_parallel": max_parallel}


# ── Logs ──

@router.get("/projects/{project_id}/logs")
async def get_logs(project_id: str, node_id: str | None = None, limit: int = 50):
    return await project_store.get_logs(project_id, node_id, limit)
