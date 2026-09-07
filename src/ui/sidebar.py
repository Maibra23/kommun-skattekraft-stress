"""Render the shared sidebar used on all dashboard pages.

render_sidebar(page_key) builds a 260 px navy sidebar containing: a brand
block (gold accent bar, 'KSS' mark, title, sub), navigation links to the three
pages, a position filter (st.pills, multi, options from POSITION_BANDS), a
legend for those bands, and a footer with data source and version string.

The filter used to cut on risk class -- quintiles of a forecast that scored
r = +0.016 against realised growth, and relative by construction, so exactly
58 kommuner were always "hog risk". It now cuts on observed position against
the national mean. See REMEDIATION_PLAN.md T1.2.

All label strings come from SWEDISH_LABELS in src/ui/labels.py.
"""

import streamlit as st

from src.ui.css import COLORS, SEQUENTIAL_SCALE
from src.ui.labels import POSITION_BANDS, SWEDISH_LABELS


# ---------------------------------------------------------------------------
# Navigation configuration
# ---------------------------------------------------------------------------

_NAV_ITEMS = [
    {"key": "landing", "label": SWEDISH_LABELS["nav_landing"], "page": "app"},
    {"key": "national", "label": SWEDISH_LABELS["nav_national"], "page": "pages/01_Riksoversikt"},
    {"key": "kommun", "label": SWEDISH_LABELS["nav_kommun"], "page": "pages/02_Kommunjamforelse"},
]

#: Highest band first, so the pills read top-down like the legend.
_BAND_OPTIONS = [band.label for band in reversed(POSITION_BANDS)]

#: Swatches taken from the map's sequential ramp, so the sidebar and the
#: choropleth agree that darker means higher.
_BAND_LEGEND = [
    (SEQUENTIAL_SCALE[5], POSITION_BANDS[2].label),
    (SEQUENTIAL_SCALE[3], POSITION_BANDS[1].label),
    (SEQUENTIAL_SCALE[1], POSITION_BANDS[0].label),
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def render_sidebar(page_key: str) -> dict:
    """Render the shared sidebar and return user selections.

    Args:
        page_key: Current page identifier — 'landing', 'national', or
            'kommun'.  Used to highlight the active navigation link.

    Returns:
        Dict with key 'selected_bands' (list[str]): the selected position-band
        labels. Empty selections are treated as "all", so the pages never
        render an empty map.
    """
    with st.sidebar:
        # ---- Brand block ----
        st.html(f"""
        <div class="shai-sidebar-brand">
            <div class="shai-brand-bar"></div>
            <div class="shai-brand-mark">{SWEDISH_LABELS["brand_mark"]}</div>
            <div class="shai-brand-title">{SWEDISH_LABELS["brand_title"]}</div>
            <div class="shai-brand-sub">{SWEDISH_LABELS["brand_sub"]}</div>
        </div>
        """)

        # ---- Navigation ----
        for item in _NAV_ITEMS:
            if item["key"] == page_key:
                # Active page — render as highlighted text (no link needed)
                st.html(
                    f'<div class="shai-sidebar-nav">'
                    f'<a class="active" href="#">{item["label"]}</a>'
                    f'</div>'
                )
            else:
                st.page_link(
                    f'{item["page"]}.py',
                    label=item["label"],
                )

        st.html('<div style="height: 8px;"></div>')

        # ---- Position filter ----
        st.html(
            f'<div class="shai-sidebar-section-label">'
            f'{SWEDISH_LABELS["label_position_filter"]}</div>'
        )
        selected_bands = st.pills(
            label=SWEDISH_LABELS["label_position_filter"],
            options=_BAND_OPTIONS,
            default=_BAND_OPTIONS,
            selection_mode="multi",
            label_visibility="collapsed",
        )
        if not selected_bands:
            selected_bands = _BAND_OPTIONS

        # ---- Band legend ----
        legend_html = '<div class="shai-risk-legend">'
        for color, label in _BAND_LEGEND:
            legend_html += (
                f'<div class="shai-risk-legend-item">'
                f'<div class="shai-risk-legend-dot" style="background:{color};"></div>'
                f'<span class="shai-risk-legend-label">{label}</span>'
                f'</div>'
            )
        legend_html += '</div>'
        st.html(legend_html)
        st.html(
            f'<div class="shai-sidebar-note">'
            f'{SWEDISH_LABELS["band_legend_note"]}</div>'
        )

        # ---- Footer ----
        st.html(f"""
        <div class="shai-sidebar-footer">
            <p>{SWEDISH_LABELS["footer_source_label"]}: {SWEDISH_LABELS["footer_source"]}</p>
            <span class="shai-footer-version">v1.0</span>
        </div>
        """)

    return {
        "selected_bands": list(selected_bands),
    }
