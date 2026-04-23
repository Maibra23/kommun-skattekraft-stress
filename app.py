"""Streamlit entry point — Landing page (Översikt).

Configures the page with st.set_page_config (title 'KSS · Översikt',
layout='wide'), injects the global CSS, and renders the sidebar.  Page
sections (in order):
  1. Hero block with navy gradient and gold accent border
  2. Stat strip: 290 KOMMUNER · 15 ÅR PANEL · 4 STRUKTURVARIABLER · FIXED EFFECTS
  3. Modellöversikt: SVG flow diagram showing inputs → regression → outputs
  4. Variabler & vikter: regression coefficients from artifacts/coefficients.parquet
  5. Pipeline steps: Datainsamling → Rensning → Estimering → Prognos
  6. Navigation cards linking to Riksöversikt and Kommunjämförelse
  7. Källor & metod credibility block

All Swedish strings come from SWEDISH_LABELS in src/ui/labels.py.
"""
