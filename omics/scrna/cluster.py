"""Community detection clustering."""

import scanpy as sc
import anndata


def run_leiden(adata: anndata.AnnData, resolution: float = 1.0, key_added: str = "leiden",
               n_iterations: int = -1, use_gpu: bool = False) -> anndata.AnnData:
    """Leiden community detection.

    Requires run_neighbors() to have been called first.

    Args:
        adata: AnnData with neighbor graph computed.
        resolution: Clustering resolution (higher = more clusters).
        key_added: Key in .obs for cluster assignments.
        n_iterations: Number of iterations (-1 = until convergence).

    Returns:
        AnnData with cluster labels in .obs[key_added].
    """
    if use_gpu:
        try:
            return _run_leiden_gpu(adata, resolution)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"GPU Leiden failed ({e}), falling back to CPU")

    sc.tl.leiden(adata, resolution=resolution, key_added=key_added, n_iterations=n_iterations,
                 flavor="igraph", directed=False)
    return adata


def _run_leiden_gpu(adata: anndata.AnnData, resolution: float = 1.0) -> anndata.AnnData:
    from cugraph import leiden
    import cupy as cp
    import pandas as pd

    if "connectivities" not in adata.obsp:
        raise ValueError("Neighbor graph not found. Run run_neighbors() first.")
    adj = adata.obsp["connectivities"]
    adj_gpu = cp.array(adj.toarray() if hasattr(adj, "toarray") else adj, dtype=cp.float32)
    vertices, clusters, _ = leiden(adj_gpu, resolution=resolution)
    adata.obs["leiden"] = pd.Categorical(clusters)
    return adata


def run_louvain(adata: anndata.AnnData, resolution: float = 1.0,
                key_added: str = "louvain") -> anndata.AnnData:
    """Louvain clustering (alternative to Leiden)."""
    sc.tl.louvain(adata, resolution=resolution, key_added=key_added, flavor="igraph")
    return adata


def run_consensus(adata: anndata.AnnData, resolutions: tuple = (0.4, 0.8, 1.2, 1.6, 2.0),
                  key_added: str = "consensus") -> anndata.AnnData:
    """Consensus clustering across multiple resolutions."""
    import numpy as np
    n_cells = adata.n_obs
    co_occurrence = np.zeros((n_cells, n_cells))

    for res in resolutions:
        sc.tl.leiden(adata, resolution=res, key_added=f"_tmp_res_{res}", flavor="igraph")
        labels = adata.obs[f"_tmp_res_{res}"].cat.codes.values
        for i in range(n_cells):
            co_occurrence[i, :] += (labels[i] == labels)

    co_occurrence /= len(resolutions)
    sc.tl.leiden(adata, adjacency=co_occurrence, key_added=key_added, flavor="igraph")
    return adata
