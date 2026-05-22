"""Extension point for shotgun metagenomics analysis."""

from abc import ABC, abstractmethod
from typing import Any


class AbstractMetagenomicsAnalysis(ABC):
    """Interface for metagenomics analysis backends."""

    modality: str = "metagenomics"

    @abstractmethod
    def classify(self, data: Any, **kwargs) -> Any:
        """Taxonomic classification (Kraken2, MetaPhlAn, etc.)."""
        ...

    def functional_profile(self, data: Any, **kwargs) -> Any:
        """Optional: functional profiling (HUMAnN3, eggNOG, etc.)."""
        raise NotImplementedError("Functional profiling not yet implemented.")

    def assemble(self, data: Any, **kwargs) -> Any:
        """Optional: metagenome assembly (MEGAHIT, metaSPAdes, etc.)."""
        raise NotImplementedError("Assembly not yet implemented.")

    def bin(self, data: Any, **kwargs) -> Any:
        """Optional: metagenomic binning (MetaBAT2, MaxBin2, etc.)."""
        raise NotImplementedError("Binning not yet implemented.")
