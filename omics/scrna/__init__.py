"""scRNA-seq analysis — single source of truth for all scanpy-based operations."""

from omics.scrna.qc import run_qc
from omics.scrna.normalize import run_normalize
from omics.scrna.hvg import run_hvg
from omics.scrna.pca import run_pca
from omics.scrna.neighbors import run_neighbors
from omics.scrna.umap import run_umap
from omics.scrna.cluster import run_leiden
from omics.scrna.markers import run_markers, get_marker_table
from omics.scrna.pipeline import run_standard_pipeline
