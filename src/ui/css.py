"""Color tokens, global CSS string, and inject_css() helper for Streamlit pages.

Defines the COLORS dict (primary navy, accent gold, risk-level colors, and
neutral palette), DIVERGING_SCALE and CHART_PALETTE lists, and GLOBAL_CSS
which imports Source Sans 3 and IBM Plex Mono from Google Fonts and applies
the design system layout rules.  The inject_css() function injects GLOBAL_CSS
via st.html().

Note: CSS class names use the 'shai-' prefix for visual fidelity to the SHAI
reference design; only the brand mark is replaced with 'KSS'.
"""

import streamlit as st

# ---------------------------------------------------------------------------
# Color tokens (PRD §6.1, locked)
# ---------------------------------------------------------------------------

COLORS = {
    "primary": "#0B1F3F",  # Navy — sidebar, KPI bars, hero
    "primary_light": "#1B2A4A",  # Lighter navy — hero gradient mid
    "secondary": "#4A6FA5",  # Blue — chart series 1
    "accent": "#C4A35A",  # Gold — eyebrows, brand bar, active
    "low_risk": "#2E7D5B",  # Green — låg risk
    "medium_risk": "#D4A03C",  # Amber — medel risk
    "high_risk": "#B94A48",  # Red — hög risk
    "bg": "#F7F8FA",
    "card_bg": "#FFFFFF",
    "text_primary": "#1A1A2E",
    "text_secondary": "#6B7280",
    "text_tertiary": "#9CA3AF",
    "border": "#EEF0F3",
    "grid": "#E5E7EB",
    "hover": "#F9FAFB",
}

DIVERGING_SCALE = [
    "#2E7D5B",
    "#5B9E78",
    "#A8C4A4",
    "#E5E7EB",
    "#E8BE7C",
    "#D4A03C",
    "#B94A48",
]

CHART_PALETTE = [
    "#4A6FA5",
    "#2E7D5B",
    "#C4A35A",
    "#B94A48",
    "#7B68A8",
    "#D4785A",
    "#3D8B6E",
    "#5A7FBD",
]

# ---------------------------------------------------------------------------
# Global CSS (PRD §6.2, §6.3)
# ---------------------------------------------------------------------------

GLOBAL_CSS = """
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Source+Sans+3:wght@300;400;600;700&display=swap');

:root {
    --color-primary: %(primary)s;
    --color-primary-light: %(primary_light)s;
    --color-secondary: %(secondary)s;
    --color-accent: %(accent)s;
    --color-low-risk: %(low_risk)s;
    --color-medium-risk: %(medium_risk)s;
    --color-high-risk: %(high_risk)s;
    --color-bg: %(bg)s;
    --color-card-bg: %(card_bg)s;
    --color-text-primary: %(text_primary)s;
    --color-text-secondary: %(text_secondary)s;
    --color-text-tertiary: %(text_tertiary)s;
    --color-border: %(border)s;
    --color-grid: %(grid)s;
    --color-hover: %(hover)s;
    --font-sans: 'Source Sans 3', sans-serif;
    --font-mono: 'IBM Plex Mono', monospace;
}

/* ---- Hide Streamlit chrome ---- */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header[data-testid="stHeader"] {display: none;}
div[data-testid="stDecoration"] {display: none;}
div[data-testid="stToolbar"] {display: none;}

/* ---- Hide auto-generated sidebar page navigation ---- */
div[data-testid="stSidebarNav"] {display: none !important;}
section[data-testid="stSidebar"] > div > div > div > ul {display: none !important;}
section[data-testid="stSidebar"] nav {display: none !important;}

/* ---- Base layout ---- */
.main .block-container {
    padding: 32px 40px !important;
    max-width: 1480px !important;
}

section[data-testid="stSidebar"] {
    width: 260px !important;
    min-width: 260px !important;
    max-width: 260px !important;
    background-color: var(--color-primary) !important;
    transform: none !important;
    transition: none !important;
}

/* Prevent sidebar from collapsing: hide toggle buttons */
button[data-testid="stSidebarCollapse"],
button[data-testid="baseButton-headerNoPadding"],
section[data-testid="stSidebar"] button[kind="headerNoPadding"],
div[data-testid="collapsedControl"] {
    display: none !important;
}

/* Keep sidebar always visible even in collapsed state */
section[data-testid="stSidebar"][aria-expanded="false"] {
    display: block !important;
    width: 260px !important;
    min-width: 260px !important;
    margin-left: 0 !important;
    transform: none !important;
}

section[data-testid="stSidebar"] .block-container {
    padding-top: 0 !important;
}

/* Force all sidebar text to be light on navy background */
section[data-testid="stSidebar"],
section[data-testid="stSidebar"] * {
    color: rgba(255, 255, 255, 0.65) !important;
}

section[data-testid="stSidebar"] .shai-brand-mark {
    color: var(--color-accent) !important;
}

section[data-testid="stSidebar"] .shai-brand-title {
    color: #FFFFFF !important;
}

section[data-testid="stSidebar"] .shai-sidebar-nav a.active {
    color: var(--color-primary) !important;
}

/* ---- Typography ---- */
html, body, [class*="css"] {
    font-family: var(--font-sans) !important;
    color: var(--color-text-primary);
}

/* ---- Hero block ---- */
.shai-hero {
    background: linear-gradient(135deg, var(--color-primary) 0%%, var(--color-primary-light) 100%%);
    border-left: 4px solid var(--color-accent);
    border-radius: 4px;
    padding: 36px 40px;
    margin-bottom: 24px;
    color: #FFFFFF;
}

.shai-hero .shai-eyebrow {
    font-family: var(--font-sans);
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: var(--color-accent);
    margin-bottom: 8px;
}

.shai-hero h1 {
    font-family: var(--font-sans);
    font-size: clamp(24px, 3vw, 36px);
    font-weight: 700;
    color: #FFFFFF;
    margin: 0 0 12px 0;
    line-height: 1.2;
}

.shai-hero .shai-lead {
    font-family: var(--font-sans);
    font-size: 15px;
    font-weight: 300;
    color: rgba(255, 255, 255, 0.85);
    line-height: 1.6;
    max-width: 720px;
}

/* ---- Page title block ---- */
.shai-page-title {
    margin-bottom: 24px;
}

.shai-page-title .shai-eyebrow {
    font-family: var(--font-sans);
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: var(--color-accent);
    margin-bottom: 4px;
}

.shai-page-title h1 {
    font-family: var(--font-sans);
    font-size: 28px;
    font-weight: 700;
    color: var(--color-text-primary);
    margin: 0 0 4px 0;
}

.shai-page-title .shai-subtitle {
    font-family: var(--font-sans);
    font-size: 14px;
    color: var(--color-text-secondary);
}

.shai-page-title .shai-year {
    font-family: var(--font-mono);
    font-size: 13px;
    font-weight: 500;
    color: var(--color-accent);
    float: right;
    margin-top: -38px;
}

/* ---- KPI card ---- */
.shai-kpi {
    background: var(--color-card-bg);
    border: 1px solid var(--color-border);
    border-radius: 4px;
    padding: 18px 20px;
    position: relative;
    border-left: 3px solid var(--color-primary);
}

.shai-kpi.variant-danger {
    border-left-color: var(--color-high-risk);
}

.shai-kpi.variant-success {
    border-left-color: var(--color-low-risk);
}

.shai-kpi .shai-kpi-label {
    font-family: var(--font-sans);
    font-size: 10.5px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--color-text-secondary);
    margin-bottom: 6px;
}

.shai-kpi .shai-kpi-value {
    font-family: var(--font-sans);
    font-size: 32px;
    font-weight: 700;
    color: var(--color-text-primary);
    font-variant-numeric: tabular-nums;
    line-height: 1.1;
}

.shai-kpi .shai-kpi-delta {
    font-family: var(--font-mono);
    font-size: 12px;
    font-weight: 500;
    margin-top: 6px;
}

.shai-kpi .shai-kpi-delta.delta-up {
    color: var(--color-low-risk);
}

.shai-kpi .shai-kpi-delta.delta-down {
    color: var(--color-high-risk);
}

.shai-kpi .shai-kpi-delta.delta-flat {
    color: var(--color-text-tertiary);
}

/* ---- Card ---- */
.shai-card {
    background: var(--color-card-bg);
    border: 1px solid var(--color-border);
    border-radius: 4px;
    padding: 22px 24px;
    margin-bottom: 24px;
}

.shai-card-header {
    border-bottom: 1px solid var(--color-border);
    padding-bottom: 12px;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.shai-card-header h3 {
    font-family: var(--font-sans);
    font-size: 15px;
    font-weight: 700;
    color: var(--color-text-primary);
    margin: 0;
}

.shai-card-header .shai-tag {
    font-family: var(--font-mono);
    font-size: 10px;
    font-weight: 500;
    color: var(--color-text-tertiary);
    background: var(--color-bg);
    padding: 2px 8px;
    border-radius: 3px;
}

.shai-card-header .shai-subtitle {
    font-family: var(--font-sans);
    font-size: 12px;
    color: var(--color-text-secondary);
    margin-top: 2px;
}

/* ---- Risk pill ---- */
.shai-pill {
    display: inline-block;
    font-family: var(--font-sans);
    font-size: 11px;
    font-weight: 600;
    padding: 3px 10px;
    border-radius: 12px;
    text-transform: capitalize;
}

.shai-pill.risk-lag {
    background: rgba(46, 125, 91, 0.12);
    color: var(--color-low-risk);
}

.shai-pill.risk-medel {
    background: rgba(212, 160, 60, 0.12);
    color: var(--color-medium-risk);
}

.shai-pill.risk-hog {
    background: rgba(185, 74, 72, 0.12);
    color: var(--color-high-risk);
}

/* ---- Stat strip ---- */
.shai-stat-strip {
    display: flex;
    gap: 0;
    margin-bottom: 24px;
}

.shai-stat-cell {
    flex: 1;
    text-align: center;
    padding: 16px 12px;
    background: var(--color-card-bg);
    border: 1px solid var(--color-border);
    border-right: none;
}

.shai-stat-cell:first-child {
    border-radius: 4px 0 0 4px;
}

.shai-stat-cell:last-child {
    border-right: 1px solid var(--color-border);
    border-radius: 0 4px 4px 0;
}

.shai-stat-cell .shai-stat-value {
    font-family: var(--font-mono);
    font-size: 22px;
    font-weight: 500;
    color: var(--color-text-primary);
    display: block;
}

.shai-stat-cell .shai-stat-label {
    font-family: var(--font-sans);
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--color-text-tertiary);
    margin-top: 4px;
    display: block;
}

/* ---- Pipeline steps ---- */
.shai-pipeline {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0;
    margin: 24px 0;
    flex-wrap: wrap;
}

.shai-pipeline-step {
    text-align: center;
    padding: 14px 20px;
    background: var(--color-card-bg);
    border: 1px solid var(--color-border);
    border-radius: 4px;
    min-width: 140px;
}

.shai-pipeline-step .shai-step-num {
    font-family: var(--font-mono);
    font-size: 10px;
    color: var(--color-accent);
    display: block;
    margin-bottom: 4px;
}

.shai-pipeline-step .shai-step-label {
    font-family: var(--font-sans);
    font-size: 13px;
    font-weight: 600;
    color: var(--color-text-primary);
}

.shai-pipeline-arrow {
    font-size: 20px;
    color: var(--color-accent);
    padding: 0 8px;
}

/* ---- Navigation card ---- */
.shai-nav-card {
    background: var(--color-card-bg);
    border: 1px solid var(--color-border);
    border-radius: 4px;
    padding: 20px 24px;
    transition: border-color 0.2s;
    cursor: pointer;
}

.shai-nav-card:hover {
    border-color: var(--color-accent);
}

.shai-nav-card h4 {
    font-family: var(--font-sans);
    font-size: 15px;
    font-weight: 700;
    color: var(--color-text-primary);
    margin: 0 0 6px 0;
}

.shai-nav-card p {
    font-family: var(--font-sans);
    font-size: 13px;
    color: var(--color-text-secondary);
    margin: 0;
    line-height: 1.5;
}

/* ---- Source pills ---- */
.shai-source-pill {
    display: inline-block;
    font-family: var(--font-mono);
    font-size: 10.5px;
    font-weight: 500;
    color: var(--color-text-secondary);
    background: var(--color-bg);
    border: 1px solid var(--color-border);
    padding: 4px 12px;
    border-radius: 12px;
    margin: 3px 4px;
}

/* ---- Footer ---- */
.shai-footer {
    text-align: center;
    padding: 20px 0 8px 0;
    margin-top: 32px;
    border-top: 1px solid var(--color-border);
}

.shai-footer .shai-footer-source {
    font-family: var(--font-sans);
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--color-text-tertiary);
}

.shai-footer .shai-footer-version {
    font-family: var(--font-mono);
    font-size: 10px;
    color: var(--color-text-tertiary);
    background: var(--color-bg);
    padding: 2px 8px;
    border-radius: 3px;
    margin-left: 8px;
}

/* ---- Table styling ---- */
div[data-testid="stDataFrame"] th {
    font-family: var(--font-sans) !important;
    font-size: 10.5px !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
}

div[data-testid="stDataFrame"] td {
    font-family: var(--font-mono) !important;
    font-size: 12px !important;
}

/* ---- Sidebar styling ---- */
.shai-sidebar-brand {
    padding: 20px 16px 16px 16px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    margin-bottom: 16px;
}

.shai-sidebar-brand .shai-brand-bar {
    width: 32px;
    height: 3px;
    background: var(--color-accent);
    margin-bottom: 12px;
}

.shai-sidebar-brand .shai-brand-mark {
    font-family: var(--font-mono);
    font-size: 14px;
    font-weight: 500;
    color: var(--color-accent);
    letter-spacing: 2px;
}

.shai-sidebar-brand .shai-brand-title {
    font-family: var(--font-sans);
    font-size: 16px;
    font-weight: 700;
    color: #FFFFFF;
    margin-top: 4px;
}

.shai-sidebar-brand .shai-brand-sub {
    font-family: var(--font-sans);
    font-size: 11px;
    color: rgba(255, 255, 255, 0.5);
}

.shai-sidebar-nav a {
    display: block;
    font-family: var(--font-sans);
    font-size: 13px;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.65);
    padding: 8px 16px;
    text-decoration: none;
    border-radius: 4px;
    margin-bottom: 2px;
    transition: all 0.15s;
}

.shai-sidebar-nav a:hover {
    color: #FFFFFF;
    background: rgba(255, 255, 255, 0.06);
}

.shai-sidebar-nav a.active {
    color: var(--color-primary);
    background: var(--color-accent);
}

.shai-sidebar-section-label {
    font-family: var(--font-sans);
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: rgba(255, 255, 255, 0.35);
    padding: 12px 16px 6px 16px;
}

.shai-sidebar-footer {
    padding: 16px;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
    margin-top: 16px;
}

.shai-sidebar-footer p {
    font-family: var(--font-sans);
    font-size: 10px;
    color: rgba(255, 255, 255, 0.35);
    margin: 0 0 4px 0;
    line-height: 1.5;
}

.shai-sidebar-footer .shai-footer-version {
    font-family: var(--font-mono);
    font-size: 9px;
    color: rgba(255, 255, 255, 0.25);
    background: rgba(255, 255, 255, 0.05);
    padding: 2px 6px;
    border-radius: 3px;
}

/* ---- Risk legend ---- */
.shai-risk-legend {
    padding: 8px 16px;
}

.shai-risk-legend-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 3px 0;
}

.shai-risk-legend-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%%;
    flex-shrink: 0;
}

.shai-risk-legend-label {
    font-family: var(--font-sans);
    font-size: 11px;
    color: rgba(255, 255, 255, 0.6);
}

/* ---- Coefficient bars ---- */
.shai-coef-bar-container {
    margin: 6px 0;
}

.shai-coef-bar-label {
    font-family: var(--font-sans);
    font-size: 12px;
    color: var(--color-text-primary);
    margin-bottom: 3px;
}

.shai-coef-bar-meta {
    font-family: var(--font-mono);
    font-size: 11px;
    color: var(--color-text-secondary);
    margin-top: 2px;
}

/* ---- Sidebar pills (st.pills year / risk filter) ---- */
section[data-testid="stSidebar"] div[data-testid="stPills"] button {
    font-family: var(--font-mono) !important;
    font-size: 11px !important;
    font-weight: 500 !important;
    color: rgba(255, 255, 255, 0.65) !important;
    background: transparent !important;
    border: 1px solid rgba(255, 255, 255, 0.12) !important;
    border-radius: 4px !important;
    padding: 4px 10px !important;
    transition: all 0.15s;
}

section[data-testid="stSidebar"] div[data-testid="stPills"] button:hover {
    color: #FFFFFF !important;
    background: rgba(255, 255, 255, 0.06) !important;
    border-color: rgba(255, 255, 255, 0.2) !important;
}

section[data-testid="stSidebar"] div[data-testid="stPills"] button[aria-checked="true"],
section[data-testid="stSidebar"] div[data-testid="stPills"] button[data-selected="true"] {
    color: var(--color-primary) !important;
    background: var(--color-accent) !important;
    border-color: var(--color-accent) !important;
    font-weight: 500 !important;
}

/* ---- Sidebar st.page_link styling ---- */
section[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"] {
    font-family: var(--font-sans) !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    color: rgba(255, 255, 255, 0.65) !important;
    padding: 8px 16px !important;
    border-radius: 4px !important;
    text-decoration: none !important;
    transition: all 0.15s;
}

section[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"]:hover {
    color: #FFFFFF !important;
    background: rgba(255, 255, 255, 0.06) !important;
}

/* ---- Sidebar label colors ---- */
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] .stSelectbox label {
    color: rgba(255, 255, 255, 0.5) !important;
}

/* ---- Download button styling ---- */
button[data-testid="stDownloadButton"] {
    font-family: var(--font-sans) !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    border: 1px solid var(--color-border) !important;
    border-radius: 4px !important;
}

/* ---- Selectbox on kommun page ---- */
div[data-testid="stSelectbox"] label {
    font-family: var(--font-sans) !important;
    font-size: 10.5px !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.5px !important;
    color: var(--color-text-secondary) !important;
}

/* ---- Link button styling ---- */
a[data-testid="stLinkButton"] {
    font-family: var(--font-sans) !important;
    font-size: 13px !important;
    font-weight: 600 !important;
}

/* ---- Summary text box ---- */
.shai-summary {
    font-family: var(--font-sans);
    font-size: 14px;
    color: var(--color-text-secondary);
    background: var(--color-bg);
    border-left: 3px solid var(--color-accent);
    padding: 14px 20px;
    margin-bottom: 24px;
    border-radius: 0 4px 4px 0;
    line-height: 1.6;
}

/* ---- Explanation text ---- */
.shai-explanation {
    font-family: var(--font-sans);
    font-size: 13px;
    color: var(--color-text-secondary);
    margin-bottom: 12px;
    line-height: 1.5;
}

/* ---- Accessibility: reduced motion ---- */
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        transition-duration: 0.01ms !important;
        animation-duration: 0.01ms !important;
    }
}
""" % COLORS


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def inject_css() -> None:
    """Inject the global CSS stylesheet into the current Streamlit page.

    Must be called once at the top of every page, after st.set_page_config().
    Uses st.html() to write a <style> block.
    """
    st.html(f"<style>{GLOBAL_CSS}</style>")
