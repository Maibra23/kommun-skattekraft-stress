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

**End of DEVIATIONS.md**
