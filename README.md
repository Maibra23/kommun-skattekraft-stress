# Kommunal Skattekraft Stress Monitor

En modell över skattekraftens utveckling i Sveriges 290 kommuner, med prognoser och strukturell dekomponering.

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://your-app-url.streamlit.app)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Abstract

A two-way fixed-effects panel model of Swedish municipal tax base growth, with predictive vulnerability ranking and structural decomposition, delivered as a Streamlit dashboard.
Panel covers 290 municipalities × 15 years (2010–2024) using four structural drivers: unemployment, dependency ratio, population growth, and education share.
Predicted 2025 growth and vulnerability ranks are precomputed and served as Parquet artifacts; no model estimation runs in the browser.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python pipeline.py          # fetch → clean → estimate → predict → decompose
streamlit run app.py
```

## Project structure

See `docs/PRD.md` §3 for the authoritative folder layout.

## Data sources

- SCB OE0101 — Skattekraft per invånare
- SCB BE0101 — Folkmängd
- SCB AA0003 — Öppen arbetslöshet (STATIV)
- SCB UF0506 — Utbildningsnivå

## Docs

- `docs/PRD.md` — Product requirements (locked specification)
- `docs/TASKS.md` — Implementation task list
- `docs/METHODOLOGY.md` — Econometric methodology
- `docs/KRI_Dataset_Identification.md` — Data source audit
