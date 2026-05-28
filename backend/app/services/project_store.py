"""SQLite project store — async CRUD for projects, files, node states, logs."""

from __future__ import annotations

import aiosqlite
import json
import time
import uuid
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent.parent / "omics_copilot.db"


async def _get_db():
    db = await aiosqlite.connect(str(DB_PATH))
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


async def init_db():
    db = await _get_db()
    await db.executescript("""
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            modality TEXT NOT NULL,
            status TEXT DEFAULT 'created',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            meta TEXT DEFAULT '{}'
        );
        CREATE TABLE IF NOT EXISTS project_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            filename TEXT NOT NULL,
            filepath TEXT NOT NULL,
            size_bytes INTEGER,
            extension TEXT,
            metadata TEXT DEFAULT '{}',
            uploaded_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS node_states (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            node_id TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            params TEXT DEFAULT '{}',
            result TEXT DEFAULT '{}',
            error_msg TEXT,
            started_at TEXT,
            finished_at TEXT,
            UNIQUE(project_id, node_id)
        );
        CREATE TABLE IF NOT EXISTS run_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            node_id TEXT NOT NULL,
            level TEXT DEFAULT 'info',
            message TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    await db.commit()
    await db.close()


# ── Projects ──

async def create_project(name: str, modality: str, meta: dict | None = None) -> dict:
    pid = str(uuid.uuid4())[:8]
    now = time.strftime("%Y-%m-%dT%H:%M:%S")
    db = await _get_db()
    await db.execute(
        "INSERT INTO projects (id, name, modality, meta, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        (pid, name, modality, json.dumps(meta or {}), now, now))
    await db.commit()
    await db.close()
    return {"id": pid, "name": name, "modality": modality, "status": "created",
            "meta": meta or {}, "created_at": now, "updated_at": now}


async def list_projects(modality: str | None = None, status: str | None = None,
                        sort: str = "created_at_desc", search: str | None = None) -> list[dict]:
    db = await _get_db()
    query = "SELECT * FROM projects WHERE 1=1"
    params: list = []
    if modality:
        query += " AND modality = ?"; params.append(modality)
    if status:
        query += " AND status = ?"; params.append(status)
    if search:
        query += " AND (name LIKE ? OR meta LIKE ?)"; params.extend([f"%{search}%", f"%{search}%"])
    order = "created_at DESC" if sort == "created_at_desc" else "created_at ASC"
    query += f" ORDER BY {order}"
    rows = await db.execute_fetchall(query, params)
    await db.close()
    return [_row_to_dict(r) for r in rows]


async def get_project(project_id: str) -> dict | None:
    db = await _get_db()
    rows = await db.execute_fetchall("SELECT * FROM projects WHERE id = ?", (project_id,))
    await db.close()
    return _row_to_dict(rows[0]) if rows else None


async def update_project(project_id: str, **kwargs) -> bool:
    if not kwargs:
        return False
    kwargs["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    sets = ", ".join(f"{k}=?" for k in kwargs)
    vals = list(kwargs.values()) + [project_id]
    db = await _get_db()
    await db.execute(f"UPDATE projects SET {sets} WHERE id=?", vals)
    await db.commit()
    await db.close()
    return True


async def delete_project(project_id: str) -> bool:
    db = await _get_db()
    await db.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    await db.commit()
    await db.close()
    return True


# ── Files ──

async def add_project_file(project_id: str, filename: str, filepath: str,
                           size_bytes: int, extension: str, metadata: dict | None = None) -> dict:
    db = await _get_db()
    cursor = await db.execute(
        "INSERT INTO project_files (project_id, filename, filepath, size_bytes, extension, metadata) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (project_id, filename, str(filepath), size_bytes, extension, json.dumps(metadata or {})))
    fid = cursor.lastrowid
    await db.commit()
    await db.close()
    return {"id": fid, "project_id": project_id, "filename": filename, "filepath": str(filepath)}


async def list_project_files(project_id: str) -> list[dict]:
    db = await _get_db()
    rows = await db.execute_fetchall(
        "SELECT * FROM project_files WHERE project_id = ? ORDER BY uploaded_at DESC", (project_id,))
    await db.close()
    return [_row_to_dict(r) for r in rows]


async def delete_project_file(file_id: int) -> dict | None:
    db = await _get_db()
    rows = await db.execute_fetchall("SELECT * FROM project_files WHERE id = ?", (file_id,))
    if rows:
        result = _row_to_dict(rows[0])
        await db.execute("DELETE FROM project_files WHERE id = ?", (file_id,))
        await db.commit()
    else:
        result = None
    await db.close()
    return result


# ── Node States ──

async def upsert_node_state(project_id: str, node_id: str, **kwargs) -> dict:
    db = await _get_db()
    rows = await db.execute_fetchall(
        "SELECT * FROM node_states WHERE project_id=? AND node_id=?", (project_id, node_id))
    if rows:
        sets = ", ".join(f"{k}=?" for k in kwargs)
        vals = list(kwargs.values()) + [project_id, node_id]
        await db.execute(f"UPDATE node_states SET {sets} WHERE project_id=? AND node_id=?", vals)
    else:
        keys = ["project_id", "node_id"] + list(kwargs.keys())
        placeholders = ", ".join("?" for _ in keys)
        vals = [project_id, node_id] + list(kwargs.values())
        await db.execute(
            f"INSERT INTO node_states ({', '.join(keys)}) VALUES ({placeholders})", vals)
    await db.commit()
    rows = await db.execute_fetchall(
        "SELECT * FROM node_states WHERE project_id=? AND node_id=?", (project_id, node_id))
    await db.close()
    return _row_to_dict(rows[0]) if rows else {}


async def get_node_states(project_id: str) -> list[dict]:
    db = await _get_db()
    rows = await db.execute_fetchall("SELECT * FROM node_states WHERE project_id = ?", (project_id,))
    await db.close()
    return [_row_to_dict(r) for r in rows]


async def reset_downstream_nodes(project_id: str, from_node_id: str, dag_nodes: list[dict]) -> int:
    downstream = _get_downstream(from_node_id, dag_nodes)
    if not downstream:
        return 0
    db = await _get_db()
    placeholders = ", ".join("?" for _ in downstream)
    await db.execute(
        f"UPDATE node_states SET status='pending', result='{{}}', error_msg=NULL "
        f"WHERE project_id=? AND node_id IN ({placeholders})",
        [project_id] + downstream)
    await db.commit()
    await db.close()
    return len(downstream)


def _get_downstream(node_id: str, dag_nodes: list[dict]) -> list[str]:
    result: set[str] = set()
    for node in dag_nodes:
        deps = node.get("depends_on", [])
        if isinstance(deps, str):
            deps = [deps]
        if node_id in deps:
            result.add(node["id"])
            result.update(_get_downstream(node["id"], dag_nodes))
    return list(result)


# ── Logs ──

async def add_log(project_id: str, node_id: str, level: str, message: str):
    db = await _get_db()
    await db.execute(
        "INSERT INTO run_logs (project_id, node_id, level, message) VALUES (?, ?, ?, ?)",
        (project_id, node_id, level, message[:2000]))
    await db.commit()
    await db.close()


async def get_logs(project_id: str, node_id: str | None = None, limit: int = 50) -> list[dict]:
    db = await _get_db()
    if node_id:
        rows = await db.execute_fetchall(
            "SELECT * FROM run_logs WHERE project_id=? AND node_id=? ORDER BY created_at DESC LIMIT ?",
            (project_id, node_id, limit))
    else:
        rows = await db.execute_fetchall(
            "SELECT * FROM run_logs WHERE project_id=? ORDER BY created_at DESC LIMIT ?",
            (project_id, limit))
    await db.close()
    return [_row_to_dict(r) for r in rows]


def _row_to_dict(row) -> dict:
    return dict(row) if row else {}
