"""Python SDK for the Multi-Omics Analysis Platform.

Provides a programmatic interface suitable for Jupyter notebooks, scripts,
and custom analysis workflows. Every method delegates to the
single-source-of-truth functions in omics.scrna.*.

Usage:
    from omics.sdk import OmicsSDK
    sdk = OmicsSDK()

    adata = sdk.data.import_scrna("sample.h5ad")
    adata = sdk.scrna.qc(adata, min_genes=200)
    adata = sdk.scrna.pipeline(adata)
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import anndata as ad
import pandas as pd


class OmicsSDK:
    """Main SDK entry point."""

    def __init__(self, config_path: Optional[Path] = None):
        from omics.utils.config import Config
        self.config = Config.load(config_path)
        self._scrna = None
        self._spatial = None
        self._data = None
        self._viz = None

    @property
    def data(self) -> "DataModule":
        if self._data is None:
            self._data = DataModule(self)
        return self._data

    @property
    def scrna(self) -> "SCRNASDK":
        if self._scrna is None:
            self._scrna = SCRNASDK(self)
        return self._scrna

    @property
    def viz(self) -> "VizSDK":
        if self._viz is None:
            self._viz = VizSDK(self)
        return self._viz

    @property
    def spatial(self):
        if self._spatial_backend is None:
            raise ModuleNotFoundError(
                "Spatial transcriptomics support is not installed. "
                "Install a spatial backend and register it via sdk.register_spatial_backend()."
            )
        return self._spatial_backend

    _spatial_backend = None

    def register_spatial_backend(self, backend) -> None:
        from omics.spatial.base import AbstractSpatialAnalysis
        if not isinstance(backend, AbstractSpatialAnalysis):
            raise TypeError(f"Expected AbstractSpatialAnalysis, got {type(backend)}")
        self._spatial_backend = backend


class DataModule:
    """Data import, export, and inspection."""

    def __init__(self, sdk: OmicsSDK):
        self.sdk = sdk

    def import_scrna(self, path, **kwargs) -> ad.AnnData:
        from omics.data.loader import SCRNABuilder
        p = Path(path)
        if p.suffix == ".h5ad":
            return SCRNABuilder.from_h5ad(p)
        if p.is_dir():
            return SCRNABuilder.from_10x_mtx(p)
        if p.suffix in (".csv", ".tsv", ".txt"):
            df = pd.read_csv(p, sep="\t" if p.suffix == ".tsv" else ",", index_col=0)
            return SCRNABuilder.from_dataframe(df)
        raise ValueError(f"Unsupported format: {p.suffix}")

    def import_spatial(self, path, **kwargs) -> ad.AnnData:
        from omics.data.loader import SpatialBuilder
        p = Path(path)
        if p.suffix == ".h5ad":
            return SpatialBuilder.from_h5ad(p)
        return SpatialBuilder.from_visium(p)

    def fetch_geo(self, accession: str, output_dir: Optional[Path] = None) -> ad.AnnData:
        """Download a GEO dataset and return as AnnData."""
        from omics.data.geo import geo_to_anndata
        return geo_to_anndata(accession, output_dir)

    def search_geo(self, query: str, max_results: int = 20) -> list:
        """Search GEO for datasets."""
        from omics.data.geo import search_geo_datasets
        return search_geo_datasets(query, max_results)

    def info(self, path) -> str:
        from omics.utils.io import get_adata_summary, read_h5ad
        return get_adata_summary(read_h5ad(Path(path)))

    def to_seurat(self, adata, output_path):
        from omics.data.converters import Converters
        Converters.anndata_to_seurat_rds(adata, Path(output_path))


class SCRNASDK:
    """Single-cell RNA-seq analysis. Every method delegates to omics.scrna.*."""

    def __init__(self, sdk: OmicsSDK):
        self.sdk = sdk

    def qc(self, adata, **kwargs) -> ad.AnnData:
        from omics.scrna.qc import run_qc
        return run_qc(adata, **kwargs)

    def normalize(self, adata, **kwargs) -> ad.AnnData:
        from omics.scrna.normalize import run_normalize
        return run_normalize(adata, **kwargs)

    def hvg(self, adata, **kwargs) -> ad.AnnData:
        from omics.scrna.hvg import run_hvg
        return run_hvg(adata, **kwargs)

    def pca(self, adata, **kwargs) -> ad.AnnData:
        from omics.scrna.pca import run_pca
        return run_pca(adata, **kwargs)

    def neighbors(self, adata, **kwargs) -> ad.AnnData:
        from omics.scrna.neighbors import run_neighbors
        return run_neighbors(adata, **kwargs)

    def umap(self, adata, **kwargs) -> ad.AnnData:
        from omics.scrna.umap import run_umap
        return run_umap(adata, **kwargs)

    def cluster(self, adata, **kwargs) -> ad.AnnData:
        from omics.scrna.cluster import run_leiden
        return run_leiden(adata, **kwargs)

    def markers(self, adata, **kwargs) -> ad.AnnData:
        from omics.scrna.markers import run_markers
        return run_markers(adata, **kwargs)

    def marker_table(self, adata) -> pd.DataFrame:
        from omics.scrna.markers import get_marker_table
        return get_marker_table(adata)

    def annotate(self, adata, **kwargs) -> ad.AnnData:
        from omics.scrna.annotation import run_marker_annotation
        return run_marker_annotation(adata, **kwargs)

    def batch_correct(self, adata, method="harmony", **kwargs) -> ad.AnnData:
        if method == "harmony":
            from omics.scrna.batch import run_harmony
            return run_harmony(adata, **kwargs)
        elif method == "scvi":
            from omics.scrna.batch import run_scvi
            return run_scvi(adata, **kwargs)
        elif method == "combat":
            from omics.scrna.batch import run_combat
            return run_combat(adata, **kwargs)
        raise ValueError(f"Unknown batch correction method: {method}")

    def trajectory(self, adata, method="dpt", **kwargs) -> ad.AnnData:
        if method == "dpt":
            from omics.scrna.trajectory import run_dpt
            return run_dpt(adata, **kwargs)
        elif method == "paga":
            from omics.scrna.trajectory import run_paga
            return run_paga(adata, **kwargs)
        elif method == "velocity":
            from omics.scrna.trajectory import run_velocity
            return run_velocity(adata, **kwargs)
        raise ValueError(f"Unknown trajectory method: {method}")

    def cell_communication(self, adata, **kwargs) -> ad.AnnData:
        from omics.scrna.communication import run_lr_analysis
        return run_lr_analysis(adata, **kwargs)

    def pipeline(self, adata, **kwargs) -> ad.AnnData:
        from omics.scrna.pipeline import run_standard_pipeline
        return run_standard_pipeline(adata, **kwargs)


class VizSDK:
    """Publication-quality visualization."""

    def __init__(self, sdk: OmicsSDK):
        self.sdk = sdk

    def compose(self, template: str, adata, output_path: Optional[Path] = None, **kwargs):
        from omics.viz.composer import SmartComposer
        story = SmartComposer.load_template(template)
        composer = SmartComposer()
        return composer.compose(story, adata, output_path=output_path, **kwargs)

    def umap(self, adata, color="leiden", output_path=None, **kwargs):
        """Generate a UMAP plot."""
        import scanpy as sc
        fig = sc.pl.umap(adata, color=color, return_fig=True, show=False)
        if output_path:
            from pathlib import Path
            fig.savefig(Path(output_path), dpi=300, bbox_inches="tight")
        return fig

    def heatmap(self, adata, var_names, groupby="leiden", output_path=None, **kwargs):
        import scanpy as sc
        fig = sc.pl.heatmap(adata, var_names=var_names, groupby=groupby, return_fig=True, show=False)
        if output_path:
            fig.savefig(Path(output_path), dpi=300, bbox_inches="tight")
        return fig
