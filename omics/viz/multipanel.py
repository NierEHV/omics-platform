"""Multi-panel figure assembly for publication layouts."""

from __future__ import annotations

from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec
from omics.viz.style import StyleManager


class MultiPanelFigure:
    """Build a multi-panel figure with consistent styling and letter labels."""

    def __init__(self, n_rows: int = 1, n_cols: int = 1, journal: str = "nature",
                 figsize: tuple = None, **kwargs):
        self.n_rows = n_rows
        self.n_cols = n_cols
        self.journal = journal
        StyleManager.set_global(journal)
        figsize = figsize or (n_cols * 3.5, n_rows * 3.0)
        self.fig = plt.figure(figsize=figsize, **kwargs)
        self.gs = GridSpec(n_rows, n_cols, figure=self.fig, hspace=0.4, wspace=0.35)
        self._panel_idx = 0

    def add_subplot(self, row: int = None, col: int = None, colspan: int = 1,
                    rowspan: int = 1) -> plt.Axes:
        if row is None and col is None:
            row = self._panel_idx // self.n_cols
            col = self._panel_idx % self.n_cols
            self._panel_idx += 1
        return self.fig.add_subplot(self.gs[row, col])

    def add_panel_label(self, ax: plt.Axes, label: str) -> None:
        ax.text(-0.12, 1.05, label, transform=ax.transAxes, fontsize=10,
                fontweight="bold", va="center", ha="left")

    def save(self, path: Path, dpi: int = 300) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.fig.savefig(path, dpi=dpi, bbox_inches="tight")
        return path

    def close(self) -> None:
        plt.close(self.fig)
