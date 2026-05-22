"""Provenance tracking: record, store, reproduce, and audit analyses."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

DEFAULT_PROVENANCE_DIR = Path.home() / ".omics" / "provenance"


@dataclass
class EnvironmentSnapshot:
    python_version: str = ""
    platform: str = ""
    conda_env: str = ""
    gpu_driver: str = ""
    cuda_version: str = ""
    packages: list[str] = field(default_factory=list)

    @classmethod
    def capture(cls) -> "EnvironmentSnapshot":
        import sys
        import platform

        packages = []
        try:
            from importlib.metadata import distributions
            for dist in distributions():
                packages.append(f"{dist.metadata['Name']}=={dist.version}")
        except Exception:
            pass

        gpu_driver = ""
        cuda_version = ""
        try:
            import subprocess
            result = subprocess.run(["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
                                   capture_output=True, text=True, timeout=5)
            gpu_driver = result.stdout.strip()
            result = subprocess.run(["nvidia-smi"], capture_output=True, text=True, timeout=5)
            for line in result.stdout.split("\n"):
                if "CUDA Version" in line:
                    cuda_version = line.split("CUDA Version:")[-1].strip().split()[0]
                    break
        except Exception:
            pass

        return cls(
            python_version=sys.version,
            platform=platform.platform(),
            conda_env=os.environ.get("CONDA_DEFAULT_ENV", ""),
            gpu_driver=gpu_driver,
            cuda_version=cuda_version,
            packages=sorted(packages),
        )


@dataclass
class StageProvenance:
    stage_name: str
    status: str = ""
    duration_seconds: float = 0.0
    input_hash: str = ""
    output_hash: str = ""
    gpu_used: bool = False
    memory_mb: float = 0.0


@dataclass
class ProvenanceRecord:
    analysis_id: str = ""
    timestamp: str = ""
    user: str = ""
    pipeline_name: str = ""
    input_path: str = ""
    input_shape: tuple = ()
    input_hash: str = ""
    output_hash: str = ""
    parameters: dict = field(default_factory=dict)
    environment: EnvironmentSnapshot = field(default_factory=EnvironmentSnapshot)
    stages: list[StageProvenance] = field(default_factory=list)
    status: str = "pending"
    duration_seconds: float = 0.0
    error_log: str = ""
    tags: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "analysis_id": self.analysis_id,
            "timestamp": self.timestamp,
            "user": self.user,
            "pipeline_name": self.pipeline_name,
            "input_path": self.input_path,
            "input_shape": list(self.input_shape),
            "input_hash": self.input_hash,
            "output_hash": self.output_hash,
            "parameters": self.parameters,
            "environment": {
                "python_version": self.environment.python_version,
                "platform": self.environment.platform,
                "gpu_driver": self.environment.gpu_driver,
                "cuda_version": self.environment.cuda_version,
                "packages": self.environment.packages[:50],
            },
            "stages": [{"stage_name": s.stage_name, "status": s.status,
                        "duration_seconds": s.duration_seconds} for s in self.stages],
            "status": self.status,
            "duration_seconds": self.duration_seconds,
            "error_log": self.error_log,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ProvenanceRecord":
        env_data = data.get("environment", {})
        env = EnvironmentSnapshot(
            python_version=env_data.get("python_version", ""),
            platform=env_data.get("platform", ""),
            gpu_driver=env_data.get("gpu_driver", ""),
            cuda_version=env_data.get("cuda_version", ""),
            packages=env_data.get("packages", []),
        )
        stages = [StageProvenance(**s) for s in data.get("stages", [])]
        return cls(
            analysis_id=data.get("analysis_id", ""),
            timestamp=data.get("timestamp", ""),
            user=data.get("user", ""),
            pipeline_name=data.get("pipeline_name", ""),
            input_path=data.get("input_path", ""),
            input_shape=tuple(data.get("input_shape", ())),
            input_hash=data.get("input_hash", ""),
            output_hash=data.get("output_hash", ""),
            parameters=data.get("parameters", {}),
            environment=env,
            stages=stages,
            status=data.get("status", ""),
            duration_seconds=data.get("duration_seconds", 0),
            error_log=data.get("error_log", ""),
        )


class ProvenanceStore:
    """JSON-file-backed provenance record store."""

    def __init__(self, base_dir: Optional[Path] = None):
        self._dir = Path(base_dir) if base_dir else DEFAULT_PROVENANCE_DIR
        self._dir.mkdir(parents=True, exist_ok=True)

    def save(self, record: ProvenanceRecord) -> Path:
        filepath = self._dir / f"{record.analysis_id}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(record.to_dict(), f, indent=2, ensure_ascii=False)
        return filepath

    def load(self, analysis_id: str) -> Optional[ProvenanceRecord]:
        filepath = self._dir / f"{analysis_id}.json"
        if not filepath.exists():
            return None
        with open(filepath, "r", encoding="utf-8") as f:
            return ProvenanceRecord.from_dict(json.load(f))

    def list_all(self, limit: int = 50) -> list[ProvenanceRecord]:
        records = []
        for fp in sorted(self._dir.glob("*.json"), key=os.path.getmtime, reverse=True)[:limit]:
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    records.append(ProvenanceRecord.from_dict(json.load(f)))
            except Exception:
                pass
        return records

    def export_methods_section(self, analysis_id: str) -> str:
        record = self.load(analysis_id)
        if record is None:
            return f"Analysis '{analysis_id}' not found."

        lines = [
            "## Methods",
            "",
            f"Analysis was performed using the omics-platform with pipeline "
            f"'{record.pipeline_name}'. ",
        ]
        if record.parameters:
            lines.append("Key parameters: " + ", ".join(
                f"{k}={v}" for k, v in record.parameters.items()) + ".")

        if record.environment.python_version:
            lines.append(f"Environment: Python {record.environment.python_version.split()[0]}.")
        if record.environment.gpu_driver:
            lines.append(f"GPU: {record.environment.gpu_driver}, CUDA {record.environment.cuda_version}.")

        if record.stages:
            lines.append("\nAnalysis steps:")
            for s in record.stages:
                lines.append(f"- {s.stage_name}: {s.status} ({s.duration_seconds:.1f}s)")

        return "\n".join(lines)


def generate_analysis_id() -> str:
    return uuid.uuid4().hex[:8]


def hash_file(path: Path, chunk_size: int = 8192) -> str:
    hasher = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def hash_adata(adata) -> str:
    """Lightweight AnnData hash (shape + col names, not full X)."""
    hasher = hashlib.md5()
    hasher.update(str(adata.shape).encode())
    hasher.update(str(sorted(adata.obs.columns)).encode())
    hasher.update(str(sorted(adata.var.columns)).encode())
    try:
        hasher.update(str(adata.X.mean()).encode())
    except Exception:
        pass
    return hasher.hexdigest()


def diff_analyses(id1: str, id2: str, base_dir: Optional[Path] = None) -> dict:
    store = ProvenanceStore(base_dir)
    r1 = store.load(id1)
    r2 = store.load(id2)
    if r1 is None or r2 is None:
        missing = id1 if r1 is None else id2
        return {"error": f"Analysis '{missing}' not found"}

    param_diff = {}
    all_keys = set(r1.parameters) | set(r2.parameters)
    for key in sorted(all_keys):
        v1 = r1.parameters.get(key, "-")
        v2 = r2.parameters.get(key, "-")
        if v1 != v2:
            param_diff[key] = {"from": v1, "to": v2}

    shared_stages = []
    stages1 = {s.stage_name: s for s in r1.stages}
    stages2 = {s.stage_name: s for s in r2.stages}
    for name in sorted(set(stages1) & set(stages2)):
        s1, s2 = stages1[name], stages2[name]
        shared_stages.append({
            "stage": name,
            "status_1": s1.status, "status_2": s2.status,
            "duration_diff": s2.duration_seconds - s1.duration_seconds,
        })

    return {
        "duration_diff": r2.duration_seconds - r1.duration_seconds,
        "parameter_diff": param_diff,
        "shared_stages": shared_stages,
    }
