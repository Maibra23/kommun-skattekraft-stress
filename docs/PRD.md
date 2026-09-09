# PRD.md - Product Requirements Document

**Project:** Skattekraftspanelen
**Status:** Current. Describes the product as built.
**Last rewritten:** 2026-09-09

> **This document was rewritten, not amended.** The original PRD specified a
> *Kommunal Skattekraft Stress Monitor*: a dashboard ranking kommuner by a
> predicted 2025 growth figure, expressed as a vulnerability score and quintile
> risk classes. That forecast was scored against the realised outcome and
> failed — Pearson r = +0.016, losing to a constant-mean benchmark by 55 % —
> and the model layer was rebuilt over 2026-09. Keeping the old spec on file
> would have meant keeping a specification for a product that was deliberately
> abandoned, which is a trap for the next reader rather than a record. The
> evidence, the diagnosis and the four replacements are in METHODOLOGY 13.4.

---

## Purpose of This Document

The master reference for what the product *is*. If a design decision is not
here, in METHODOLOGY, or in the code, it is not part of the project.

Two things this document deliberately does **not** contain:

* **The Swedish label dictionary.** It lives in `src/ui/labels.py`, which is
  the single source of truth. The original PRD duplicated all of it here, and
  the copy drifted.
* **The econometric method.** That is METHODOLOGY's job. This document says
  what the product shows; METHODOLOGY says why the numbers are what they are.

---

## 1. Project Identity

| | |
|---|---|
| **Name** | Skattekraftspanelen |
| **Brand mark** | SKP |
| **Subtitle** | Läge och förflyttning |
| **Repository** | `skattekraftspanelen` |
| **Language** | All user-facing text in Swedish. Code, comments and docs in English. |

**What it does.** Shows where each of Sweden's 290 kommuner stands in
skattekraft against the national average, which way it has moved over 5 and 10
years, and what structural factors explain the difference.

**What it is not.** It is not a risk ranking, a distress monitor, or a
one-year forecast. It is descriptive first: the model explains differences
between kommuner, it does not predict them. The one forward-looking number it
carries — a five-year drift forecast — is published only alongside its own
backtest score, and the pipeline writes nothing if that score falls below its
gate.

---

## 2. Tech Stack

Python 3.11. Pinned in `requirements.txt` for Streamlit Community Cloud, kept
in sync with `pyproject.toml`.

| Layer | Library |
|---|---|
| Data | `requests`, `pandas`, `pyarrow` |
| Econometrics | `linearmodels` (PanelOLS), `statsmodels` (OLS, HC3) |
| Dashboard | `streamlit==1.55.0` |
| Charts | `plotly` |
| Map | `folium`, `branca`, `streamlit-folium` |
| Tests | `pytest` |

Theme is set in `.streamlit/config.toml`; `showSidebarNavigation = false`
because the sidebar is custom.

---

## 3. Folder Structure

Authoritative listing is in README.md, which is regenerated from disk. In
outline:

```
app.py              Startsida
pages/              Riksöversikt, Kommunjämförelse
pipeline.py         fetch → clean → estimate → decompose → forecast
src/provenance.py   which year has which variables; never hardcode a year
src/fetch/          SCB PxWeb clients, one per source
src/clean/          harmonisation, derived variables, panel build
src/model/          position, estimate, estimate_cross, decompose_cross,
                    diagnostics, forecast, backtest
src/ui/             css, components, sidebar, filters, chart_theme,
                    choropleth, labels
artifacts/          precomputed parquet the dashboard reads directly
data/               raw cache, processed panel, geojson, lookups
docs/               METHODOLOGY, KRI_Dataset_Identification, this file
tests/              pytest
```

---

## 4. Core Data Variables

Outcome and four structural variables, all per kommun-year.

| Variable | Meaning | Source |
|---|---|---|
| `tax_base_per_capita` | Skattekraft, SEK per inhabitant | SCB OE0101 |
| `tax_base_index_riket` | SCB's own published index, riket = 100, population-weighted | SCB OE0101 |
| `relative_position` | Our index: kommun ÷ unweighted mean of the 290 × 100 | derived |
| `unemployment_rate` | Öppen arbetslöshet, % | SCB AA0003 |
| `dependency_ratio` | (under 20 + over 64) ÷ 20-64 | derived from SCB BE0101 |
| `population_growth_pct` | % change in population on the year before | derived from SCB BE0101 |
| `edu_share` | Share aged 25-64 with 3+ years post-secondary, % | SCB UF0506 |

**The two index measures must never be mixed.** They differ in denominator,
not in quality: ours weights every kommun equally, SCB's weights every
inhabitant equally, so ours reads ~8 index points higher for all 290. Rank
correlation between them is 0.999. See METHODOLOGY 7.13.

**The panel is ragged.** Sources end in different years — skattekraft 2026,
population and education 2025, unemployment 2024. Anything needing all four
must read `artifacts/data_provenance.json` through `src/provenance.py`, never
`max(panel.year)`. See METHODOLOGY 13.2.

---

## 5. Empirical Model

Two models answering two different questions, plus one forecast. Full
specification in METHODOLOGY 2 and 3; this is the product-level summary.

**Cross-section — the headline.** Why does a kommun sit where it sits? OLS of
relative position on the four structural variables for the latest complete-case
year, no entity effects. R² ≈ 0.69. Of the four variables, only `edu_share` and
`unemployment_rate` are separately identified; the other two are reported as
controls and **never drawn as bars**, because their confidence intervals span
zero. The identification judgement is a boolean column in the artifact, not a
rule anyone has to remember.

**Panel, two-way fixed effects — demoted.** What moves growth within a kommun
over time? Presented under its own heading with an explicit statement that it
**cannot rank kommuner**: 98 % of the variation in relative position is between
kommuner, which is exactly what entity effects remove.

**Forecast.** Five-year drift in relative position, never one-year growth.
Gated in code by a rolling-origin backtest written before the forecaster;
intervals come from the backtest's own errors, not from nominal standard
errors. Published together with its Spearman, its RMSE and two benchmarks.

---

## 6. Design System

Navy and gold over an off-white ground; Source Sans 3 for text, IBM Plex Mono
for figures. Palette and CSS live in `src/ui/css.py`; the Plotly theme in
`src/ui/chart_theme.py`.

CSS class names keep the `shai-` prefix from the visual reference the design
was adapted from. Renaming them is deliberate wasted scope — they are internal
identifiers, invisible to users. The same reasoning keeps `kss-` on the map
legend classes and the `kss_choropleth` widget key after the project rename.

**Number formatting is a single policy**, implemented in `src/ui/labels.py`:
decimal comma throughout, one decimal for movements and effects, whole numbers
for index values, explicit sign where direction is the point, and no sign at
all on a value that rounds to zero. Charts and the tables beside them must
agree to the last digit.

---

## 7. Page Structure

**Startsida (`app.py`)** — what the measure is, what the model can and cannot
separate. Hero; concept expander; stat strip with the counts read from the
artifacts; model diagram; the coefficient chart as dot-and-whisker with a
reading guide; the within-kommun panel under its own heading; pipeline steps;
navigation; sources.

**Riksöversikt (`pages/01_Riksoversikt.py`)** — all 290 at once. KPI row
(index spread, largest 10-year fall and rise, cross-sectional R²); choropleth
with a position/drift layer toggle beside a histogram of the same quantity;
the two index measures plotted against each other; the forecast with its
backtest panel; the full sortable table with CSV download.

**Kommunjämförelse (`pages/02_Kommunjamforelse.py`)** — one kommun in depth.
Selector ordered by position; lead sentence; KPI row; position over time
against 100; skattekraft in kronor with optional comparison kommuner; the
decomposition of the position gap with controls shown as numbers rather than
bars; nearest peers by position.

Every chart carries a reading guide with a worked example, and every term the
dashboard uses is defined in the glossary.

---

## 8. Acceptance Criteria

1. All three pages render against the committed artifacts with no exception
   and no unresolved `{placeholder}` — enforced by `tests/test_pages_render.py`.
2. Every `SWEDISH_LABELS` key a page references exists — enforced by
   `tests/test_labels.py`, matching both quote styles.
3. Every number quoted in the UI copy matches the artifacts — enforced by
   `tests/test_copy_matches_artifacts.py`. A pipeline rerun that changes a
   result fails the suite until the copy is updated.
4. No rendered string describes the retired model, and no rendered string uses
   the "tappa mark" idiom — both enforced in `tests/test_labels.py`.
5. No typographic dashes in user-facing Swedish text.
6. The forecast artifact is absent rather than wrong when the backtest gate
   fails, and the dashboard renders correctly without it.
7. No year is hardcoded where `src/provenance.py` can supply it.

---

## 9. Two Layer Language Rule

**Every user-facing string is Swedish and comes from `SWEDISH_LABELS` in
`src/ui/labels.py`.** Swedish text hardcoded in component logic is rejected in
review. Code, comments, docstrings, commit messages and documentation are
English.

This is the most violated rule in projects of this kind. The check is
mechanical: if a Swedish word appears inside a `.py` file outside
`labels.py`, it is a bug.

---

## 10. Deployment

Streamlit Community Cloud, serving the branch directly with no build step.

**This is why `artifacts/` is committed and is a published contract**
(METHODOLOGY 11.7). `pipeline.py` runs locally only; the deployed app reads
the parquet files straight from git. An artifact whose schema changes in the
same commit as the page that reads it is fine; changing one without the other
breaks the live site.

---

## 11. Out of Scope

* Real (inflation-adjusted) skattekraft
* Causal identification of any kind — the decomposition is descriptive
* One-year growth forecasting; the data does not support it
* Kommun-level policy recommendations
* Any ranking by predicted distress

---

## 12. Document Cross-References

| Document | Contents |
|---|---|
| `METHODOLOGY.md` | Model specification, formulas, limitations, decision record |
| `KRI_Dataset_Identification.md` | SCB tables, API queries, data audit |
| `README.md` | Orientation, install, file tree |
