"""Plotly chart theme and layout factory for the dashboard.

Defines CHART_PALETTE (8-color sequence) and get_chart_layout(title, height,
xaxis_title, yaxis_title, showlegend) which returns a Plotly Layout dict
conforming to the design system: Source Sans 3 12 px base font, white plot
background, navy (#0B1F3F) hover background, gridlines #E5E7EB, and no
Plotly branding.  All axis label strings should be passed in from
SWEDISH_LABELS by the calling page.
"""

from src.ui.css import CHART_PALETTE, COLORS  # noqa: F401 — re-export for convenience

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_chart_layout(
    title: str = "",
    height: int = 400,
    xaxis_title: str = "",
    yaxis_title: str = "",
    showlegend: bool = True,
) -> dict:
    """Return a Plotly layout dict conforming to the KSS design system.

    Uses Source Sans 3 as the base font, white plot background, navy hover
    background, dotted Y gridlines, and no Plotly branding (logo, mode bar).

    Args:
        title: Chart title (Swedish, from SWEDISH_LABELS).
        height: Chart height in pixels.
        xaxis_title: X-axis label (Swedish).
        yaxis_title: Y-axis label (Swedish).
        showlegend: Whether to show the legend.

    Returns:
        Dict suitable for ``fig.update_layout(**get_chart_layout(...))``.
    """
    return {
        "title": {
            "text": title,
            "font": {"family": "Source Sans 3, sans-serif", "size": 15, "color": COLORS["text_primary"]},
            "x": 0,
            "xanchor": "left",
        },
        "height": height,
        "font": {
            "family": "Source Sans 3, sans-serif",
            "size": 12,
            "color": COLORS["text_primary"],
        },
        "plot_bgcolor": "#FFFFFF",
        "paper_bgcolor": "#FFFFFF",
        "xaxis": {
            "title": {
                "text": xaxis_title,
                "font": {"size": 11, "color": COLORS["text_secondary"]},
            },
            "gridcolor": COLORS["grid"],
            "gridwidth": 1,
            "griddash": "dot",
            "showline": True,
            "linecolor": COLORS["border"],
            "linewidth": 1,
            "tickfont": {"family": "IBM Plex Mono, monospace", "size": 11, "color": COLORS["text_secondary"]},
        },
        "yaxis": {
            "title": {
                "text": yaxis_title,
                "font": {"size": 11, "color": COLORS["text_secondary"]},
            },
            "gridcolor": COLORS["grid"],
            "gridwidth": 1,
            "griddash": "dot",
            "showline": False,
            "tickfont": {"family": "IBM Plex Mono, monospace", "size": 11, "color": COLORS["text_secondary"]},
        },
        "hoverlabel": {
            "bgcolor": COLORS["primary"],
            "font_size": 12,
            "font_family": "Source Sans 3, sans-serif",
            "font_color": "#FFFFFF",
        },
        "showlegend": showlegend,
        "legend": {
            "font": {"size": 11, "color": COLORS["text_secondary"]},
            "bgcolor": "rgba(0,0,0,0)",
        },
        "margin": {"l": 48, "r": 16, "t": 48, "b": 40},
        "modebar": {"remove": ["logo", "lasso2d", "select2d"]},
    }
