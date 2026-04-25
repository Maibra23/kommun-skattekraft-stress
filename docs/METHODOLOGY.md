# METHODOLOGY.md — Methodology Bible

**Project:** Kommunal Skattekraft Stress Monitor

This document is both a development reference (read by Cursor and Claude Code during implementation) and the basis for the methodology section displayed in the dashboard. It documents the theoretical foundation, the exact regression specification, every formula, the evaluation criteria, and all known limitations.

For data sources and URLs, see `KRI_Dataset_Identification.md`. This document focuses on **why** and **how**, not **where the data lives**.

---

## 1. Theoretical Foundation

### 1.1 The economic question

Swedish kommuner finance their operations primarily through municipal income tax (kommunalskatt) levied on residents' taxable employment income. The tax base per inhabitant — *skattekraft* — is therefore the central determinant of a kommun's fiscal capacity.

Skattekraft varies enormously across the 290 kommuner: in 2024, Danderyd reported approximately 481 000 SEK per inhabitant while small Norrland kommuner reported under 150 000 SEK. The Swedish kommunalekonomisk utjämningssystem partially offsets these differences through grants from high-skattekraft to low-skattekraft kommuner, but the underlying tax base remains a real constraint on each kommun's fiscal autonomy and creditworthiness.

### 1.2 Why study skattekraft *growth* rather than levels

Levels are dominated by structural, slow-moving differences (industry composition, geography, settlement history). The interesting analytical and policy question is the *direction* of change: which kommuner are seeing their tax base erode or expand, and what structural factors drive this?

Growth rates are also stationary, which is required for valid panel inference. Levels are non-stationary in nominal SEK due to inflation and real growth.

### 1.3 Why structural factors

Standard public-finance literature (e.g. Bergvall et al. on Nordic municipal finance; OECD reports on subnational fiscal sustainability) identifies four structural drivers of municipal tax base trajectories:

1. **Labor market conditions** (unemployment) — direct effect on income tax collected
2. **Demographic composition** (dependency ratio) — share of population in tax-paying ages
3. **Population dynamics** (growth or decline) — net migration affects future tax base
4. **Human capital** (education levels) — predicts wage growth and labor force participation

These are the four right-hand-side variables in our model.

### 1.4 What this model is NOT

* **Not a causal model.** The estimated coefficients describe associations within a panel, not causal effects. Reverse causality (low growth → unemployment) is plausible. The fixed-effects specification controls for time-invariant confounders but not for simultaneity.
* **Not a long-horizon forecast.** Predictions are one-year-ahead only. Out-of-sample accuracy beyond 2025 is not claimed.
* **Not a substitute for the official utjämningssystem analysis.** That analysis uses confidential micro-data and richer covariates. This is a public-data, replicable analog.

---

## 2. Empirical Model Specification

### 2.1 Equation

For kommun *i* and year *t*:

$$
\Delta\text{TaxBase}_{it} = \alpha_i + \gamma_t + \beta_1 \text{Unemployment}_{it} + \beta_2 \text{DependencyRatio}_{it} + \beta_3 \text{PopGrowth}_{it} + \beta_4 \text{EduShare}_{it} + \varepsilon_{it}
$$

Where:
* `ΔTaxBase_it` = year-over-year percent change in skattekraft per inhabitant, current SEK
* `α_i` = kommun fixed effect (290 dummies, one omitted)
* `γ_t` = year fixed effect (15 dummies, one omitted)
* `β_1, β_2, β_3, β_4` = structural coefficients
* `ε_it` = idiosyncratic error

### 2.2 Variable construction

| Variable | Construction |
|---|---|
| `tax_base_growth_pct` | `(skattekraft_t / skattekraft_{t-1} - 1) * 100` |
| `unemployment_rate` | Direct from SCB STATIV, percent |
| `dependency_ratio` | `(pop_0_19 + pop_65plus) / pop_20_64`, computed from BE0101 |
| `population_growth_pct` | `(pop_total_t / pop_total_{t-1} - 1) * 100` |
| `edu_share` | Direct from SCB UF0506 (sum of SUN codes 6+7), percent |

### 2.3 Sample

* **Cross-sectional units:** 290 kommuner (all Swedish municipalities, 2024 boundaries)
* **Time period:** 2010 to 2024 (15 years, annual)
* **Total observations:** 4 350 (balanced panel)
* **Lag for growth variables:** 2010 growth requires 2009 levels for skattekraft and population; ensure fetch covers 2009 even though 2009 is dropped from the regression sample.

### 2.4 Estimation

`linearmodels.PanelOLS` with `entity_effects=True, time_effects=True`. Standard errors clustered at kommun level (`cov_type='clustered', cluster_entity=True`).

### 2.5 Why two-way fixed effects

* `α_i` absorbs all time-invariant kommun characteristics: geography, industry mix, historical settlement, distance to Stockholm, language minority status, etc.
* `γ_t` absorbs all aggregate annual shocks: national wage growth, federal policy changes, COVID, inflation surges, business cycle.
* What's left in `β_1..β_4` is the within-kommun, between-year association after both layers of fixed effects.

This is the standard specification in modern applied micro for panel data. It is not the only specification (random effects, between estimator, dynamic panel) but it is the most defensible default when both kommun and year heterogeneity matter.

### 2.6 Robustness specifications (run, report in Methodology tab)

| Robustness | Specification | Why |
|---|---|---|
| Lagged independents | Replace `X_it` with `X_{i,t-1}` on RHS | Mitigates simultaneity |
| Drop COVID | Exclude 2020 and 2021 | COVID may dominate year FE |
| Larger kommuner only | Subsample with 2024 population > 10 000 | Small kommuner have noisier growth |
| Without education | Drop β₄ | Education stock varies slowly; check if it materially changes other betas |

If the main coefficients are stable across these specifications, the model is robust. If they flip sign or change magnitude dramatically, document and discuss.

---

## 3. Vulnerability Score (Path A: Prediction)

### 3.1 Construction

For each kommun *i*, compute predicted growth for 2025:

$$
\widehat{\Delta\text{TaxBase}}_{i, 2025} = \hat{\alpha}_i + \bar{\gamma}_{recent} + \hat{\beta}_1 \text{Unemployment}_{i, 2024} + \hat{\beta}_2 \text{DependencyRatio}_{i, 2024} + \hat{\beta}_3 \text{PopGrowth}_{i, 2024} + \hat{\beta}_4 \text{EduShare}_{i, 2024}
$$

Where:
* `α̂_i` = estimated kommun fixed effect
* `γ̄_recent` = mean of estimated year fixed effects for 2022, 2023, 2024 (proxy for unobserved 2025)
* `β̂_k` = estimated coefficients
* RHS values are most recent observed (2024)

### 3.2 Standardization to vulnerability_score

To make scores comparable and interpretable as "vulnerability":

$$
\text{vulnerability\_score}_i = -1 \times \frac{\widehat{\Delta\text{TaxBase}}_{i, 2025} - \mu_{\text{predictions}}}{\sigma_{\text{predictions}}}
$$

Where μ and σ are mean and standard deviation across all 290 predictions. The `-1` flips the sign so that **higher score = more vulnerable** (lower predicted growth).

### 3.3 Risk class assignment

* **Hög** (high risk): bottom 20% of predicted growth (top 20% of vulnerability_score) = 58 kommuner
* **Medel** (medium risk): middle 60% = 174 kommuner
* **Låg** (low risk): top 20% of predicted growth = 58 kommuner

Quintiles computed on `predicted_growth_2025`, not on `vulnerability_score` (mathematically equivalent but cleaner to document).

### 3.4 Why prediction is defensible despite causal limitations

Prediction does not require causal identification. It requires that the relationship between RHS variables and growth is stable enough to extrapolate one period ahead. Two-way FE controls for many confounders, and the one-year horizon limits structural change risk. For a stress monitor (early-warning tool) rather than a policy counterfactual, predictive validity is the right standard.

---

## 4. Decomposition (Path B: Structural Explanation)

### 4.1 Construction

For each kommun *i* in 2024, decompose the gap between its actual growth and the national mean:

$$
\Delta\text{TaxBase}_{i, 2024} - \bar{\Delta\text{TaxBase}}_{2024} = \sum_{k=1}^{4} \hat{\beta}_k \cdot (X_{ki, 2024} - \bar{X}_{k, 2024}) + (\hat{\alpha}_i - \bar{\hat{\alpha}}) + (\varepsilon_{i, 2024} - \bar{\varepsilon}_{2024})
$$

This expresses the gap as the sum of:
* Four structural contributions (one per RHS variable)
* A kommun fixed-effect contribution (time-invariant unobservables)
* A residual (idiosyncratic 2024 shock)

### 4.2 Display in dashboard

Horizontal bar chart, one bar per contribution component:
* Positive bars (green) = factor contributes to *higher* growth than national average
* Negative bars (red) = factor contributes to *lower* growth than national average
* Bars sum to the total gap

For interpretability, the residual is grouped with kommun fixed effect into a single "Residual (kommunspecifika faktorer)" bar.

### 4.3 What the decomposition means

For Filipstad (illustrative): "Of the 1.8 percentage point gap below the national mean in 2024, 0.6 pp is explained by lower education share, 0.4 pp by adverse demographics, 0.3 pp by population decline, 0.2 pp by higher unemployment, and 0.3 pp is residual."

This is a valuable controller-level insight: which structural factors are driving underperformance.

---

## 5. Number Formatting Conventions

All user-facing numbers follow Swedish conventions, applied via helpers in `src/ui/labels.py`:

| Type | Format | Example |
|---|---|---|
| Currency (SEK) | Integer with `\u202f` thousands separator + " kr" suffix | `271\u202f000 kr` displayed as `271 000 kr` |
| Percentage | One decimal, comma decimal separator, " %" suffix | `2,3 %` |
| Signed percentage | Same with leading sign | `+2,3 %` or `-1,8 %` |
| Z-score / vulnerability_score | Two decimals, comma decimal, signed | `+0,67` |
| Year | Bare integer | `2024` |

Never display SEK with the "SEK" code in user-facing text. Always "kr".

---

## 6. Sanity Checks (run automatically in pipeline)

The pipeline raises an error and stops if any of these fail. Failure indicates a data quality or join error, not a modeling problem.

### 6.1 Skattekraft level checks

| Check | Expected | Source |
|---|---|---|
| Highest 2024 skattekraft | Danderyd (kod 0162), approximately 481 000 kr | SCB OE0101 fetched data |
| Bottom 5 skattekraft kommuner 2024 | All from Norrland or sparsely populated regions | Domain knowledge |
| National mean skattekraft 2024 | Unweighted mean approximately 231 000 kr (range 200 000–350 000 kr) | Pipeline computed; note: SCB's published "riksmedelvärde" (~271 000 kr) is population-weighted and therefore higher |
| All 290 kommuner present in every year | Yes | Implementation |

### 6.2 Population checks

| Check | Expected |
|---|---|
| National total 2024 | Approximately 10.55 million |
| Stockholm kommun (0180) is largest | True |
| Sum of kommun populations approximates national total | Within 0.1% |

### 6.3 Growth rate sanity

| Check | Expected |
|---|---|
| Mean tax_base_growth_pct over 2010–2024 | Positive, between 2.5% and 5% annually (observed: 2.65 %) |
| No kommun has tax_base_growth_pct below -10% in any year | True (observed min: −4.9 %; extreme outliers indicate data error) |
| 2020 growth distribution | Lower than 2019 (COVID effect visible; observed: 2019 mean 3.2 %, 2020 mean 2.2 %) |
| Dependency ratio range | 0.5 to 1.25 across kommuner (observed: 0.508–1.241) |

### 6.4 Model fit checks

| Check | Expected | Actual (2026-04-24 review) | Status |
|---|---|---|---|
| R² (within) | Originally expected >0.10 | **0.0083** — see §7.10 for explanation | ⚠ Below prior expectation |
| At least 2 of 4 betas statistically significant | At cluster-robust 5% level | 3 of 4 significant (unemployment p<0.001, dependency p<0.001, population p=0.008; education p=0.52 n.s.) | ✓ Pass |
| Sign of β₁ (unemployment) | Negative | **−0.059** (p<0.001) | ✓ Pass |
| Sign of β₃ (population growth) | Originally expected positive | **−0.080** (p=0.008) — negative after two-way demeaning; see §7.11 | ⚠ Sign reversal (explained) |
| β₄ (edu_share) significance | May be insignificant (§7.7) | **+0.019** (p=0.52) — confirmed insignificant | ✓ Expected |

**Note on §6.4 enforcement:** These model fit checks are **diagnostic, not blocking**. Unlike the data integrity checks in §6.1–§6.3 (which halt the pipeline on failure), the model fit checks are informational — a low R²(within) or an unexpected coefficient sign indicates that the specification should be interpreted carefully, but does not indicate a data error. The pipeline logs these results but does not halt, because the findings are empirically valid (see §7.10 and §7.11 for detailed explanations).

---

## 7. Known Limitations (volunteer in interviews)

These limitations are documented here, displayed in the dashboard's Metod section, and should be raised proactively in interviews. Interviewers respect candidates who self-criticize before being challenged.

### 7.1 Open arbetslöshet is a register-based proxy, not AKU

The unemployment variable comes from Arbetsförmedlingen registrations, not from the AKU labor force survey. AKU is the official unemployment statistic but is unavailable at kommun level for small kommuner due to sampling. Register-based open arbetslöshet captures only those who have registered with Arbetsförmedlingen, so it underestimates true unemployment among groups less likely to register (young people not yet eligible for benefits, some immigrants, etc.). It is, however, the standard kommun-level measure used by SKR and Finansdepartementet for kommun-level analysis.

### 7.2 No causal identification claim

Two-way FE controls for time-invariant confounders and aggregate year shocks. It does not address simultaneity (low growth → unemployment), measurement error, or omitted time-varying variables. The model is descriptive and predictive, not causal.

### 7.3 Predictions assume structural stability

The model is trained on 2010–2024 patterns. A 2025 shock unlike anything in the training period would not be captured. COVID is in the training data, which helps for similar future shocks, but a unique event (e.g. a major industrial closure in a single kommun) would be missed.

### 7.4 Year fixed effect proxy in prediction

The 2025 year fixed effect is unobserved. We proxy with the mean of 2022–2024 estimated year FE. This is a standard shortcut but introduces uncertainty not reflected in displayed prediction intervals. A more sophisticated approach would model year FE as a time series.

### 7.5 No housing or migration variables

Migration flows (in/out flytting) and housing market variables (kommun-level house prices) could strengthen the model but were descoped to maintain the 5-day timeline. Easy extension if pursued further.

### 7.6 Skattekraft published with 2-year lag relative to income year

The skattekraft figure for year *t* reflects income earned in year *t-2*. The 2025 published number reflects 2023 income. The dashboard displays this lag explicitly in tooltips and the methodology tab. For our growth rate calculation, this is consistent across years and does not bias the analysis, but it does mean "2024 skattekraft" actually summarizes 2022 economic activity.

### 7.7 Education variable moves slowly

The within-kommun variation in education share across 15 years is modest. β₄ may have a wide confidence interval and may not be statistically significant. This is a known feature of slow-moving demographic stocks, not a defect in the model. If β₄ is insignificant, we report it honestly and discuss interpretation.

### 7.8 Definition change in unemployment series (2018)

SCB updated the methodology for "Andel öppet arbetslösa" in 2018, applied retroactively to 1997. Pre-2018 published values may differ slightly from current values. We use the current (post-2018) consistent series throughout.

### 7.9 Unemployment rate is the SCB-published total aggregate

The pipeline requests unemployment rates using the SCB-provided total-aggregate codes (`BakgrVar='TOT'`, `Kön='1+2'`, `UtbNiv='000'`). These codes select the already-aggregated "all backgrounds, both sexes, all education levels" series that SCB publishes directly. No client-side averaging across sub-categories is performed.

This approach was adopted during pipeline implementation when the SCB STATIV tables were restructured (see §12.2). Using the published total avoids the weighting ambiguity entirely and ensures the series matches the aggregate figures SCB publishes in its statistical news releases.

### 7.10 Low R²(within) is expected after two-way demeaning

The within R² of 0.0083 means that the four structural variables explain only 0.83% of the residual variation **after removing entity and year fixed effects**. This does not mean the model is useless — it means the entity and year effects absorb the vast majority of variation, which is the point of two-way FE.

**Why this is expected:**
* Entity fixed effects absorb all time-invariant kommun differences (geography, industry mix, commuting patterns, historical settlement) — these explain most cross-sectional variation in tax base growth.
* Year fixed effects absorb all aggregate annual shocks (national wage growth, inflation, policy changes, COVID) — these explain most time-series variation in tax base growth.
* What remains after absorbing both layers is the **within-kommun, between-year deviation from trend** — a very small residual signal.
* The individual coefficients are still statistically significant and economically meaningful: a 1 pp increase in unemployment within a kommun is associated with a −0.059 pp decrease in tax base growth, holding all else constant.

**Implications for prediction:**
* The vulnerability score is dominated by the entity fixed effects (historical patterns), not by current structural conditions.
* The structural variables contribute a small marginal adjustment on top of the entity-specific baseline.
* This is honest and should be communicated: the model ranks kommuner primarily by their historical trajectory, with modest adjustments for current structural conditions.

**In academic context:** Two-way FE specifications commonly show low within R² in municipal-level panels (see Wooldridge 2010 ch. 10; Angrist & Pischke 2009 ch. 5). The R² statistic is not the right criterion for assessing whether coefficients are informative — t-statistics and coefficient stability across robustness specifications are more relevant.

### 7.11 Population growth coefficient is negative after demeaning

The population growth coefficient β₃ = −0.080 (p = 0.008) is negative, which contradicts the intuitive expectation (and the raw positive correlation) that growing populations should be associated with growing tax bases.

**Explanation:** After two-way demeaning:
* The raw (level) positive correlation between population growth and tax base growth reflects **between-kommun** differences: thriving kommuner have both growing populations and growing tax bases.
* The **within-entity** effect captures a different dynamic: when a specific kommun experiences above-trend population growth in a specific year (holding its time-invariant characteristics constant), the per-capita tax base may temporarily dilute. This happens because population inflows (especially young families, immigrants, or students) may initially contribute less to the per-capita tax base than the existing residents.
* This within-entity negative effect is consistent with findings in the municipal finance literature where rapid population growth creates a lag between population arrivals and tax base expansion.

**This is not a data error.** The "no_education" and "lagged" robustness specifications should be consulted to verify that the sign and magnitude are stable. If β₃ flips sign in robustness checks, this finding should be treated with caution.

### 7.12 Nominal tax base growth includes inflation

`tax_base_growth_pct` is computed from nominal SEK values (not inflation-adjusted). The year fixed effects (γ_t) absorb the common inflation component across all kommuner, so the β coefficients capture the association between structural variables and growth **in excess of the national average**. However, the predicted growth for 2025 — which uses a year FE proxy — will include an inflation component. Users should interpret predicted growth rates as nominal, not real.

### 7.13 Unweighted cross-sectional statistics

The national mean, vulnerability scores (z-scores), and rankings treat all 290 kommuner equally regardless of population size. Stockholm (population ~1 million) receives the same weight as Bjurholm (population ~2,400). This is standard for cross-sectional municipal analysis where the unit of interest is the municipality as a fiscal entity, not the individual resident. For population-weighted analysis, SCB's published "riksmedelvärde" (~271,000 SEK) should be consulted instead.

---

## 8. Reproducibility

Every step of the pipeline is deterministic given the source data. To reproduce:

1. Clone the repository
2. Install dependencies: `pip install -e .`
3. Run pipeline: `python pipeline.py`
4. Compare generated artifacts in `artifacts/` to the committed versions

If artifacts differ, document the cause (typically: SCB has refreshed underlying data, or you are using a different Python version).

The repository commits both the input parquet (`data/processed/panel.parquet`) and the output artifacts so that a reviewer can verify the model independently of SCB API availability.

---

## 9. Interpretation Guide for Non-Econometricians

This section is shown in the dashboard's Metod tab to help kommun-level users interpret results.

**What does "två vägs fixed effects" mean?**
The model controls for all time-invariant differences between kommuner (geography, industry mix, history) and all year-level shocks that affect every kommun (national policy, economy-wide events). What's left explains differences in growth that come from changes within a kommun over time.

**Why is my kommun ranked where it is?**
The vulnerability ranking reflects predicted growth in 2025 based on your kommun's most recent values for unemployment, dependency ratio, population growth, and education share, combined with your kommun's historical growth pattern. A high rank does not mean fiscal crisis; it means weaker predicted growth than other kommuner.

**Can I trust the prediction?**
The prediction is a model-based estimate, not a forecast in the strict economic sense. Use it as one input among many. Local knowledge of upcoming events (a major employer relocation, a planned development project) is not in the model and should be combined with the prediction.

**What does the decomposition tell me?**
The decomposition shows which structural factors are pulling your kommun above or below the national average. If the "demographics" bar is large and negative, your dependency ratio is heavier than average and that explains part of the gap. If the "residual" bar is large, kommun-specific factors not captured by the four structural variables matter most.

---

## 10. References

* Anderson, J. E. (2012). *Public Finance: Principles and Policy.* (general framework for tax base analysis)
* SCB (annual). *Kommunalskatterna* statistical news series.
* SCB. *Räkenskapssammandrag för kommuner och regioner* (background on kommun finance, not used in model).
* SKR (Sveriges Kommuner och Regioner). Annual *Ekonomirapporten* (context for kommun fiscal trends).
* Wooldridge, J. M. (2010). *Econometric Analysis of Cross Section and Panel Data*, Chapter 10 (panel methods).
* `linearmodels` documentation: https://bashtage.github.io/linearmodels/

---

## 11. Pipeline Implementation Decisions

This section documents technical decisions made during the implementation of the data fetching pipeline (Tasks 1.2–1.6) that affect data quality, reliability, or reproducibility. These decisions are recorded here so that future maintainers and reviewers understand the rationale.

### 11.1 Shared infrastructure in pxweb_client

All four fetcher modules (`fetch_skattekraft`, `fetch_population`, `fetch_unemployment`, `fetch_education`) share common infrastructure centralized in `src/fetch/pxweb_client.py`:

* **Cache helpers** (`is_cache_fresh`, `save_df_cache`, `load_df_cache`): standardized 7-day cache freshness check, JSON serialization/deserialization, and type casting. Centralizing these eliminates duplicated cache logic and ensures consistent behavior across all fetchers.
* **Metadata helpers** (`get_dimension_codes`, `extract_tid_years`): shared functions for inspecting PxWeb table metadata. Avoids duplicating lookup logic in each fetcher.
* **Retry logic**: both `fetch_metadata` (GET) and `query_pxweb` (POST) retry up to 3 times with exponential back-off (1 s, 2 s, 4 s) on HTTP 429 (rate-limit) and 5xx (server error) responses. Non-retryable 4xx errors fail immediately. This ensures consistent resilience to transient SCB API issues across all operations.

### 11.2 Deferred metadata calls

The `fetch_skattekraft` module defers its metadata call (to confirm the ContentsCode) until data actually needs to be fetched from the API. When loading from cache, no network requests are made. This avoids unnecessary latency and eliminates a failure point during cached reads.

### 11.3 Population chunking uses per-year caching

The `fetch_population` module implements its own per-year query loop with per-year cache files (`data/raw/population_{year}.json`) rather than using the generic `chunk_query_by_year` function from `pxweb_client`. This is a deliberate improvement: per-year cache files enable incremental re-fetching of individual years without re-downloading the full 16-year series. The `chunk_query_by_year` function remains available in `pxweb_client` for other use cases that do not require per-year caching.

### 11.4 Unemployment metric column identification

The `fetch_unemployment` module identifies the unemployment rate metric column using the PxWeb response column position convention: PxWeb always places key/dimension columns first (matching the `key` array in the JSON data), followed by value/content columns. When a single ContentsCode is requested, the last column in the response is always the metric value. This positional approach is more reliable than the previously considered unique-ratio heuristic (`unique_ratio < 0.05`), which could misclassify high-cardinality metric columns as disaggregation dimensions.

### 11.5 Education fetcher uses NamedTuple for table configuration

The `fetch_education` module uses a `TableConfig` named tuple to bundle the 8 parameters resolved during table discovery (table URL, contents code, education dimension code and values, age dimension code and values, sex dimension code and values). This improves readability and self-documentation compared to unpacking an anonymous 8-element tuple.

### 11.6 Verification check severity

All fetcher verification checks follow a consistent severity policy:

* **Hard checks** (raise `ValueError`): missing kommuner, implausible value ranges, structural data integrity failures (e.g. Danderyd not highest skattekraft, national mean outside expected range). These indicate a data integrity problem that would corrupt downstream artifacts.
* **Soft checks** (log warning): unexpected but non-fatal observations (e.g. Stockholm not the largest kommune, unemployment mean outside the narrow 3–8 % historical range but within the wider 1–15 % plausible range). These may indicate data quality issues worth investigating but do not block the pipeline.

---

## 12. SCB API Structural Changes Discovered During Implementation

This section documents the SCB PxWeb API changes encountered and adapted to during pipeline implementation. Future maintainers should consult this section first if any fetcher fails with HTTP 400 or HTTP 403 errors.

### 12.1 Value-set filter `vs:RegionKommun07EjAggr` is no longer accepted

**Symptom:** All four fetchers returned HTTP 400 on POST queries that used `"filter": "vs:RegionKommun07EjAggr"` with an empty `"values": []` list.

**Root cause:** The SCB PxWeb v1 API no longer honours the `vs:` (value-set) filter syntax for the Region dimension. The documentation still lists this filter type, but the API rejects it.

**Fix applied (all four fetchers):** At fetch time, the pipeline first calls the metadata endpoint (`GET /api/v1/...`) to retrieve all Region dimension codes. It then filters to 4-digit all-numeric codes (`len(c) == 4 and c.isdigit()`) to isolate the 290 municipality codes (county codes are 2 digits; the national total is `"00"`). The POST query then uses `"filter": "item"` with the explicit list of 290 codes. This produces identical results to the value-set filter and is robust to future value-set changes.

### 12.2 SCB STATIV AA0003 unemployment table restructure

**Symptom:** Metadata GET for the old `AA0003B/IntGr1KomKonUtb` subtable returned HTTP 400 ("table not found").

**Root cause:** SCB reorganized the STATIV unemployment tables around 2023–2024. The old subtable `AA0003B/IntGr1KomKonUtb` (and its siblings `IntGr1KomKon`, `IntGr1Kom`) were moved to an archive path `AA0003X`. A new subtable `AA0003B/IntGr1KomUtbBAS` was introduced but only covers 2022 onwards.

**Fix applied:** The `fetch_unemployment` module uses a two-table strategy:

| Year range | Table URL | Coverage |
|---|---|---|
| 2010–2021 | `AA0003X/IntGr1KomKonUtb` | 1997–2021 (archived, still accessible) |
| 2022–2024 | `AA0003B/IntGr1KomUtbBAS` | 2022–present |

Results from both tables are concatenated to form the complete 2010–2024 series. Constants `_OLD_TABLE_LAST_YEAR = 2021` and `_NEW_TABLE_FIRST_YEAR = 2022` control the split. If SCB updates the new table to cover earlier years in the future, adjusting these constants is sufficient to change the routing.

**Total-code optimization:** Both tables provide total-aggregate codes (`BakgrVar='TOT'`, `Kön='1+2'`, `UtbNiv='000'`). The pipeline selects these codes directly, reducing each POST to 290 × 1 × 1 × 1 × n_years cells (well within SCB's ~150 000-cell limit). This also avoids the unweighted-mean approximation described previously in §7.9.

### 12.3 SCB UF0506 education table renamed

**Symptom:** Metadata GET for candidate URLs `UF0506B/Utbildning4`, `UF0506B/Utbildning3`, and `UF0506B/Utbildning4C` all returned HTTP 400.

**Root cause:** SCB consolidated the UF0506 education disaggregation tables. The active subtable is now `UF0506B/Utbildning` (covering 1985–2024). A backup candidate `UF0506B/UtbBefRegionR` is tried if the primary fails.

**Fix applied:** Updated `_CANDIDATE_URLS` in `fetch_education.py` to the current table names.

### 12.4 Education fetcher: per-sex-year chunking to stay within cell limit

**Symptom:** POST queries to `UF0506B/Utbildning` returned HTTP 403 (cell limit exceeded).

**Root cause:** The new education table disaggregates by Kön (sex) using only individual codes `'1'` and `'2'` (no `'1+2'` total). With 290 municipalities × 40 age codes × 8 education levels × 2 sex codes = 185 600 cells per year, the SCB limit of ~150 000 cells is exceeded.

**Fix applied:** The pipeline detects this condition (`len(sex_codes) > 1 and '1+2' not in sex_codes and len(age_codes) > 5`) and switches to `_fetch_chunked_by_sex_year`: one POST per (year, sex) combination. Each POST covers 290 × 40 × 8 × 1 = 92 800 cells, well within the limit. The two sex-specific frames are concatenated before aggregation. The `edu_share` variable (share with tertiary education, SUN codes 6+7) is computed after aggregating across sex, yielding the correct population-level share.

### 12.5 2009 skattekraft baseline required for 2010 growth computation

**Background:** The `tax_base_growth_pct` variable for year *t* is computed as `(skattekraft_t / skattekraft_{t-1} − 1) × 100`. The first year in the analysis window is 2010, so 2009 values are needed as the lag baseline.

**Fix applied:** `build_panel.py` fetches skattekraft for years 2009–2024 (constant `_FETCH_YEARS_SKATTEKRAFT`). After computing growth rates, the 2009 rows are dropped (`df_skatt_growth = df_skatt_growth[df_skatt_growth["year"].isin(_PANEL_YEARS)]`). The skattekraft cache file (`data/raw/skattekraft.json`) therefore covers 2009–2024, while the final panel covers only 2010–2024. The same logic applies to population: `_FETCH_YEARS_POPULATION` includes 2009 for the population growth computation.

---

**End of METHODOLOGY.md**