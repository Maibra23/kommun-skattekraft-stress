"""Streamlit page 3 — Municipality detail and decomposition (Kommunjämförelse).

Configures the page with st.set_page_config (title 'KSS · Kommunjämförelse',
layout='wide'), injects CSS, and renders the sidebar.  A st.selectbox lets the
user choose a municipality (default: top of vulnerability rank).  Page
sections:
  1. KPI row (4 cards): skattekraft 2024, tillväxt 2024 (%), prognos 2025 (%),
     sårbarhetsrang (X / 290)
  2. Historisk trend: line chart of tax_base_per_capita 2010–2024 for selected
     municipality vs national mean
  3. Dekomponering: horizontal bar chart of structural contribution columns from
     decomposition.parquet, green = positive, red = negative
  4. Peer comparison table: 5 most similar municipalities by vulnerability_score
  5. Methodology link pointing to METHODOLOGY.md on GitHub

All data loaded from precomputed artifacts using @st.cache_data.
All Swedish strings come from SWEDISH_LABELS in src/ui/labels.py.
"""

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# Page config (must be first Streamlit call)
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="KSS \u00b7 Kommunjämförelse",
    page_icon=None,
    layout="wide",
    menu_items={"Get Help": None, "Report a bug": None},
)

from src.ui.chart_theme import get_chart_layout  # noqa: E402
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
    format_sek,
    format_signed_pct,
)
from src.ui.sidebar import render_sidebar  # noqa: E402

# ---------------------------------------------------------------------------
# Inject CSS and render sidebar
# ---------------------------------------------------------------------------

inject_css()
sidebar_state = render_sidebar("kommun")

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
def _load_decomposition() -> pd.DataFrame:
    """Load 290-row decomposition artifact."""
    return pd.read_parquet(_ARTIFACTS_DIR / "decomposition.parquet")


@st.cache_data
def _load_panel() -> pd.DataFrame:
    """Load full panel data for historical trends."""
    return pd.read_parquet(
        _PROJECT_ROOT / "data" / "processed" / "panel.parquet"
    )


predictions_df = _load_predictions()
decomposition_df = _load_decomposition()
panel_df = _load_panel()

# ---------------------------------------------------------------------------
# Section 1: Page title
# ---------------------------------------------------------------------------

st.html(
    page_title(
        eyebrow=SWEDISH_LABELS["eyebrow_kommun"],
        title=SWEDISH_LABELS["title_kommun"],
        subtitle=SWEDISH_LABELS["subtitle_kommun"],
    )
)

# ---------------------------------------------------------------------------
# Section 2: Kommun selector
# ---------------------------------------------------------------------------

sorted_predictions = predictions_df.sort_values("vulnerability_rank")


def _shorten_lan(lan_name: str) -> str:
    """Shorten 'Värmlands län' to 'Värmland' etc."""
    short = lan_name.replace(" län", "")
    if short.endswith("s"):
        short = short[:-1]
    return short


kommun_options = [
    f"{row['kommun_name']} ({_shorten_lan(row['lan_name'])}) "
    f"\u2014 Rang {int(row['vulnerability_rank'])}"
    for _, row in sorted_predictions.iterrows()
]
kommun_koder = sorted_predictions["kommun_kod"].tolist()

selected_option = st.selectbox(
    SWEDISH_LABELS["label_kommun_select"],
    options=kommun_options,
    index=0,
)

# Find selected kommun code
selected_idx = kommun_options.index(selected_option)
selected_kod = kommun_koder[selected_idx]

# Get data for selected kommun
selected_pred = predictions_df[
    predictions_df["kommun_kod"] == selected_kod
].iloc[0]
selected_panel = panel_df[panel_df["kommun_kod"] == selected_kod].sort_values(
    "year"
)
selected_decomp = decomposition_df[
    decomposition_df["kommun_kod"] == selected_kod
].iloc[0]

# Latest panel data (2024)
latest_panel = selected_panel[selected_panel["year"] == 2024].iloc[0]

# ---------------------------------------------------------------------------
# Section 3: KPI row
# ---------------------------------------------------------------------------

growth_2024 = latest_panel["tax_base_growth_pct"]
delta_dir = "up" if growth_2024 >= 0 else "down"

kpi_cards = [
    kpi_card(
        SWEDISH_LABELS["kpi_skattekraft_2024"],
        value=format_sek(latest_panel["tax_base_per_capita"]),
        variant="default",
    ),
    kpi_card(
        SWEDISH_LABELS["kpi_growth_2024"],
        value=format_signed_pct(growth_2024),
        delta_direction=delta_dir,
        variant="default",
    ),
    kpi_card(
        SWEDISH_LABELS["kpi_prognosis_2025"],
        value=format_signed_pct(selected_pred["predicted_growth_2025"]),
        variant="default",
    ),
    kpi_card(
        SWEDISH_LABELS["kpi_vulnerability_rank"],
        value=f"{int(selected_pred['vulnerability_rank'])} / 290",
        variant="default",
    ),
]
render_kpi_row(kpi_cards)

# ---------------------------------------------------------------------------
# Section 4: Historisk trend (kommun vs national average)
# ---------------------------------------------------------------------------

with st.container(border=True):
    st.html(card_header(SWEDISH_LABELS["chart_historical"]))

    # National average per year (unweighted across 290 kommuner)
    national_avg = (
        panel_df.groupby("year")["tax_base_per_capita"]
        .mean()
        .reset_index()
        .sort_values("year")
    )

    fig_trend = go.Figure()

    # Selected kommun line
    fig_trend.add_trace(
        go.Scatter(
            x=selected_panel["year"],
            y=selected_panel["tax_base_per_capita"],
            name=selected_pred["kommun_name"],
            line=dict(color=COLORS["secondary"], width=2.5),
            mode="lines+markers",
            marker=dict(size=4),
            hovertemplate=(
                f"<b>{selected_pred['kommun_name']}</b><br>"
                + SWEDISH_LABELS["axis_year"]
                + ": %{x}<br>"
                + SWEDISH_LABELS["axis_skattekraft"]
                + ": %{y:,.0f} "
                + SWEDISH_LABELS["unit_sek"]
                + "<extra></extra>"
            ),
        )
    )

    # National average line (gray dashed)
    fig_trend.add_trace(
        go.Scatter(
            x=national_avg["year"],
            y=national_avg["tax_base_per_capita"],
            name=SWEDISH_LABELS["chart_national_avg"],
            line=dict(
                color=COLORS["text_secondary"], width=1.5, dash="dash"
            ),
            mode="lines",
            hovertemplate=(
                f"<b>{SWEDISH_LABELS['chart_national_avg']}</b><br>"
                + SWEDISH_LABELS["axis_year"]
                + ": %{x}<br>"
                + SWEDISH_LABELS["axis_skattekraft"]
                + ": %{y:,.0f} "
                + SWEDISH_LABELS["unit_sek"]
                + "<extra></extra>"
            ),
        )
    )

    trend_layout = get_chart_layout(
        height=380,
        xaxis_title=SWEDISH_LABELS["axis_year"],
        yaxis_title=SWEDISH_LABELS["axis_skattekraft"],
    )
    fig_trend.update_layout(**trend_layout)
    st.plotly_chart(
        fig_trend,
        use_container_width=True,
        config={"displayModeBar": False},
    )

# ---------------------------------------------------------------------------
# Section 5: Dekomponering (horizontal bar chart)
# ---------------------------------------------------------------------------

with st.container(border=True):
    st.html(card_header(SWEDISH_LABELS["chart_decomposition"]))

    decomp_components = [
        ("decomp_unemployment", SWEDISH_LABELS["contrib_unemployment"]),
        ("decomp_dependency", SWEDISH_LABELS["contrib_dependency"]),
        ("decomp_population", SWEDISH_LABELS["contrib_population"]),
        ("decomp_education", SWEDISH_LABELS["contrib_education"]),
        ("decomp_residual", SWEDISH_LABELS["contrib_residual"]),
    ]

    values = [float(selected_decomp[col]) for col, _ in decomp_components]
    labels = [lbl for _, lbl in decomp_components]
    bar_colors = [
        COLORS["low_risk"] if v >= 0 else COLORS["high_risk"] for v in values
    ]

    fig_decomp = go.Figure()
    fig_decomp.add_trace(
        go.Bar(
            x=values,
            y=labels,
            orientation="h",
            marker_color=bar_colors,
            text=[format_signed_pct(v) for v in values],
            textposition="outside",
            textfont={"family": "IBM Plex Mono", "size": 11},
            hovertemplate=(
                "<b>%{y}</b><br>"
                + SWEDISH_LABELS["axis_growth_pct"]
                + ": %{x:+.2f}<extra></extra>"
            ),
        )
    )

    decomp_layout = get_chart_layout(
        height=300,
        xaxis_title=SWEDISH_LABELS["axis_growth_pct"],
        showlegend=False,
    )
    decomp_layout["margin"]["l"] = 220
    fig_decomp.update_layout(**decomp_layout)
    st.plotly_chart(
        fig_decomp,
        use_container_width=True,
        config={"displayModeBar": False},
    )

# ---------------------------------------------------------------------------
# Section 6: Peer comparison (5 closest by vulnerability_score)
# ---------------------------------------------------------------------------

with st.container(border=True):
    st.html(card_header(SWEDISH_LABELS["chart_peers_title"]))

    selected_vuln = selected_pred["vulnerability_score"]
    peers = predictions_df.copy()
    peers["_score_diff"] = (peers["vulnerability_score"] - selected_vuln).abs()
    peers = peers[peers["kommun_kod"] != selected_kod]
    peers = peers.nsmallest(5, "_score_diff")

    peer_display = pd.DataFrame(
        {
            SWEDISH_LABELS["th_kommun"]: peers["kommun_name"].values,
            SWEDISH_LABELS["th_lan"]: peers["lan_name"].values,
            SWEDISH_LABELS["th_prognosis"]: peers["predicted_growth_2025"]
            .apply(lambda x: format_pct(x))
            .values,
            SWEDISH_LABELS["kpi_vulnerability_rank"]: peers[
                "vulnerability_rank"
            ]
            .astype(int)
            .values,
        }
    )

    st.dataframe(peer_display, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# Section 7: Methodology link
# ---------------------------------------------------------------------------

with st.container(border=True):
    st.link_button(
        SWEDISH_LABELS["btn_show_method"],
        "https://github.com/mustafa-2024/kommun-skattekraft-stress/blob/main/docs/METHODOLOGY.md",
    )

# ---------------------------------------------------------------------------
# Section 8: Footer
# ---------------------------------------------------------------------------

st.html(footer_note(SWEDISH_LABELS["footer_source"], "v1.0"))
