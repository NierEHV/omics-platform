"""Batch correction: Harmony, scVI, ComBat."""

import logging
import anndata

logger = logging.getLogger(__name__)


def run_harmony(adata: anndata.AnnData, batch_key: str = "batch", theta: float = 2.0,
                max_iter_harmony: int = 10) -> anndata.AnnData:
    """Harmony batch correction.

    Requires: pip install harmonypy

    Args:
        adata: AnnData with X_pca in .obsm.
        batch_key: Column in .obs with batch labels.
        theta: Diversity clustering penalty.
        max_iter_harmony: Maximum Harmony iterations.

    Returns:
        AnnData with .obsm['X_pca_harmony'] set.
    """
    try:
        import harmonypy
    except ImportError:
        raise ImportError("harmonypy not installed. Run: pip install harmonypy")

    ho = harmonypy.run_harmony(
        adata.obsm["X_pca"], adata.obs, batch_key,
        theta=theta, max_iter_harmony=max_iter_harmony,
    )
    adata.obsm["X_pca_harmony"] = ho.Z_corr.T
    return adata


def run_scvi(adata: anndata.AnnData, batch_key: str = "batch",
             n_latent: int = 30, n_layers: int = 2, max_epochs: int = 400) -> anndata.AnnData:
    """scVI deep batch correction.

    Requires: pip install scvi-tools

    Args:
        adata: AnnData with raw counts in .X.
        batch_key: Column in .obs with batch labels.
        n_latent: Latent space dimension.
        n_layers: Number of hidden layers.
        max_epochs: Maximum training epochs.

    Returns:
        AnnData with .obsm['X_scvi'] (latent representation).
    """
    try:
        import scvi
    except ImportError:
        raise ImportError("scvi-tools not installed. Run: pip install scvi-tools")

    scvi.model.SCVI.setup_anndata(adata, batch_key=batch_key)
    model = scvi.model.SCVI(adata, n_latent=n_latent, n_layers=n_layers)
    model.train(max_epochs=max_epochs)
    adata.obsm["X_scvi"] = model.get_latent_representation()
    return adata


def run_combat(adata: anndata.AnnData, batch_key: str = "batch") -> anndata.AnnData:
    """ComBat batch correction (simplified implementation).

    Adjusts mean and variance per gene across batches using
    empirical Bayes shrinkage. For full ComBat, use the R version.

    Args:
        adata: Log-normalized AnnData.
        batch_key: Column in .obs with batch labels.

    Returns:
        AnnData with batch-corrected expression in .layers['combat_corrected'].
    """
    import numpy as np
    import pandas as pd

    expr = adata.X.toarray() if hasattr(adata.X, "toarray") else adata.X
    batches = adata.obs[batch_key].values
    batch_labels = sorted(set(batches))

    corrected = expr.copy().astype(float)
    grand_mean = expr.mean(axis=0)
    grand_var = expr.var(axis=0, ddof=1)

    for batch in batch_labels:
        mask = batches == batch
        if mask.sum() < 3:
            continue
        batch_expr = expr[mask]
        batch_mean = batch_expr.mean(axis=0)
        batch_var = batch_expr.var(axis=0, ddof=1)

        # Empirical Bayes shrinkage
        gamma = (batch_var / (grand_var + 1e-8))
        gamma = np.clip(gamma, 0.1, 10)
        adj_std = np.sqrt(np.maximum(grand_var, 1e-8) * gamma)

        for j in range(expr.shape[1]):
            if adj_std[j] > 0:
                corrected[mask, j] = (expr[mask, j] - batch_mean[j]) / adj_std[j]
                corrected[mask, j] = corrected[mask, j] * np.sqrt(np.maximum(grand_var[j], 1e-8)) + grand_mean[j]

    adata.layers["combat_corrected"] = corrected
    return adata
