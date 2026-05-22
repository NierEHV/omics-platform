"""Quality control: filter cells and genes, compute QC metrics."""

import scanpy as sc
import anndata


def run_qc(adata: anndata.AnnData, min_genes: int = 200, min_cells: int = 3,
           max_pct_mt: float = 20.0, filter_doublets: bool = False) -> anndata.AnnData:
    """Filter low-quality cells and genes. Computes QC metrics in-place.

    Args:
        adata: AnnData object (raw counts expected in .X).
        min_genes: Minimum genes per cell.
        min_cells: Minimum cells per gene.
        max_pct_mt: Maximum percentage mitochondrial reads.
        filter_doublets: If True, run Scrublet doublet detection.

    Returns:
        Filtered AnnData (not a copy — operates on the input).
    """
    adata.var["mt"] = adata.var_names.str.startswith(("MT-", "mt-", "Mt-"))
    adata.var["ribo"] = adata.var_names.str.startswith(("RPS", "RPL", "rps", "rpl"))

    sc.pp.calculate_qc_metrics(adata, qc_vars=["mt", "ribo"], percent_top=None, log1p=False, inplace=True)

    sc.pp.filter_cells(adata, min_genes=min_genes)
    sc.pp.filter_genes(adata, min_cells=min_cells)
    adata = adata[adata.obs.pct_counts_mt < max_pct_mt].copy()

    if filter_doublets:
        import scrublet as scr
        scrub = scr.Scrublet(adata.X.toarray() if hasattr(adata.X, "toarray") else adata.X)
        doublet_scores, predicted_doublets = scrub.scrub_doublets()
        adata.obs["doublet_score"] = doublet_scores
        adata.obs["predicted_doublet"] = predicted_doublets
        adata = adata[~adata.obs["predicted_doublet"]].copy()

    return adata
