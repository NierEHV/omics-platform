"""Library-size normalization and log transformation."""

import scanpy as sc
import anndata


def run_normalize(adata: anndata.AnnData, target_sum: float = 10000,
                  exclude_highly_expressed: bool = False, max_fraction: float = 0.05) -> anndata.AnnData:
    """Normalize total counts per cell and log1p-transform.

    Args:
        adata: AnnData with raw counts in .X.
        target_sum: Target sum per cell after normalization.
        exclude_highly_expressed: Exclude very highly expressed genes.
        max_fraction: Maximum fraction of counts for a gene to be included.

    Returns:
        AnnData with .layers['raw'] set and .X replaced by log1p(normalized).
    """
    adata.layers["raw"] = adata.X.copy()
    sc.pp.normalize_total(adata, target_sum=target_sum,
                          exclude_highly_expressed=exclude_highly_expressed,
                          max_fraction=max_fraction)
    sc.pp.log1p(adata)
    adata.layers["log1p"] = adata.X.copy()
    return adata
