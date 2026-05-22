"""Cell-cell communication: ligand-receptor analysis."""

import logging
import anndata

logger = logging.getLogger(__name__)

# Curated immune-focused ligand-receptor pairs
CURATED_LR_PAIRS: list[tuple[str, str, str]] = [
    ("L", "CD4", "CD4", "IL16", "IL16"),
    ("L", "CD40LG", "CD40LG", "CD40", "TNFRSF5"),
    ("L", "CD28", "CD28", "CD80", "CD80"),
    ("L", "CD28", "CD28", "CD86", "CD86"),
    ("L", "CTLA4", "CTLA4", "CD80", "CD80"),
    ("L", "PDCD1", "PD1", "CD274", "PD-L1"),
    ("L", "IFNG", "IFNG", "IFNGR1", "IFNGR1"),
    ("L", "TNF", "TNF", "TNFRSF1A", "TNFRSF1A"),
    ("L", "IL2", "IL2", "IL2RA", "IL2RA"),
    ("L", "IL10", "IL10", "IL10RA", "IL10RA"),
    ("L", "CCL5", "CCL5", "CCR5", "CCR5"),
    ("L", "CXCL10", "CXCL10", "CXCR3", "CXCR3"),
    ("L", "CXCL12", "CXCL12", "CXCR4", "CXCR4"),
    ("L", "CCL2", "CCL2", "CCR2", "CCR2"),
    ("R", "CSF1", "CSF1", "CSF1R", "CSF1R"),
    ("R", "IL1B", "IL1B", "IL1R1", "IL1R1"),
    ("R", "TGFB1", "TGFB1", "TGFBR2", "TGFBR2"),
    ("S", "NOTCH1", "NOTCH1", "DLL4", "DLL4"),
    ("S", "JAG1", "JAG1", "NOTCH2", "NOTCH2"),
    ("C", "HLA-A", "HLA-A", "CD8A", "CD8A"),
    ("C", "HLA-B", "HLA-B", "KIR3DL1", "KIR3DL1"),
]


def run_lr_analysis(adata: anndata.AnnData, cluster_key: str = "leiden",
                    lr_pairs: list | None = None,
                    key_added: str = "lr_interactions") -> anndata.AnnData:
    """Ligand-receptor interaction analysis between clusters.

    Computes mean expression of each ligand/receptor per cluster,
    then scores interactions where both partners are expressed.

    Args:
        adata: Log-normalized AnnData with cluster labels.
        cluster_key: Column in .obs with cluster assignments.
        lr_pairs: List of (pathway, ligand, lig_gene, receptor, rec_gene) tuples.
                  Uses built-in curated pairs if None.
        key_added: Key in .uns for the interaction results.

    Returns:
        AnnData with interaction scores in .uns[key_added].
    """
    import numpy as np

    if lr_pairs is None:
        lr_pairs = CURATED_LR_PAIRS

    clusters = sorted(adata.obs[cluster_key].unique().astype(str))
    n_clusters = len(clusters)
    expr = adata.X.toarray() if hasattr(adata.X, "toarray") else adata.X

    interactions = []
    for pathway, lig_name, lig_gene, rec_name, rec_gene in lr_pairs:
        lig_idx = _find_gene_index(adata, lig_gene)
        rec_idx = _find_gene_index(adata, rec_gene)
        if lig_idx is None or rec_idx is None:
            continue

        lig_expr = expr[:, lig_idx]
        rec_expr = expr[:, rec_idx]

        for i, sender in enumerate(clusters):
            sender_mask = adata.obs[cluster_key].astype(str) == sender
            lig_mean = lig_expr[sender_mask].mean() if sender_mask.any() else 0

            for j, receiver in enumerate(clusters):
                rec_mask = adata.obs[cluster_key].astype(str) == receiver
                rec_mean = rec_expr[rec_mask].mean() if rec_mask.any() else 0

                score = lig_mean * rec_mean
                if score > 0:
                    interactions.append({
                        "pathway": pathway,
                        "ligand": lig_name,
                        "ligand_gene": lig_gene,
                        "receptor": rec_name,
                        "receptor_gene": rec_gene,
                        "sender": sender,
                        "receiver": receiver,
                        "ligand_mean": float(lig_mean),
                        "receptor_mean": float(rec_mean),
                        "score": float(score),
                    })

    adata.uns[key_added] = sorted(interactions, key=lambda x: x["score"], reverse=True)
    logger.info(f"LR analysis: {len(interactions)} significant interactions found")
    return adata


def run_cellphonedb(adata: anndata.AnnData, cell_type_key: str = "cell_type",
                    pvalue_threshold: float = 0.05) -> anndata.AnnData:
    """CellPhoneDB interaction analysis (requires CellPhoneDB CLI).

    This writes temporary files and runs the cellphonedb command-line tool.
    Requires: pip install cellphonedb

    Args:
        adata: AnnData with cell type labels.
        cell_type_key: Column in .obs with cell type labels.
        pvalue_threshold: P-value cutoff for significant interactions.

    Returns:
        AnnData with results referenced in .uns['cellphonedb_results'].
    """
    import subprocess
    import tempfile
    from pathlib import Path

    try:
        import cellphonedb
    except ImportError:
        raise ImportError("cellphonedb not installed. Run: pip install cellphonedb")

    tmpdir = Path(tempfile.mkdtemp())
    counts_path = tmpdir / "counts.txt"
    meta_path = tmpdir / "meta.txt"
    output_dir = tmpdir / "output"

    expr = adata.X.toarray() if hasattr(adata.X, "toarray") else adata.X
    import pandas as pd
    counts_df = pd.DataFrame(expr.T, index=adata.var_names, columns=adata.obs_names)
    counts_df.to_csv(counts_path, sep="\t")

    meta_df = adata.obs[[cell_type_key]].copy()
    meta_df.insert(0, "Cell", meta_df.index)
    meta_df.to_csv(meta_path, sep="\t", index=False)

    subprocess.run([
        "cellphonedb", "method", "statistical_analysis",
        str(meta_path), str(counts_path),
        "--output-path", str(output_dir),
        "--threshold", str(pvalue_threshold),
    ], check=True)

    adata.uns["cellphonedb_results"] = str(output_dir)
    return adata


def _find_gene_index(adata: anndata.AnnData, gene: str) -> int | None:
    """Find the index of a gene in adata.var_names. Case-insensitive."""
    if gene in adata.var_names:
        return list(adata.var_names).index(gene)
    for i, name in enumerate(adata.var_names):
        if name.upper() == gene.upper():
            return i
    return None
