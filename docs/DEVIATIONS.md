# DEVIATIONS.md

**Project:** Skattekraftspanelen
**Purpose:** Documents how the implementation has deviated from the original PRD and TASKS specifications, why, and how each deviation was resolved.

## 1. SCB API Structural Changes

### 1.1 Value-set filter deprecation
**Original plan:** Use `vs:RegionKommun07EjAggr` filter for all SCB queries.
**Deviation:** SCB deprecated this filter, returning HTTP 400.
**Resolution:** All four fetchers now discover explicit 4-digit municipality codes from metadata at runtime. See METHODOLOGY 12.1.

### 1.2 Unemployment table restructure
**Original plan:** Single table `AA0003B/IntGr1KomKonUtb` for all years.
**Deviation:** SCB moved the old table to an archive path `AA0003X` and introduced a new table `AA0003B/IntGr1KomUtbBAS` covering only 2022+.
**Resolution:** Two-table strategy with constants controlling the year split. See METHODOLOGY 12.2.

### 1.3 Education table renamed
**Original plan:** Use `UF0506B/Utbildning4` or similar subtable.
**Deviation:** All candidate URLs returned HTTP 400. Active table is now `UF0506B/Utbildning`.
**Resolution:** Updated candidate URLs. See METHODOLOGY 12.3.

### 1.4 Education per-sex chunking
**Original plan:** Single query per year.
**Deviation:** The current education table has no combined sex code (`1+2`), causing cell limit exceeded errors.
**Resolution:** Per-(year, sex) chunking with aggregation after fetching. See METHODOLOGY 12.4.

## 2. Model Results Differing from Prior Expectations

### 2.1 Low R2(within)
**Original expectation (PRD/METHODOLOGY 6.4):** R2(within) > 0.10.
**Actual:** R2(within) = 0.0083.
**Resolution:** Documented as expected behavior for two-way FE specifications. Entity and year fixed effects absorb the vast majority of variation. Model fit checks reclassified as diagnostic, not blocking. See METHODOLOGY 7.10.

### 2.2 Negative population growth coefficient
**Original expectation:** Positive (growing population = growing tax base).
**Actual:** beta_3 = -0.080 (p = 0.008), negative.
**Resolution:** Documented as within-entity effect (temporary per-capita dilution from population inflows). The raw positive correlation is a between-entity effect absorbed by entity FE. See METHODOLOGY 7.11.

### 2.3 Insignificant education coefficient
**Original expectation:** May be insignificant (documented in METHODOLOGY 7.7 as a known risk).
**Actual:** beta_4 = +0.019 (p = 0.52), confirmed insignificant.
**Resolution:** Retained in model for theoretical completeness. Reported honestly with correct sign but wide confidence interval.

## 3. Dashboard Enhancements Beyond Original PRD

### 3.1 Collapsible concept explanation
**Original plan:** Not specified in PRD.
**Addition:** Added a collapsible section on the landing page explaining what Skattekraft is and why it matters, with scenario-based examples for different user types (credit analysts, controllers, researchers).
**Rationale:** Makes the dashboard accessible to users unfamiliar with the concept.

### 3.2 Usage guide
**Original plan:** Not specified in PRD.
**Addition:** Added a collapsible usage guide on the landing page explaining how to navigate the dashboard, what risk classes mean, and how to interpret results.
**Rationale:** Reduces the learning curve for first-time users.

### 3.3 Graph explanations across all pages
**Original plan:** Landing page had collapsible explanations for the model diagram and coefficient chart. Other pages had no graph explanations.
**Addition:** Standardized collapsible explanatory text added to every chart and table: choropleth map, histogram, historical trend, decomposition, ranking table, and peer comparison table.
**Rationale:** Users need guidance on how to read and interpret each visualization. Consistent pattern across all pages.

### 3.4 Coefficient value table
**Original plan:** Only a bar chart for coefficient display.
**Addition:** Added a data table below the coefficient bar chart showing all coefficient values, significance levels, and plain-language interpretation. This addresses the problem that the dependency ratio coefficient (-3.75) is on a different scale than the others (-0.06 to +0.02), making the smaller bars nearly invisible.
**Rationale:** Ensures all variable values are clearly visible regardless of scale differences.

### 3.5 Side-by-side municipality comparison
**Original plan:** Historical trend chart showed only the selected municipality vs national average.
**Addition:** Added a multi-select (up to 4 additional municipalities) that overlays comparison lines on the historical skattekraft chart.
**Rationale:** Enables direct visual comparison between municipalities, putting each municipality's trajectory into perspective relative to peers or rivals.

### 3.6 Extended SWEDISH_LABELS
**Original plan (PRD section 9):** Dictionary contained approximately 50 label entries.
**Current state:** Dictionary contains approximately 110 label entries.
**Rationale:** All new UI elements (concept explanation, usage guide, graph explanations, comparison controls) require label entries per the two-layer language rule.

## 4. Documentation Structure

### 4.1 REVIEW_2026-04-24.md
**Original plan:** Not in the original PRD folder structure.
**Addition:** Created after the initial code review to document empirical findings, bugs fixed, and API verification results.
**Rationale:** Provides an audit trail of the code review process and captures verification evidence.

### 4.2 This file (DEVIATIONS.md)
**Original plan:** Not in the original PRD folder structure.
**Addition:** Created to document deviations from the original plan.
**Rationale:** Transparency about how the implementation evolved relative to the original specification.

## 5. Removed from Original PRD

### 5.1 Year selector in sidebar
**Original plan (PRD 6.5):** Year selector via `st.pills()`, single, default 2024.
**Current state:** Removed. The dashboard shows all years in historical views and uses 2024/2025 as the reference year for predictions. A year selector added confusion because predictions are always for 2025 and decomposition is always for 2024 data.
**Rationale:** Simplification. The year context is implicit and clear from the data displayed.

## 6. Data Source Withdrawals

### 6.1 Unemployment 2010-2021 served from a committed snapshot, not from SCB

**Original plan (METHODOLOGY 8):** Every variable is fetched from the SCB API on each pipeline run; the panel is reproducible from source by anyone who clones the repository.

**Deviation:** SCB withdrew the AA0003X archive group. `AA0003X/IntGr1KomKonUtb`, which served open unemployment for 1997-2021, returns HTTP 400 — as does the group URL itself and the sibling tables `IntGr1KomKon` and `IntGr1Kom`. The group is still listed in the `AA0003` directory response but no path into it resolves. The live successor `AA0003B/IntGr1KomUtbBAS` carries only 2022-2024.

No replacement exists. `AA0003E` (demography), `AA0003H` (education), `AM0207` (RAMS, municipal series end 2018/2021) and `AM0210D` (BAS, 2020-2024, different definition) were each checked and ruled out. Open unemployment for 2010-2021 — 3 480 kommun-year observations — is no longer obtainable from SCB by any route.

**Options considered:**

| | Approach | Consequence |
|---|---|---|
| **A** *(chosen)* | Snapshot 2010-2021 from the committed panel; fetch 2022+ live | Panel preserved intact; reproducibility becomes "from repo" for one variable |
| B | Truncate the panel to 2022+ | Tested: 80 % of observations lost, 3 years remain, zero 5-year drift windows. Would make REMEDIATION_PLAN T1.1 and T3.2 impossible |
| C/E | Re-source from Arbetsförmedlingen or Kolada | Tested: ranks agree (Spearman +0.93/+0.95) but levels differ by 3.65x and 0.72x. Creates a step change at the 2021/2022 seam |
| D | Drop unemployment entirely | Loses the second-strongest variable (beta x within-SD = -0.111) |

**Resolution:** Option A. `data/lookup/unemployment_2010_2021.csv` holds the 3 480 historical observations with a provenance header; `fetch_unemployment` reads it below 2022 and queries SCB above. The dead archive URL was removed from the fetcher so no code path can request it.

Option A was chosen partly because it is the only option that preserves the T0.3 audit baseline fixture. The remediation's whole premise is a before/after comparison against the 2026-09-04 audit; C or E would have changed every historical unemployment value at the same time as the model specification changed, making the comparison uninterpretable.

**Validation:** the overlap years 2022-2024 exist in both the snapshot-era fetch and the live table. Re-fetched live on 2026-09-07 and compared across all 870 overlapping kommun-years: **max abs diff 0.000000 pp**. A cold `fetch_unemployment(force_refresh=True)` through the new snapshot/live split reproduces all 4 350 committed rows with zero changed values. `scripts/freeze_unemployment_snapshot.py` refuses to write the snapshot if the overlap diverges by more than 0.05 pp.

**Consequence to keep in view:** the snapshot can be copied forward but never regenerated from source. METHODOLOGY 8.1 states this rather than leaving the old reproducibility claim standing, and `tests/test_fetch_unemployment.py` asserts the snapshot still matches the committed panel row for row, so a silent change fails the suite.

**Reference:** REMEDIATION_PLAN.md T0.2a; METHODOLOGY 8.1 and 12.6.

### 6.2 The panel is no longer balanced

**Original plan (PRD 4, METHODOLOGY 2.3):** A balanced panel of 290 kommuner x 15 years = 4 350 observations, every variable populated in every cell.

**Deviation:** The four SCB sources no longer share an end year. Skattekraft reaches 2026, population and education 2025, unemployment 2024. Holding the panel balanced would mean truncating every source to 2024 and discarding the newest skattekraft — the opposite of the intent behind extending coverage.

**Resolution:** The panel is anchored on skattekraft and left ragged: 290 x 17 = **4 930 rows**, 2010-2026, with shorter sources null in the years they do not reach. All 290 kommuner appear in every year; the raggedness is across variables only. `artifacts/data_provenance.json` records each source's coverage and the `complete_case_max_year` (2024), and any consumer needing all four structural variables must read it rather than assume `max(panel.year)`.

The estimation sample is unchanged. `PanelOLS` drops incomplete cases, so the model is still fit on 2010-2024 and the T0.3 audit baseline still passes with the same coefficients.

**Also corrected here:** `tax_base_index_riket` was merged into the panel but omitted from `_FINAL_COLUMNS`, so it was dropped before writing. T0.1's definition of done would have failed silently after the rebuild. The column is now written and non-null for every kommun-year.

**Reference:** REMEDIATION_PLAN.md T0.2; METHODOLOGY 2.3.1 and 12.7.

---

### 6.3 Population is read from SCB's published total, not summed from age cells

**Original plan (METHODOLOGY 2.2, 6.2):** Fetch single-year age counts from BE0101, sum them to obtain each kommun's population, and sanity-check the national total against an approximate expectation.

**Deviation:** That arithmetic stopped being valid in 2025. SCB published that year in a new table, `BefolkningCKM`, whose cells are disclosure-protected: its published totals exceed the sum of the categories beneath them in every dimension. Summing roughly 200 protected cells per kommun therefore produced a population that was systematically short — 154 nationally, but **1.005 % in Överkalix**, which is one full standard deviation of `population_growth_pct`. The panel reported Överkalix shrinking 1.56 % in 2025 when SCB's own figures say 0.56 %. `BefolkningNy`, which serves 2010-2024, has no such gap: its parts sum to its published total exactly, for all 290 kommuner.

Found on 2026-09-07 during a live review of Phase 0, by comparing the panel against SCB rather than against its own previous year.

**Resolution:** Three changes, in `fetch_population` and `compute_derived`.

1. `population` now comes from the publisher's own all-ages aggregate (`fetch_population_total`), pinned to each table's own total codes. It is exact by construction rather than assembled here.
2. Age groups are read from 5-year bands where the table offers them, which cuts the cells summed per kommun from ~202 to 21 and the worst-kommun residual from 1.005 % to 0.447 %. `BefolkningNy` offers no bands and needs none. No band spanning 20 or 65 is ever selected — `_age_code_to_group` raises rather than assign one, because a 10-year band such as `60-69` would put 65-69 year-olds into the working-age denominator.
3. `_verify_against_published_totals` compares the summed groups against the published total on every run and raises when they disagree: above 1.5 % for any kommun, or 0.05 % nationally. Per METHODOLOGY 11.6 this is a hard check — a client-side sum that disagrees with the publisher is a structural integrity failure.

**Effect on the rebuilt panel:** 290 rows changed, all in 2025. The national 2025 population now matches SCB's published 10 605 520 exactly; Överkalix reads 3 183 and -0.5623 %. `dependency_ratio` moved by at most 0.046 and `population_growth_pct` by at most 1.00 pp, both in the smallest kommuner. **Every other value in the panel is unchanged, and all eight artifacts are byte-identical** — 2025 entered no specification, because `complete_case_max_year` is 2024.

**Why it was worth fixing before it mattered:** the defect arms itself twice. The dashboard starts displaying 2025 the moment T1.2 stops hardcoding `year == 2024`, and 2025 enters the estimation sample when SCB publishes 2025 unemployment, expected February 2027.

**Reference:** REMEDIATION_PLAN.md, the 2026-09-07 review entries; METHODOLOGY 6.2 and 12.8.

---

### 6.4 PRD §5 "Empirical Model (Locked)" was deliberately unlocked

**Original plan (PRD 5):** The empirical model was declared locked: a two-way fixed-effects panel regression of skattekraft growth on four structural variables, producing a vulnerability score, a quintile risk class, and a one-year-ahead growth forecast. "Locked" meant it was not to be renegotiated during implementation.

**Deviation:** It was unlocked and substantially replaced. This is the largest specification change in the project's history and the one most in need of a record.

**What forced it.** An audit on 2026-09-04 scored the shipped forecast against outcomes SCB had by then published:

| Metric | Result |
|---|---|
| Pearson r, predicted vs realised 2025 growth | **+0.016** |
| RMSE | 1.512 pp against 0.974 pp for guessing the national mean |
| Predicted dispersion | 0.33 pp against a realised 0.98 pp |
| Realised growth by risk class | låg 4.74 %, medel 4.52 %, hög 4.68 % — unseparated and non-monotone |

The forecast lost to the naive benchmark by 55 %, and the risk classes did not order kommuner by what happened. Reproduced three times through independent code paths agreeing to four decimal places, so this was a property of the model rather than of the measurement.

**The diagnosis was an estimand mismatch, not a bug.** The model was correctly estimated. It was answering a different question from the one the dashboard asked. **98.2 % of the variation in relative position is between kommuner**, and entity fixed effects absorb exactly that variation — so a two-way FE specification was structurally incapable of ranking kommuner, however well it was fitted. Year-demeaned persistence of the growth rate is about −0.05, so the one-year target was not recoverable either.

**Resolution.** Four changes, each with its own evidence:

1. **A descriptive spine that needs no model.** Relative position and drift over 1, 3, 5 and 10 years, from skattekraft alone. Rank stability is 0.99 at one year and 0.93 at ten — the most reliable thing the project can say, and it was previously absent from the dashboard entirely.
2. **A cross-sectional estimator for the ranking.** Same four variables, no entity effects, R² = 0.690–0.723 across 2021–2024. Two of the four variables are not separately identified between kommuner and are reported as controls rather than drawn as bars; the identification judgement is a boolean in the artifact, not a rule someone has to remember.
3. **The FE model kept, demoted, and relabelled.** It answers "within a kommun over time" and is presented under its own heading with an explicit statement that it cannot rank kommuner. Its lagged specification is now primary: every regressor's within-kommun correlation peaks at t−1 or later.
4. **The forecast rebuilt on terms that make the failure hard to repeat.** Five-year drift rather than one-year growth; a rolling-origin backtest written *before* the forecaster; two mandatory benchmarks; intervals from the backtest's own errors; and a gate enforced in code that writes nothing when out-of-sample Spearman falls below 0.25. Measured: **+0.329**, beating both benchmarks, with intervals calibrated at 81 % against a nominal 80 %.

**What the vulnerability score's fate is.** Retired from every part of the dashboard except one map layer, which carries a callout stating what it scored. `predictions.parquet` and `ranking.parquet` are still written and read by nothing else.

**Two thresholds in the remediation plan itself proved arithmetically impossible** and were corrected in place rather than quietly met: T2.2's "mean |residual| < 40 % of the gap" (unreachable given the R² it was derived from) and T3.2's "predicted dispersion within 30 % of realised" (requires r ≥ 0.70 while the same DoD asks only for ρ > 0.25). Both were replaced with criteria that test the same intent — residual *variance* share, and interval *coverage*.

**Reference:** `docs/REMEDIATION_PLAN.md` in full, including its status log; METHODOLOGY 2.6, 2.7, 3.4, 3.5, 6.4, 7.10, 7.13–7.16.

---

**End of DEVIATIONS.md**
