"""Smart Multi-Panel Figure Composer — narrative-aware publication figures."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec

from omics.viz.style import BIOLOGICAL_PALETTE, StyleManager

logger = logging.getLogger(__name__)


@dataclass
class PanelSpec:
    title: str
    plot_func: str = ""
    plot_kwargs: dict = field(default_factory=dict)
    panel_label: str = ""
    caption: str = ""
    row_span: int = 1
    col_span: int = 1


@dataclass
class FigureStory:
    title: str
    description: str
    panels: list[PanelSpec] = field(default_factory=list)
    journal: str = "nature"
    template: str = ""


STORY_TEMPLATES: dict[str, FigureStory] = {
    "cell_type_atlas": FigureStory(
        title="Cell Type Atlas",
        description="Comprehensive cell type profiling with UMAP, marker expression, and composition.",
        template="cell_type_atlas",
        panels=[
            PanelSpec("UMAP by Cluster", "umap", {"color_by": "leiden"}, "A"),
            PanelSpec("Marker Gene Dotplot", "dotplot", {"groupby": "leiden", "n_genes": 10}, "B"),
            PanelSpec("Top Marker Heatmap", "heatmap", {"groupby": "leiden", "n_genes": 5}, "C"),
            PanelSpec("Cell Type Proportions", "bar", {"groupby": "leiden"}, "D"),
        ],
    ),
    "differential_response": FigureStory(
        title="Differential Expression Response",
        description="Comparison between conditions showing DEGs and pathways.",
        template="differential_response",
        panels=[
            PanelSpec("UMAP by Condition", "umap", {"color_by": "condition"}, "A"),
            PanelSpec("Volcano Plot", "volcano", {}, "B"),
            PanelSpec("Top DEG Heatmap", "heatmap", {"n_genes": 20}, "C"),
            PanelSpec("Pathway Enrichment", "pathway", {"top_n": 10}, "D"),
        ],
    ),
    "trajectory_analysis": FigureStory(
        title="Trajectory & Differentiation",
        description="Pseudotime trajectory with key gene expression trends.",
        template="trajectory_analysis",
        panels=[
            PanelSpec("UMAP by Pseudotime", "umap", {"color_by": "dpt_pseudotime"}, "A"),
            PanelSpec("UMAP by Cluster", "umap", {"color_by": "leiden"}, "B"),
            PanelSpec("Gene Expression Trends", "line", {"genes": []}, "C"),
            PanelSpec("Branch Point Heatmap", "heatmap", {}, "D"),
        ],
    ),
    "qc_report": FigureStory(
        title="Quality Control Report",
        description="Comprehensive quality control metrics.",
        template="qc_report",
        panels=[
            PanelSpec("nGenes vs nCounts", "scatter", {"x": "n_counts", "y": "n_genes"}, "A"),
            PanelSpec("QC Violin Plot", "violin", {"metrics": ["n_genes", "n_counts", "pct_mt"]}, "B"),
            PanelSpec("Filtering Summary", "bar", {}, "C"),
            PanelSpec("UMAP Post-QC", "umap", {"color_by": "leiden"}, "D"),
        ],
    ),
    "integration_overview": FigureStory(
        title="Multi-Omics Integration Overview",
        description="Overview of integrated multi-omics analysis.",
        template="integration_overview",
        panels=[
            PanelSpec("Factor Plot", "scatter", {"x": "Factor1", "y": "Factor2"}, "A"),
            PanelSpec("Variance Explained", "bar", {}, "B"),
            PanelSpec("Top Feature Weights", "heatmap", {}, "C"),
            PanelSpec("UMAP by Modality", "umap", {"color_by": "modality"}, "D"),
        ],
    ),
}


class SmartComposer:
    """Narrative-aware multi-panel figure composer."""

    _CELL_COLORS = BIOLOGICAL_PALETTE

    def __init__(self, journal: str = "nature"):
        self.journal = journal
        self._cell_type_colors: dict[str, str] = {}

    def compose(self, story: FigureStory, adata, output_path: Optional[Path] = None,
                dpi: int = 300) -> Figure:
        n_panels = len(story.panels)
        if n_panels == 0:
            raise ValueError("FigureStory has no panels.")

        n_rows, n_cols = self._auto_layout(n_panels)
        self._compute_color_map(adata)
        StyleManager.set_global(self.journal)

        fig_width = 7.0 if n_cols <= 2 else 10.5 if n_cols <= 3 else 14.0
        fig_height = 5.0 if n_rows <= 2 else 8.0 if n_rows <= 3 else 11.0

        fig = plt.figure(figsize=(fig_width, fig_height), dpi=dpi)
        gs = GridSpec(n_rows, n_cols, figure=fig, hspace=0.45, wspace=0.35)

        for i, panel in enumerate(story.panels):
            row = i // n_cols
            col = i % n_cols
            ax = fig.add_subplot(gs[row, col])
            self._render_panel(panel, ax, adata)
            letter = panel.panel_label or chr(65 + i)
            ax.text(-0.12, 1.05, letter, transform=ax.transAxes, fontsize=10,
                    fontweight="bold", va="center", ha="left")

        fig.suptitle(story.title, fontsize=10, fontweight="bold", y=0.98)

        if output_path:
            self._export(fig, Path(output_path), dpi)

        return fig

    def _render_panel(self, panel: PanelSpec, ax, adata) -> None:
        plot_type = panel.plot_func
        kwargs = panel.plot_kwargs or {}
        try:
            if plot_type == "umap":
                self._render_umap(ax, adata, kwargs)
            elif plot_type == "dotplot":
                self._render_dotplot(ax, adata, kwargs)
            elif plot_type == "heatmap":
                self._render_heatmap(ax, adata, kwargs)
            elif plot_type == "volcano":
                self._render_volcano(ax, adata, kwargs)
            elif plot_type == "bar":
                self._render_bar(ax, adata, kwargs)
            elif plot_type == "scatter":
                self._render_scatter(ax, adata, kwargs)
            elif plot_type == "violin":
                self._render_violin(ax, adata, kwargs)
            elif plot_type == "pathway":
                self._render_pathway(ax, adata, kwargs)
            elif plot_type == "line":
                self._render_line(ax, adata, kwargs)
            else:
                ax.text(0.5, 0.5, f"[{plot_type}]", ha="center", va="center", transform=ax.transAxes)
        except Exception as e:
            ax.text(0.5, 0.5, f"Render error:\n{e}", ha="center", va="center",
                    transform=ax.transAxes, fontsize=7, color="red")
            logger.warning(f"Panel render error: {e}")
        ax.set_title(panel.title, fontsize=8, fontweight="bold", loc="left")

    def _render_umap(self, ax, adata, kwargs) -> None:
        color_by = kwargs.get("color_by", "leiden")
        if "X_umap" not in adata.obsm:
            ax.text(0.5, 0.5, "No UMAP embedding.\nRun run_umap() first.", ha="center", va="center",
                    transform=ax.transAxes, fontsize=7, color="gray")
            return
        coords = adata.obsm["X_umap"]
        if color_by in adata.obs.columns:
            categories = adata.obs[color_by].astype(str)
            for cat in sorted(categories.unique()):
                mask = categories == cat
                ax.scatter(coords[mask, 0], coords[mask, 1], s=1, alpha=0.6,
                           label=cat, color=self._get_color(cat), rasterized=True)
            ax.legend(fontsize=5, markerscale=3, loc="upper right", bbox_to_anchor=(1.25, 1.0))
        else:
            ax.scatter(coords[:, 0], coords[:, 1], s=1, alpha=0.5, color="gray", rasterized=True)
        ax.set_xlabel("UMAP1", fontsize=7)
        ax.set_ylabel("UMAP2", fontsize=7)

    def _render_dotplot(self, ax, adata, kwargs) -> None:
        groupby = kwargs.get("groupby", "leiden")
        n_genes = kwargs.get("n_genes", 10)
        if groupby not in adata.obs.columns:
            ax.text(0.5, 0.5, f"No '{groupby}' column", ha="center", va="center",
                    transform=ax.transAxes, fontsize=7)
            return
        genes = list(adata.var_names[:n_genes])
        groups = sorted(adata.obs[groupby].unique().astype(str))[:6]
        if not groups or not genes:
            return
        n_show_genes = min(8, len(genes))
        genes = genes[:n_show_genes]
        dot_data = np.zeros((len(groups), len(genes)))
        for i, group in enumerate(groups):
            mask = adata.obs[groupby].astype(str) == group
            if mask.sum() > 0:
                for j, gene in enumerate(genes):
                    if gene in adata.var_names:
                        gene_idx = list(adata.var_names).index(gene)
                        vals = adata.X[mask, gene_idx]
                        if hasattr(vals, "toarray"):
                            vals = vals.toarray()
                        dot_data[i, j] = float(np.mean(vals > 0))
        im = ax.imshow(dot_data, aspect="auto", cmap="Blues", vmin=0, vmax=1)
        ax.set_xticks(range(len(genes)))
        ax.set_xticklabels(genes, rotation=45, ha="right", fontsize=6)
        ax.set_yticks(range(len(groups)))
        ax.set_yticklabels(groups, fontsize=7)
        plt.colorbar(im, ax=ax, shrink=0.8)

    def _render_heatmap(self, ax, adata, kwargs) -> None:
        groupby = kwargs.get("groupby", "leiden")
        n_genes = kwargs.get("n_genes", 10)
        genes = list(adata.var_names[:min(n_genes, adata.n_vars)])
        groups = sorted(adata.obs[groupby].unique().astype(str)) if groupby in adata.obs.columns else []

        if not groups:
            ax.text(0.5, 0.5, "No group data available.\nRun clustering first.",
                    ha="center", va="center", transform=ax.transAxes, fontsize=8, color="red")
            return

        heat_data = []
        for group in groups[:5]:
            mask = adata.obs[groupby].astype(str) == group
            if mask.sum() == 0:
                continue
            n_samples = min(5, mask.sum())
            indices = np.random.choice(np.where(mask)[0], size=n_samples, replace=False)
            for idx in indices:
                row = []
                for gene in genes:
                    if gene in adata.var_names:
                        gene_idx = list(adata.var_names).index(gene)
                        row.append(float(adata.X[idx, gene_idx]))
                    else:
                        row.append(0)
                heat_data.append(row)
            if len(heat_data) >= 50:
                break

        if heat_data:
            im = ax.imshow(np.array(heat_data), aspect="auto", cmap="RdBu_r")
            ax.set_xticks(range(len(genes)))
            ax.set_xticklabels(genes, rotation=45, ha="right", fontsize=5)
            ax.set_ylabel("Cells", fontsize=7)
            plt.colorbar(im, ax=ax, shrink=0.8)
        else:
            ax.text(0.5, 0.5, "No data to display.", ha="center", va="center",
                    transform=ax.transAxes, fontsize=8, color="gray")

    def _render_volcano(self, ax, adata, kwargs) -> None:
        if "rank_genes_groups" not in adata.uns:
            ax.text(0.5, 0.5, "No DEG results.\nRun run_markers() first.",
                    ha="center", va="center", transform=ax.transAxes, fontsize=8, color="gray")
            return
        rgg = adata.uns["rank_genes_groups"]
        names = rgg["names"]
        scores = rgg["scores"]
        pvals = rgg["pvals_adj"]
        group_names = names.dtype.names if hasattr(names, "dtype") else []
        if not group_names:
            return
        first_group = group_names[0]
        n_genes = min(100, len(names[first_group]))
        log2fc = np.array([float(scores[first_group][i]) for i in range(n_genes)])
        pval = np.array([float(pvals[first_group][i]) for i in range(n_genes)])
        neg_log_p = -np.log10(np.maximum(pval, 1e-300))
        sig = pval < 0.05
        ax.scatter(log2fc[~sig], neg_log_p[~sig], s=3, alpha=0.3, color="gray", rasterized=True)
        ax.scatter(log2fc[sig], neg_log_p[sig], s=5, alpha=0.6, color="red", rasterized=True)
        ax.axhline(-np.log10(0.05), color="gray", linestyle="--", linewidth=0.5, alpha=0.5)
        ax.set_xlabel("log2FC", fontsize=7)
        ax.set_ylabel("-log10(p)", fontsize=7)

    def _render_bar(self, ax, adata, kwargs) -> None:
        groupby = kwargs.get("groupby", "leiden")
        if groupby in adata.obs.columns:
            counts = adata.obs[groupby].value_counts().head(15)
            colors = [self._get_color(str(c)) for c in counts.index]
            ax.barh(range(len(counts)), counts.values, color=colors, height=0.7)
            ax.set_yticks(range(len(counts)))
            ax.set_yticklabels(counts.index.astype(str), fontsize=6)
            ax.set_xlabel("Count", fontsize=7)
        else:
            ax.text(0.5, 0.5, "No group data", ha="center", va="center", transform=ax.transAxes, fontsize=7)

    def _render_scatter(self, ax, adata, kwargs) -> None:
        x_key = kwargs.get("x", "")
        y_key = kwargs.get("y", "")
        if x_key in adata.obs.columns and y_key in adata.obs.columns:
            ax.scatter(adata.obs[x_key], adata.obs[y_key], s=2, alpha=0.5, rasterized=True)
            ax.set_xlabel(x_key, fontsize=7)
            ax.set_ylabel(y_key, fontsize=7)
        else:
            ax.text(0.5, 0.5, "Data not available", ha="center", va="center", transform=ax.transAxes, fontsize=7)

    def _render_violin(self, ax, adata, kwargs) -> None:
        metrics = kwargs.get("metrics", ["n_genes", "n_counts", "pct_mt"])
        valid = [m for m in metrics if m in adata.obs.columns]
        if valid:
            data = [adata.obs[m].dropna().values for m in valid]
            ax.violinplot(data, positions=range(len(valid)), showmeans=True, showmedians=True)
            ax.set_xticks(range(len(valid)))
            ax.set_xticklabels(valid, fontsize=7, rotation=30)
        else:
            ax.text(0.5, 0.5, "No QC metrics", ha="center", va="center", transform=ax.transAxes, fontsize=7)

    def _render_pathway(self, ax, adata, kwargs) -> None:
        try:
            from omics.knowledge.engine import KnowledgeEngine
            engine = KnowledgeEngine()
            genes = list(adata.var_names[:200])
            results = engine.run_enrichment(genes, databases=["hallmark"], p_threshold=0.1, min_overlap=3)
            top_n = kwargs.get("top_n", 10)
            results = results[:top_n]
            if results:
                names = [r.gene_set_name[:30] for r in results]
                neg_log_p = [-np.log10(max(r.adjusted_p_value, 1e-10)) for r in results]
                ax.barh(range(len(results)), neg_log_p, color="#3C5488", height=0.6)
                ax.set_yticks(range(len(results)))
                ax.set_yticklabels(names, fontsize=5)
                ax.set_xlabel("-log10(p_adj)", fontsize=7)
            else:
                ax.text(0.5, 0.5, "No significant\nenrichment", ha="center", va="center",
                        transform=ax.transAxes, fontsize=7)
        except Exception as e:
            ax.text(0.5, 0.5, f"Pathway analysis\nunavailable: {e}", ha="center", va="center",
                    transform=ax.transAxes, fontsize=7)

    def _render_line(self, ax, adata, kwargs) -> None:
        genes = kwargs.get("genes", [])
        if not genes:
            genes = list(adata.var_names[:5])
        x = np.arange(min(100, adata.n_obs))
        for gene in genes[:5]:
            if gene in adata.var_names:
                idx = list(adata.var_names).index(gene)
                y = adata.X[:100, idx]
                if hasattr(y, "toarray"):
                    y = y.toarray().flatten()
                ax.plot(x, y, linewidth=1, alpha=0.7, label=gene)
        if genes:
            ax.legend(fontsize=5, loc="upper right")
        ax.set_xlabel("Ordered Cells", fontsize=7)
        ax.set_ylabel("Expression", fontsize=7)

    def _get_color(self, key: str) -> str:
        if key not in self._cell_type_colors:
            idx = len(self._cell_type_colors) % len(self._CELL_COLORS)
            self._cell_type_colors[key] = self._CELL_COLORS[idx]
        return self._cell_type_colors[key]

    def _compute_color_map(self, adata) -> dict:
        if hasattr(adata, "obs"):
            for col in ["leiden", "cell_type", "CellType"]:
                if col in adata.obs.columns:
                    for cat in sorted(adata.obs[col].astype(str).unique()):
                        self._get_color(cat)
                    break
        return self._cell_type_colors

    def _auto_layout(self, n_panels: int) -> tuple[int, int]:
        if n_panels <= 2:
            return 1, 2
        if n_panels <= 4:
            return 2, 2
        if n_panels <= 6:
            return 2, 3
        if n_panels <= 9:
            return 3, 3
        return (n_panels + 2) // 3, min(3, n_panels)

    def _export(self, fig: Figure, output_path: Path, dpi: int = 300) -> list[Path]:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        exported = []
        fig.savefig(output_path, dpi=dpi, bbox_inches="tight")
        exported.append(output_path)
        stem, parent = output_path.stem, output_path.parent
        if output_path.suffix != ".png":
            png_path = parent / f"{stem}.png"
            fig.savefig(png_path, dpi=dpi, bbox_inches="tight")
            exported.append(png_path)
        logger.info(f"Figure saved: {output_path}")
        return exported

    @staticmethod
    def load_template(name: str) -> FigureStory:
        if name not in STORY_TEMPLATES:
            available = list(STORY_TEMPLATES.keys())
            raise ValueError(f"Unknown template '{name}'. Available: {available}")
        return STORY_TEMPLATES[name]
