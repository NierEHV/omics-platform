"""Project management routes."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ..schemas import ProjectCreate
from ..services import project_store, dag_registry

router = APIRouter(tags=["projects"])

UPLOADS_BASE = Path(__file__).resolve().parent.parent.parent / "uploads"
ALLOWED_EXTENSIONS = {".h5ad", ".h5mu", ".csv", ".tsv", ".txt", ".fastq", ".fq", ".fasta", ".fa"}


@router.get("/projects")
async def list_projects(modality: str | None = None, status: str | None = None,
                        sort: str = "created_at_desc", search: str | None = None):
    projects = await project_store.list_projects(modality, status, sort, search)
    for p in projects:
        p["files_count"] = len(await project_store.list_project_files(p["id"]))
        nodes = await project_store.get_node_states(p["id"])
        p["progress"] = _calc_progress(nodes)
    return projects


@router.post("/projects")
async def create_project(req: ProjectCreate):
    return await project_store.create_project(req.name, req.modality, req.meta)


@router.get("/projects/{project_id}")
async def get_project(project_id: str):
    p = await project_store.get_project(project_id)
    if not p:
        raise HTTPException(404, "Project not found")
    p["files"] = await project_store.list_project_files(project_id)
    p["node_states"] = await project_store.get_node_states(project_id)
    p["template"] = dag_registry.load_template(p["modality"])
    return p


@router.put("/projects/{project_id}")
async def update_project(project_id: str, req: dict):
    project = await project_store.get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    allowed = {"name", "meta", "status"}
    updates = {k: v for k, v in req.items() if k in allowed}
    if "meta" in updates and isinstance(updates["meta"], dict):
        updates["meta"] = json.dumps(updates["meta"])
    await project_store.update_project(project_id, **updates)
    return {"status": "ok"}


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    project = await project_store.get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    await project_store.delete_project(project_id)
    return {"status": "deleted"}


# ── Files ──

@router.get("/projects/{project_id}/files")
async def list_files(project_id: str):
    return await project_store.list_project_files(project_id)


@router.post("/projects/{project_id}/files/upload")
async def upload_file(project_id: str, file: UploadFile):
    project = await project_store.get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type: {ext}")
    proj_dir = UPLOADS_BASE / project_id
    proj_dir.mkdir(parents=True, exist_ok=True)
    dest = proj_dir / file.filename
    content = await file.read()
    dest.write_bytes(content)
    metadata = {}
    if ext == ".h5ad":
        try:
            from omics.utils.io import read_h5ad
            adata = read_h5ad(dest)
            metadata = {"n_obs": adata.n_obs, "n_vars": adata.n_vars, "shape": list(adata.shape)}
        except Exception:
            pass
    result = await project_store.add_project_file(
        project_id, file.filename, str(dest), len(content), ext, metadata)
    await project_store.upsert_node_state(project_id, "import", status="done",
        result='{"status":"success","msg":"数据已导入"}')
    return result


@router.delete("/projects/{project_id}/files/{file_id}")
async def delete_file(project_id: str, file_id: int):
    f = await project_store.delete_project_file(file_id)
    if not f:
        raise HTTPException(404, "File not found")
    path = Path(f["filepath"])
    if path.exists():
        path.unlink()
    return {"status": "deleted"}


@router.get("/projects/{project_id}/files/{file_id}/download")
async def download_file(project_id: str, file_id: int):
    f = await project_store.delete_project_file(file_id)
    if not f:
        raise HTTPException(404, "File not found")
    path = Path(f["filepath"])
    if not path.exists():
        raise HTTPException(404, "File not found on disk")
    return FileResponse(path, filename=path.name)


def _calc_progress(nodes: list[dict]) -> dict:
    total = len(nodes)
    done = sum(1 for n in nodes if n.get("status") == "done")
    failed = sum(1 for n in nodes if n.get("status") == "failed")
    running = sum(1 for n in nodes if n.get("status") == "running")
    return {"total": total, "done": done, "failed": failed, "running": running,
            "pct": round(done / total * 100) if total > 0 else 0}
