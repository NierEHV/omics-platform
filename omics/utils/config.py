"""Configuration system: YAML loading, typed dataclass hierarchy, project scaffolding."""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

from omics.utils.constants import PROJECT_SUBDIRS
from omics.utils.exceptions import ConfigError

DEFAULT_CONFIG_YAML = Path(__file__).parent.parent.parent / "config.yaml"


@dataclass
class GPUConfig:
    enabled: bool = True
    device: int = 0
    memory_fraction: float = 0.85
    fallback_to_cpu: bool = True


@dataclass
class SCRNADefaults:
    min_genes: int = 200
    min_cells: int = 3
    max_pct_mt: float = 20.0
    n_hvg: int = 2000
    n_neighbors: int = 15
    n_pcs: int = 50
    cluster_resolution: float = 1.0
    batch_key: str = "batch"


@dataclass
class VizDefaults:
    style: str = "nature"
    dpi: int = 300
    format: str = "pdf"
    font_family: str = "Arial"
    font_size: int = 7
    fig_width: float = 7.0
    fig_height: float = 5.0


@dataclass
class Config:
    gpu: GPUConfig = field(default_factory=GPUConfig)
    scrna: SCRNADefaults = field(default_factory=SCRNADefaults)
    viz: VizDefaults = field(default_factory=VizDefaults)
    data: dict = field(default_factory=dict)

    _project_root: Path = field(default_factory=Path.cwd, repr=False)
    _config_path: Optional[Path] = field(default=None, repr=False)

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "Config":
        config = cls()
        if path is None:
            path = DEFAULT_CONFIG_YAML
        config._config_path = Path(path)

        if config._config_path.exists():
            with open(config._config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            config._merge_dict(data)

        config._apply_env_overrides()
        return config

    def save(self, path: Optional[Path] = None) -> None:
        if path is None:
            path = self._config_path or DEFAULT_CONFIG_YAML
        data = {
            "gpu": _dataclass_to_dict(self.gpu),
            "scrna": _dataclass_to_dict(self.scrna),
            "viz": _dataclass_to_dict(self.viz),
            "data": self.data,
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)

    def _merge_dict(self, data: dict) -> None:
        for key, value in data.items():
            if hasattr(self, key):
                attr = getattr(self, key)
                if isinstance(value, dict) and hasattr(attr, "__dataclass_fields__"):
                    _merge_into_dataclass(attr, value)
                else:
                    setattr(self, key, value)

    def _apply_env_overrides(self) -> None:
        for key, attr in [
            ("OMICS_GPU_DEVICE", "gpu.device"),
            ("OMICS_VIZ_STYLE", "viz.style"),
            ("OMICS_VIZ_DPI", "viz.dpi"),
            ("OMICS_LOG_LEVEL", "data.log_level"),
        ]:
            val = os.environ.get(key)
            if val is not None:
                obj_path, field_name = attr.rsplit(".", 1)
                obj = getattr(self, obj_path)
                if isinstance(obj, dict):
                    obj[field_name] = val
                elif hasattr(obj, field_name):
                    field_type = type(getattr(obj, field_name))
                    setattr(obj, field_name, field_type(val))


def scaffold_project(base_dir: Path, title: str, description: str = "") -> dict:
    """Create a new analysis project with standard directory structure."""
    project_id = f"PROJ_{uuid.uuid4().hex[:6].upper()}"
    project_dir = base_dir / project_id

    for subdir in PROJECT_SUBDIRS:
        (project_dir / subdir).mkdir(parents=True, exist_ok=True)

    import datetime
    meta = {
        "project_id": project_id,
        "title": title,
        "description": description,
        "created_at": datetime.datetime.now().isoformat(),
    }
    meta_path = project_dir / "metadata.yaml"
    with open(meta_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(meta, f)

    config = Config.load()
    config._project_root = project_dir
    config.save(project_dir / "config.yaml")
    return meta


def _dataclass_to_dict(obj) -> dict:
    if not hasattr(obj, "__dataclass_fields__"):
        return obj
    result = {}
    for f_name in obj.__dataclass_fields__:
        if f_name.startswith("_"):
            continue
        val = getattr(obj, f_name)
        if hasattr(val, "__dataclass_fields__"):
            result[f_name] = _dataclass_to_dict(val)
        elif isinstance(val, Path):
            result[f_name] = str(val)
        else:
            result[f_name] = val
    return result


def _merge_into_dataclass(dc, data: dict) -> None:
    for key, value in data.items():
        if hasattr(dc, key) and not key.startswith("_"):
            attr = getattr(dc, key)
            if isinstance(value, dict) and hasattr(attr, "__dataclass_fields__"):
                _merge_into_dataclass(attr, value)
            else:
                setattr(dc, key, value)
