import pytest
import numpy as np
import pandas as pd
import anndata
from omics.spatial.analysis import SpatialAnalysis


@pytest.fixture
def mock_spatial_adata():
    """Synthetic spatial data: 100 spots x 200 genes, with spatial coords."""
    rng = np.random.RandomState(42)
    n_spots, n_genes = 100, 200
    adata = anndata.AnnData(
        X=rng.poisson(5, (n_spots, n_genes)).astype(np.float64),
        obs=pd.DataFrame(index=[f'spot_{i}' for i in range(n_spots)]),
        var=pd.DataFrame(index=[f'G{i}' for i in range(n_genes)]),
    )
    adata.obsm['spatial'] = rng.rand(n_spots, 2) * 100
    return adata


def test_preprocess_filters_spots(mock_spatial_adata):
    pytest.importorskip("squidpy")
    sa = SpatialAnalysis()
    result = sa.preprocess(mock_spatial_adata, min_counts=50)
    assert result.n_obs <= 100


def test_cluster_adds_leiden(mock_spatial_adata):
    pytest.importorskip("squidpy")
    sa = SpatialAnalysis()
    result = sa.cluster(mock_spatial_adata)
    assert 'leiden' in result.obs.columns
    assert 'X_umap' in result.obsm


def test_niche_analysis(mock_spatial_adata):
    pytest.importorskip("squidpy")
    sa = SpatialAnalysis()
    mock_spatial_adata.obs['leiden'] = np.random.choice(['0', '1', '2', '3'], 100)
    result = sa.niche_analysis(mock_spatial_adata)
    assert 'cluster_key' in result


def test_spatial_variable_genes(mock_spatial_adata):
    sa = SpatialAnalysis()
    result = sa.spatial_variable_genes(mock_spatial_adata)
    assert 'gene' in result.columns
    assert len(result) == mock_spatial_adata.n_vars


def test_spatial_markers(mock_spatial_adata):
    pytest.importorskip("squidpy")
    sa = SpatialAnalysis()
    mock_spatial_adata.obs['leiden'] = np.random.choice(['0', '1', '2'], 100)
    result = sa.spatial_markers(mock_spatial_adata)
    assert result is not None


def test_lr_spatial(mock_spatial_adata):
    pytest.importorskip("squidpy")
    sa = SpatialAnalysis()
    mock_spatial_adata.obs['leiden'] = np.random.choice(['0', '1', '2'], 100)
    result = sa.lr_spatial(mock_spatial_adata)
    assert isinstance(result, pd.DataFrame)
