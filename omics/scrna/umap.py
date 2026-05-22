"""UMAP embedding (CPU + GPU)."""

import logging
import scanpy as sc
import anndata

logger = logging.getLogger(__name__)


def run_umap(adata: anndata.AnnData, min_dist: float = 0.5, spread: float = 1.0,
             n_components: int = 2, use_gpu: bool = False) -> anndata.AnnData:
    """Compute UMAP embedding.

    Requires run_neighbors() to have been called first.

    Args:
        adata: AnnData with neighbor graph computed.
        min_dist: Minimum distance between embedded points.
        spread: Effective scale of embedded points.
        n_components: Dimension of the embedding (usually 2).
        use_gpu: Attempt GPU UMAP via cuML.

    Returns:
        AnnData with .obsm['X_umap'] set.
    """
    if use_gpu:
        try:
            return _run_umap_gpu(adata, min_dist, spread, n_components)
        except Exception as e:
            logger.warning(f"GPU UMAP failed ({e}), falling back to CPU")

    sc.tl.umap(adata, min_dist=min_dist, spread=spread, n_components=n_components)
    return adata


def _run_umap_gpu(adata: anndata.AnnData, min_dist: float = 0.1,
                  spread: float = 1.0, n_components: int = 2) -> anndata.AnnData:
    from cuml.manifold import UMAP as cuUMAP
    model = cuUMAP(n_components=n_components, min_dist=min_dist, spread=spread)
    result = model.fit_transform(adata.obsm["X_pca"])
    adata.obsm["X_umap"] = result
    return adata
