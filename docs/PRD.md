# PRD.md — Product Requirements Document

**Project:** Kommunal Skattekraft Stress Monitor
**Repository name:** `kommun-skattekraft-stress`
**Status:** Locked specification, ready for implementation
**Owner:** [your name]
**Target completion:** 5 working days
**Deployment target:** Streamlit Community Cloud (public)

---

## Purpose of This Document

This is the master reference file that Cursor and Claude Code load as project context for every task. Every prompt in `TASKS.md` references sections of this document. If a design decision is not in this PRD, it is not part of the project.

**Two layer language rule (enforced everywhere):**

* **Code layer (developer reads):** All English. Variable names, function names, file names, comments, docstrings, log messages, exception messages, all four documentation files. Example: `tax_base_growth_pct`, `fetch_skattekraft()`, `data_fetcher.py`.
* **User layer (dashboard user sees):** All Swedish. Page titles, chart axes, tooltips, table headers, sidebar labels, buttons, error messages shown in the UI. Example: "Skattekraft per invånare (kr)", "Riskklass", "Inga data tillgängliga för den valda perioden". Enforced through the `SWEDISH_LABELS` dictionary in section 9.

---

## 1. Project Identity

**One-line description (English, for README/repo):**
A two-way fixed-effects panel model of Swedish municipal tax base growth, with predictive vulnerability ranking and structural decomposition, delivered as a Streamlit dashboard.

**One-line description (Swedish, for landing page hero):**
"En modell över skattekraftens utveckling i Sveriges 290 kommuner, med prognoser och strukturell dekomponering."

**Research question:** Which Swedish kommuner have the weakest predicted tax base growth in the next year, and which structural factors drive both kommun and aggregate variation?

**Target audience:** Bank credit analysts, kommun controllers, SKR analysts, regional policy makers, hiring managers reviewing portfolio.

**Target hiring roles:** ekonom, statistiker, controller, bankrådgivare, dataanalys (Sweden).

---

## 2. Tech Stack

| Layer | Technology | Version constraint | Reason |
|---|---|---|---|
| Language | Python | 3.11 (>=3.11,<3.12) | Streamlit Cloud compatibility, modern typing |
| Data fetching | `requests` | latest | direct pxweb control |
| Data manipulation | `pandas`, `pyarrow` | pandas >=2.0 | parquet I/O, modern API |
| Panel regression | `linearmodels` | >=6.0 | standard for two-way FE in Python |
| Dashboard | `streamlit` | >=1.30 | as specified |
| Plotting | `plotly` | >=5.0 | interactive, integrates with Streamlit |
| Map (choropleth) | `folium`, `branca`, `streamlit-folium` | latest | matches design reference, polygon-based |
| Testing | `pytest` | latest | unit tests on data harmonization |

**Excluded by design:** statsmodels (worse FE handling than linearmodels), seaborn (not needed in Streamlit context), heavy ML libraries (out of scope), live model estimation in Streamlit (precomputed artifacts pattern).

---

## 3. Folder Structure (Authoritative)

```
kommun-skattekraft-stress/
├── README.md                          # Swedish, with English abstract
├── pyproject.toml                     # dependencies, build config
├── requirements.txt                   # pinned for Streamlit Cloud
├── .gitignore
├── .streamlit/
│   └── config.toml                    # theme, server settings
├── data/
│   ├── raw/                           # cached pxweb pulls (JSON), gitignored except .gitkeep
│   ├── processed/
│   │   └── panel.parquet              # cleaned 290 x 15 panel
│   ├── geo/
│   │   └── kommuner.geojson           # boundary file from okfse/sweden-geojson
│   └── lookup/
│       └── kommunkod_harmonization.csv  # static lookup of merged/renamed kommuner
├── artifacts/                         # PRECOMPUTED outputs loaded by Streamlit
│   ├── model_results.pkl              # fitted PanelOLS object
│   ├── coefficients.parquet           # for methodology display
│   ├── predictions.parquet            # 290 kommuner x predicted 2025 growth
│   ├── decomposition.parquet          # 290 x 5 contribution columns
│   └── ranking.parquet                # vulnerability rank, sorted
├── src/
│   ├── __init__.py
│   ├── fetch/
│   │   ├── __init__.py
│   │   ├── pxweb_client.py            # generic pxweb POST + chunking
│   │   ├── fetch_skattekraft.py
│   │   ├── fetch_population.py
│   │   ├── fetch_unemployment.py
│   │   └── fetch_education.py
│   ├── clean/
│   │   ├── __init__.py
│   │   ├── harmonize_kommunkod.py
│   │   ├── compute_derived.py         # dependency_ratio, growth rates
│   │   └── build_panel.py
│   ├── model/
│   │   ├── __init__.py
│   │   ├── estimate.py                # PanelOLS fit
│   │   ├── predict.py                 # next-period predictions
│   │   └── decompose.py               # contribution accounting
│   └── ui/
│       ├── __init__.py
│       ├── css.py                     # COLORS dict, GLOBAL_CSS, inject_css()
│       ├── components.py              # page_title, kpi_card, card_header, etc.
│       ├── sidebar.py                 # render_sidebar(page_key)
│       ├── chart_theme.py             # get_chart_layout(), CHART_PALETTE
│       ├── choropleth.py              # render_choropleth()
│       └── labels.py                  # SWEDISH_LABELS dict
├── pipeline.py                        # orchestrates fetch -> clean -> model -> predict -> decompose
├── app.py                             # landing page (entry point for Streamlit)
├── pages/
│   ├── 01_Riksoversikt.py             # national overview + choropleth
│   └── 02_Kommunjamforelse.py         # kommun detail + decomposition
├── tests/
│   ├── __init__.py
│   ├── test_harmonize.py
│   └── test_decompose.py
├── docs/
│   ├── PRD.md                         # this file
│   ├── TASKS.md
│   ├── METHODOLOGY.md
│   └── KRI_Dataset_Identification.md
└── notebooks/
    └── 01_exploratory.ipynb           # Day 2 EDA, kept for reference
```

**Why this structure:** Clean separation between pipeline (run once locally, writes artifacts) and serving (Streamlit Cloud loads artifacts). Mirrors standard ML deployment pattern. Mirrors the SHAI reference structure where applicable.

---

## 4. Core Data Variables

### Dependent variable

| Code name | Swedish display | Definition | Source | pxweb table |
|---|---|---|---|---|
| `tax_base_per_capita` | "Skattekraft per invånare" | Beskattningsbar förvärvsinkomst per invånare, kr | SCB | OE0101 SkatteKraft |
| `tax_base_growth_pct` | "Skattekraftstillväxt (%)" | Year-over-year percent change, computed | derived | — |

### Independent variables

| Code name | Swedish display | Definition | Source | pxweb table |
|---|---|---|---|---|
| `unemployment_rate` | "Öppen arbetslöshet (%)" | Andel öppet arbetslösa, share of pop 20-64 registered with Arbetsförmedlingen | SCB STATIV | AA0003 |
| `dependency_ratio` | "Försörjningskvot" | (Pop 0-19 + Pop 65+) / Pop 20-64, computed | SCB BE0101 | BE0101 |
| `population_growth_pct` | "Befolkningstillväxt (%)" | Year-over-year percent change in folkmängd, computed | SCB BE0101 | BE0101 |
| `edu_share` | "Andel eftergymnasialt utbildade (%)" | Share of pop 25-64 with eftergymnasial utbildning 3+ years | SCB UF0506 | UF0506 |

### Identifiers and metadata

| Code name | Swedish display | Definition |
|---|---|---|
| `kommun_kod` | "Kommunkod" | 4-digit SCB kommun code, zero-padded, harmonized to 2024 boundaries |
| `kommun_name` | "Kommun" | Kommun name in Swedish, 2024 spelling |
| `lan_kod` | "Länskod" | 2-digit län code |
| `lan_name` | "Län" | Län name |
| `year` | "År" | Reference year, integer |

### Derived outputs (artifacts)

| Code name | Swedish display | Definition |
|---|---|---|
| `predicted_growth_2025` | "Prognos 2025 (%)" | Out-of-sample prediction for 2025 |
| `vulnerability_score` | "Sårbarhetsindex" | Standardized predicted growth (z-score, sign-flipped so high = vulnerable) |
| `vulnerability_rank` | "Rang" | Rank 1 to 290, 1 = most vulnerable |
| `risk_class` | "Riskklass" | Categorical: "lag", "medel", "hog" — bottom quintile = "hog" |
| `decomp_unemployment` | "Bidrag: arbetslöshet" | Contribution of unemployment differential to gap vs national mean |
| `decomp_dependency` | "Bidrag: försörjningskvot" | Contribution of dependency ratio differential |
| `decomp_population` | "Bidrag: befolkning" | Contribution of population growth differential |
| `decomp_education` | "Bidrag: utbildning" | Contribution of education share differential |
| `decomp_residual` | "Bidrag: residual" | Kommun fixed effect plus error |

---

## 5. Empirical Model (Locked)

```
ΔTax_base_it = α_i + γ_t + β₁·Unemployment_it + β₂·DependencyRatio_it + β₃·PopGrowth_it + β₄·EduShare_it + ε_it
```

Where i indexes kommun (290), t indexes year (2010 to 2024). Two-way fixed effects (kommun and year). Standard errors clustered at kommun level. Estimated with `linearmodels.PanelOLS(entity_effects=True, time_effects=True)`. Robustness: lagged independents, drop COVID years, larger-kommuner subsample.

**Vulnerability score for prediction (2025):**
* Use estimated betas
* Use most recent observed (2024) values of independents
* Use kommun's own fixed effect estimate
* Year fixed effect = mean of last 3 years (proxy)
* Compute predicted growth, standardize across kommuner, sign-flip so high score = high vulnerability
* Bottom quintile (58 kommuner) = "hog" risk class
* Quintiles 2–4 = "medel"
* Top quintile = "lag"

**Decomposition (gap vs national mean):**
For each kommun and each independent variable, compute (kommun value − national mean) × β. Plus residual = α_i + ε_i.

Full methodology in `METHODOLOGY.md`.

---

## 6. Design System (Adapted from SHAI Reference)

### 6.1 Color tokens (locked)

Defined in `src/ui/css.py` as `COLORS` dict:

```python
COLORS = {
    "primary":        "#0B1F3F",   # Navy — sidebar, KPI bars, hero
    "primary_light":  "#1B2A4A",   # Lighter navy — hero gradient mid
    "secondary":      "#4A6FA5",   # Blue — chart series 1
    "accent":         "#C4A35A",   # Gold — eyebrows, brand bar, active
    "low_risk":       "#2E7D5B",   # Green — låg risk
    "medium_risk":    "#D4A03C",   # Amber — medel risk
    "high_risk":      "#B94A48",   # Red — hög risk
    "bg":             "#F7F8FA",
    "card_bg":        "#FFFFFF",
    "text_primary":   "#1A1A2E",
    "text_secondary": "#6B7280",
    "text_tertiary":  "#9CA3AF",
    "border":         "#EEF0F3",
    "grid":           "#E5E7EB",
    "hover":          "#F9FAFB",
}

DIVERGING_SCALE = [
    "#2E7D5B", "#5B9E78", "#A8C4A4",
    "#E5E7EB",
    "#E8BE7C", "#D4A03C", "#B94A48",
]

CHART_PALETTE = [
    "#4A6FA5", "#2E7D5B", "#C4A35A", "#B94A48",
    "#7B68A8", "#D4785A", "#3D8B6E", "#5A7FBD",
]
```

### 6.2 Typography

Loaded via Google Fonts `@import` in `GLOBAL_CSS`:
```
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Source+Sans+3:wght@300;400;600;700&display=swap');
```

| Use | Family | Weight | Size |
|---|---|---|---|
| Page title | Source Sans 3 | 700 | 28px |
| Hero headline | Source Sans 3 | 700 | clamp(24px, 3vw, 36px) |
| Card title | Source Sans 3 | 700 | 15px |
| Eyebrow | Source Sans 3 | 600 | 11px uppercase, 1.5px tracking |
| Body | Source Sans 3 | 400 | 14–15px |
| KPI value | Source Sans 3 | 700 | 32px tabular-nums |
| Numeric data | IBM Plex Mono | 400–500 | 11–12px |
| Table headers | Source Sans 3 | 600 | 10.5px uppercase |

### 6.3 Layout

Same as SHAI reference: page padding 32px 40px, max-width 1480px, section gap 24px, card padding 22px 24px, card radius 4px, card border 1px solid #EEF0F3.

### 6.4 Streamlit setup (every page)

```python
st.set_page_config(
    page_title="KSS · <Page Name>",
    page_icon=None,
    layout="wide",
    menu_items={"Get Help": None, "Report a bug": None},
)
from src.ui.css import inject_css
inject_css()
```

**Brand mark:** "KSS" (Kommunal Skattekraft Stress) replaces SHAI in the brand block. All other CSS classes keep the `shai-` prefix for visual fidelity to the reference, but document this choice in code comments. (Renaming all CSS classes is wasted scope.)

### 6.5 Sidebar

`render_sidebar(page_key)` in `src/ui/sidebar.py`. Dimensions: 260px wide, navy background.

* Brand block: gold accent bar + "KSS" mark + title "Skattekraft Stress" + sub "Kommunal panelmodell"
* Navigation links to: Översikt (landing), Riksöversikt, Kommunjämförelse
* Year selector: `st.pills()`, single, default 2024
* Risk filter: `st.pills()`, multi, options "Hög" / "Medel" / "Låg"
* Risk legend with colored dots
* Footer: data source, last-updated date, version

### 6.6 Components

All in `src/ui/components.py`:
* `page_title(eyebrow, title, subtitle, year)` — page header
* `kpi_card(label, value, unit, delta, delta_direction, variant, tooltip)` — KPI tile
* `render_kpi_row(cards)` — equal-width column layout for KPIs
* `card_header(title, subtitle, tag)` — card top
* `card(title, subtitle, tag, content)` — full card
* `risk_pill(level)` — Låg/Medel/Hög pill
* `footer_note(source, version)` — page bottom

Delta direction semantics for skattekraft growth:
* `up` = growth, GREEN (good for kommun)
* `down` = decline, RED (bad)
* `flat` = stable, GRAY

This is **inverted from SHAI** (where rising prices = bad). Document in code.

### 6.7 Choropleth map

`src/ui/choropleth.py`. Folium polygon-based. Diverging green→neutral→red scale on `vulnerability_score`. Height 480px. Uses `data/geo/kommuner.geojson` from okfse/sweden-geojson (see KRI_Dataset_Identification.md §5).

Legend caption (Swedish): "Sårbarhetsindex · Lägre = bättre, Högre = sämre"

### 6.8 Chart theme

`get_chart_layout(title, height, xaxis_title, yaxis_title, showlegend)` in `src/ui/chart_theme.py`. Same properties as SHAI reference: Source Sans 3 12px base, white plot bg, navy hover bg, gridlines #E5E7EB.

---

## 7. Page Structure (3 Pages)

### Page 1: `app.py` — Landing (Översikt)

**Route:** `/`
**Page title:** "KSS · Översikt"
**Eyebrow:** "KOMMUNAL SKATTEKRAFT STRESS MONITOR"
**Headline:** "Skattekraftens utveckling i Sveriges 290 kommuner"
**Lead:** "En panelmodell som identifierar kommuner med svag prognosticerad skattekraftstillväxt och dekomponerar drivkrafterna bakom skillnaderna mellan kommuner."

**Sections:**
1. Hero block (navy gradient, gold border)
2. Stat strip (4 cells): "290 KOMMUNER", "15 ÅR PANEL", "4 STRUKTURVARIABLER", "FIXED EFFECTS"
3. Modellöversikt (3 input boxes → Regressionsmodell box → 3 output boxes; SVG flow)
4. Variabler & vikter (regression coefficients displayed as bars, NOT arbitrary index weights — this is the key adaptation from SHAI)
5. Pipeline steps (4 steps with arrow connectors): Datainsamling → Rensning → Estimering → Prognos
6. Navigation cards (2 cards): Riksöversikt, Kommunjämförelse
7. Källor & metod block (credibility): SCB OE0101, SCB BE0101, SCB AA0003, SCB UF0506

### Page 2: `pages/01_Riksoversikt.py` — National Overview

**Page title:** "KSS · Riksöversikt"
**Eyebrow:** "NATIONELL VY"
**Title:** "Riksöversikt"
**Subtitle:** "Skattekraftens prognosticerade utveckling 2025, alla 290 kommuner"

**Sections:**
1. KPI row (4 cards):
   * "Median prognos 2025" — predicted growth, national median
   * "Kommuner i hög risk" — count of bottom quintile
   * "Största nedgång (prognos)" — most negative predicted growth, with kommun name
   * "Modellens R²" — within R² from regression
2. Geografisk fördelning (choropleth map, Folium, full-width or 3:2 split with histogram)
3. Histogram of predicted growth across kommuner (right side of choropleth in 3:2 layout)
4. Rangordning (sortable table, all 290 kommuner): Rang, Kommun, Län, Prognos 2025 (%), Riskklass. CSV download.

### Page 3: `pages/02_Kommunjamforelse.py` — Kommun Detail

**Page title:** "KSS · Kommunjämförelse"
**Eyebrow:** "KOMMUNDETALJ"
**Title:** "Kommunjämförelse"
**Subtitle:** "Strukturell dekomponering för vald kommun"

**Selector:** `st.selectbox` for kommun, default to top of vulnerability rank.

**Sections:**
1. KPI row (4 cards for selected kommun):
   * "Skattekraft 2024" (kr per invånare)
   * "Tillväxt 2024 (%)"
   * "Prognos 2025 (%)"
   * "Sårbarhetsrang" (X / 290)
2. Historisk trend (line chart): kommun vs riksgenomsnitt, 2010–2024
3. Dekomponering (horizontal bar chart): contribution of each variable to gap vs national mean, 2024. Color-coded: positive = green, negative = red.
4. Peer comparison table: 5 most similar kommuner by vulnerability score, with their values for each input variable
5. Metod-länk: link to METHODOLOGY.md on GitHub

---

## 8. Acceptance Criteria

A page is "done" when ALL of these pass:

**Functional:**
* Loads in under 5 seconds from cold start
* No Python errors in console
* All charts render
* All tables sortable and downloadable where specified
* Choropleth tooltip shows kommun name + key metrics

**Visual:**
* Matches design system (colors, fonts, spacing, card style)
* Sidebar visible and styled per spec
* All chrome (Streamlit menu, footer, default header) hidden
* Responsive: usable on screens 1280px wide (no need for mobile)

**Language:**
* ZERO English text visible to user (check every label, tooltip, error)
* All numeric formatting uses Swedish conventions: comma as decimal separator, narrow no-break space (`\u202f`) as thousands separator
* Currency: "kr" suffix, never "SEK" in user-facing text
* Percentages: comma decimal, "%" suffix

**Code quality:**
* All public functions have English docstrings
* `pytest` passes
* No hardcoded paths (use `pathlib.Path` relative to project root)
* No print statements (use `logging`)

**Data integrity (sanity checks, see METHODOLOGY §6):**
* Danderyd has highest skattekraft level in 2024 data
* Dorotea or similar small Norrland kommun has lowest skattekraft level
* Predictions sum/average is in plausible range (3–5% growth typical)
* No kommun has missing values across all years

---

## 9. SWEDISH_LABELS Dictionary (Authoritative)

Defined in `src/ui/labels.py`. Every user-facing string MUST come from here. Code that hardcodes Swedish text in component logic is rejected in code review.

```python
SWEDISH_LABELS = {
    # Brand and navigation
    "brand_mark": "KSS",
    "brand_title": "Skattekraft Stress",
    "brand_sub": "Kommunal panelmodell",
    "nav_landing": "Översikt",
    "nav_national": "Riksöversikt",
    "nav_kommun": "Kommunjämförelse",

    # Page eyebrows and titles
    "eyebrow_landing": "KOMMUNAL SKATTEKRAFT STRESS MONITOR",
    "eyebrow_national": "NATIONELL VY",
    "eyebrow_kommun": "KOMMUNDETALJ",
    "title_landing": "Skattekraftens utveckling i Sveriges 290 kommuner",
    "title_national": "Riksöversikt",
    "title_kommun": "Kommunjämförelse",

    # Sidebar controls
    "label_year": "ÅR",
    "label_risk_filter": "RISKKLASS",
    "label_kommun_select": "VÄLJ KOMMUN",

    # Risk classes
    "risk_low": "Låg",
    "risk_medium": "Medel",
    "risk_high": "Hög",

    # KPI labels (national)
    "kpi_median_prognosis": "Median prognos 2025",
    "kpi_high_risk_count": "Kommuner i hög risk",
    "kpi_largest_decline": "Största nedgång (prognos)",
    "kpi_model_r2": "Modellens R²",

    # KPI labels (kommun)
    "kpi_skattekraft_2024": "Skattekraft 2024",
    "kpi_growth_2024": "Tillväxt 2024",
    "kpi_prognosis_2025": "Prognos 2025",
    "kpi_vulnerability_rank": "Sårbarhetsrang",

    # Chart axes and titles
    "axis_year": "År",
    "axis_skattekraft": "Skattekraft per invånare (kr)",
    "axis_growth_pct": "Tillväxt (%)",
    "axis_kommuner_count": "Antal kommuner",
    "chart_historical": "Historisk skattekraft",
    "chart_decomposition": "Strukturell dekomponering",
    "chart_distribution": "Fördelning av prognosticerad tillväxt",

    # Table headers
    "th_rank": "Rang",
    "th_kommun": "Kommun",
    "th_lan": "Län",
    "th_prognosis": "Prognos 2025 (%)",
    "th_risk_class": "Riskklass",
    "th_skattekraft": "Skattekraft (kr)",
    "th_unemployment": "Arbetslöshet (%)",
    "th_dependency": "Försörjningskvot",
    "th_pop_growth": "Befolkning (%)",
    "th_education": "Utbildning (%)",

    # Variable display names
    "var_unemployment": "Öppen arbetslöshet",
    "var_dependency": "Försörjningskvot",
    "var_population": "Befolkningstillväxt",
    "var_education": "Andel eftergymnasialt utbildade",
    "var_residual": "Residual (kommunspecifika faktorer)",

    # Decomposition contributions
    "contrib_unemployment": "Bidrag: arbetslöshet",
    "contrib_dependency": "Bidrag: försörjningskvot",
    "contrib_population": "Bidrag: befolkning",
    "contrib_education": "Bidrag: utbildning",
    "contrib_residual": "Bidrag: residual",

    # Map
    "map_title": "Geografisk fördelning",
    "map_subtitle": "Sårbarhetsindex per kommun",
    "map_legend_caption": "Sårbarhetsindex · Lägre = bättre, Högre = sämre",
    "map_color_scale_note": "Färgskala: Grön = låg sårbarhet · Gul = medel · Röd = hög sårbarhet",

    # Buttons and actions
    "btn_download_csv": "Ladda ned som CSV",
    "btn_show_method": "Visa metod",

    # States
    "state_loading": "Laddar data...",
    "state_no_data": "Inga data tillgängliga för den valda perioden",
    "state_error_io": "Kunde inte hämta data. Försök igen senare.",
    "state_error_compute": "Beräkningsfel. Se metodologisidan för detaljer.",

    # Footer
    "footer_source_label": "KÄLLA",
    "footer_source": "SCB · OE0101, BE0101, AA0003, UF0506",
    "footer_method_link": "Metodologi",

    # Methodology callouts
    "method_model_name": "Tvåvägs fixed effects panelmodell",
    "method_period": "Period: 2010–2024",
    "method_units": "290 kommuner × 15 år = 4 350 observationer",

    # Units (use these everywhere)
    "unit_sek": "kr",
    "unit_pct": "%",
    "unit_per_capita": "per invånare",
}
```

**Number formatting helpers** (in `src/ui/labels.py`):

```python
def format_sek(value: float) -> str:
    """Format integer SEK with narrow no-break space thousands separator."""
    return f"{int(round(value)):,}".replace(",", "\u202f") + " kr"

def format_pct(value: float, decimals: int = 1) -> str:
    """Format percentage with comma decimal, % suffix."""
    return f"{value:.{decimals}f}".replace(".", ",") + " %"

def format_signed_pct(value: float, decimals: int = 1) -> str:
    """Format signed percentage with sign always shown."""
    return f"{value:+.{decimals}f}".replace(".", ",") + " %"
```

---

## 10. Two Layer Language Rule (Restated for Emphasis)

This is the most violated rule in projects of this kind. Every prompt in `TASKS.md` includes a reminder. Code review checklist:

* Variable names: English. `tax_base_growth_pct`, never `skattekraftstillvaxt_pct`.
* Function names: English. `compute_dependency_ratio()`, never `berakna_forsorjningskvot()`.
* File names: English. `fetch_skattekraft.py` is borderline (acceptable since it names a Swedish concept), but `data_fetcher.py` is preferred where natural.
* Comments and docstrings: English.
* Log messages: English. `logger.info("Fetched 4350 rows from OE0101")`.
* Internal exception messages: English. `raise ValueError("kommun_kod must be 4-digit string")`.
* User-facing strings: Swedish, from `SWEDISH_LABELS`.
* Chart axis labels passed to Plotly: Swedish, from `SWEDISH_LABELS`.
* Streamlit error messages shown to user (`st.error`, `st.warning`): Swedish.
* Print statements / `st.write` debug output during development: English, but must be removed before deployment.

---

## 11. Deployment

* GitHub repo public, name: `kommun-skattekraft-stress`
* Streamlit Community Cloud connected to repo
* App entry point: `app.py`
* Requirements pinned in `requirements.txt`
* Artifacts committed to repo (small files, well under 1 GB limit)
* Pipeline NOT run on Streamlit Cloud. User runs `python pipeline.py` locally, commits artifacts, pushes.
* Cold start expected: under 5 seconds
* Caching: `@st.cache_data` on artifact loaders only. No `@st.cache_resource` needed.

---

## 12. Out of Scope (Explicit Non-Goals)

* Live model re-estimation in app
* Län-level rollups
* Mobile-optimized layout (desktop-first only)
* Authentication / user accounts
* Database backend (parquet only)
* Real-time data refresh (annual SCB publication is the cadence)
* Causal identification claims
* Forecasts beyond t+1
* Comparison with other Nordic countries

---

## 13. Document Cross-References

* Tasks: `docs/TASKS.md` — every task references PRD sections
* Methodology details: `docs/METHODOLOGY.md` — theoretical foundation, formulas, sanity checks
* Data audit: `docs/KRI_Dataset_Identification.md` — every variable's source URL, query, schema

---

**End of PRD.md**