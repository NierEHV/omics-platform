"""Trajectory inference: pseudotime, PAGA, RNA velocity, Palantir."""

import logging
import anndata
import scanpy as sc

logger = logging.getLogger(__name__)


def run_dpt(adata: anndata.AnnData, root_cell: int | None = None,
            n_branchings: int = 0, n_dcs: int = 15) -> anndata.AnnData:
    """Diffusion pseudotime analysis.

    Requires run_neighbors() first.

    Args:
        adata: AnnData with neighbor graph.
        root_cell: Index of root cell. Auto-detected if None (uses first cell).
        n_branchings: Number of branchings to detect.
        n_dcs: Number of diffusion components.

    Returns:
        AnnData with .obs['dpt_pseudotime'].
    """
    sc.tl.diffmap(adata, n_comps=n_dcs)
    if root_cell is None:
        root_cell = 0
    adata.uns["iroot"] = root_cell
    sc.tl.dpt(adata, n_branchings=n_branchings)
    return adata


def run_paga(adata: anndata.AnnData, groups: str = "leiden",
             threshold: float = 0.03) -> anndata.AnnData:
    """PAGA graph abstraction for trajectory inference.

    Args:
        adata: AnnData with neighbor graph and clustering.
        groups: Clustering column in .obs.
        threshold: Edge threshold for the PAGA graph.

    Returns:
        AnnData with PAGA graph in .uns['paga'].
    """
    sc.tl.paga(adata, groups=groups)
    return adata


def run_velocity(adata: anndata.AnnData, mode: str = "dynamical",
                 min_shared_counts: int = 20, n_top_genes: int = 2000) -> dict:
    """RNA velocity analysis via scVelo.

    Requires: pip install scvelo
    Also requires unspliced/spliced counts in separate layers.

    Args:
        adata: AnnData with 'spliced' and 'unspliced' layers.
        mode: 'deterministic', 'stochastic', or 'dynamical'.
        min_shared_counts: Minimum shared counts for gene filtering.
        n_top_genes: Number of top genes for velocity.

    Returns:
        Dictionary with 'velocity' array and 'velocity_graph'.
    """
    try:
        import scvelo as scv
    except ImportError:
        raise ImportError("scvelo not installed. Run: pip install scvelo")

    if "spliced" not in adata.layers or "unspliced" not in adata.layers:
        raise ValueError("AnnData must have 'spliced' and 'unspliced' layers for RNA velocity")

    scv.pp.filter_and_normalize(adata, min_shared_counts=min_shared_counts,
                                 n_top_genes=n_top_genes)
    scv.pp.moments(adata, n_pcs=30, n_neighbors=30)
    if mode == "dynamical":
        scv.tl.recover_dynamics(adata)
    scv.tl.velocity(adata, mode=mode)
    scv.tl.velocity_graph(adata)

    return {"velocity": adata.layers.get("velocity"),
            "velocity_graph": adata.uns.get("velocity_graph")}


def run_palantir(adata: anndata.AnnData, root_cell: str | None = None,
                 n_waypoints: int = 1200) -> anndata.AnnData:
    """Palantir trajectory inference.

    Requires: pip install palantir

    Args:
        adata: Normalized, log-transformed AnnData with X_pca.
        root_cell: Name of root cell in .obs_names. Auto-detected if None.
        n_waypoints: Number of waypoints for Palantir.

    Returns:
        AnnData with .obs['palantir_pseudotime'].
    """
    try:
        import palantir
    except ImportError:
        raise ImportError("palantir not installed. Run: pip install palantir")

    if root_cell is None:
        root_cell = adata.obs_names[0]

    pr_res = palantir.run_palantir(
        adata.obsm["X_pca"],
        pd.DataFrame(adata.obsm["X_pca"], index=adata.obs_names),
        root_cell=root_cell,
        num_waypoints=n_waypoints,
    )

    adata.obs["palantir_pseudotime"] = pr_res.pseudotime
    adata.obs["palantir_entropy"] = pr_res.entropy
    return adata
