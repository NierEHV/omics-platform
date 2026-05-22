"""Enums and constants for the omics platform."""

from enum import Enum
from pathlib import Path


class Modality(str, Enum):
    SCRNA = "scrna"
    SPATIAL = "spatial"
    AMPLICON = "amplicon"
    METAGENOMICS = "metagenomics"


class FigureFormat(str, Enum):
    PDF = "pdf"
    SVG = "svg"
    PNG = "png"
    TIFF = "tiff"
    EPS = "eps"


class JournalStyle(str, Enum):
    NATURE = "nature"
    CELL = "cell"
    SCIENCE = "science"


class StageStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class AnalysisIntent(str, Enum):
    DIFFERENTIAL = "differential"
    CLUSTERING = "clustering"
    TRAJECTORY = "trajectory"
    INTEGRATION = "integration"
    VISUALIZATION = "visualization"
    ANNOTATION = "annotation"
    QUALITY_CONTROL = "quality_control"
    CELL_COMMUNICATION = "cell_communication"
    UNKNOWN = "unknown"


# Standard AnnData slot names
class ObsSlot:
    SAMPLE_ID = "sample_id"
    CONDITION = "condition"
    N_GENES = "n_genes"
    N_COUNTS = "n_counts"
    CLUSTER = "cluster"
    CELL_TYPE = "cell_type"


class ObspSlot:
    SPATIAL_CONNECTIVITIES = "spatial_connectivities"
    SPATIAL_DISTANCES = "spatial_distances"
    NEIGHBORS_CONNECTIVITIES = "connectivities"
    NEIGHBORS_DISTANCES = "distances"


class UnsSlot:
    PROVENANCE = "provenance"
    PIPELINE_PARAMS = "pipeline_params"
    SPATIAL_IMAGE = "spatial"


# Project structure
PROJECT_SUBDIRS = ["raw", "processed", "output/figures", "output/reports", "output/models", "notebooks"]

# Cache location
DEFAULT_CACHE_DIR = Path.home() / ".omics" / "cache"

# Input formats per modality
SCRNA_INPUT_FORMATS = [".h5ad", ".h5", ".mtx", ".loom", ".csv", ".txt"]
SPATIAL_INPUT_FORMATS = [".h5ad", ".h5", ".mtx"]
AMPLICON_INPUT_FORMATS = [".fastq", ".fastq.gz", ".fq", ".fq.gz", ".qza", ".biom", ".tsv"]
METAGENOMICS_INPUT_FORMATS = [".fastq", ".fastq.gz", ".fq", ".fq.gz", ".tsv", ".txt"]
