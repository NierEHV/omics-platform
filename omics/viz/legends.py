"""Legend utilities for publication figures."""

import matplotlib.pyplot as plt


def add_legend_outside(ax: plt.Axes, loc: str = "upper left",
                        bbox_to_anchor: tuple = (1.02, 1.0),
                        fontsize: int = 7, title: str = "") -> plt.Legend:
    """Place legend outside the plot area."""
    legend = ax.legend(loc=loc, bbox_to_anchor=bbox_to_anchor, fontsize=fontsize,
                       frameon=False, title=title)
    if title:
        legend.get_title().set_fontsize(fontsize)
    return legend


def add_stat_annotation(ax: plt.Axes, x1: float, x2: float, y: float,
                        p_value: float, fontsize: int = 7) -> None:
    """Add statistical significance bracket with stars."""
    stars = "***" if p_value < 0.001 else "**" if p_value < 0.01 else "*" if p_value < 0.05 else "ns"
    if stars == "ns":
        return
    bar_y = y * 1.05
    ax.plot([x1, x1, x2, x2], [y, bar_y, bar_y, y], color="black", linewidth=0.5)
    ax.text((x1 + x2) / 2, bar_y, stars, ha="center", va="bottom", fontsize=fontsize)
