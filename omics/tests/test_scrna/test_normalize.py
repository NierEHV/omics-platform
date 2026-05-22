"""Tests for omics.scrna.normalize."""

import numpy as np
import anndata
from omics.scrna.normalize import run_normalize


class TestRunNormalize:
    def test_normalize_sets_raw_layer(self, qc_adata):
        adata = run_normalize(qc_adata, target_sum=10000)
        assert "raw" in adata.layers
        assert "log1p" in adata.layers

    def test_normalize_returns_anndata(self, qc_adata):
        result = run_normalize(qc_adata)
        assert isinstance(result, anndata.AnnData)

    def test_normalize_preserves_cell_count(self, qc_adata):
        n_before = qc_adata.n_obs
        adata = run_normalize(qc_adata)
        assert adata.n_obs == n_before

    def test_normalize_target_sum_effect(self, qc_adata):
        adata = run_normalize(qc_adata, target_sum=10000)
        row_sums = np.array(adata.X.sum(axis=1)).flatten()
        np.testing.assert_allclose(row_sums, 1, atol=0.5)  # log1p of normalized
