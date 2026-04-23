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
