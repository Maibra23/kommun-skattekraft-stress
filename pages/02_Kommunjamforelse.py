"""Streamlit page 3 — Municipality detail (Kommunjämförelse).

Leads with where the kommun stands and which way it is moving, then explains
that position (REMEDIATION_PLAN.md T1.2).  Page sections:

  1. Kommun selector, ordered by position rather than by a forecast rank
  2. Lead sentence: index, and the five-year movement behind it
  3. KPI row: our index, SCB's index, 5-year drift, 10-year drift
  4. Position over time, against the national mean at 100
  5. Historical skattekraft in kronor, with optional comparison kommuner
  6. Decomposition of the position gap — bars only for the variables the model
     can separate between kommuner, with the controls stated as numbers
  7. Peer comparison, by position

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
    page_title="KSS Kommunjämförelse",
    page_icon=None,
    layout="wide",
    menu_items={"Get Help": None, "Report a bug": None},
)

from src.provenance import analysis_year, panel_max_year  # noqa: E402
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
    POSITION_BANDS,
    SWEDISH_LABELS,
    classify_position,
    format_index_points,
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

_POSITION_YEAR = panel_max_year()
_ANALYSIS_YEAR = analysis_year()
#: The drift window the lead sentence quotes.
_DRIFT_WINDOW = 5


@st.cache_data
def _load_position() -> pd.DataFrame:
    """Full position history, all years."""
    return pd.read_parquet(_ARTIFACTS_DIR / "position.parquet")


@st.cache_data
def _load_decomposition() -> pd.DataFrame:
    """Position-gap decomposition for the analysis year."""
    return pd.read_parquet(_ARTIFACTS_DIR / "decomposition_cross.parquet")


@st.cache_data
def _load_coefficients() -> pd.DataFrame:
    """Cross-sectional coefficients, for the controls' intervals."""
    coefs = pd.read_parquet(_ARTIFACTS_DIR / "coefficients_cross.parquet")
    return coefs[coefs["spec"] == f"year_{_ANALYSIS_YEAR}"]


@st.cache_data
def _load_panel() -> pd.DataFrame:
    """Full panel, for the skattekraft trend and the peer table."""
    return pd.read_parquet(_PROJECT_ROOT / "data" / "processed" / "panel.parquet")


position_all = _load_position()
decomposition_df = _load_decomposition()
coef_cross = _load_coefficients()
panel_df = _load_panel()

names_df = panel_df[["kommun_kod", "kommun_name", "lan_name"]].drop_duplicates()
position_latest = position_all[position_all["year"] == _POSITION_YEAR].merge(
    names_df, on="kommun_kod", how="left"
)

_UPDATED_DATE = ""
if (_ARTIFACTS_DIR / "position.parquet").exists():
    _UPDATED_DATE = datetime.fromtimestamp(
        (_ARTIFACTS_DIR / "position.parquet").stat().st_mtime
    ).strftime("%Y-%m-%d")

# ---------------------------------------------------------------------------
# Sidebar filter: position bands
# ---------------------------------------------------------------------------

_BAND_BY_LABEL = {band.label: band for band in POSITION_BANDS}
_selected_bands = {
    _BAND_BY_LABEL[label].key
    for label in sidebar_state["selected_bands"]
    if label in _BAND_BY_LABEL
}
position_latest["band_key"] = position_latest["relative_position"].apply(
    lambda v: (classify_position(v).key if classify_position(v) else "")
)
_filtered = position_latest[position_latest["band_key"].isin(_selected_bands)]
if _filtered.empty:
    _filtered = position_latest

# ---------------------------------------------------------------------------
# Section 1: Page title and kommun selector
# ---------------------------------------------------------------------------

st.html(
    page_title(
        eyebrow=SWEDISH_LABELS["eyebrow_kommun"],
        title=SWEDISH_LABELS["title_kommun"],
    )
)


def _shorten_lan(lan_name: str) -> str:
    """Shorten 'Värmlands län' to 'Värmland' etc."""
    short = str(lan_name).replace(" län", "")
    return short[:-1] if short.endswith("s") else short


# Ordered by position, lowest first: the kommuner furthest below the national
# mean are the ones a user most often arrives looking for.
sorted_kommuner = _filtered.sort_values("relative_position")
kommun_options = [
    f"{row['kommun_name']} ({_shorten_lan(row['lan_name'])}) "
    f"— index {row['relative_position']:.0f}"
    for _, row in sorted_kommuner.iterrows()
]
kommun_koder = sorted_kommuner["kommun_kod"].tolist()

selected_option = st.selectbox(
    SWEDISH_LABELS["label_kommun_select"],
    options=kommun_options,
    index=0,
)
selected_kod = kommun_koder[kommun_options.index(selected_option)]

selected_row = position_latest[
    position_latest["kommun_kod"] == selected_kod
].iloc[0]
selected_history = position_all[
    position_all["kommun_kod"] == selected_kod
].sort_values("year")
selected_panel = panel_df[panel_df["kommun_kod"] == selected_kod].sort_values("year")
selected_decomp = decomposition_df[
    decomposition_df["kommun_kod"] == selected_kod
].iloc[0]

_drift = selected_row[f"drift_{_DRIFT_WINDOW}y"]
_position_text = f"{selected_row['relative_position']:.0f}"
if pd.notna(_drift):
    _lead = SWEDISH_LABELS["kommun_position_lead"].format(
        kommun=selected_row["kommun_name"],
        position=_position_text,
        drift=format_index_points(_drift),
        since=_POSITION_YEAR - _DRIFT_WINDOW,
    )
else:
    _lead = SWEDISH_LABELS["kommun_position_lead_no_drift"].format(
        kommun=selected_row["kommun_name"],
        position=_position_text,
    )
st.html(f'<div class="shai-summary">{_lead}</div>')

st.html(
    '<div class="shai-vintage">'
    + SWEDISH_LABELS["vintage_note"].format(
        position_year=_POSITION_YEAR, analysis_year=_ANALYSIS_YEAR
    )
    + "</div>"
)

# ---------------------------------------------------------------------------
# Section 2: KPI row
# ---------------------------------------------------------------------------

_latest_panel_row = selected_panel[selected_panel["year"] == _ANALYSIS_YEAR]
_skattekraft = (
    _latest_panel_row["tax_base_per_capita"].iloc[0]
    if not _latest_panel_row.empty
    else float("nan")
)

kpi_cards = [
    kpi_card(
        SWEDISH_LABELS["index_compare_ours"],
        value=f"{selected_row['relative_position']:.1f}".replace(".", ","),
        variant="default",
    ),
    kpi_card(
        SWEDISH_LABELS["index_compare_scb"],
        value=f"{selected_row['tax_base_index_riket']:.0f}",
        variant="default",
    ),
    kpi_card(
        SWEDISH_LABELS["drift_5y"],
        value=(
            format_index_points(selected_row["drift_5y"])
            if pd.notna(selected_row["drift_5y"])
            else "–"
        ),
        variant="danger" if selected_row["drift_5y"] < 0 else "default",
    ),
    kpi_card(
        SWEDISH_LABELS["drift_10y"],
        value=(
            format_index_points(selected_row["drift_10y"])
            if pd.notna(selected_row["drift_10y"])
            else "–"
        ),
        variant="danger" if selected_row["drift_10y"] < 0 else "default",
    ),
]
render_kpi_row(kpi_cards)

# ---------------------------------------------------------------------------
# Section 3: Position over time
# ---------------------------------------------------------------------------

with st.container(border=True):
    st.html(card_header(SWEDISH_LABELS["chart_position_history"]))

    fig_pos = go.Figure()
    fig_pos.add_trace(
        go.Scatter(
            x=selected_history["year"],
            y=selected_history["relative_position"],
            name=selected_row["kommun_name"],
            line=dict(color=COLORS["secondary"], width=2.5),
            mode="lines+markers",
            marker=dict(size=4),
            hovertemplate=(
                f"<b>{selected_row['kommun_name']}</b><br>"
                + SWEDISH_LABELS["axis_year"]
                + ": %{x}<br>"
                + SWEDISH_LABELS["axis_index"]
                + ": %{y:.1f}<extra></extra>"
            ),
        )
    )
    # The national mean is 100 by construction, in every year.
    fig_pos.add_hline(
        y=100,
        line_dash="dash",
        line_width=1.5,
        line_color=COLORS["text_secondary"],
        annotation_text=SWEDISH_LABELS["chart_national_avg"],
        annotation_position="bottom right",
        annotation_font_size=11,
    )

    pos_layout = get_chart_layout(
        height=340,
        xaxis_title=SWEDISH_LABELS["axis_year"],
        yaxis_title=SWEDISH_LABELS["axis_index"],
        showlegend=False,
    )
    fig_pos.update_layout(**pos_layout)
    st.plotly_chart(fig_pos, use_container_width=True, config={"displayModeBar": False})
    st.html(
        f'<div class="shai-explanation">'
        f'{SWEDISH_LABELS["index_compare_explanation"]}</div>'
    )

# ---------------------------------------------------------------------------
# Section 4: Historisk skattekraft (kronor), with comparison kommuner
# ---------------------------------------------------------------------------

with st.container(border=True):
    st.html(card_header(SWEDISH_LABELS["chart_historical"]))

    _all_names = sorted(position_latest["kommun_name"].dropna().unique())
    compare_kommuner = st.multiselect(
        SWEDISH_LABELS["compare_label"],
        options=[n for n in _all_names if n != selected_row["kommun_name"]],
        default=[],
        max_selections=4,
        placeholder=SWEDISH_LABELS["compare_placeholder"],
    )

    national_avg = (
        panel_df.groupby("year")["tax_base_per_capita"]
        .mean()
        .reset_index()
        .sort_values("year")
    )

    fig_trend = go.Figure()
    fig_trend.add_trace(
        go.Scatter(
            x=selected_panel["year"],
            y=selected_panel["tax_base_per_capita"],
            name=selected_row["kommun_name"],
            line=dict(color=COLORS["secondary"], width=2.5),
            mode="lines+markers",
            marker=dict(size=4),
            hovertemplate=(
                f"<b>{selected_row['kommun_name']}</b><br>"
                + SWEDISH_LABELS["axis_year"]
                + ": %{x}<br>"
                + SWEDISH_LABELS["axis_skattekraft"]
                + ": %{y:,.0f} "
                + SWEDISH_LABELS["unit_sek"]
                + "<extra></extra>"
            ),
        )
    )

    from src.ui.css import CHART_PALETTE  # noqa: E402

    for i, comp_name in enumerate(compare_kommuner):
        comp_kod = position_latest.loc[
            position_latest["kommun_name"] == comp_name, "kommun_kod"
        ].iloc[0]
        comp_panel = panel_df[panel_df["kommun_kod"] == comp_kod].sort_values("year")
        fig_trend.add_trace(
            go.Scatter(
                x=comp_panel["year"],
                y=comp_panel["tax_base_per_capita"],
                name=comp_name,
                line=dict(color=CHART_PALETTE[(i + 2) % len(CHART_PALETTE)], width=1.8),
                mode="lines+markers",
                marker=dict(size=3),
                hovertemplate=(
                    f"<b>{comp_name}</b><br>"
                    + SWEDISH_LABELS["axis_year"]
                    + ": %{x}<br>"
                    + SWEDISH_LABELS["axis_skattekraft"]
                    + ": %{y:,.0f} "
                    + SWEDISH_LABELS["unit_sek"]
                    + "<extra></extra>"
                ),
            )
        )

    fig_trend.add_trace(
        go.Scatter(
            x=national_avg["year"],
            y=national_avg["tax_base_per_capita"],
            name=SWEDISH_LABELS["chart_national_avg"],
            line=dict(color=COLORS["text_secondary"], width=1.5, dash="dash"),
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
        height=360,
        xaxis_title=SWEDISH_LABELS["axis_year"],
        yaxis_title=SWEDISH_LABELS["axis_skattekraft"],
    )
    fig_trend.update_layout(**trend_layout)
    st.plotly_chart(
        fig_trend, use_container_width=True, config={"displayModeBar": False}
    )
    with st.expander(SWEDISH_LABELS["explain_trend_expander"]):
        st.markdown(SWEDISH_LABELS["explain_trend_text"])

# ---------------------------------------------------------------------------
# Section 5: Decomposition of the position gap
# ---------------------------------------------------------------------------

_VAR_LABELS = {
    "unemployment_rate": SWEDISH_LABELS["var_unemployment"],
    "dependency_ratio": SWEDISH_LABELS["var_dependency"],
    "population_growth_pct": SWEDISH_LABELS["var_population"],
    "edu_share": SWEDISH_LABELS["var_education"],
}

with st.container(border=True):
    st.html(card_header(SWEDISH_LABELS["decomp_position_title"]))
    st.html(
        f'<div class="shai-explanation">'
        f'{SWEDISH_LABELS["decomp_position_explanation"]}</div>'
    )

    # Bars are drawn only for what the decomposition attributed.  Which
    # variables those are comes from the artifact's own column names, so the
    # judgement lives in the model layer and not in this page.
    contrib_cols = [c for c in decomposition_df.columns if c.startswith("contrib_")]
    control_cols = [c for c in decomposition_df.columns if c.startswith("control_")]

    bar_labels = [
        _VAR_LABELS.get(c.removeprefix("contrib_"), c.removeprefix("contrib_"))
        for c in contrib_cols
    ] + [SWEDISH_LABELS["var_residual"]]
    bar_values = [float(selected_decomp[c]) for c in contrib_cols] + [
        float(selected_decomp["residual"])
    ]

    order = sorted(range(len(bar_values)), key=lambda i: bar_values[i])
    bar_labels = [bar_labels[i] for i in order]
    bar_values = [bar_values[i] for i in order]

    fig_decomp = go.Figure()
    fig_decomp.add_trace(
        go.Bar(
            x=bar_values,
            y=bar_labels,
            orientation="h",
            marker_color=[
                COLORS["text_tertiary"]
                if label == SWEDISH_LABELS["var_residual"]
                else (COLORS["positive"] if v >= 0 else COLORS["negative"])
                for label, v in zip(bar_labels, bar_values)
            ],
            text=[format_index_points(v) for v in bar_values],
            # Inside: an outside label on a negative bar lands on the category
            # name, given the wide left margin these labels need.
            textposition="inside",
            insidetextanchor="middle",
            textfont={"family": "IBM Plex Mono", "size": 11, "color": "#FFFFFF"},
            hovertemplate=(
                "<b>%{y}</b><br>%{x:+.2f} "
                + SWEDISH_LABELS["unit_index_points"]
                + "<extra></extra>"
            ),
        )
    )
    fig_decomp.add_vline(
        x=0, line_width=1.5, line_dash="dash", line_color=COLORS["text_tertiary"]
    )

    decomp_layout = get_chart_layout(
        height=300,
        xaxis_title=SWEDISH_LABELS["unit_index_points"],
        showlegend=False,
    )
    decomp_layout["margin"]["l"] = 240
    fig_decomp.update_layout(**decomp_layout)
    st.plotly_chart(
        fig_decomp, use_container_width=True, config={"displayModeBar": False}
    )

    st.html(f'<div class="shai-explanation">{SWEDISH_LABELS["decomp_residual_note"]}</div>')

    # Controls: reported as numbers with their intervals, never as bars.  A bar
    # would claim a precision the interval denies.
    st.html(card_header(SWEDISH_LABELS["decomp_controls_title"]))
    st.html(
        f'<div class="shai-explanation">'
        + SWEDISH_LABELS["decomp_controls_explanation"].format(year=_ANALYSIS_YEAR)
        + "</div>"
    )

    control_rows = []
    for col in control_cols:
        var = col.removeprefix("control_")
        coef_row = coef_cross[coef_cross["variable"] == var]
        ci = ""
        if not coef_row.empty:
            low = coef_row["lower_ci_sd"].iloc[0]
            high = coef_row["upper_ci_sd"].iloc[0]
            ci = f"[{low:+.2f}, {high:+.2f}]".replace(".", ",")
        control_rows.append(
            {
                SWEDISH_LABELS["vars_table_variable"]: _VAR_LABELS.get(var, var),
                SWEDISH_LABELS["decomp_contribution_col"]: format_index_points(
                    float(selected_decomp[col])
                ),
                SWEDISH_LABELS["vars_table_ci"]: ci,
                SWEDISH_LABELS["vars_table_identified"]: SWEDISH_LABELS[
                    "identified_no"
                ],
            }
        )
    st.dataframe(
        pd.DataFrame(control_rows), use_container_width=True, hide_index=True
    )

    with st.expander(SWEDISH_LABELS["explain_decomp_expander"]):
        st.markdown(SWEDISH_LABELS["explain_decomp_text"])

# ---------------------------------------------------------------------------
# Section 6: Peer comparison — nearest by position
# ---------------------------------------------------------------------------

with st.container(border=True):
    st.html(card_header(SWEDISH_LABELS["chart_peers_title"]))

    peers = position_latest[position_latest["kommun_kod"] != selected_kod].copy()
    peers["_gap"] = (
        peers["relative_position"] - selected_row["relative_position"]
    ).abs()
    peers = peers.nsmallest(5, "_gap")

    structural = panel_df[panel_df["year"] == _ANALYSIS_YEAR][
        [
            "kommun_kod",
            "unemployment_rate",
            "dependency_ratio",
            "population_growth_pct",
            "edu_share",
        ]
    ]
    peers = peers.merge(structural, on="kommun_kod", how="left")

    peer_display = pd.DataFrame(
        {
            SWEDISH_LABELS["th_kommun"]: peers["kommun_name"].values,
            SWEDISH_LABELS["th_lan"]: peers["lan_name"].values,
            SWEDISH_LABELS["col_with_year"].format(
                label=SWEDISH_LABELS["position_index_short"], year=_POSITION_YEAR
            ): [f"{v:.1f}".replace(".", ",") for v in peers["relative_position"]],
            SWEDISH_LABELS["drift_5y"]: [
                format_index_points(v) if pd.notna(v) else "–"
                for v in peers["drift_5y"]
            ],
            SWEDISH_LABELS["col_with_year"].format(
                label=SWEDISH_LABELS["th_unemployment"], year=_ANALYSIS_YEAR
            ): [
                format_pct(v) if pd.notna(v) else "–"
                for v in peers["unemployment_rate"]
            ],
            SWEDISH_LABELS["col_with_year"].format(
                label=SWEDISH_LABELS["th_education"], year=_ANALYSIS_YEAR
            ): [format_pct(v) if pd.notna(v) else "–" for v in peers["edu_share"]],
        }
    )
    st.dataframe(peer_display, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# Section 7: Footer
# ---------------------------------------------------------------------------

st.html(footer_note(SWEDISH_LABELS["footer_source"], "v1.0", updated=_UPDATED_DATE))
