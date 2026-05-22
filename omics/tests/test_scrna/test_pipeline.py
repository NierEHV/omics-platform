"""Tests for omics.scrna.pipeline — end-to-end standard pipeline."""

import anndata
from omics.scrna.pipeline import run_standard_pipeline


class TestStandardPipeline:
    def test_pipeline_runs_end_to_end(self, tiny_adata):
        adata = run_standard_pipeline(
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
        assert isinstance(adata, anndata.AnnData)
        assert adata.n_obs > 0
        assert adata.n_vars > 0

    def test_pipeline_produces_pca(self, tiny_adata):
        adata = run_standard_pipeline(
            tiny_adata, min_genes=10, min_cells=2, max_pct_mt=50.0,
            n_hvg=50, n_pcs=10, n_neighbors=5, resolution=0.5,
        )
        assert "X_pca" in adata.obsm

    def test_pipeline_produces_umap(self, tiny_adata):
        adata = run_standard_pipeline(
            tiny_adata, min_genes=10, min_cells=2, max_pct_mt=50.0,
            n_hvg=50, n_pcs=10, n_neighbors=5, resolution=0.5,
        )
        assert "X_umap" in adata.obsm

    def test_pipeline_produces_clusters(self, tiny_adata):
        adata = run_standard_pipeline(
            tiny_adata, min_genes=10, min_cells=2, max_pct_mt=50.0,
            n_hvg=50, n_pcs=10, n_neighbors=5, resolution=0.5,
        )
        assert "leiden" in adata.obs.columns
        assert adata.obs["leiden"].nunique() >= 1

    def test_pipeline_produces_markers(self, tiny_adata):
        adata = run_standard_pipeline(
            tiny_adata, min_genes=10, min_cells=2, max_pct_mt=50.0,
            n_hvg=50, n_pcs=10, n_neighbors=5, resolution=0.5,
        )
        assert "rank_genes_groups" in adata.uns

    def test_pipeline_preserves_raw_layer(self, tiny_adata):
        adata = run_standard_pipeline(
            tiny_adata, min_genes=10, min_cells=2, max_pct_mt=50.0,
            n_hvg=50, n_pcs=10, n_neighbors=5, resolution=0.5,
        )
        assert "raw" in adata.layers
