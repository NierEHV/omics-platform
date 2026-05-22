"""Extension point for spatial transcriptomics analysis.

To add spatial transcriptomics support:
    from omics.spatial.base import AbstractSpatialAnalysis

    class MySpatialBackend(AbstractSpatialAnalysis):
        def preprocess(self, adata, **kwargs):
            import scanpy as sc
            import squidpy as sq
            ...
            return adata

        def cluster(self, adata, **kwargs):
            ...  # spatial-aware clustering
            return adata

    sdk.register_spatial_backend(MySpatialBackend())
"""

from abc import ABC, abstractmethod
from typing import Any


class AbstractSpatialAnalysis(ABC):
    """Interface for spatial transcriptomics backends.

    Implement this class to add spatial analysis support.
    Required methods are abstract; optional methods raise
    NotImplementedError with helpful messages.
    """

    modality: str = "spatial"

    @abstractmethod
    def preprocess(self, adata: Any, **kwargs) -> Any:
        """Filter spots, normalize, select HVGs.

        Args:
            adata: AnnData from Visium/MERFISH/etc.
            **kwargs: Passed to scanpy/squidpy functions.

        Returns:
            Preprocessed AnnData.
        """
        ...

    @abstractmethod
    def cluster(self, adata: Any, **kwargs) -> Any:
        """Spatial-aware clustering.

        Args:
            adata: Preprocessed AnnData.
            **kwargs: Resolution, n_neighbors, etc.

        Returns:
            AnnData with cluster labels and spatial embeddings.
        """
        ...

    def deconvolve(self, adata: Any, **kwargs) -> Any:
        """Optional: cell-type deconvolution from spatial spots."""
        raise NotImplementedError(
            "Spatial deconvolution is not yet implemented. "
            "Install planned in a future release."
        )

    def niche_analysis(self, adata: Any, **kwargs) -> Any:
        """Optional: spatial niche/cellular neighborhood analysis."""
        raise NotImplementedError(
            "Spatial niche analysis is not yet implemented."
        )

    def lr_spatial(self, adata: Any, **kwargs) -> Any:
        """Optional: spatially-aware ligand-receptor analysis."""
        raise NotImplementedError(
            "Spatial ligand-receptor analysis is not yet implemented."
        )
