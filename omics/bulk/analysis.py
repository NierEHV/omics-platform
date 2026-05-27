"""Concrete bulk RNA-seq analysis backed by pandas + rpy2 DESeq2 + GSEApy."""
from __future__ import annotations
from typing import Any, Optional
import logging
import re
import numpy as np
import pandas as pd
import anndata
from .base import AbstractBulkRNAAnalysis

logger = logging.getLogger(__name__)


class BulkRNAAnalysis(AbstractBulkRNAAnalysis):

    def load_counts(self, path: str, **kwargs) -> anndata.AnnData:
        """Load count matrix (CSV/TSV). First column = gene_id, rest = samples."""
        sep = kwargs.pop('sep', '\t' if str(path).endswith('.tsv') else ',')
        raw = pd.read_csv(path, sep=sep, **kwargs)
        gene_ids = raw.iloc[:, 0].astype(str).values
        sample_ids = [re.sub(r'[^a-zA-Z0-9_.-]', '_', str(c)) for c in raw.columns[1:].tolist()]
        counts = raw.iloc[:, 1:].values.astype(np.float64)
        adata = anndata.AnnData(
            X=counts.T,
            obs=pd.DataFrame(index=sample_ids),
            var=pd.DataFrame(index=gene_ids),
        )
        adata.var['gene_id'] = gene_ids
        return adata

    def qc_filter(self, adata: anndata.AnnData, min_total_count: int = 10,
                  **kwargs) -> anndata.AnnData:
        """Remove genes with total count < min_total_count across all samples."""
        gene_sums = np.array(adata.X.sum(axis=0)).flatten()
        keep = gene_sums >= min_total_count
        return adata[:, keep].copy()

    def normalize(self, adata: anndata.AnnData, method: str = "deseq2",
                  **kwargs) -> anndata.AnnData:
        """DESeq2 median-of-ratios normalization via rpy2. Falls back to CPM."""
        if method not in ("deseq2", "cpm"):
            raise ValueError(f"Unknown normalization method: {method}. Supported: deseq2, cpm")
        if method == "deseq2":
            try:
                from rpy2.robjects import pandas2ri, r
                from rpy2.robjects.packages import importr
                pandas2ri.activate()
                deseq2 = importr('DESeq2')
                counts_df = pd.DataFrame(
                    adata.X.T.astype(int), index=adata.var_names, columns=adata.obs_names
                )
                r_counts = pandas2ri.py2rpy(counts_df)
                r.assign('counts_r', r_counts)
                r('dds <- DESeqDataSetFromMatrix(countData=counts_r, '
                  'colData=data.frame(condition=factor(colnames(counts_r))), '
                  'design=~1)')
                r('dds <- estimateSizeFactors(dds)')
                sf = np.array(r('sizeFactors(dds)'))
                adata.layers['normalized'] = adata.X / sf[:, None]
                adata.uns['normalization'] = 'deseq2_mr'
                return adata
            except (ImportError, ModuleNotFoundError, Exception) as exc:
                logger.warning("DESeq2 normalization failed, falling back to CPM: %s", exc)
        # Fallback: simple library-size normalization (CPM)
        lib_sizes = np.array(adata.X.sum(axis=1)).flatten()
        adata.layers['cpm'] = (adata.X / lib_sizes[:, None]) * 1e6
        adata.uns['normalization'] = 'cpm_fallback'
        return adata

    def differential_expression(self, adata: anndata.AnnData, design: str,
                                 contrast: tuple, **kwargs) -> pd.DataFrame:
        """DESeq2 differential expression via rpy2. Returns log2FC, pvalue, padj."""
        from rpy2.robjects import pandas2ri, r
        from rpy2.robjects.packages import importr
        pandas2ri.activate()
        deseq2 = importr('DESeq2')
        counts_df = pd.DataFrame(
            adata.X.T.astype(int), index=adata.var_names, columns=adata.obs_names
        )
        if contrast[0] not in adata.obs.columns:
            raise ValueError(f"Contrast column '{contrast[0]}' not found in obs. Available columns: {list(adata.obs.columns)}")
        if not re.match(r'^~\s*\w+(\s*[+*]\s*\w+)*$', design):
            raise ValueError(f"Invalid design formula: {design}. Use format: ~condition")
        for i, val in enumerate(contrast):
            if not re.match(r'^[a-zA-Z0-9_.-]+$', str(val)):
                raise ValueError(f"Invalid contrast value: {val}")
            r.assign(f'contrast_val{i+1}', str(val))
        condition = np.array(adata.obs[contrast[0]].values)
        r_counts = pandas2ri.py2rpy(counts_df)
        r.assign('counts_r', r_counts)
        r.assign('condition_r', condition)
        r.assign('design_formula', design)
        r('dds <- DESeqDataSetFromMatrix(countData=counts_r, '
          'colData=data.frame(condition=condition_r), design=design_formula)')
        r('dds <- DESeq(dds)')
        r('res <- results(dds, contrast=c(contrast_val1, contrast_val2, contrast_val3))')
        res_df = pandas2ri.rpy2py(r('as.data.frame(res)'))
        return res_df.rename(columns={
            'log2FoldChange': 'log2FC', 'pvalue': 'pvalue', 'padj': 'padj'
        })

    def enrichment(self, de_results: pd.DataFrame, gene_sets: str = "GO",
                   **kwargs) -> pd.DataFrame:
        """GSEApy enrichment analysis. gene_sets: GO/KEGG/MSigDB."""
        import gseapy as gp
        de_results = de_results.dropna(subset=['pvalue'])
        if 'log2FC' not in de_results.columns:
            raise ValueError("DE results must contain a 'log2FC' column for enrichment ranking")
        de_results = de_results.copy()
        de_results['rank'] = -np.log10(de_results['pvalue'].values) * np.sign(
            de_results['log2FC'].values
        )
        ranked = de_results['rank'].sort_values(ascending=False)
        if gene_sets == "GO":
            gs = 'GO_Biological_Process_2023'
        elif gene_sets == "KEGG":
            gs = 'KEGG_2021_Human'
        elif gene_sets == "MSigDB":
            gs = 'MSigDB_Hallmark_2020'
        else:
            gs = gene_sets
        enr = gp.prerank(rnk=ranked, gene_sets=gs, seed=42, **kwargs)
        return enr.res2d

    def visualize_volcano(self, de_results: pd.DataFrame, output: Optional[str] = None,
                          **kwargs):
        """Volcano plot: log2FC vs -log10(padj)."""
        import matplotlib.pyplot as plt
        df = de_results.dropna(subset=['padj', 'log2FC'])
        fig, ax = plt.subplots(figsize=(8, 6))
        sig = df['padj'] < 0.05
        ax.scatter(df.loc[~sig, 'log2FC'], -np.log10(df.loc[~sig, 'padj']),
                   c='grey', s=5, alpha=0.3, label='NS')
        ax.scatter(df.loc[sig, 'log2FC'], -np.log10(df.loc[sig, 'padj']),
                   c='red', s=10, alpha=0.6, label='padj<0.05')
        ax.axhline(-np.log10(0.05), ls='--', color='grey', alpha=0.5)
        ax.set_xlabel('log2 Fold Change'); ax.set_ylabel('-log10(padj)')
        ax.legend()
        if output:
            fig.savefig(output, dpi=300, bbox_inches='tight')
        return fig

    def visualize_heatmap(self, adata: anndata.AnnData, gene_list: list[str],
                          output: Optional[str] = None, **kwargs):
        """Heatmap of selected genes across samples."""
        import matplotlib.pyplot as plt
        import seaborn as sns
        idx = [i for i, g in enumerate(adata.var_names) if g in gene_list]
        if not idx:
            raise ValueError("No matching genes found")
        mat = adata.X[:, idx]
        fig, ax = plt.subplots(figsize=(max(8, len(idx)*0.3), max(6, adata.n_obs*0.3)))
        sns.heatmap(pd.DataFrame(mat, index=adata.obs_names, columns=adata.var_names[idx]),
                    cmap='RdBu_r', center=0, ax=ax)
        if output:
            fig.savefig(output, dpi=300, bbox_inches='tight')
        return fig

    def visualize_pca(self, adata: anndata.AnnData, output: Optional[str] = None,
                      **kwargs):
        """PCA plot of samples."""
        from sklearn.decomposition import PCA
        import matplotlib.pyplot as plt
        pca = PCA(n_components=2)
        coords = pca.fit_transform(adata.X)
        fig, ax = plt.subplots(figsize=(6, 6))
        ax.scatter(coords[:, 0], coords[:, 1], s=80)
        for i, name in enumerate(adata.obs_names):
            ax.annotate(name, (coords[i, 0], coords[i, 1]), fontsize=8)
        ax.set_xlabel(f'PC1 ({pca.explained_variance_ratio_[0]:.1%})')
        ax.set_ylabel(f'PC2 ({pca.explained_variance_ratio_[1]:.1%})')
        if output:
            fig.savefig(output, dpi=300, bbox_inches='tight')
        return fig

    def run_pipeline(self, path: str, design: str, contrast: tuple,
                     **kwargs) -> dict:
        """One-shot: load → QC → normalize → DE → enrichment → volcano."""
        adata = self.load_counts(path)
        adata = self.qc_filter(adata)
        adata = self.normalize(adata)
        de = self.differential_expression(adata, design, contrast)
        try:
            enr = self.enrichment(de)
        except Exception:
            enr = None
        volcano = self.visualize_volcano(de)
        return {'adata': adata, 'de_results': de, 'enrichment': enr,
                'volcano': volcano}
