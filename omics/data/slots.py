"""Standardized AnnData slot definitions per modality."""

from dataclasses import dataclass, field


@dataclass
class ModalitySchema:
    modality: str
    X_dtype: str = "float32"
    obs_columns: list[str] = field(default_factory=list)
    var_columns: list[str] = field(default_factory=list)
    obsm_keys: list[str] = field(default_factory=list)
    obsp_keys: list[str] = field(default_factory=list)
    uns_keys: list[str] = field(default_factory=list)
    layers: list[str] = field(default_factory=list)


SCRNA_SCHEMA = ModalitySchema(
    modality="scrna",
    obs_columns=["n_genes", "n_counts"],
    var_columns=["mt", "ribo", "highly_variable"],
    obsm_keys=["X_pca", "X_umap"],
    obsp_keys=["connectivities", "distances"],
    uns_keys=["rank_genes_groups"],
    layers=["raw", "log1p"],
)

SPATIAL_SCHEMA = ModalitySchema(
    modality="spatial",
    obs_columns=["n_genes", "n_counts"],
    obsm_keys=["spatial", "X_pca", "X_umap"],
    obsp_keys=["spatial_connectivities", "spatial_distances"],
    uns_keys=["spatial"],
)

AMPLICON_SCHEMA = ModalitySchema(
    modality="amplicon",
    X_dtype="int64",
    obs_columns=["sample_id"],
    var_columns=["taxonomy", "sequence"],
    uns_keys=["taxonomy_table", "phylogenetic_tree"],
)

METAGENOMICS_SCHEMA = ModalitySchema(
    modality="metagenomics",
    X_dtype="float32",
    obs_columns=["sample_id"],
    var_columns=["taxon_id", "taxon_rank", "domain", "phylum", "genus", "species"],
    uns_keys=["kraken2_report"],
)

ALL_SCHEMAS: dict[str, ModalitySchema] = {
    "scrna": SCRNA_SCHEMA,
    "spatial": SPATIAL_SCHEMA,
    "amplicon": AMPLICON_SCHEMA,
    "metagenomics": METAGENOMICS_SCHEMA,
}


def get_schema(modality: str) -> ModalitySchema:
    if modality not in ALL_SCHEMAS:
        raise ValueError(f"Unknown modality: {modality}. Available: {list(ALL_SCHEMAS)}")
    return ALL_SCHEMAS[modality]
