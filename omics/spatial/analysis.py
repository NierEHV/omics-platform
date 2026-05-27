"""Concrete spatial transcriptomics backend backed by Squidpy, cell2location, SPARK-X."""
from typing import Any, Optional
import anndata
import pandas as pd
import numpy as np
from .base import AbstractSpatialAnalysis


class SpatialAnalysis(AbstractSpatialAnalysis):

    def preprocess(self, adata: anndata.AnnData, **kwargs) -> anndata.AnnData:
        """QC + normalize spatial data via Squidpy."""
        import squidpy as sq
        import scanpy as sc
        min_counts = kwargs.pop('min_counts', 100)
        min_spots = kwargs.pop('min_spots', 3)
        max_pct_mt = kwargs.pop('max_pct_mt', 20)

        sq.pp.filter_genes(adata, min_counts=min_counts)
        sq.pp.filter_spots(adata, min_counts=min_spots)

        # MT fraction filtering
        mt_mask = adata.var_names.str.lower().str.startswith('mt-')
        if mt_mask.any():
            adata.obs['pct_mt'] = (
                adata[:, mt_mask].X.sum(axis=1).A1 if hasattr(adata[:, mt_mask].X, 'A1')
                else np.array(adata[:, mt_mask].X.sum(axis=1)).flatten()
            ) / np.array(adata.X.sum(axis=1)).flatten() * 100
            adata = adata[adata.obs['pct_mt'] < max_pct_mt, :].copy()

        sq.pp.calculate_qc_metrics(adata, inplace=True)
        sc.pp.normalize_total(adata, target_sum=1e4)
        sc.pp.log1p(adata)
        return adata

    def cluster(self, adata: anndata.AnnData, **kwargs) -> anndata.AnnData:
        """Spatial-aware clustering via Squidpy + scanpy."""
        import squidpy as sq
        import scanpy as sc
        n_neighbors = kwargs.pop('n_neighbors', 15)
        resolution = kwargs.pop('resolution', 1.0)
        n_pcs = kwargs.pop('n_pcs', 50)

        sq.gr.spatial_neighbors(adata, n_neighs=n_neighbors, **kwargs)
        sc.pp.pca(adata, n_comps=min(n_pcs, adata.n_vars - 1))
        sc.pp.neighbors(adata, n_neighbors=n_neighbors)
        sc.tl.leiden(adata, resolution=resolution)
        sc.tl.umap(adata)
        return adata

    def deconvolve(self, adata: anndata.AnnData, reference: anndata.AnnData,
                   **kwargs) -> anndata.AnnData:
        """Cell-type deconvolution from spatial spots via cell2location."""
        import cell2location
        cell2location.run_cell2location(adata, reference, **kwargs)
        return adata

    def niche_analysis(self, adata: anndata.AnnData,
                       cluster_key: str = 'leiden', **kwargs) -> dict:
        """Cellular neighborhood / niche analysis via Squidpy."""
        import squidpy as sq
        if 'spatial_neighbors' not in adata.uns:
            sq.gr.spatial_neighbors(adata)
        sq.gr.nhood_enrichment(adata, cluster_key=cluster_key)
        return {
            'nhood_enrichment': adata.uns.get('nhood_enrichment'),
            'cluster_key': cluster_key,
        }

    def lr_spatial(self, adata: anndata.AnnData, cluster_key: str = 'leiden',
                   **kwargs) -> pd.DataFrame:
        """Spatially-aware ligand-receptor analysis via Squidpy ligrec."""
        import squidpy as sq
        sq.gr.ligrec(adata, cluster_key=cluster_key, **kwargs)
        return adata.uns.get('ligrec', pd.DataFrame())

    def spatial_variable_genes(self, adata: anndata.AnnData, **kwargs) -> pd.DataFrame:
        """Detect spatially variable genes. SPARK-X with Squidpy Moran's I fallback."""
        try:
            import sparkx
            results = sparkx.run(adata.X.T, adata.obsm['spatial'])
            return pd.DataFrame({
                'gene': adata.var_names,
                'pvalue': results.get('pval', results.get('pvalue', [])),
                'qvalue': results.get('adj_pval', results.get('qvalue', [])),
            }).sort_values('pvalue')
        except (ImportError, KeyError):
            try:
                import squidpy as sq
                sq.gr.spatial_autocorr(adata, mode='moran')
                result = adata.uns.get('moranI', pd.DataFrame())
                if isinstance(result, pd.DataFrame):
                    return result.sort_values('moranI', ascending=False) if 'moranI' in result.columns else result
            except ImportError:
                pass
            return pd.DataFrame({'gene': adata.var_names})

    def spatial_markers(self, adata: anndata.AnnData,
                        cluster_key: str = 'leiden', **kwargs) -> pd.DataFrame:
        """Find spatially-aware marker genes per cluster via Squidpy."""
        import squidpy as sq
        sq.tl.marker_genes(adata, cluster_key=cluster_key, **kwargs)
        return adata.uns.get('marker_genes', pd.DataFrame())
