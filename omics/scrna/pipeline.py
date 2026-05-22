"""Convenience pipeline: run the standard scRNA-seq workflow in one call."""

import logging
import anndata
from omics.scrna.qc import run_qc
from omics.scrna.normalize import run_normalize
from omics.scrna.hvg import run_hvg
from omics.scrna.pca import run_pca
from omics.scrna.neighbors import run_neighbors
from omics.scrna.umap import run_umap
from omics.scrna.cluster import run_leiden
from omics.scrna.markers import run_markers

logger = logging.getLogger(__name__)


def run_standard_pipeline(adata: anndata.AnnData, **kwargs) -> anndata.AnnData:
    """Run the standard scRNA-seq workflow end-to-end.

    QC → normalize → HVG → PCA → neighbors → UMAP → Leiden → markers.

    Args:
        adata: Raw counts AnnData.
        **kwargs: Passed through to individual functions:
            min_genes, min_cells, max_pct_mt, target_sum, n_hvg,
            n_pcs, n_neighbors, resolution, use_gpu.

    Returns:
        Processed AnnData with X_pca, X_umap, leiden, and markers.
    """
    adata = run_qc(adata,
                   min_genes=kwargs.get("min_genes", 200),
                   min_cells=kwargs.get("min_cells", 3),
                   max_pct_mt=kwargs.get("max_pct_mt", 20.0))
    adata = run_normalize(adata, target_sum=kwargs.get("target_sum", 10000))
    adata = run_hvg(adata, n_top_genes=kwargs.get("n_hvg", 2000))
    adata = run_pca(adata, n_comps=kwargs.get("n_pcs", 50), use_gpu=kwargs.get("use_gpu", False))
    adata = run_neighbors(adata, n_neighbors=kwargs.get("n_neighbors", 15))
    adata = run_umap(adata, use_gpu=kwargs.get("use_gpu", False))
    adata = run_leiden(adata, resolution=kwargs.get("resolution", 1.0))
    adata = run_markers(adata)
    logger.info(f"Pipeline complete: {adata.n_obs} cells, {adata.obs['leiden'].nunique()} clusters")
    return adata


def run_pipeline_dag(adata: anndata.AnnData, use_gpu: bool = False,
                     include_annotation: bool = False,
                     include_trajectory: bool = False,
                     include_communication: bool = False,
                     **kwargs) -> anndata.AnnData:
    """Run a DAG-based pipeline with provenance tracking.

    Uses the pipeline engine for topological execution with checkpointing.
    """
    from omics.pipeline.dag import Pipeline

    pipe = Pipeline(name="scRNA-seq Pipeline")

    pipe.add_stage("qc", lambda ctx: run_qc(adata, **kwargs), description="Quality control")
    pipe.add_stage("normalize", lambda ctx: run_normalize(adata, **kwargs),
                   depends_on=["qc"], description="Normalize + log1p")
    pipe.add_stage("hvg", lambda ctx: run_hvg(adata, **kwargs),
                   depends_on=["normalize"], description="HVG selection")
    pipe.add_stage("pca", lambda ctx: run_pca(adata, use_gpu=use_gpu, **kwargs),
                   depends_on=["hvg"], description="PCA", gpu_beneficial=True)
    pipe.add_stage("neighbors", lambda ctx: run_neighbors(adata, **kwargs),
                   depends_on=["pca"], description="kNN graph")
    pipe.add_stage("umap", lambda ctx: run_umap(adata, use_gpu=use_gpu),
                   depends_on=["neighbors"], description="UMAP", gpu_beneficial=True)
    pipe.add_stage("cluster", lambda ctx: run_leiden(adata, **kwargs),
                   depends_on=["neighbors"], description="Leiden clustering")
    pipe.add_stage("markers", lambda ctx: run_markers(adata),
                   depends_on=["cluster"], description="Marker genes")

    pipe.run(use_gpu=use_gpu)
    return adata
