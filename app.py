"""Streamlit entry point, Landing page (Startsida).

Configures the page with st.set_page_config (title 'KSS Startsida',
layout='wide'), injects the global CSS, and renders the sidebar.  Page
sections (in order):
  1. Hero block with navy gradient and gold accent border
  2. Stat strip: 290 KOMMUNER, 15 AR PANEL, 4 STRUKTURVARIABLER, FIXED EFFECTS
  3. Modelloversikt: SVG flow diagram with explanation and collapsible example
  4. Variabler och vikter: regression coefficients bar chart with collapsible guide
  5. Pipeline steps: Datainsamling, Rensning, Estimering, Prognos
  6. Navigation cards linking to Riksoversikt and Kommunjaemfoerelse
  7. Kaellor och metod credibility block

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
    page_title="KSS Startsida",
    page_icon=None,
    layout="wide",
    menu_items={"Get Help": None, "Report a bug": None},
)

from src.provenance import analysis_year, panel_max_year  # noqa: E402
from src.ui.chart_theme import get_chart_layout  # noqa: E402
from src.ui.components import (  # noqa: E402
    card_header,
    footer_note,
)
from src.ui.css import COLORS, inject_css  # noqa: E402
from src.ui.labels import SWEDISH_LABELS  # noqa: E402
from src.ui.sidebar import render_sidebar  # noqa: E402

# ---------------------------------------------------------------------------
# Inject CSS and render sidebar
# ---------------------------------------------------------------------------

inject_css()
sidebar_state = render_sidebar("landing")

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parent
_ARTIFACTS_DIR = _PROJECT_ROOT / "artifacts"

# Never hardcoded: 2024 today, and it moves when SCB publishes 2025
# unemployment.  See src/provenance.py.
_ANALYSIS_YEAR = analysis_year()
_PANEL_YEAR = panel_max_year()


@st.cache_data
def _load_cross_coefficients() -> pd.DataFrame:
    """Cross-sectional coefficients for the analysis year.

    This is the headline model: it explains why kommuner differ from each
    other, which is the question the dashboard is about.
    """
    coefs = pd.read_parquet(_ARTIFACTS_DIR / "coefficients_cross.parquet")
    return coefs[coefs["spec"] == f"year_{_ANALYSIS_YEAR}"].copy()


@st.cache_data
def _load_within_primary() -> pd.DataFrame:
    """The FE panel's primary specification, for the within-time section.

    Selected by ``role``, not by spec name: T2.4 promoted the lagged spec
    without renaming anything, because the names are a published contract.
    """
    coefs = pd.read_parquet(_ARTIFACTS_DIR / "coefficients.parquet")
    if "role" in coefs.columns:
        return coefs[coefs["role"] == "primary"].copy()
    return coefs[coefs["spec"] == "lagged"].copy()


cross_df = _load_cross_coefficients()
within_df = _load_within_primary()

_UPDATED_DATE = ""
if (_ARTIFACTS_DIR / "position.parquet").exists():
    _UPDATED_DATE = datetime.fromtimestamp(
        (_ARTIFACTS_DIR / "position.parquet").stat().st_mtime
    ).strftime("%Y-%m-%d")

# ---------------------------------------------------------------------------
# Section 1: Hero block
# ---------------------------------------------------------------------------

st.html(f"""
<div class="shai-hero">
    <div class="shai-eyebrow">{SWEDISH_LABELS["eyebrow_landing"]}</div>
    <h1>{SWEDISH_LABELS["title_landing"]}</h1>
    <div class="shai-lead">{SWEDISH_LABELS["landing_lead"]}</div>
</div>
""")

# Collapsible concept explanation
with st.expander(SWEDISH_LABELS["concept_skattekraft_expander"]):
    st.markdown(SWEDISH_LABELS["concept_skattekraft_text"])

# Collapsible usage guide
with st.expander(SWEDISH_LABELS["guide_expander"]):
    st.markdown(SWEDISH_LABELS["guide_text"])

# ---------------------------------------------------------------------------
# Section 2: Stat strip
# ---------------------------------------------------------------------------

st.html(f"""
<div class="shai-stat-strip">
    <div class="shai-stat-cell">
        <span class="shai-stat-value">290</span>
        <span class="shai-stat-label">{SWEDISH_LABELS["landing_stat_kommuner"]}</span>
    </div>
    <div class="shai-stat-cell">
        <span class="shai-stat-value">17</span>
        <span class="shai-stat-label">{SWEDISH_LABELS["landing_stat_panel"]}</span>
    </div>
    <div class="shai-stat-cell">
        <span class="shai-stat-value">4</span>
        <span class="shai-stat-label">{SWEDISH_LABELS["landing_stat_vars"]}</span>
    </div>
    <div class="shai-stat-cell">
        <span class="shai-stat-value">2</span>
        <span class="shai-stat-label">{SWEDISH_LABELS["landing_stat_identified"]}</span>
    </div>
</div>
""")

# ---------------------------------------------------------------------------
# Section 3: Modellöversikt (SVG flow diagram)
# ---------------------------------------------------------------------------

st.html(f"""
<div class="shai-card">
    <div class="shai-card-header">
        <div><h3>{SWEDISH_LABELS["landing_model_title"]}</h3></div>
        <span class="shai-tag">{SWEDISH_LABELS["method_model_name"]}</span>
    </div>
    <svg viewBox="0 0 800 170" xmlns="http://www.w3.org/2000/svg"
         style="width:100%;max-width:800px;margin:12px auto;display:block;"
         aria-hidden="true">
        <!-- Identified drivers: solid, full weight.  These two separate
             kommuner from each other; the model can tell them apart. -->
        <text x="10" y="18" font-family="Source Sans 3" font-size="10"
              font-weight="700" fill="{COLORS['text_secondary']}"
              letter-spacing="0.5">{SWEDISH_LABELS["svg_identified_heading"]}</text>

        <rect x="10" y="26" width="180" height="34" rx="4"
              fill="{COLORS['bg']}" stroke="{COLORS['primary']}" stroke-width="1.5" />
        <text x="100" y="48" text-anchor="middle"
              font-family="Source Sans 3" font-size="11" fill="{COLORS['text_primary']}">
            {SWEDISH_LABELS["var_education"]}</text>

        <rect x="10" y="66" width="180" height="34" rx="4"
              fill="{COLORS['bg']}" stroke="{COLORS['primary']}" stroke-width="1.5" />
        <text x="100" y="88" text-anchor="middle"
              font-family="Source Sans 3" font-size="11" fill="{COLORS['text_primary']}">
            {SWEDISH_LABELS["var_unemployment"]}</text>

        <!-- Controls: dashed and muted.  They are in the model, but between
             kommuner their effect cannot be told from zero. -->
        <text x="10" y="122" font-family="Source Sans 3" font-size="10"
              font-weight="700" fill="{COLORS['text_tertiary']}"
              letter-spacing="0.5">{SWEDISH_LABELS["svg_controls_heading"]}</text>

        <rect x="10" y="130" width="88" height="28" rx="4"
              fill="none" stroke="{COLORS['text_tertiary']}" stroke-width="1"
              stroke-dasharray="3 3" />
        <text x="54" y="148" text-anchor="middle"
              font-family="Source Sans 3" font-size="9" fill="{COLORS['text_tertiary']}">
            {SWEDISH_LABELS["var_dependency"]}</text>

        <rect x="102" y="130" width="88" height="28" rx="4"
              fill="none" stroke="{COLORS['text_tertiary']}" stroke-width="1"
              stroke-dasharray="3 3" />
        <text x="146" y="148" text-anchor="middle"
              font-family="Source Sans 3" font-size="9" fill="{COLORS['text_tertiary']}">
            {SWEDISH_LABELS["var_population"]}</text>

        <!-- Arrows: solid from the drivers, dashed from the controls -->
        <line x1="192" y1="43" x2="316" y2="62" stroke="{COLORS['accent']}"
              stroke-width="1.8" marker-end="url(#arrow)" />
        <line x1="192" y1="83" x2="316" y2="72" stroke="{COLORS['accent']}"
              stroke-width="1.8" marker-end="url(#arrow)" />
        <line x1="192" y1="144" x2="316" y2="88" stroke="{COLORS['text_tertiary']}"
              stroke-width="1" stroke-dasharray="3 3" marker-end="url(#arrow-muted)" />

        <!-- Model -->
        <rect x="320" y="46" width="170" height="52" rx="4"
              fill="{COLORS['primary']}" stroke="none" />
        <text x="405" y="68" text-anchor="middle"
              font-family="Source Sans 3" font-size="12" font-weight="700"
              fill="#FFFFFF">{SWEDISH_LABELS["svg_regression_model"]}</text>
        <text x="405" y="86" text-anchor="middle"
              font-family="IBM Plex Mono" font-size="9" fill="{COLORS['accent']}">
            {SWEDISH_LABELS["svg_cross_section"]}</text>

        <!-- Outputs: an explanation of position, not a forecast -->
        <line x1="490" y1="62" x2="600" y2="45" stroke="{COLORS['accent']}"
              stroke-width="1.8" marker-end="url(#arrow)" />
        <line x1="490" y1="82" x2="600" y2="99" stroke="{COLORS['accent']}"
              stroke-width="1.8" marker-end="url(#arrow)" />

        <rect x="604" y="28" width="186" height="34" rx="4"
              fill="{COLORS['bg']}" stroke="{COLORS['border']}" />
        <text x="697" y="50" text-anchor="middle"
              font-family="Source Sans 3" font-size="11" fill="{COLORS['text_primary']}">
            {SWEDISH_LABELS["svg_position"]}</text>

        <rect x="604" y="82" width="186" height="34" rx="4"
              fill="{COLORS['bg']}" stroke="{COLORS['border']}" />
        <text x="697" y="104" text-anchor="middle"
              font-family="Source Sans 3" font-size="11" fill="{COLORS['text_primary']}">
            {SWEDISH_LABELS["svg_decomposition"]}</text>

        <defs>
            <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5"
                    markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 0 L 10 5 L 0 10 z" fill="{COLORS['accent']}" />
            </marker>
            <marker id="arrow-muted" viewBox="0 0 10 10" refX="9" refY="5"
                    markerWidth="5" markerHeight="5" orient="auto-start-reverse">
                <path d="M 0 0 L 10 5 L 0 10 z" fill="{COLORS['text_tertiary']}" />
            </marker>
        </defs>
    </svg>
    <p style="font-family: 'Source Sans 3', sans-serif; font-size: 14px;
              color: {COLORS['text_secondary']}; margin: 12px 20px 4px 20px;
              line-height: 1.6;">
        {SWEDISH_LABELS["landing_model_explanation"]}
    </p>
</div>
""")

with st.expander(SWEDISH_LABELS["landing_model_expander"]):
    st.markdown(SWEDISH_LABELS["landing_model_example"])

# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Section 4: Variabler & koefficienter (effect per standard deviation)
# ---------------------------------------------------------------------------

_VAR_LABEL_MAP = {
    "unemployment_rate": SWEDISH_LABELS["var_unemployment"],
    "dependency_ratio": SWEDISH_LABELS["var_dependency"],
    "population_growth_pct": SWEDISH_LABELS["var_population"],
    "edu_share": SWEDISH_LABELS["var_education"],
}

# Effects are shown per standard deviation, with intervals.  Raw coefficients
# are not comparable across variables measured in different units: the
# dependency ratio's raw coefficient is the largest of the four and its actual
# effect the smallest but one, so a bar chart of raw betas inverts the ranking.
plot_df = cross_df.copy()
plot_df["label"] = plot_df["variable"].map(_VAR_LABEL_MAP)
plot_df = plot_df.sort_values("beta_sd")

fig_coefs = go.Figure()
fig_coefs.add_trace(
    go.Bar(
        x=plot_df["beta_sd"],
        y=plot_df["label"],
        orientation="h",
        marker_color=[
            (COLORS["low_risk"] if v >= 0 else COLORS["high_risk"])
            if ident
            else COLORS["text_tertiary"]
            for v, ident in zip(plot_df["beta_sd"], plot_df["identified"])
        ],
        marker_line_width=0,
        error_x=dict(
            type="data",
            symmetric=False,
            array=(plot_df["upper_ci_sd"] - plot_df["beta_sd"]).tolist(),
            arrayminus=(plot_df["beta_sd"] - plot_df["lower_ci_sd"]).tolist(),
            color=COLORS["text_secondary"],
            thickness=1.2,
            width=6,
        ),
        text=[f"{v:+.1f}".replace(".", ",") for v in plot_df["beta_sd"]],
        textposition="outside",
        textfont={"family": "IBM Plex Mono", "size": 12, "color": COLORS["text_primary"]},
        hovertemplate=(
            "<b>%{y}</b><br>%{x:+.2f} "
            + SWEDISH_LABELS["unit_index_points"]
            + "<extra></extra>"
        ),
    )
)
fig_coefs.add_vline(x=0, line_width=1, line_color=COLORS["border"])

layout = get_chart_layout(
    height=300,
    xaxis_title=SWEDISH_LABELS["axis_beta_sd"],
    showlegend=False,
)
layout["yaxis"]["tickfont"] = {
    "family": "Source Sans 3, sans-serif",
    "size": 13,
    "color": COLORS["text_primary"],
}
layout["margin"]["l"] = 240
layout["margin"]["r"] = 90
layout["bargap"] = 0.35
fig_coefs.update_layout(**layout)

with st.container(border=True):
    st.html(
        card_header(
            SWEDISH_LABELS["landing_vars_title"],
            tag=SWEDISH_LABELS["method_period"],
        )
    )
    st.html(f'<div class="shai-explanation">{SWEDISH_LABELS["landing_vars_explanation"]}</div>')
    st.plotly_chart(fig_coefs, use_container_width=True, config={"displayModeBar": False})
    st.html(f'<div class="shai-explanation">{SWEDISH_LABELS["landing_vars_scale_note"]}</div>')

    coef_table = pd.DataFrame(
        {
            SWEDISH_LABELS["vars_table_variable"]: plot_df["label"].values,
            SWEDISH_LABELS["vars_table_effect_sd"]: [
                f"{v:+.2f}".replace(".", ",") for v in plot_df["beta_sd"]
            ],
            SWEDISH_LABELS["vars_table_ci"]: [
                f"[{lo:+.2f}, {hi:+.2f}]".replace(".", ",")
                for lo, hi in zip(plot_df["lower_ci_sd"], plot_df["upper_ci_sd"])
            ],
            SWEDISH_LABELS["vars_table_identified"]: [
                SWEDISH_LABELS["identified_yes"]
                if ident
                else SWEDISH_LABELS["identified_no"]
                for ident in plot_df["identified"]
            ],
        }
    )
    st.dataframe(coef_table, use_container_width=True, hide_index=True)

    with st.expander(SWEDISH_LABELS["landing_vars_expander"]):
        st.markdown(SWEDISH_LABELS["landing_vars_example"])
    with st.expander(SWEDISH_LABELS["explain_coef_chart_expander"]):
        st.markdown(SWEDISH_LABELS["explain_coef_chart_text"])

# ---------------------------------------------------------------------------
# Section 4b: Samband inom kommuner över tid (the FE panel, T2.4)
# ---------------------------------------------------------------------------

# Physically separated from everything above, because it answers a different
# question and cannot rank kommuner.
with st.container(border=True):
    st.html(card_header(SWEDISH_LABELS["within_section_title"]))
    st.html(f'<div class="shai-explanation">{SWEDISH_LABELS["within_section_lead"]}</div>')
    st.html(f'<div class="shai-explanation">{SWEDISH_LABELS["within_section_spec"]}</div>')

    within_table = within_df.copy()
    within_table["label"] = within_table["variable"].map(_VAR_LABEL_MAP)
    within_table = within_table.sort_values("t_stat")

    def _sig_label(p: float) -> str:
        if p < 0.001:
            return "***"
        if p < 0.01:
            return "**"
        if p < 0.05:
            return "*"
        return SWEDISH_LABELS["sig_not_significant"]

    st.dataframe(
        pd.DataFrame(
            {
                SWEDISH_LABELS["vars_table_variable"]: within_table["label"].values,
                SWEDISH_LABELS["vars_table_coef"]: [
                    f"{v:+.4f}".replace(".", ",") for v in within_table["coefficient"]
                ],
                SWEDISH_LABELS["vars_table_sig"]: [
                    _sig_label(p) for p in within_table["p_value"]
                ],
            }
        ),
        use_container_width=True,
        hide_index=True,
    )
    st.html(f'<div class="shai-explanation">{SWEDISH_LABELS["within_section_caveat"]}</div>')

# ---------------------------------------------------------------------------
# Section 5: Pipeline steps
# ---------------------------------------------------------------------------

steps = [
    ("01", SWEDISH_LABELS["landing_step_1"]),
    ("02", SWEDISH_LABELS["landing_step_2"]),
    ("03", SWEDISH_LABELS["landing_step_3"]),
    ("04", SWEDISH_LABELS["landing_step_4"]),
]

pipeline_html = '<div class="shai-pipeline">'
for i, (num, label) in enumerate(steps):
    pipeline_html += f"""
    <div class="shai-pipeline-step">
        <span class="shai-step-num">{num}</span>
        <span class="shai-step-label">{label}</span>
    </div>
    """
    if i < len(steps) - 1:
        pipeline_html += '<span class="shai-pipeline-arrow">&gt;</span>'
pipeline_html += '</div>'
st.html(pipeline_html)

# ---------------------------------------------------------------------------
# Section 6: Navigation cards
# ---------------------------------------------------------------------------

st.html(f"""
<div style="margin-top: 32px; margin-bottom: 8px;">
    <h3 style="font-family: 'Source Sans 3', sans-serif; font-size: 18px;
               font-weight: 700; color: {COLORS['text_primary']}; margin: 0;">
        {SWEDISH_LABELS["landing_nav_title"]}
    </h3>
    <p style="font-family: 'Source Sans 3', sans-serif; font-size: 14px;
              color: {COLORS['text_secondary']}; margin: 4px 0 0 0;">
        {SWEDISH_LABELS["landing_nav_explanation"]}
    </p>
</div>
""")

col1, col2 = st.columns(2)

with col1:
    st.html(f"""
    <div class="shai-nav-card">
        <h4>{SWEDISH_LABELS["nav_national"]}</h4>
        <p>{SWEDISH_LABELS["landing_nav_national_desc"]}</p>
    </div>
    """)
    st.page_link("pages/01_Riksoversikt.py", label=SWEDISH_LABELS['nav_national'])

with col2:
    st.html(f"""
    <div class="shai-nav-card">
        <h4>{SWEDISH_LABELS["nav_kommun"]}</h4>
        <p>{SWEDISH_LABELS["landing_nav_kommun_desc"]}</p>
    </div>
    """)
    st.page_link("pages/02_Kommunjamforelse.py", label=SWEDISH_LABELS['nav_kommun'])

# ---------------------------------------------------------------------------
# Section 7: Källor & metod
# ---------------------------------------------------------------------------

source_pills = [
    "SCB OE0101",
    "SCB BE0101",
    "SCB AA0003",
    "SCB UF0506",
]

pills_html = " ".join(
    f'<span class="shai-source-pill">{s}</span>' for s in source_pills
)

st.html(f"""
<div class="shai-card" style="text-align:center;">
    <div class="shai-card-header" style="justify-content:center;">
        <div><h3>{SWEDISH_LABELS["landing_sources_title"]}</h3></div>
    </div>
    <div style="margin-top:8px;">
        {pills_html}
    </div>
    <p style="font-size:12px;color:{COLORS['text_secondary']};margin-top:12px;">
        {SWEDISH_LABELS["method_model_name"]},
        {SWEDISH_LABELS["method_period"]},
        {SWEDISH_LABELS["method_units"]}
    </p>
</div>
""")

# ---------------------------------------------------------------------------
# Section 8: Footer
# ---------------------------------------------------------------------------

st.html(footer_note(SWEDISH_LABELS["footer_source"], "v1.0", updated=_UPDATED_DATE))
