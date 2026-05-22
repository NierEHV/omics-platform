"""Marker gene detection and differential expression."""

import scanpy as sc
import pandas as pd
import anndata


def run_markers(adata: anndata.AnnData, groupby: str = "leiden", method: str = "wilcoxon",
                n_genes: int = 100, layer: str | None = None) -> anndata.AnnData:
    """Find marker genes per cluster using rank_genes_groups.

    Args:
        adata: AnnData with cluster labels in .obs[groupby].
        groupby: Column in .obs to group by.
        method: Statistical test ('wilcoxon', 't-test', 'logreg', 't-test_overestim_var').
        n_genes: Number of top marker genes per group.
        layer: Layer to use for expression values (None = .X).

    Returns:
        AnnData with results in .uns['rank_genes_groups'].
    """
    sc.tl.rank_genes_groups(adata, groupby=groupby, method=method, n_genes=n_genes, layer=layer)
    return adata


def get_marker_table(adata: anndata.AnnData, key: str = "rank_genes_groups") -> pd.DataFrame:
    """Extract marker gene results as a tidy DataFrame.

    Returns:
        DataFrame with columns: group, rank, gene, logfoldchange, pval, pval_adj.
    """
    result = adata.uns[key]
    groups = result["names"].dtype.names
    rows = []
    for group in groups:
        n_genes = len(result["names"][group])
        for i in range(n_genes):
            rows.append({
                "group": group,
                "rank": i + 1,
                "gene": result["names"][group][i],
                "logfoldchange": result["logfoldchanges"][group][i],
                "pval": result["pvals"][group][i],
                "pval_adj": result["pvals_adj"][group][i],
            })
    return pd.DataFrame(rows)


def run_degs(adata: anndata.AnnData, groupby: str, group1: str, group2: str,
             method: str = "wilcoxon") -> pd.DataFrame:
    """Differential expression between two specific groups.

    Args:
        adata: AnnData with group labels.
        groupby: Column in .obs.
        group1, group2: The two groups to compare.
        method: Statistical test.

    Returns:
        DataFrame with DEG results.
    """
    sc.tl.rank_genes_groups(adata, groupby=groupby, groups=[group1], reference=group2,
                            method=method)
    return get_marker_table(adata)
