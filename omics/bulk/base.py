"""Extension point for bulk RNA-seq analysis."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import anndata
    import pandas as pd


class AbstractBulkRNAAnalysis(ABC):
    """Interface for bulk RNA-seq analysis backends (DESeq2, edgeR, GSEApy)."""

    modality: str = "bulk_rna"

    @abstractmethod
    def load_counts(self, path: str, **kwargs) -> anndata.AnnData:
        """Load count matrix from file."""
        ...

    @abstractmethod
    def qc_filter(self, adata: anndata.AnnData, **kwargs) -> anndata.AnnData:
        """Filter low-count genes and samples."""
        ...

    @abstractmethod
    def normalize(self, adata: anndata.AnnData, method: str = "deseq2", **kwargs) -> anndata.AnnData:
        """Normalize counts (DESeq2 median-of-ratios or edgeR TMM)."""
        ...

    @abstractmethod
    def differential_expression(
        self, adata: anndata.AnnData, design: str, contrast: tuple, **kwargs
    ) -> pd.DataFrame:
        """Run differential expression analysis."""
        ...

    def enrichment(
        self, de_results: pd.DataFrame, gene_sets: str = "GO", **kwargs
    ) -> pd.DataFrame:
        """Optional: gene-set enrichment analysis (GSEApy)."""
        raise NotImplementedError("Enrichment analysis not yet implemented.")

    def visualize_volcano(self, de_results: pd.DataFrame, **kwargs) -> Any:
        """Optional: volcano plot of DE results."""
        raise NotImplementedError("Volcano plot not yet implemented.")

    def visualize_heatmap(
        self, adata: anndata.AnnData, gene_list: list[str], **kwargs
    ) -> Any:
        """Optional: heatmap of selected genes."""
        raise NotImplementedError("Heatmap visualization not yet implemented.")

    def visualize_pca(self, adata: anndata.AnnData, **kwargs) -> Any:
        """Optional: PCA plot of samples."""
        raise NotImplementedError("PCA visualization not yet implemented.")

    def run_pipeline(
        self, path: str, design: str, contrast: tuple, **kwargs
    ) -> dict:
        """Optional: end-to-end pipeline from counts to report."""
        raise NotImplementedError("Pipeline not yet implemented.")
