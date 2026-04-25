# Kommunal Skattekraft Stress Monitor

En modell över skattekraftens utveckling i Sveriges 290 kommuner, med prognoser och strukturell dekomponering.

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://kommun-skattekraft-stress.streamlit.app)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)

---

## Abstract

A two-way fixed-effects panel model of Swedish municipal tax base growth, with predictive vulnerability ranking and structural decomposition, delivered as a Streamlit dashboard. The panel covers 290 municipalities × 15 years (2010–2024) using four structural drivers: unemployment rate, dependency ratio, population growth, and tertiary education share. Predicted 2025 growth and vulnerability ranks are precomputed and served as Parquet artifacts — no model estimation runs in the browser.

---

## Om projektet

Skattekraften — beskattningsbar förvärvsinkomst per invånare — är det centrala måttet på en kommuns skattemässiga kapacitet. Skillnaderna mellan kommuner är enorma: Danderyd rapporterade ca 481 000 kr per invånare 2024, medan flera Norrlandskommuner låg under 180 000 kr.

Det här projektet bygger en panelmodell (tvåvägs fixed effects) som identifierar vilka kommuner som har den svagaste prognosticerade skattekraftstillväxten och vilka strukturella faktorer som driver variationen. Resultaten levereras som en interaktiv Streamlit-dashboard med tre sidor: en översikt, en nationell kartvy med rangordning, och en kommundetaljsida med strukturell dekomponering.

**Målgrupp:** Kreditanalytiker, kommunala controllers, SKR-analytiker, regionala beslutsfattare.

---

## Skärmdumpar

> *Skärmdumpar läggs till efter driftsättning på Streamlit Cloud.*

| Översikt | Riksöversikt | Kommunjämförelse |
|:---:|:---:|:---:|
| ![Översikt](docs/screenshots/landing.png) | ![Riksöversikt](docs/screenshots/riksoversikt.png) | ![Kommunjämförelse](docs/screenshots/kommunjamforelse.png) |

---

## Modell

Regressionsspecifikation (tvåvägs fixed effects):

```
ΔSkattekraft_it = α_i + γ_t + β₁·Arbetslöshet_it + β₂·Försörjningskvot_it
                  + β₃·Befolkningstillväxt_it + β₄·Utbildningsandel_it + ε_it
```

Där *i* indexerar kommun (290), *t* indexerar år (2010–2024). Standardfel klustrade på kommunnivå. Estimerad med `linearmodels.PanelOLS`.

**Sårbarhetsindex:** Prognosticerad tillväxt 2025 standardiseras (z-poäng, teckenvänd så högt = sårbar). Nedre kvintilen (58 kommuner) klassas som "Hög risk".

Se [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md) för fullständig metodbeskrivning inklusive robusthetsanalyser och begränsningar.

---

## Datakällor

| Källa | Tabell-ID | Variabel | Period |
|---|---|---|---|
| SCB Statistikdatabasen | OE0101 | Skattekraft per invånare | 2009–2024 |
| SCB Statistikdatabasen | BE0101 | Folkmängd (ålder, kön) | 2009–2024 |
| SCB Statistikdatabasen | AA0003 | Öppen arbetslöshet (STATIV) | 2010–2024 |
| SCB Statistikdatabasen | UF0506 | Utbildningsnivå | 2010–2024 |
| okfse/sweden-geojson | — | Kommungränser (GeoJSON) | 2024 |

Se [`docs/KRI_Dataset_Identification.md`](docs/KRI_Dataset_Identification.md) för detaljerad datarevision med API-endpoints, query-parametrar och validering.

---

## Köra lokalt

### Förutsättningar

- Python 3.11
- Git

### Installation

```bash
git clone https://github.com/mustafa-2024/kommun-skattekraft-stress.git
cd kommun-skattekraft-stress
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### Kör datapipelinen

Pipelinen hämtar data från SCB:s API, rensar, estimerar modellen och genererar alla artefakter:

```bash
python pipeline.py
```

### Starta dashboarden

```bash
streamlit run app.py
```

Öppna `http://localhost:8501` i webbläsaren.

### Kör tester

```bash
pytest
```

---

## Filstruktur

```
kommun-skattekraft-stress/
├── app.py                          # Startsida (Översikt)
├── pipeline.py                     # Orkestrerar fetch → clean → estimate → predict → decompose
├── pages/
│   ├── 01_Riksoversikt.py          # Nationell vy med karta och rangordning
│   └── 02_Kommunjamforelse.py      # Kommundetalj med dekomponering
├── src/
│   ├── fetch/                      # SCB PxWeb API-klienter
│   │   ├── pxweb_client.py         # Generisk POST + chunking
│   │   ├── fetch_skattekraft.py    # OE0101
│   │   ├── fetch_population.py     # BE0101 (med per-års-chunkning)
│   │   ├── fetch_unemployment.py   # AA0003 (tvåtabellssplitsa)
│   │   └── fetch_education.py      # UF0506
│   ├── clean/                      # Harmonisering och härledda variabler
│   │   ├── harmonize_kommunkod.py  # Kommunkodsmapping till 2024 gränser
│   │   ├── compute_derived.py      # Försörjningskvot, tillväxttakt
│   │   └── build_panel.py          # Bygg balanserad 290×15 panel
│   ├── model/                      # Ekonometri
│   │   ├── estimate.py             # PanelOLS med robusthetsspecifikationer
│   │   ├── predict.py              # Prognos 2025
│   │   └── decompose.py            # Strukturell dekomponering
│   └── ui/                         # Streamlit-komponenter
│       ├── css.py                  # Designsystem (färger, typografi, CSS)
│       ├── components.py           # KPI-kort, sidtitel, footer
│       ├── sidebar.py              # Gemensam sidebar
│       ├── chart_theme.py          # Plotly-tema
│       ├── choropleth.py           # Folium-karta
│       └── labels.py               # SWEDISH_LABELS + nummerformatering
├── artifacts/                      # Förberäknade resultat (laddas av Streamlit)
│   ├── model_results.pkl           # Fitted PanelOLS-objekt
│   ├── coefficients.parquet        # Regressionskoefficienter
│   ├── predictions.parquet         # 290 kommuner × prognos 2025
│   ├── decomposition.parquet       # Strukturell bidragsanalys
│   └── ranking.parquet             # Sårbarhetsrankning
├── data/
│   ├── raw/                        # Cachade SCB-svar (JSON)
│   ├── processed/panel.parquet     # Rensad 290×15 panel
│   ├── geo/kommuner.geojson        # Kommungränser
│   └── lookup/                     # Statisk kommunkodsmapping
├── tests/                          # pytest-tester
├── docs/                           # Dokumentation
│   ├── PRD.md                      # Produktkrav (låst specifikation)
│   ├── TASKS.md                    # Implementeringsuppgifter
│   ├── METHODOLOGY.md              # Ekonometrisk metod
│   └── KRI_Dataset_Identification.md  # Datakällrevision
└── notebooks/
    └── 01_exploratory.ipynb        # EDA
```

---

## Begränsningar

Modellen har flera kända begränsningar, dokumenterade i [`docs/METHODOLOGY.md` §7](docs/METHODOLOGY.md#7-limitations-and-caveats):

- **Låg R²(within)** (~0,8 %) — förväntat efter tvåvägs demeaning; år-fixed effects absorberar >95 % av variationen
- **Befolkningstillväxtens negativa koefficient** — reflekterar within-entity-dynamik (tillfällig per-capita-utspädning), inte tvärsnittssamband
- **Simultaneitet** — tvåvägs FE adresserar inte omvänd kausalitet
- **Nominell skattekraft** — inkluderar inflation, inte realt justerad
- **Utbildningsandel insignifikant** — för lite within-variation under 15-årsperioden

---

## Källor

- SCB Statistikdatabasen: [statistikdatabasen.scb.se](https://www.statistikdatabasen.scb.se/)
  - [OE0101 — Skattekraft](https://www.statistikdatabasen.scb.se/pxweb/sv/ssd/START__OE__OE0101/SkatteKraft/)
  - [BE0101 — Folkmängd](https://www.statistikdatabasen.scb.se/pxweb/sv/ssd/START__BE__BE0101__BE0101A/BefolkningNy/)
  - [AA0003 — Öppen arbetslöshet](https://www.statistikdatabasen.scb.se/pxweb/sv/ssd/START__AA__AA0003/)
  - [UF0506 — Utbildningsnivå](https://www.statistikdatabasen.scb.se/pxweb/sv/ssd/START__UF__UF0506__UF0506B/Utbildning/)
- Kommungränser: [okfse/sweden-geojson](https://github.com/okfse/sweden-geojson)

---

## Licens

MIT — se [LICENSE](LICENSE).
