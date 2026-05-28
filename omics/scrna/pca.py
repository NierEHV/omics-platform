"""PCA dimensionality reduction (CPU + GPU)."""

import logging
import scanpy as sc
import anndata

logger = logging.getLogger(__name__)


def run_pca(adata: anndata.AnnData, n_comps: int = 50, svd_solver: str = "arpack",
            use_highly_variable: bool = True, use_gpu: bool = False) -> anndata.AnnData:
    """Run PCA dimensionality reduction.

    Args:
        adata: AnnData with log-normalized expression.
        n_comps: Number of principal components.
        svd_solver: SVD solver ('arpack', 'randomized', 'auto').
        use_highly_variable: Only use HVGs for PCA. Falls back to all genes
            if 'highly_variable' column is not in adata.var.
        use_gpu: Attempt GPU-accelerated PCA via cuML.

    Returns:
        AnnData with .obsm['X_pca'] set.
    """
    if use_gpu:
        try:
            return _run_pca_gpu(adata, n_comps)
        except Exception as e:
            logger.warning(f"GPU PCA failed ({e}), falling back to CPU")

    mask = None
    if use_highly_variable:
        hv = adata.var.get("highly_variable")
        if hv is not None and hv.sum() > 0:
            mask = "highly_variable"

    sc.pp.pca(adata, n_comps=n_comps, svd_solver=svd_solver, mask_var=mask)
    return adata


def _run_pca_gpu(adata: anndata.AnnData, n_comps: int = 50) -> anndata.AnnData:
    import cupy as cp
    from cuml.decomposition import PCA as cuPCA

    expr = adata.X.toarray() if hasattr(adata.X, "toarray") else adata.X
    expr_gpu = cp.array(expr, dtype=cp.float32)
    model = cuPCA(n_components=n_comps)
    result = model.fit_transform(expr_gpu)
    adata.obsm["X_pca"] = cp.asnumpy(result)
    return adata
