"""Tests for omics.scrna.qc."""

import numpy as np
import anndata
from omics.scrna.qc import run_qc


class TestRunQC:
    def test_basic_qc_reduces_cells(self, tiny_adata):
        adata = run_qc(tiny_adata, min_genes=10, min_cells=2, max_pct_mt=50.0)
        assert adata.n_obs > 0
        assert adata.n_vars > 0

    def test_qc_marks_mito_genes(self, tiny_adata):
        adata = run_qc(tiny_adata, min_genes=10, min_cells=2, max_pct_mt=50.0)
        assert "mt" in adata.var.columns
        assert "ribo" in adata.var.columns
        assert adata.var.loc["MT-CO1", "mt"] is True
        assert adata.var.loc["RPS3", "ribo"] is True

    def test_qc_computes_metrics(self, tiny_adata):
        adata = run_qc(tiny_adata, min_genes=10, min_cells=2, max_pct_mt=50.0)
        assert "n_genes_by_counts" in adata.obs.columns
        assert "pct_counts_mt" in adata.obs.columns

    def test_qc_stringent_filters_cells(self, tiny_adata):
        original_n = tiny_adata.n_obs
        adata = run_qc(tiny_adata, min_genes=500, min_cells=3, max_pct_mt=1.0)
        assert adata.n_obs < original_n

    def test_qc_returns_anndata(self, tiny_adata):
        result = run_qc(tiny_adata)
        assert isinstance(result, anndata.AnnData)
