"""Cell type annotation via marker-based matching, CellTypist, or SingleR."""

import logging
import anndata

logger = logging.getLogger(__name__)

# Common cell type marker genes (curated, expandable)
CELL_TYPE_MARKERS: dict[str, list[str]] = {
    "T cell": ["CD3D", "CD3E", "CD3G"],
    "CD4+ T cell": ["CD4", "IL7R"],
    "CD8+ T cell": ["CD8A", "CD8B", "NKG7"],
    "NK cell": ["NKG7", "GNLY", "KLRF1", "KLRD1", "NCR1"],
    "B cell": ["CD19", "MS4A1", "CD79A", "CD79B", "PAX5"],
    "Plasma cell": ["MZB1", "SDC1", "JCHAIN", "XBP1"],
    "Monocyte": ["CD14", "FCGR3A", "CSF1R", "LYZ", "S100A8", "S100A9"],
    "Macrophage": ["CD68", "ITGAM", "CD163", "MRC1"],
    "Dendritic cell": ["FCER1A", "CLEC10A", "CD1C", "XCR1"],
    "Neutrophil": ["FCGR3B", "CXCR2", "CSF3R", "ELANE"],
    "Mast cell": ["KIT", "CPA3", "TPSAB1"],
    "Erythrocyte": ["HBA1", "HBB", "HBD"],
    "Platelet": ["PPBP", "PF4", "ITGA2B"],
    "Endothelial": ["PECAM1", "CDH5", "VWF", "CLDN5"],
    "Fibroblast": ["COL1A1", "COL1A2", "DCN", "LUM", "FAP"],
    "Epithelial": ["EPCAM", "KRT8", "KRT18", "KRT19"],
}


def run_marker_annotation(adata: anndata.AnnData, cluster_key: str = "leiden",
                          markers: dict | None = None,
                          key_added: str = "cell_type") -> anndata.AnnData:
    """Annotate clusters by matching top marker genes against known cell type signatures.

    Args:
        adata: AnnData with cluster labels and rank_genes_groups in .uns.
        cluster_key: Column in .obs with cluster assignments.
        markers: Dict of cell_type -> [gene list]. Uses built-in markers if None.
        key_added: Key in .obs for the annotation result.

    Returns:
        AnnData with cell type labels in .obs[key_added].
    """
    if markers is None:
        markers = CELL_TYPE_MARKERS

    from omics.scrna.markers import get_marker_table
    from omics.knowledge.engine import KnowledgeEngine

    marker_table = get_marker_table(adata)
    cluster_markers: dict[str, list[str]] = {}
    for group in marker_table["group"].unique():
        top_genes = marker_table[marker_table["group"] == group].head(50)["gene"].tolist()
        cluster_markers[str(group)] = top_genes

    engine = KnowledgeEngine()
    matches = engine.match_cell_types(cluster_markers, top_n_per_cluster=50)

    # Assign best-matching cell type per cluster
    cluster_to_ct: dict[str, str] = {}
    for match in matches:
        cluster = match.query_cluster
        ct = match.matched_cell_type
        if cluster not in cluster_to_ct:
            cluster_to_ct[cluster] = ct

    adata.obs[key_added] = adata.obs[cluster_key].astype(str).map(
        lambda c: cluster_to_ct.get(c, "Unknown")
    ).astype("category")
    return adata


def run_celltypist(adata: anndata.AnnData, model: str = "Immune_All_Low.pkl",
                   majority_voting: bool = True, key_added: str = "cell_type_celltypist") -> anndata.AnnData:
    """CellTypist automatic cell type annotation.

    Requires: pip install celltypist

    Args:
        adata: AnnData with raw counts in .X or .layers['raw'].
        model: CellTypist model name or path.
        majority_voting: Aggregate predictions across cells within each cluster.
        key_added: Key in .obs for the result.

    Returns:
        AnnData with predicted labels in .obs[key_added].
    """
    try:
        import celltypist
    except ImportError:
        raise ImportError("celltypist not installed. Run: pip install celltypist")

    celltypist.models.download_models(force_update=False, model=model)
    predictions = celltypist.annotate(adata, model=model, majority_voting=majority_voting)
    adata.obs[key_added] = predictions.predicted_labels["majority_voting"].values
    return adata


def run_singler(adata: anndata.AnnData, reference: str = "HumanPrimaryCellAtlasData",
                key_added: str = "cell_type_singler") -> anndata.AnnData:
    """SingleR annotation via rpy2 bridge to R.

    Requires: pip install rpy2 + R with SingleR and celldex packages.

    Args:
        adata: Log-normalized AnnData.
        reference: celldex reference dataset name.
        key_added: Key in .obs for the result.

    Returns:
        AnnData with predicted labels in .obs[key_added].
    """
    try:
        import rpy2.robjects as ro
        from rpy2.robjects import pandas2ri
        pandas2ri.activate()
    except ImportError:
        raise ImportError("rpy2 not installed. Run: pip install rpy2")

    ro.r(f"""
        library(SingleR)
        library(celldex)
        ref <- {reference}()
    """)

    expr = adata.X.toarray() if hasattr(adata.X, "toarray") else adata.X
    expr_r = pandas2ri.py2rpy(expr.T)

    ro.globalenv["expr_matrix"] = expr_r
    ro.r("predictions <- SingleR(test=expr_matrix, ref=ref, labels=ref$label.main)")
    predictions = ro.r("predictions$labels")

    adata.obs[key_added] = list(predictions)
    return adata
