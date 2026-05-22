"""Journal-specific styling for publication-quality figures."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import matplotlib as mpl


@dataclass
class JournalTheme:
    name: str
    font_family: str = "Arial"
    font_size: int = 7
    dpi: int = 300
    fig_width_inches: float = 7.0
    fig_height_inches: float = 5.0
    line_width: float = 0.5
    tick_width: float = 0.5
    axes_linewidth: float = 0.5


NATURE_THEME = JournalTheme("nature", "Arial", 7, 300, 7.0, 5.0, 0.5, 0.5, 0.5)
CELL_THEME = JournalTheme("cell", "Helvetica", 7, 300, 7.0, 5.0, 0.5, 0.5, 0.5)
SCIENCE_THEME = JournalTheme("science", "Helvetica", 6, 300, 6.5, 4.5, 0.5, 0.5, 0.5)

THEMES = {"nature": NATURE_THEME, "cell": CELL_THEME, "science": SCIENCE_THEME}

# Color palettes
OKABE_ITO: dict[str, str] = {
    "orange": "#E69F00", "sky_blue": "#56B4E9", "green": "#009E73",
    "yellow": "#F0E442", "blue": "#0072B5", "red": "#D55E00",
    "pink": "#CC79A7", "black": "#000000",
}

BIOLOGICAL_PALETTE: list[str] = [
    "#E64B35", "#4DBBD5", "#00A087", "#3C5488", "#F39B7F",
    "#8491B4", "#91D1C2", "#DC0000", "#7E6148", "#B09C85",
    "#00A1D5", "#E18727", "#20854E", "#BC3C29", "#0072B5",
    "#7878BA", "#FFDC91", "#EE4C97", "#2CAADC", "#6F99AD",
]

CELL_TYPE_COLORS = dict(zip(
    ["T cell", "CD4+ T", "CD8+ T", "NK", "B cell", "Plasma", "Monocyte",
     "Macrophage", "Dendritic", "Neutrophil", "Mast", "Erythrocyte", "Endothelial", "Fibroblast"],
    BIOLOGICAL_PALETTE[:14]
))


class StyleManager:
    """Apply journal-specific themes to matplotlib figures."""

    @staticmethod
    def get_theme(journal: str = "nature") -> JournalTheme:
        return THEMES.get(journal, NATURE_THEME)

    @staticmethod
    def apply(fig: Figure, journal: str = "nature", **kwargs) -> Figure:
        theme = StyleManager.get_theme(journal)
        for ax in fig.axes:
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.spines["left"].set_linewidth(theme.axes_linewidth)
            ax.spines["bottom"].set_linewidth(theme.axes_linewidth)
            ax.tick_params(width=theme.tick_width, labelsize=theme.font_size - 1)
            ax.xaxis.label.set_size(theme.font_size)
            ax.yaxis.label.set_size(theme.font_size)
            if ax.title:
                ax.title.set_size(theme.font_size)
            if ax.legend_:
                ax.legend_.prop.set_size(theme.font_size - 2) if hasattr(ax.legend_, 'prop') else None
        return fig

    @staticmethod
    def set_global(journal: str = "nature") -> None:
        theme = StyleManager.get_theme(journal)
        mpl.rcParams.update({
            "font.family": "sans-serif",
            "font.sans-serif": [theme.font_family, "DejaVu Sans"],
            "font.size": theme.font_size,
            "figure.dpi": theme.dpi,
            "savefig.dpi": theme.dpi,
            "axes.linewidth": theme.axes_linewidth,
            "lines.linewidth": theme.line_width,
            "xtick.labelsize": theme.font_size - 1,
            "ytick.labelsize": theme.font_size - 1,
            "axes.labelsize": theme.font_size,
            "axes.titlesize": theme.font_size,
            "legend.fontsize": theme.font_size - 2,
            "figure.figsize": (theme.fig_width_inches, theme.fig_height_inches),
        })
