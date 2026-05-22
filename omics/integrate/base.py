"""Extension point for multi-omics integration."""

from abc import ABC, abstractmethod
from typing import Any


class AbstractIntegration(ABC):
    """Interface for multi-omics integration backends.

    Implementations would include MOFA, Mowgli, WNN, etc.
    """

    modality: str = "integration"

    @abstractmethod
    def integrate(self, modalities: list[Any], **kwargs) -> Any:
        """Integrate multiple modalities into a joint representation.

        Args:
            modalities: List of AnnData objects from different modalities.
            **kwargs: Method-specific parameters (n_factors, etc.).

        Returns:
            MuData or similar multi-modal container.
        """
        ...

    def factor_analysis(self, data: Any, **kwargs) -> Any:
        """Optional: factor decomposition and interpretation."""
        raise NotImplementedError("Factor analysis not yet implemented.")

    def cross_modality_prediction(self, data: Any, **kwargs) -> Any:
        """Optional: predict one modality from another."""
        raise NotImplementedError("Cross-modality prediction not yet implemented.")
