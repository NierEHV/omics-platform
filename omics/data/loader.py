"""Build AnnData objects from various file formats."""

from __future__ import annotations

import logging
from pathlib import Path

import anndata as ad
import pandas as pd
import numpy as np

from omics.utils.exceptions import DataImportError

logger = logging.getLogger(__name__)


class SCRNABuilder:
    """Construct scRNA-seq AnnData from various input formats."""

    @staticmethod
    def from_h5ad(path: Path) -> ad.AnnData:
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        adata = ad.read_h5ad(path)
        adata.var_names_make_unique()
        logger.info(f"Loaded h5ad: {adata.n_obs} cells x {adata.n_vars} genes")
        return adata

    @staticmethod
    def from_10x_mtx(path: Path, var_names: str = "gene_symbols") -> ad.AnnData:
        path = Path(path)
        if not path.is_dir():
            raise DataImportError(f"10x directory not found: {path}")
        adata = ad.read_10x_mtx(path, var_names=var_names, cache=False)
        adata.var_names_make_unique()
        logger.info(f"Loaded 10x mtx: {adata.n_obs} cells x {adata.n_vars} genes")
        return adata

    @staticmethod
    def from_10x_h5(path: Path) -> ad.AnnData:
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        adata = ad.read_10x_h5(path)
        adata.var_names_make_unique()
        logger.info(f"Loaded 10x h5: {adata.n_obs} cells x {adata.n_vars} genes")
        return adata

    @staticmethod
    def from_dataframe(df: pd.DataFrame, transpose: bool = True) -> ad.AnnData:
        if transpose and df.shape[0] > df.shape[1]:
            df = df.T
        adata = ad.AnnData(df.values.astype(np.float32))
        adata.obs_names = df.index.astype(str).tolist()
        adata.var_names = df.columns.astype(str).tolist()
        return adata


class SpatialBuilder:
    """Construct spatial transcriptomics AnnData."""

    @staticmethod
    def from_h5ad(path: Path) -> ad.AnnData:
        return SCRNABuilder.from_h5ad(path)

    @staticmethod
    def from_visium(path: Path) -> ad.AnnData:
        try:
            import squidpy as sq
        except ImportError:
            raise ImportError("squidpy not installed. Run: pip install squidpy")
        path = Path(path)
        if not path.is_dir():
            raise DataImportError(f"Visium directory not found: {path}")
        adata = sq.read.visium(path)
        adata.var_names_make_unique()
        return adata


class AmpliconBuilder:
    """Construct 16S rRNA amplicon AnnData."""

    @staticmethod
    def from_feature_table(feature_table: pd.DataFrame, taxonomy: pd.DataFrame | None = None,
                           metadata: pd.DataFrame | None = None) -> ad.AnnData:
        if feature_table.shape[0] > feature_table.shape[1]:
            feature_table = feature_table.T
        adata = ad.AnnData(feature_table.values.astype(np.float32))
        adata.obs_names = feature_table.index.astype(str).tolist()
        adata.var_names = feature_table.columns.astype(str).tolist()
        if taxonomy is not None:
            for col in taxonomy.columns:
                adata.var[col] = taxonomy[col].values
        if metadata is not None:
            for col in metadata.columns:
                adata.obs[col] = metadata[col].values
        return adata

    @staticmethod
    def from_tsv(path: Path) -> ad.AnnData:
        df = pd.read_csv(path, sep="\t", index_col=0)
        return AmpliconBuilder.from_feature_table(df)

    @staticmethod
    def from_biom(path: Path, metadata_path: Path | None = None) -> ad.AnnData:
        try:
            import biom
        except ImportError:
            raise ImportError("biom-format not installed. Run: pip install biom-format")
        table = biom.load_table(str(path))
        df = pd.DataFrame(table.matrix_data.toarray(),
                          index=table.ids(axis="sample"),
                          columns=table.ids(axis="observation"))
        meta = pd.read_csv(metadata_path, sep="\t", index_col=0) if metadata_path else None
        return AmpliconBuilder.from_feature_table(df, metadata=meta)


class MetagenomicsBuilder:
    """Construct metagenomics AnnData from Kraken2/Bracken/HUMAnN3 outputs."""

    @staticmethod
    def from_kraken2_report(reports: dict[str, Path]) -> ad.AnnData:
        samples = {}
        all_taxa = set()
        for sample_name, report_path in reports.items():
            df = pd.read_csv(report_path, sep="\t", header=None,
                            names=["pct", "count_clade", "count_direct", "rank", "taxid", "name"])
            df = df[df["rank"] == "S"].copy()
            df.set_index("name", inplace=True)
            samples[sample_name] = df["count_direct"]
            all_taxa.update(df.index)

        all_taxa = sorted(all_taxa)
        mat = np.zeros((len(samples), len(all_taxa)), dtype=np.float32)
        for i, (name, counts) in enumerate(samples.items()):
            for j, taxon in enumerate(all_taxa):
                mat[i, j] = counts.get(taxon, 0)

        adata = ad.AnnData(mat)
        adata.obs_names = list(samples.keys())
        adata.var_names = all_taxa
        return adata
