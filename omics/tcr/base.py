"""Abstract base class for TCR/BCR analysis."""
from abc import ABC, abstractmethod
from typing import Any


class AbstractTCRAnalysis(ABC):
    """Interface for TCR/BCR immune repertoire analysis backends."""

    modality: str = "tcr"

    @abstractmethod
    def load_vdj(self, path: str, **kwargs) -> Any:
        """Load TCR/BCR data: 10X VDJ, MiXCR txt, AIRR tsv, TRUST4 output."""
        ...

    @abstractmethod
    def define_clonotypes(self, adata: Any, **kwargs) -> Any:
        """Define clonotypes from CDR3 AA sequences."""
        ...

    @abstractmethod
    def clonal_expansion(self, adata: Any, **kwargs) -> dict:
        """Clonal expansion analysis: clone sizes, expansion groups."""
        ...

    @abstractmethod
    def vj_usage(self, adata: Any, groupby: str = None, **kwargs) -> Any:
        """V/D/J gene segment usage frequency analysis."""
        ...

    def cdr3_analysis(self, adata: Any, **kwargs) -> dict:
        """CDR3 length distribution and amino acid composition."""
        raise NotImplementedError("CDR3 analysis not yet implemented.")

    def repertoire_diversity(self, adata: Any, **kwargs) -> dict:
        """Immunarch diversity metrics: Shannon, Simpson, D50, Chao1."""
        raise NotImplementedError("Repertoire diversity not yet implemented.")

    def clonotype_overlap(self, adata_list: list, **kwargs) -> Any:
        """Multi-sample clonotype overlap: Morisita similarity, Jaccard."""
        raise NotImplementedError("Clonotype overlap not yet implemented.")

    def tcr_distance(self, adata: Any, **kwargs) -> Any:
        """TCR sequence biochemical distance matrix via TCRdist."""
        raise NotImplementedError("TCR distance not yet implemented.")

    def integrate_with_scrna(self, tcr_adata: Any, scrna_adata: Any, **kwargs) -> Any:
        """Merge TCR clonotype info into scRNA-seq AnnData.obs."""
        raise NotImplementedError("scRNA integration not yet implemented.")

    def immune_repertoire_profile(self, adata: Any, groupby: str, **kwargs) -> dict:
        """Composite immune repertoire profile report."""
        raise NotImplementedError("Immune repertoire profile not yet implemented.")
