"""Shared fixtures for omics-platform tests."""

import numpy as np
import pandas as pd
import pytest
import anndata


@pytest.fixture
def tiny_adata() -> anndata.AnnData:
    """Synthetic AnnData: 200 cells x 100 genes, raw counts, no preprocessing."""
    rng = np.random.default_rng(42)
    n_cells, n_genes = 200, 100
    X = rng.poisson(5, size=(n_cells, n_genes)).astype(np.float32)
    X[:10, :10] = rng.poisson(50, size=(10, 10)).astype(np.float32)  # Some highly expressed

    gene_names = [f"GENE_{i}" for i in range(n_genes)]
    # Add mitochondrial and ribosomal genes
    gene_names[0] = "MT-CO1"
    gene_names[1] = "MT-ND1"
    gene_names[2] = "RPS3"
    gene_names[3] = "RPL5"

    cell_names = [f"Cell_{i}" for i in range(n_cells)]

    adata = anndata.AnnData(X, obs=pd.DataFrame(index=cell_names), var=pd.DataFrame(index=gene_names))
    adata.obs["batch"] = ["A"] * 150 + ["B"] * 50
    return adata


@pytest.fixture
def qc_adata(tiny_adata) -> anndata.AnnData:
    """AnnData after QC: mt/ribo genes marked, basic filtering applied."""
    from omics.scrna.qc import run_qc
    return run_qc(tiny_adata, min_genes=10, min_cells=2, max_pct_mt=50.0)


@pytest.fixture
def norm_adata(qc_adata) -> anndata.AnnData:
    """AnnData after QC + normalization."""
    from omics.scrna.normalize import run_normalize
    return run_normalize(qc_adata, target_sum=10000)


@pytest.fixture
def hvg_adata(norm_adata) -> anndata.AnnData:
    """AnnData after QC + norm + HVG selection."""
    from omics.scrna.hvg import run_hvg
    return run_hvg(norm_adata, n_top_genes=50)


@pytest.fixture
def full_adata(tiny_adata) -> anndata.AnnData:
    """AnnData after complete standard pipeline."""
    from omics.scrna.pipeline import run_standard_pipeline
    return run_standard_pipeline(
        tiny_adata,
        min_genes=10,
        min_cells=2,
        max_pct_mt=50.0,
        target_sum=10000,
        n_hvg=50,
        n_pcs=10,
        n_neighbors=5,
        resolution=0.5,
    )
