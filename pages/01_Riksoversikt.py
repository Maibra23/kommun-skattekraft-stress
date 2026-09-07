"""Streamlit page 2 — National overview (Riksöversikt).

Leads with relative position and drift, which is the reliable descriptive fact
this project has, rather than with a forecast that scored r = +0.016 against
realised 2025 growth (REMEDIATION_PLAN.md T1.2).  Page sections:

  1. Page title block
  2. KPI row: index spread, largest 10-year fall and rise, cross-sectional R²
  3. Choropleth with a layer toggle — position / 5-year drift / vulnerability —
     beside a histogram of the same quantity
  4. Table of all 290 kommuner: our index, SCB's index, and both drifts

The vulnerability score survives as one map layer and nowhere else.  It is not
what sorts the table, not what filters the sidebar, and not a KPI.

All data loaded from precomputed artifacts using @st.cache_data.
All Swedish strings come from SWEDISH_LABELS in src/ui/labels.py.
"""

from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# Page config (must be first Streamlit call)
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="KSS Riksöversikt",
    page_icon=None,
    layout="wide",
    menu_items={"Get Help": None, "Report a bug": None},
)

from src.provenance import analysis_year, panel_max_year  # noqa: E402
from src.ui.chart_theme import get_chart_layout  # noqa: E402
from src.ui.choropleth import MAP_LAYERS, render_choropleth, resolve_layer  # noqa: E402
from src.ui.components import (  # noqa: E402
    card_header,
    footer_note,
    kpi_card,
    page_title,
    render_kpi_row,
)
from src.ui.css import COLORS, inject_css  # noqa: E402
from src.ui.labels import (  # noqa: E402
    POSITION_BANDS,
    SWEDISH_LABELS,
    classify_position,
    format_index_points,
    format_pct,
)
from src.ui.sidebar import render_sidebar  # noqa: E402

# ---------------------------------------------------------------------------
# Inject CSS and render sidebar
# ---------------------------------------------------------------------------

inject_css()
sidebar_state = render_sidebar("national")

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_ARTIFACTS_DIR = _PROJECT_ROOT / "artifacts"

# Position runs to the panel's own last year; the model stops at the last year
# with every structural variable.  Neither is hardcoded — see src/provenance.py.
_POSITION_YEAR = panel_max_year()
_ANALYSIS_YEAR = analysis_year()


@st.cache_data
def _load_position() -> pd.DataFrame:
    """Position and drift for the latest year the panel reaches."""
    df = pd.read_parquet(_ARTIFACTS_DIR / "position.parquet")
    return df[df["year"] == _POSITION_YEAR].copy()


@st.cache_data
def _load_names() -> pd.DataFrame:
    """Kommun and län names, from the panel."""
    panel = pd.read_parquet(_PROJECT_ROOT / "data" / "processed" / "panel.parquet")
    return panel[["kommun_kod", "kommun_name", "lan_name"]].drop_duplicates()


@st.cache_data
def _load_panel_latest() -> pd.DataFrame:
    """Structural variables for the latest complete-case year, for tooltips."""
    panel = pd.read_parquet(_PROJECT_ROOT / "data" / "processed" / "panel.parquet")
    return panel[panel["year"] == _ANALYSIS_YEAR][
        ["kommun_kod", "tax_base_per_capita", "unemployment_rate", "population"]
    ].copy()


@st.cache_data
def _load_vulnerability() -> pd.DataFrame:
    """The deprecated score, kept only to draw its map layer."""
    path = _ARTIFACTS_DIR / "predictions.parquet"
    if not path.exists():
        return pd.DataFrame(columns=["kommun_kod", "vulnerability_score"])
    return pd.read_parquet(path)[
        ["kommun_kod", "vulnerability_score", "vulnerability_rank", "risk_class"]
    ]


@st.cache_data
def _load_cross_r2() -> float:
    """Cross-sectional R² for the analysis year, from the coefficient table."""
    coefs = pd.read_parquet(_ARTIFACTS_DIR / "coefficients_cross.parquet")
    row = coefs[coefs["spec"] == f"year_{_ANALYSIS_YEAR}"]
    return float(row["r_squared"].iloc[0])


position_df = _load_position().merge(_load_names(), on="kommun_kod", how="left")
panel_latest = _load_panel_latest()
vulnerability_df = _load_vulnerability()
cross_r2 = _load_cross_r2()

map_df = position_df.merge(panel_latest, on="kommun_kod", how="left").merge(
    vulnerability_df, on="kommun_kod", how="left"
)

_UPDATED_DATE = ""
if (_ARTIFACTS_DIR / "position.parquet").exists():
    _UPDATED_DATE = datetime.fromtimestamp(
        (_ARTIFACTS_DIR / "position.parquet").stat().st_mtime
    ).strftime("%Y-%m-%d")

# ---------------------------------------------------------------------------
# Section 1: Page title
# ---------------------------------------------------------------------------

st.html(
    page_title(
        eyebrow=SWEDISH_LABELS["eyebrow_national"],
        title=SWEDISH_LABELS["title_national"],
        subtitle=SWEDISH_LABELS["subtitle_national"],
        year=_POSITION_YEAR,
    )
)

# ---------------------------------------------------------------------------
# Section 2: KPI row — spread, movers, fit
# ---------------------------------------------------------------------------

_highest = position_df.loc[position_df["relative_position"].idxmax()]
_lowest = position_df.loc[position_df["relative_position"].idxmin()]

_with_drift = position_df.dropna(subset=["drift_10y"])
_biggest_fall = _with_drift.loc[_with_drift["drift_10y"].idxmin()]
_biggest_rise = _with_drift.loc[_with_drift["drift_10y"].idxmax()]

kpi_cards = [
    kpi_card(
        SWEDISH_LABELS["kpi_index_spread"],
        value=(
            f"{_highest['relative_position']:.0f} / "
            f"{_lowest['relative_position']:.0f}"
        ),
        variant="default",
    ),
    kpi_card(
        SWEDISH_LABELS["kpi_largest_fall_10y"],
        value=(
            f"{format_index_points(_biggest_fall['drift_10y'])}, "
            f"{_biggest_fall['kommun_name']}"
        ),
        variant="danger",
    ),
    kpi_card(
        SWEDISH_LABELS["kpi_largest_rise_10y"],
        value=(
            f"{format_index_points(_biggest_rise['drift_10y'])}, "
            f"{_biggest_rise['kommun_name']}"
        ),
        variant="default",
    ),
    kpi_card(
        SWEDISH_LABELS["kpi_cross_r2"],
        value=format_pct(cross_r2 * 100, decimals=0),
        variant="default",
        tooltip=SWEDISH_LABELS["kpi_cross_r2_tooltip"].format(year=_ANALYSIS_YEAR),
    ),
]
render_kpi_row(kpi_cards)

st.html(
    '<div class="shai-summary">'
    + SWEDISH_LABELS["national_position_summary"].format(
        high_name=_highest["kommun_name"],
        high=_highest["relative_position"],
        low_name=_lowest["kommun_name"],
        low=_lowest["relative_position"],
    )
    + "</div>"
)

# ---------------------------------------------------------------------------
# Sidebar filter: position bands
# ---------------------------------------------------------------------------

_BAND_BY_LABEL = {band.label: band for band in POSITION_BANDS}
_selected_bands = {
    _BAND_BY_LABEL[label].key
    for label in sidebar_state["selected_bands"]
    if label in _BAND_BY_LABEL
}


def _band_key(index: float) -> str:
    band = classify_position(index)
    return band.key if band else ""


position_df["band_key"] = position_df["relative_position"].apply(_band_key)
filtered_df = position_df[position_df["band_key"].isin(_selected_bands)].copy()

# ---------------------------------------------------------------------------
# Section 3 & 4: Choropleth with layer toggle (left) + histogram (right)
# ---------------------------------------------------------------------------

col_map, col_hist = st.columns([3, 2])

with col_map:
    with st.container(border=True):
        st.html(
            card_header(
                SWEDISH_LABELS["map_title"],
                subtitle=SWEDISH_LABELS["map_subtitle"],
            )
        )
        _layer_label = st.radio(
            SWEDISH_LABELS["map_layer_label"],
            options=[layer.label for layer in MAP_LAYERS.values()],
            index=0,
            horizontal=True,
        )
        active_layer = resolve_layer(_layer_label)
        render_choropleth(map_df, layer=active_layer)
        with st.expander(SWEDISH_LABELS["explain_choropleth_expander"]):
            st.markdown(SWEDISH_LABELS["explain_choropleth_text"])

with col_hist:
    with st.container(border=True):
        st.html(card_header(SWEDISH_LABELS["chart_distribution"]))

        # The histogram follows the map: same quantity, same units, so the two
        # cannot disagree about what is being shown.
        hist_values = filtered_df.merge(
            vulnerability_df, on="kommun_kod", how="left"
        )[active_layer.column]

        fig_hist = go.Figure()
        fig_hist.add_trace(
            go.Histogram(
                x=hist_values,
                nbinsx=30,
                marker_color=COLORS["secondary"],
                hovertemplate=(
                    f"{active_layer.label}: %{{x:.1f}}<br>"
                    + SWEDISH_LABELS["axis_kommuner_count"]
                    + ": %{y}<extra></extra>"
                ),
            )
        )

        # Reference line: the national mean for a level, zero for a signed
        # quantity.  Drawing a zero line on an index would be meaningless.
        fig_hist.add_vline(
            x=0 if active_layer.diverging else 100,
            line_dash="dash",
            line_width=1,
            line_color=COLORS["text_secondary"],
        )

        hist_layout = get_chart_layout(
            height=400,
            xaxis_title=active_layer.label,
            yaxis_title=SWEDISH_LABELS["axis_kommuner_count"],
            showlegend=False,
        )
        fig_hist.update_layout(**hist_layout)
        st.plotly_chart(
            fig_hist,
            use_container_width=True,
            config={"displayModeBar": False},
        )
        with st.expander(SWEDISH_LABELS["explain_histogram_expander"]):
            st.markdown(SWEDISH_LABELS["explain_histogram_text"])

# ---------------------------------------------------------------------------
# Section 5: The two index measures, side by side (T1.3)
# ---------------------------------------------------------------------------

with st.container(border=True):
    st.html(card_header(SWEDISH_LABELS["index_compare_title"]))
    st.html(
        f'<div class="shai-explanation">'
        f'{SWEDISH_LABELS["index_compare_explanation"]}</div>'
    )

# ---------------------------------------------------------------------------
# Section 6: Table of all kommuner
# ---------------------------------------------------------------------------

with st.container(border=True):
    st.html(card_header(SWEDISH_LABELS["chart_ranking_title"]))
    with st.expander(SWEDISH_LABELS["explain_ranking_expander"]):
        st.markdown(SWEDISH_LABELS["explain_ranking_text"])

    table_df = filtered_df.sort_values("relative_position", ascending=False)
    display_df = pd.DataFrame(
        {
            SWEDISH_LABELS["th_kommun"]: table_df["kommun_name"].values,
            SWEDISH_LABELS["th_lan"]: table_df["lan_name"].values,
            SWEDISH_LABELS["index_compare_ours"]: table_df[
                "relative_position"
            ].round(1).values,
            SWEDISH_LABELS["index_compare_scb"]: table_df[
                "tax_base_index_riket"
            ].values,
            SWEDISH_LABELS["drift_5y"]: table_df["drift_5y"].round(1).values,
            SWEDISH_LABELS["drift_10y"]: table_df["drift_10y"].round(1).values,
        }
    )

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            SWEDISH_LABELS["index_compare_ours"]: st.column_config.NumberColumn(
                format="%.1f"
            ),
            SWEDISH_LABELS["index_compare_scb"]: st.column_config.NumberColumn(
                format="%.0f"
            ),
            SWEDISH_LABELS["drift_5y"]: st.column_config.NumberColumn(format="%+.1f"),
            SWEDISH_LABELS["drift_10y"]: st.column_config.NumberColumn(format="%+.1f"),
        },
    )

    csv_data = display_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label=SWEDISH_LABELS["btn_download_csv"],
        data=csv_data,
        file_name="riksoversikt_position.csv",
        mime="text/csv",
    )

# ---------------------------------------------------------------------------
# Section 7: Footer
# ---------------------------------------------------------------------------

st.html(footer_note(SWEDISH_LABELS["footer_source"], "v1.0", updated=_UPDATED_DATE))
