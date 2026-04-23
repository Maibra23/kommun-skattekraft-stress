"""Streamlit page 2 — National overview (Riksöversikt).

Configures the page with st.set_page_config (title 'KSS · Riksöversikt',
layout='wide'), injects CSS, and renders the sidebar.  Page sections:
  1. KPI row (4 cards): median prognos 2025, kommuner i hög risk,
     största nedgång with kommune name, modellens R²
  2. Geografisk fördelning: full-width Folium choropleth map (3:2 split with
     histogram on right) showing vulnerability_score per municipality
  3. Histogram: distribution of predicted_growth_2025 across 290 municipalities
  4. Rangordning: sortable table of all 290 municipalities with CSV download

All data loaded from precomputed artifacts using @st.cache_data.
All Swedish strings come from SWEDISH_LABELS in src/ui/labels.py.
"""
