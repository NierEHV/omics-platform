"""Format converters: AnnData <-> Seurat, CSV, 10x formats."""

from pathlib import Path
import pandas as pd
import anndata as ad


class Converters:
    """Static methods for converting between analysis formats."""

    @staticmethod
    def anndata_to_seurat_rds(adata: ad.AnnData, output_path: Path) -> None:
        """Convert AnnData to Seurat RDS via rpy2."""
        try:
            import rpy2.robjects as ro
            from rpy2.robjects import pandas2ri, numpy2ri
            pandas2ri.activate()
            numpy2ri.activate()
        except ImportError:
            raise ImportError("rpy2 not installed. Run: pip install rpy2")

        ro.r("library(Seurat)")

        expr = adata.X.toarray() if hasattr(adata.X, "toarray") else adata.X
        expr_r = numpy2ri.py2rpy(expr.T)
        ro.globalenv["counts"] = expr_r

        ro.r(f"""
            rownames(counts) <- c({','.join(f"'{g}'" for g in adata.var_names[:100])})
            colnames(counts) <- c({','.join(f"'{c}'" for c in adata.obs_names[:100])})
            seurat_obj <- CreateSeuratObject(counts=counts)
            saveRDS(seurat_obj, file='{output_path}')
        """)

    @staticmethod
    def seurat_rds_to_anndata(rds_path: Path) -> ad.AnnData:
        """Load a Seurat RDS file as AnnData via rpy2."""
        try:
            import rpy2.robjects as ro
            from rpy2.robjects import pandas2ri, numpy2ri
            pandas2ri.activate()
            numpy2ri.activate()
        except ImportError:
            raise ImportError("rpy2 not installed. Run: pip install rpy2")

        ro.r("library(Seurat)")
        ro.r(f"seurat_obj <- readRDS('{rds_path}')")
        counts = ro.r("GetAssayData(seurat_obj, slot='counts')")
        meta = ro.r("seurat_obj@meta.data")

        import numpy as np
        adata = ad.AnnData(np.array(counts).T.astype(np.float32))
        adata.var_names = list(counts.rownames)
        adata.obs_names = list(counts.colnames)
        if meta is not ro.NULL:
            adata.obs = pandas2ri.rpy2py(meta)
        return adata

    @staticmethod
    def anndata_to_csv(adata: ad.AnnData, output_dir: Path) -> None:
        """Export AnnData as CSV files (counts, obs, var)."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        expr = adata.X.toarray() if hasattr(adata.X, "toarray") else adata.X
        pd.DataFrame(expr.T, index=adata.var_names, columns=adata.obs_names).to_csv(
            output_dir / "counts.csv")
        adata.obs.to_csv(output_dir / "obs.csv")
        adata.var.to_csv(output_dir / "var.csv")
