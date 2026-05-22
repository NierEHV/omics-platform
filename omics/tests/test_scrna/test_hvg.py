"""Tests for omics.scrna.hvg."""

import anndata
from omics.scrna.hvg import run_hvg


class TestRunHVG:
    def test_hvg_marks_variable_genes(self, norm_adata):
        adata = run_hvg(norm_adata, n_top_genes=50)
        assert "highly_variable" in adata.var.columns
        assert adata.var["highly_variable"].sum() > 0
        assert adata.var["highly_variable"].sum() <= 50

    def test_hvg_respects_n_top_genes(self, norm_adata):
        adata = run_hvg(norm_adata, n_top_genes=20)
        assert adata.var["highly_variable"].sum() <= 20

    def test_hvg_returns_anndata(self, norm_adata):
        result = run_hvg(norm_adata)
        assert isinstance(result, anndata.AnnData)
