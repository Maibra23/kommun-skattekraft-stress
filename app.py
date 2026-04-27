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

from src.ui.chart_theme import get_chart_layout  # noqa: E402
from src.ui.components import (  # noqa: E402
    card_header,
    footer_note,
    render_kpi_row,
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


@st.cache_data
def _load_coefficients() -> pd.DataFrame:
    """Load regression coefficients from artifacts."""
    return pd.read_parquet(_ARTIFACTS_DIR / "coefficients.parquet")


coef_df = _load_coefficients()

_UPDATED_DATE = ""
if (_ARTIFACTS_DIR / "predictions.parquet").exists():
    _UPDATED_DATE = datetime.fromtimestamp(
        (_ARTIFACTS_DIR / "predictions.parquet").stat().st_mtime
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
        <span class="shai-stat-value">15</span>
        <span class="shai-stat-label">{SWEDISH_LABELS["landing_stat_panel"]}</span>
    </div>
    <div class="shai-stat-cell">
        <span class="shai-stat-value">4</span>
        <span class="shai-stat-label">{SWEDISH_LABELS["landing_stat_vars"]}</span>
    </div>
    <div class="shai-stat-cell">
        <span class="shai-stat-value">FE</span>
        <span class="shai-stat-label">{SWEDISH_LABELS["landing_stat_fe"]}</span>
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
    <svg viewBox="0 0 800 120" xmlns="http://www.w3.org/2000/svg"
         style="width:100%;max-width:800px;margin:12px auto;display:block;"
         aria-hidden="true">
        <!-- Input boxes -->
        <rect x="10" y="10" width="130" height="36" rx="4"
              fill="{COLORS['bg']}" stroke="{COLORS['border']}" />
        <text x="75" y="33" text-anchor="middle"
              font-family="Source Sans 3" font-size="11" fill="{COLORS['text_primary']}">
            {SWEDISH_LABELS["var_unemployment"]}</text>

        <rect x="10" y="54" width="130" height="36" rx="4"
              fill="{COLORS['bg']}" stroke="{COLORS['border']}" />
        <text x="75" y="77" text-anchor="middle"
              font-family="Source Sans 3" font-size="11" fill="{COLORS['text_primary']}">
            {SWEDISH_LABELS["var_dependency"]}</text>

        <rect x="10" y="10" width="130" height="0" rx="4" fill="none" />

        <rect x="150" y="10" width="130" height="36" rx="4"
              fill="{COLORS['bg']}" stroke="{COLORS['border']}" />
        <text x="215" y="33" text-anchor="middle"
              font-family="Source Sans 3" font-size="11" fill="{COLORS['text_primary']}">
            {SWEDISH_LABELS["var_population"]}</text>

        <rect x="150" y="54" width="130" height="36" rx="4"
              fill="{COLORS['bg']}" stroke="{COLORS['border']}" />
        <text x="215" y="77" text-anchor="middle"
              font-family="Source Sans 3" font-size="11" fill="{COLORS['text_primary']}">
            {SWEDISH_LABELS["var_education"]}</text>

        <!-- Arrows to regression box -->
        <line x1="280" y1="30" x2="320" y2="55" stroke="{COLORS['accent']}"
              stroke-width="1.5" marker-end="url(#arrow)" />
        <line x1="280" y1="72" x2="320" y2="58" stroke="{COLORS['accent']}"
              stroke-width="1.5" marker-end="url(#arrow)" />

        <!-- Regression box (center) -->
        <rect x="320" y="30" width="160" height="50" rx="4"
              fill="{COLORS['primary']}" stroke="none" />
        <text x="400" y="52" text-anchor="middle"
              font-family="Source Sans 3" font-size="12" font-weight="700"
              fill="#FFFFFF">{SWEDISH_LABELS["svg_regression_model"]}</text>
        <text x="400" y="70" text-anchor="middle"
              font-family="IBM Plex Mono" font-size="9" fill="{COLORS['accent']}">
            {SWEDISH_LABELS["svg_panel_ols"]}</text>

        <!-- Arrows from regression box -->
        <line x1="480" y1="45" x2="520" y2="28" stroke="{COLORS['accent']}"
              stroke-width="1.5" marker-end="url(#arrow)" />
        <line x1="480" y1="55" x2="520" y2="55" stroke="{COLORS['accent']}"
              stroke-width="1.5" marker-end="url(#arrow)" />
        <line x1="480" y1="65" x2="520" y2="82" stroke="{COLORS['accent']}"
              stroke-width="1.5" marker-end="url(#arrow)" />

        <!-- Output boxes -->
        <rect x="520" y="10" width="130" height="36" rx="4"
              fill="{COLORS['bg']}" stroke="{COLORS['border']}" />
        <text x="585" y="33" text-anchor="middle"
              font-family="Source Sans 3" font-size="11" fill="{COLORS['text_primary']}">
            {SWEDISH_LABELS["svg_prognosis"]}</text>

        <rect x="520" y="54" width="130" height="36" rx="4"
              fill="{COLORS['bg']}" stroke="{COLORS['border']}" />
        <text x="585" y="77" text-anchor="middle"
              font-family="Source Sans 3" font-size="11" fill="{COLORS['text_primary']}">
            {SWEDISH_LABELS["svg_ranking"]}</text>

        <rect x="660" y="32" width="130" height="36" rx="4"
              fill="{COLORS['bg']}" stroke="{COLORS['border']}" />
        <text x="725" y="55" text-anchor="middle"
              font-family="Source Sans 3" font-size="11" fill="{COLORS['text_primary']}">
            {SWEDISH_LABELS["svg_decomposition"]}</text>

        <!-- Arrow marker definition -->
        <defs>
            <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5"
                    markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 0 L 10 5 L 0 10 z" fill="{COLORS['accent']}" />
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
# Section 4: Variabler & vikter (regression coefficients as bars)
# ---------------------------------------------------------------------------

main_coefs = coef_df[coef_df["spec"] == "main"].copy()

# Map code names to Swedish display labels
_VAR_LABEL_MAP = {
    "unemployment_rate": SWEDISH_LABELS["var_unemployment"],
    "dependency_ratio": SWEDISH_LABELS["var_dependency"],
    "population_growth_pct": SWEDISH_LABELS["var_population"],
    "edu_share": SWEDISH_LABELS["var_education"],
}

main_coefs["label"] = main_coefs["variable"].map(_VAR_LABEL_MAP)
main_coefs = main_coefs.sort_values("coefficient")

# Significance stars
def _sig_star(p: float) -> str:
    if p < 0.001:
        return " ***"
    if p < 0.01:
        return " **"
    if p < 0.05:
        return " *"
    return ""

main_coefs["star"] = main_coefs["p_value"].apply(_sig_star)

# Round coefficients for display (2 decimals preserves the message)
main_coefs["coef_rounded"] = main_coefs["coefficient"].round(2)

# Build horizontal bar chart
fig_coefs = go.Figure()

bar_colors = [
    COLORS["low_risk"] if c >= 0 else COLORS["high_risk"]
    for c in main_coefs["coef_rounded"]
]

fig_coefs.add_trace(
    go.Bar(
        x=main_coefs["coef_rounded"],
        y=main_coefs["label"],
        orientation="h",
        marker_color=bar_colors,
        marker_line_width=0,
        text=[
            f"{c:+.2f}{s}"
            for c, s in zip(main_coefs["coef_rounded"], main_coefs["star"])
        ],
        textposition="outside",
        textfont={"family": "IBM Plex Mono", "size": 12, "color": COLORS["text_primary"]},
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Koefficient: %{x:+.2f}<br>"
            "<extra></extra>"
        ),
    )
)

fig_coefs.add_vline(
    x=0, line_width=1, line_color=COLORS["border"],
)

layout = get_chart_layout(
    height=280,
    xaxis_title=SWEDISH_LABELS["axis_coefficient"],
    showlegend=False,
)
layout["yaxis"]["tickfont"] = {
    "family": "Source Sans 3, sans-serif",
    "size": 13,
    "color": COLORS["text_primary"],
}
layout["margin"]["l"] = 220
layout["margin"]["r"] = 80
layout["bargap"] = 0.35
fig_coefs.update_layout(**layout)

with st.container(border=True):
    st.html(card_header(SWEDISH_LABELS["landing_vars_title"], tag=SWEDISH_LABELS["method_period"]))
    st.html(f'<div class="shai-explanation">{SWEDISH_LABELS["landing_vars_explanation"]}</div>')
    st.plotly_chart(fig_coefs, use_container_width=True, config={"displayModeBar": False})

    # Show all coefficient values in a table for clarity
    _sig_label = lambda p: "***" if p < 0.001 else ("**" if p < 0.01 else ("*" if p < 0.05 else "ej sign."))
    _interp = {
        "unemployment_rate": "1 procentenhets ökning i arbetslöshet ger ca {v} procentenheter tillväxt",
        "dependency_ratio": "0,1 ökning i försörjningskvot ger ca {v} procentenheter tillväxt",
        "population_growth_pct": "1 procentenhets befolkningstillväxt ger ca {v} procentenheter tillväxt",
        "edu_share": "1 procentenhets ökning i utbildningsandel ger ca {v} procentenheter tillväxt",
    }
    coef_table_data = []
    for _, row in main_coefs.iterrows():
        var_name = row["variable"]
        coef_val = row["coefficient"]
        if var_name == "dependency_ratio":
            effect_str = f"{coef_val / 10:+.3f}".replace(".", ",")
        else:
            effect_str = f"{coef_val:+.3f}".replace(".", ",")
        interp_template = _interp.get(var_name, "")
        interp_text = interp_template.format(v=effect_str) if interp_template else ""
        coef_table_data.append({
            SWEDISH_LABELS["vars_table_variable"]: row["label"],
            SWEDISH_LABELS["vars_table_coef"]: f"{coef_val:+.4f}".replace(".", ","),
            SWEDISH_LABELS["vars_table_sig"]: _sig_label(row["p_value"]),
            SWEDISH_LABELS["vars_table_interpretation"]: interp_text,
        })
    st.dataframe(
        pd.DataFrame(coef_table_data),
        use_container_width=True,
        hide_index=True,
    )

    with st.expander(SWEDISH_LABELS["landing_vars_expander"]):
        st.markdown(SWEDISH_LABELS["landing_vars_example"])
    with st.expander(SWEDISH_LABELS["explain_coef_chart_expander"]):
        st.markdown(SWEDISH_LABELS["explain_coef_chart_text"])

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
