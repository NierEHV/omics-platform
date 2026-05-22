"""Highly variable gene selection."""

import scanpy as sc
import anndata


def run_hvg(adata: anndata.AnnData, n_top_genes: int = 2000, flavor: str = "seurat",
            batch_key: str | None = None, span: float = 0.3) -> anndata.AnnData:
    """Select highly variable genes.

    Args:
        adata: Normalized, log-transformed AnnData.
        n_top_genes: Number of HVGs to select.
        flavor: 'seurat', 'seurat_v3', or 'cell_ranger'.
        batch_key: obs column for batch-aware HVG selection.
        span: Loess span for seurat_v3 flavor.

    Returns:
        AnnData with .var['highly_variable'] boolean column.
    """
    sc.pp.highly_variable_genes(adata, n_top_genes=n_top_genes, flavor=flavor,
                                batch_key=batch_key, span=span)
    return adata
