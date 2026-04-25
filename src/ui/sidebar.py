"""Render the shared sidebar used on all dashboard pages.

render_sidebar(page_key) builds a 260 px navy sidebar containing: a brand
block (gold accent bar, 'KSS' mark, title, sub), navigation links to the three
pages, a year selector (st.pills, single, default 2024), a risk-class filter
(st.pills, multi, options from SWEDISH_LABELS), a color-coded risk legend, and
a footer with data source, last-updated date, and version string.

All label strings come from SWEDISH_LABELS in src/ui/labels.py.
"""

import streamlit as st

from src.ui.css import COLORS
from src.ui.labels import SWEDISH_LABELS


# ---------------------------------------------------------------------------
# Navigation configuration
# ---------------------------------------------------------------------------

_NAV_ITEMS = [
    {"key": "landing", "label": SWEDISH_LABELS["nav_landing"], "page": "app"},
    {"key": "national", "label": SWEDISH_LABELS["nav_national"], "page": "pages/01_Riksoversikt"},
    {"key": "kommun", "label": SWEDISH_LABELS["nav_kommun"], "page": "pages/02_Kommunjamforelse"},
]

_RISK_OPTIONS = [
    SWEDISH_LABELS["risk_high"],
    SWEDISH_LABELS["risk_medium"],
    SWEDISH_LABELS["risk_low"],
]

_YEAR_OPTIONS = list(range(2024, 2009, -1))

_RISK_LEGEND = [
    (COLORS["high_risk"], SWEDISH_LABELS["risk_high"]),
    (COLORS["medium_risk"], SWEDISH_LABELS["risk_medium"]),
    (COLORS["low_risk"], SWEDISH_LABELS["risk_low"]),
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
        Dict with keys:
            'selected_year' (int): The year selected in the year pill.
            'selected_risks' (list[str]): Selected risk class labels
                (Swedish strings from SWEDISH_LABELS).
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
            active = "active" if item["key"] == page_key else ""
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

        # ---- Year selector ----
        st.html(
            f'<div class="shai-sidebar-section-label">'
            f'{SWEDISH_LABELS["label_year"]}</div>'
        )
        selected_year = st.pills(
            label=SWEDISH_LABELS["label_year"],
            options=_YEAR_OPTIONS,
            default=2024,
            label_visibility="collapsed",
        )
        if selected_year is None:
            selected_year = 2024

        # ---- Risk filter ----
        st.html(
            f'<div class="shai-sidebar-section-label">'
            f'{SWEDISH_LABELS["label_risk_filter"]}</div>'
        )
        selected_risks = st.pills(
            label=SWEDISH_LABELS["label_risk_filter"],
            options=_RISK_OPTIONS,
            default=_RISK_OPTIONS,
            selection_mode="multi",
            label_visibility="collapsed",
        )
        if not selected_risks:
            selected_risks = _RISK_OPTIONS

        # ---- Risk legend ----
        legend_html = '<div class="shai-risk-legend">'
        for color, label in _RISK_LEGEND:
            legend_html += (
                f'<div class="shai-risk-legend-item">'
                f'<div class="shai-risk-legend-dot" style="background:{color};"></div>'
                f'<span class="shai-risk-legend-label">{label}</span>'
                f'</div>'
            )
        legend_html += '</div>'
        st.html(legend_html)

        # ---- Footer ----
        st.html(f"""
        <div class="shai-sidebar-footer">
            <p>{SWEDISH_LABELS["footer_source_label"]}: {SWEDISH_LABELS["footer_source"]}</p>
            <span class="shai-footer-version">v1.0</span>
        </div>
        """)

    return {
        "selected_year": int(selected_year),
        "selected_risks": list(selected_risks),
    }
