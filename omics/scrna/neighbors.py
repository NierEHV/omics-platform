"""kNN neighborhood graph construction."""

import scanpy as sc
import anndata


def run_neighbors(adata: anndata.AnnData, n_neighbors: int = 15, n_pcs: int | None = None,
                  use_rep: str = "X_pca", metric: str = "euclidean") -> anndata.AnnData:
    """Compute the k-nearest-neighbors graph.

    Args:
        adata: AnnData with X_pca in .obsm.
        n_neighbors: Number of neighbors.
        n_pcs: Number of PCs to use (if None, uses all in X_pca).
        use_rep: Key in .obsm to use for distance computation.
        metric: Distance metric.

    Returns:
        AnnData with .obsp['connectivities'] and .obsp['distances'].
    """
    sc.pp.neighbors(adata, n_neighbors=n_neighbors, n_pcs=n_pcs, use_rep=use_rep, metric=metric)
    return adata
