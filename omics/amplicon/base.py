"""Extension point for 16S rRNA amplicon analysis."""

from abc import ABC, abstractmethod
from typing import Any


class AbstractAmpliconAnalysis(ABC):
    """Interface for 16S rRNA amplicon analysis backends."""

    modality: str = "amplicon"

    @abstractmethod
    def denoise(self, data: Any, **kwargs) -> Any:
        """DADA2/UNOISE denoising to generate ASVs."""
        ...

    @abstractmethod
    def classify(self, data: Any, **kwargs) -> Any:
        """Taxonomic classification (Naive Bayes, VSEARCH, etc.)."""
        ...

    def diversity(self, data: Any, **kwargs) -> Any:
        """Optional: alpha/beta diversity metrics."""
        raise NotImplementedError("Diversity analysis not yet implemented.")

    def differential_abundance(self, data: Any, **kwargs) -> Any:
        """Optional: differential abundance testing (ALDEx2, ANCOM, etc.)."""
        raise NotImplementedError("Differential abundance not yet implemented.")
