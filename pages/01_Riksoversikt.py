"""Streamlit page 2 — National overview (Riksöversikt).

Configures the page with st.set_page_config (title 'KSS · Riksöversikt',
layout='wide'), injects CSS, and renders the sidebar.  Page sections:
  1. Page title block with eyebrow and year badge
  2. KPI row (4 cards): median prognos 2025, kommuner i hög risk,
     största nedgång with kommun name, modellens R²
  3. Geografisk fördelning: Folium choropleth map (3:2 split with
     histogram on right) showing vulnerability_score per municipality
  4. Histogram: distribution of predicted_growth_2025 across municipalities
  5. Rangordning: sortable table of all 290 municipalities with CSV download

All data loaded from precomputed artifacts using @st.cache_data.
All Swedish strings come from SWEDISH_LABELS in src/ui/labels.py.
"""

import pickle
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

from src.ui.chart_theme import get_chart_layout  # noqa: E402
from src.ui.choropleth import render_choropleth  # noqa: E402
from src.ui.components import (  # noqa: E402
    card_header,
    footer_note,
    kpi_card,
    page_title,
    render_kpi_row,
)
from src.ui.css import COLORS, inject_css  # noqa: E402
from src.ui.labels import (  # noqa: E402
    SWEDISH_LABELS,
    format_pct,
    format_signed_pct,
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


@st.cache_data
def _load_predictions() -> pd.DataFrame:
    """Load 290-row prediction artifact."""
    return pd.read_parquet(_ARTIFACTS_DIR / "predictions.parquet")


@st.cache_data
def _load_ranking() -> pd.DataFrame:
    """Load ranking artifact sorted by vulnerability_rank."""
    return pd.read_parquet(_ARTIFACTS_DIR / "ranking.parquet")


@st.cache_data
def _load_coefficients() -> pd.DataFrame:
    """Load regression coefficients artifact."""
    return pd.read_parquet(_ARTIFACTS_DIR / "coefficients.parquet")


@st.cache_data
def _load_within_r2() -> float:
    """Extract within-R² from the pickled model results."""
    with open(_ARTIFACTS_DIR / "model_results.pkl", "rb") as f:
        res = pickle.load(f)
    return float(res.rsquared_within)


@st.cache_data
def _load_panel_2024() -> pd.DataFrame:
    """Load 2024 panel data for choropleth supplementary columns."""
    panel = pd.read_parquet(
        _PROJECT_ROOT / "data" / "processed" / "panel.parquet"
    )
    return panel[panel["year"] == 2024][
        ["kommun_kod", "tax_base_per_capita", "unemployment_rate", "population"]
    ].copy()


predictions_df = _load_predictions()
ranking_df = _load_ranking()
coef_df = _load_coefficients()
within_r2 = _load_within_r2()
panel_2024 = _load_panel_2024()

_UPDATED_DATE = ""
if (_ARTIFACTS_DIR / "predictions.parquet").exists():
    _UPDATED_DATE = datetime.fromtimestamp(
        (_ARTIFACTS_DIR / "predictions.parquet").stat().st_mtime
    ).strftime("%Y-%m-%d")

# ---------------------------------------------------------------------------
# Section 1: Page title
# ---------------------------------------------------------------------------

st.html(
    page_title(
        eyebrow=SWEDISH_LABELS["eyebrow_national"],
        title=SWEDISH_LABELS["title_national"],
        subtitle=SWEDISH_LABELS["subtitle_national"],
        year=2025,
    )
)

# ---------------------------------------------------------------------------
# Section 2: KPI row
# ---------------------------------------------------------------------------

median_predicted_growth = predictions_df["predicted_growth_2025"].median()
count_hog_risk = int((predictions_df["risk_class"] == "hog").sum())
worst_idx = predictions_df["predicted_growth_2025"].idxmin()
min_predicted = predictions_df.loc[worst_idx, "predicted_growth_2025"]
worst_kommun = predictions_df.loc[worst_idx, "kommun_name"]

kpi_cards = [
    kpi_card(
        SWEDISH_LABELS["kpi_median_prognosis"],
        value=format_pct(median_predicted_growth),
        variant="default",
    ),
    kpi_card(
        SWEDISH_LABELS["kpi_high_risk_count"],
        value=str(count_hog_risk),
        variant="danger",
    ),
    kpi_card(
        SWEDISH_LABELS["kpi_largest_decline"],
        value=f"{format_signed_pct(min_predicted)}, {worst_kommun}",
        variant="danger",
    ),
    kpi_card(
        SWEDISH_LABELS["kpi_model_r2"],
        value=format_pct(within_r2 * 100),
        variant="default",
        tooltip=SWEDISH_LABELS["kpi_r2_tooltip"],
    ),
]
render_kpi_row(kpi_cards)

# Contextual summary
_summary_text = SWEDISH_LABELS["national_summary_template"].format(
    median=format_pct(median_predicted_growth),
    count=count_hog_risk,
    kommun=worst_kommun,
    decline=format_signed_pct(min_predicted),
)
st.html(f'<div class="shai-summary">{_summary_text}</div>')

# ---------------------------------------------------------------------------
# Sidebar filter: risk class mapping
# ---------------------------------------------------------------------------

_RISK_LABEL_TO_CODE = {
    SWEDISH_LABELS["risk_high"]: "hog",
    SWEDISH_LABELS["risk_medium"]: "medel",
    SWEDISH_LABELS["risk_low"]: "lag",
}
_RISK_CODE_TO_LABEL = {v: k for k, v in _RISK_LABEL_TO_CODE.items()}

selected_risk_codes = [
    _RISK_LABEL_TO_CODE[lbl]
    for lbl in sidebar_state["selected_risks"]
    if lbl in _RISK_LABEL_TO_CODE
]

# Filtered data for table and histogram (NOT choropleth)
filtered_df = predictions_df[
    predictions_df["risk_class"].isin(selected_risk_codes)
].copy()

# ---------------------------------------------------------------------------
# Section 3 & 4: Two-column layout — Choropleth (left) + Histogram (right)
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
        # Merge predictions with 2024 panel data for choropleth tooltips
        choropleth_data = predictions_df.merge(
            panel_2024, on="kommun_kod", how="left"
        )
        render_choropleth(choropleth_data)
        with st.expander(SWEDISH_LABELS["explain_choropleth_expander"]):
            st.markdown(SWEDISH_LABELS["explain_choropleth_text"])

with col_hist:
    with st.container(border=True):
        st.html(
            card_header(SWEDISH_LABELS["chart_distribution"])
        )

        fig_hist = go.Figure()
        fig_hist.add_trace(
            go.Histogram(
                x=filtered_df["predicted_growth_2025"],
                nbinsx=30,
                marker_color=COLORS["secondary"],
                hovertemplate=(
                    SWEDISH_LABELS["axis_growth_pct"]
                    + ": %{x:.1f}<br>"
                    + SWEDISH_LABELS["axis_kommuner_count"]
                    + ": %{y}<extra></extra>"
                ),
            )
        )

        # Risk class boundary lines
        _p20 = predictions_df["predicted_growth_2025"].quantile(0.2)
        _p80 = predictions_df["predicted_growth_2025"].quantile(0.8)
        fig_hist.add_vline(
            x=_p20, line_dash="dash", line_width=1,
            line_color=COLORS["high_risk"],
            annotation_text=SWEDISH_LABELS["risk_boundary_high_medium"],
            annotation_position="top left",
            annotation_font_size=10,
            annotation_font_color=COLORS["text_secondary"],
        )
        fig_hist.add_vline(
            x=_p80, line_dash="dash", line_width=1,
            line_color=COLORS["low_risk"],
            annotation_text=SWEDISH_LABELS["risk_boundary_medium_low"],
            annotation_position="top right",
            annotation_font_size=10,
            annotation_font_color=COLORS["text_secondary"],
        )

        hist_layout = get_chart_layout(
            height=440,
            xaxis_title=SWEDISH_LABELS["axis_growth_pct"],
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
# Section 5: Rangordning (sortable table + CSV download)
# ---------------------------------------------------------------------------

with st.container(border=True):
    st.html(card_header(SWEDISH_LABELS["chart_ranking_title"]))
    with st.expander(SWEDISH_LABELS["explain_ranking_expander"]):
        st.markdown(SWEDISH_LABELS["explain_ranking_text"])

    table_df = filtered_df.sort_values("vulnerability_rank")
    display_df = pd.DataFrame(
        {
            SWEDISH_LABELS["th_rank"]: table_df["vulnerability_rank"].astype(int).values,
            SWEDISH_LABELS["th_kommun"]: table_df["kommun_name"].values,
            SWEDISH_LABELS["th_lan"]: table_df["lan_name"].values,
            SWEDISH_LABELS["th_prognosis"]: table_df["predicted_growth_2025"].values,
            SWEDISH_LABELS["th_risk_class"]: table_df["risk_class"]
            .map(_RISK_CODE_TO_LABEL)
            .values,
        }
    )

    def _color_risk(val):
        colors = {
            SWEDISH_LABELS["risk_high"]: (
                f"background-color: rgba(185, 74, 72, 0.12); "
                f"color: {COLORS['high_risk']}; font-weight: 600;"
            ),
            SWEDISH_LABELS["risk_medium"]: (
                f"background-color: rgba(212, 160, 60, 0.12); "
                f"color: {COLORS['medium_risk']}; font-weight: 600;"
            ),
            SWEDISH_LABELS["risk_low"]: (
                f"background-color: rgba(46, 125, 91, 0.12); "
                f"color: {COLORS['low_risk']}; font-weight: 600;"
            ),
        }
        return colors.get(val, "")

    styled_df = display_df.style.map(
        _color_risk, subset=[SWEDISH_LABELS["th_risk_class"]]
    )

    st.dataframe(
        styled_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            SWEDISH_LABELS["th_prognosis"]: st.column_config.NumberColumn(
                format="%.1f %%",
            ),
        },
    )

    csv_export = display_df.copy()
    csv_export[SWEDISH_LABELS["th_prognosis"]] = csv_export[
        SWEDISH_LABELS["th_prognosis"]
    ].apply(lambda x: format_pct(x))
    csv_data = csv_export.to_csv(index=False).encode("utf-8")
    st.download_button(
        label=SWEDISH_LABELS["btn_download_csv"],
        data=csv_data,
        file_name="riksoversikt_ranking.csv",
        mime="text/csv",
    )

# ---------------------------------------------------------------------------
# Section 6: Footer
# ---------------------------------------------------------------------------

st.html(footer_note(SWEDISH_LABELS["footer_source"], "v1.0", updated=_UPDATED_DATE))
