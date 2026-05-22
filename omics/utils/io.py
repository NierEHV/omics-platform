"""AnnData I/O utilities: format detection, batch reading/writing."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import anndata as ad

from omics.utils.exceptions import DataImportError

logger = logging.getLogger(__name__)


def detect_format(path: Path) -> Optional[str]:
    """Detect the format of a single-cell data file."""
    if path.is_dir():
        if (path / "matrix.mtx.gz").exists() or (path / "matrix.mtx").exists():
            return "10x_mtx"
        if (path / "filtered_feature_bc_matrix.h5").exists():
            return "10x_h5"
        if (path / "spatial").exists():
            return "visium"
        return "directory"

    suffix = path.suffix.lower()
    if suffix == ".h5ad":
        return "h5ad"
    if suffix in (".h5", ".hdf5"):
        return "h5"
    if suffix == ".loom":
        return "loom"
    if suffix == ".mtx":
        return "mtx"
    if suffix in (".csv", ".tsv", ".txt"):
        return "table"
    return None


def read_h5ad(path: Path) -> ad.AnnData:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    return ad.read_h5ad(path)


def write_h5ad(adata: ad.AnnData, path: Path, **kwargs) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    adata.write(path, **kwargs)
    logger.debug(f"Written: {path} ({adata.n_obs} obs x {adata.n_vars} vars)")


def get_adata_summary(adata: ad.AnnData) -> str:
    lines = [
        f"AnnData: {adata.n_obs} observations x {adata.n_vars} variables",
        f"  .X:       {type(adata.X).__name__}, shape={adata.X.shape}",
        f"  .obs:     {list(adata.obs.columns)}",
        f"  .var:     {list(adata.var.columns)}",
        f"  .obsm:    {list(adata.obsm.keys())}",
        f"  .obsp:    {list(adata.obsp.keys())}",
        f"  .layers:  {list(adata.layers.keys())}",
        f"  .uns:     {list(adata.uns.keys())[:10]}",
    ]
    return "\n".join(lines)
