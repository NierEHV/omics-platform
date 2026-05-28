"""File management routes — upload, list, delete, info."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ..schemas import FileInfo

router = APIRouter(tags=["files"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"

ALLOWED_EXTENSIONS = {".h5ad", ".h5mu", ".csv", ".tsv", ".txt", ".fastq", ".fq", ".fasta", ".fa"}


def _get_file_info(path: Path) -> FileInfo:
    stat = path.stat()
    ext = path.suffix.lower()
    metadata = {}
    if ext == ".h5ad":
        try:
            from omics.utils.io import read_h5ad
            adata = read_h5ad(path)
            metadata = {"n_obs": adata.n_obs, "n_vars": adata.n_vars, "shape": list(adata.shape)}
        except Exception:
            pass
    return FileInfo(
        name=path.name,
        path=str(path),
        size=stat.st_size,
        extension=ext,
        created_at=datetime.fromtimestamp(stat.st_ctime).isoformat(),
        metadata=metadata or None,
    )


@router.get("/files", response_model=List[FileInfo])
async def list_files():
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    files = []
    for f in sorted(UPLOAD_DIR.iterdir(), key=lambda x: x.stat().st_ctime, reverse=True):
        if f.is_file() and f.suffix.lower() in ALLOWED_EXTENSIONS:
            files.append(_get_file_info(f))
    return files


@router.post("/files/upload", response_model=FileInfo)
async def upload_file(file: UploadFile):
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type: {ext}")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    dest = UPLOAD_DIR / file.filename
    content = await file.read()
    dest.write_bytes(content)
    return _get_file_info(dest)


@router.get("/files/{filename:path}/info", response_model=FileInfo)
async def file_info(filename: str):
    path = UPLOAD_DIR / filename
    if not path.exists():
        raise HTTPException(404, "File not found")
    return _get_file_info(path)


@router.delete("/files/{filename:path}")
async def delete_file(filename: str):
    path = UPLOAD_DIR / filename
    if not path.exists():
        raise HTTPException(404, "File not found")
    path.unlink()
    return {"status": "deleted", "filename": filename}


@router.get("/files/{filename:path}/download")
async def download_file(filename: str):
    path = UPLOAD_DIR / filename
    if not path.exists():
        raise HTTPException(404, "File not found")
    return FileResponse(path, filename=path.name)
