# DEVIATIONS.md

**Project:** Kommunal Skattekraft Stress Monitor
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

---

**End of DEVIATIONS.md**
