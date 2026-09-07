# METHODOLOGY.md - Methodology Bible

**Project:** Kommunal Skattekraft Stress Monitor

This document is both a development reference and the basis for the methodology section displayed in the dashboard. It documents the theoretical foundation, the exact regression specification, every formula, the evaluation criteria, and all known limitations.

For data sources and URLs, see `KRI_Dataset_Identification.md`. This document focuses on **why** and **how**, not **where the data lives**.

---

## 1. Theoretical Foundation

### 1.1 The economic question

Swedish kommuner finance their operations primarily through municipal income tax (kommunalskatt) levied on residents' taxable employment income. The tax base per inhabitant, *skattekraft*, is therefore the central determinant of a kommun's fiscal capacity.

Skattekraft varies enormously across the 290 kommuner: in 2024, Danderyd reported approximately 481 000 SEK per inhabitant while small Norrland kommuner reported under 150 000 SEK. The Swedish kommunalekonomisk utjämningssystem partially offsets these differences through grants from high-skattekraft to low-skattekraft kommuner, but the underlying tax base remains a real constraint on each kommun's fiscal autonomy and creditworthiness.

### 1.2 Why study skattekraft *growth* rather than levels

Levels are dominated by structural, slow-moving differences (industry composition, geography, settlement history). The interesting analytical and policy question is the *direction* of change: which kommuner are seeing their tax base erode or expand, and what structural factors drive this?

Growth rates are also stationary, which is required for valid panel inference. Levels are non-stationary in nominal SEK due to inflation and real growth.

### 1.3 Why structural factors

Standard public-finance literature (e.g. Bergvall et al. on Nordic municipal finance; OECD reports on subnational fiscal sustainability) identifies four structural drivers of municipal tax base trajectories:

1. **Labor market conditions** (unemployment): direct effect on income tax collected
2. **Demographic composition** (dependency ratio): share of population in tax-paying ages
3. **Population dynamics** (growth or decline): net migration affects future tax base
4. **Human capital** (education levels): predicts wage growth and labor force participation

These are the four right-hand-side variables in our model.

### 1.4 What this model is NOT

* **Not a causal model.** The estimated coefficients describe associations within a panel, not causal effects. Reverse causality (low growth leads to unemployment) is plausible. The fixed-effects specification controls for time-invariant confounders but not for simultaneity.
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
* `DeltaTaxBase_it` = year-over-year percent change in skattekraft per inhabitant, current SEK
* `alpha_i` = kommun fixed effect (290 dummies, one omitted)
* `gamma_t` = year fixed effect (15 dummies, one omitted)
* `beta_1, beta_2, beta_3, beta_4` = structural coefficients
* `epsilon_it` = idiosyncratic error

Since 2026-09-07 the **primary** version of this equation carries the RHS variables at *t−1*, not *t*. See §2.6 for the evidence and §2.7 for what this model is and is not used for.

### 2.2 Variable construction

| Variable | Construction |
|---|---|
| `tax_base_growth_pct` | `(skattekraft_t / skattekraft_{t-1} - 1) * 100` |
| `unemployment_rate` | Direct from SCB STATIV, percent |
| `dependency_ratio` | `(pop_0_19 + pop_65plus) / pop_20_64`, computed from BE0101 |
| `population_growth_pct` | `(pop_total_t / pop_total_{t-1} - 1) * 100` |
| `edu_share` | `100 × (SUN 6 + SUN 7) / (all SUN levels)`, ages 25–64, both sexes, from SCB UF0506 |

*The `edu_share` denominator was incomplete here until 2026-09-07 and is stated precisely now, because the choice moves the level materially.* The denominator is **every** person aged 25–64 including SUN level `US` — *uppgift om utbildningsnivå saknas*. Excluding the unknowns instead would raise Danderyd from 61.17 to 63.27 and Filipstad from 11.89 to 12.28 (2024), so the choice shifts levels by roughly 0.4–2.1 points and shifts them *unevenly*, more for high-education kommuner. It barely moves the ranking, but `edu_share` is the dominant cross-sectional driver (β × SD = +10.03), so any figure quoted from it depends on this convention. Verified live against SCB on 2026-09-07: the panel reproduces the with-`US` definition exactly (max abs diff 0.0).

### 2.3 Sample

* **Cross-sectional units:** 290 kommuner (all Swedish municipalities, 2024 boundaries)
* **Time period:** 2010 to 2026 (17 years, annual)
* **Total observations:** 4 930 (**unbalanced** — see 2.3.1)
* **Estimation sample:** 2010 to 2024, where all four structural variables exist
* **Lag for growth variables:** 2010 growth requires 2009 levels for skattekraft and population; ensure fetch covers 2009 even though 2009 is dropped from the regression sample.

#### 2.3.1 The panel is ragged at the top end

The four SCB sources refresh on different cadences and no longer share an end year:

| Source | Variables | Coverage |
|---|---|---|
| OE0101 skattekraft | `tax_base_per_capita`, `tax_base_growth_pct`, `tax_base_index_riket` | 2010–**2026** |
| BE0101 befolkning | `dependency_ratio`, `population`, `population_growth_pct` | 2010–**2025** |
| UF0506 utbildning | `edu_share` | 2010–**2025** |
| AA0003 arbetslöshet | `unemployment_rate` | 2010–**2024** |

Truncating every source to the shortest would discard the newest skattekraft, which is the point of maintaining current coverage. The panel is therefore anchored on skattekraft: every kommun-year with a skattekraft growth rate is a row, and shorter sources are null in the years they do not reach. All 290 kommuner are present in every year — the raggedness is across *variables*, never across municipalities.

`PanelOLS` tolerates unbalanced panels and the estimation `.dropna()` reduces the sample to complete cases, so the model is fit on 2010–2024 exactly as before.

**Any analysis needing all four structural variables must read `complete_case_max_year` from `artifacts/data_provenance.json` rather than assuming `max(panel.year)`.** That file records each source's coverage and is regenerated on every pipeline run. Assuming the panel's own maximum year would silently use 2026, where three of the four variables are null.

#### 2.3.2 Data status as of 2026-09-07, and when it changes

| Variables | Complete through | Constraint |
|---|---|---|
| skattekraft, growth, SCB index | **2026** | none — SCB publishes this two years ahead |
| dependency ratio, population, population growth | **2025** | 2026 population does not exist until Feb 2027 |
| education share | **2025** | 2026 education does not exist until 2027 |
| unemployment | **2024** | **the binding constraint** — see below |
| **all five together** | **2024** | `complete_case_max_year` |

**Why skattekraft is ahead is not an accident, and it is not a forecast.** Because of the t−2 rule (7.6), the tax base for year *t* is set from income in *t−2*: the 2026 figure reflects **2024 income**. It is a decided, published amount, not a projection. This also means pairing 2026 skattekraft with hypothetical 2026 values of the other variables would be pairing 2024 income with 2026 conditions — the ragged tail reflects the real structure of these statistics rather than a gap to be closed.

**The unemployment gap closes around February 2027.** `AA0003B/IntGr1KomUtbBAS` was last updated 2026-02-13 carrying 2022–2024, so the annual STATIV refresh appears to land in February. Until then no municipal open-unemployment figure for 2025 exists at SCB.

**Sources checked and ruled out for filling 2025 unemployment** (verified 2026-09-07 — recorded so this is not re-investigated):

| Source | Why not |
|---|---|
| `AA0003B/IntGr1KomUtbBAS` | the live STATIV table; `Tid` = 2022–2024, no 2025 |
| `AM0210D/ArRegArbStatus` (BAS) | municipal, but 2020–2024 and a different definition |
| `AM0401N/NAKUBefolkningLK` (AKU/LFS) | quarterly to 2026K2, but `Region` holds only **3 municipalities** (Stockholm, Malmö, Göteborg) out of 290. AKU is a sample survey — its own ContentsCodes include "Margin of error ±" — so municipal estimates for small kommuner are not producible |
| `AM0207` (RAMS) | municipal series end 2018/2021 |
| Kolada `N01720`, `N03937` | carry 2025, but at 0.72x and 3.65x our levels respectively; splicing puts a definitional break at the estimation year. See 12.6 |

**The cost of waiting is low.** Relative position is near-frozen: Spearman(position_t, position_t+1) = 0.991 and 0.929 at ten years. Moving the cross-section from 2024 to 2025 would move the median kommun **2 rank places out of 290**. The descriptive spine, which is what users see, is unaffected either way because it is computed from skattekraft alone and already runs to 2026.

### 2.4 Estimation

`linearmodels.PanelOLS` with `entity_effects=True, time_effects=True`. Standard errors clustered at kommun level (`cov_type='clustered', cluster_entity=True`).

### 2.5 Why two-way fixed effects

* `alpha_i` absorbs all time-invariant kommun characteristics: geography, industry mix, historical settlement, distance to Stockholm, language minority status, etc.
* `gamma_t` absorbs all aggregate annual shocks: national wage growth, federal policy changes, COVID, inflation surges, business cycle.
* What's left in `beta_1..beta_4` is the within-kommun, between-year association after both layers of fixed effects.

This is the standard specification in modern applied micro for panel data. It is not the only specification (random effects, between estimator, dynamic panel) but it is the most defensible default when both kommun and year heterogeneity matter.

### 2.6 Specifications: which one is primary

*Revised 2026-09-07 by REMEDIATION_PLAN.md T2.4. The full rewrite of this document is T4.1; this section is corrected early because it is what tells a reader which numbers to quote.*

The **lagged specification is primary**. `X_it` is replaced by `X_{i,t-1}` on the RHS; the contemporaneous specification is retained as a robustness check.

**Why the lag is primary, not a robustness check.** Within-kommun correlation between `tax_base_growth_pct` and each regressor, by lag, on the 2010–2026 panel (entity-demeaned, N = 4 350 at lags 0–2):

| Lag | `unemployment_rate` | `dependency_ratio` | `population_growth_pct` | `edu_share` |
|---|---|---|---|---|
| t (contemporaneous) | −0.180 | +0.151 | −0.132 | +0.217 |
| **t−1** | **−0.500** | **+0.376** | −0.087 | **+0.481** |
| t−2 | −0.405 | +0.288 | **−0.287** | +0.380 |
| t−3 | −0.152 | +0.235 | +0.115 | +0.323 |

Every regressor's association peaks at t−1 or later — three of four at t−1, population growth at t−2. This is what the two-year publication lag on skattekraft (§7.6) implies: the income year underlying a given skattekraft figure precedes it, so pairing `X_it` with `Y_it` pairs each regressor with an outcome partly determined before it was measured. Closes audit finding F4.

The estimated specifications agree. Values below are from `artifacts/coefficients.parquet`, which now carries a `role` column (`primary` / `robustness`) plus `n_obs` and `r_squared_within` per spec:

| | contemporaneous (`main`) | **lagged (primary)** |
|---|---|---|
| `unemployment_rate` | −0.0586 (t = −3.77) | **−0.1063 (t = −7.32)** |
| `dependency_ratio` | −3.746 (t = −4.63) | −3.805 (t = −4.88) |
| `population_growth_pct` | −0.0798 (t = −2.64) | −0.0792 (t = −2.57) |
| `edu_share` | +0.0187 (t = +0.65) | −0.0071 (t = −0.29) |
| R²(within) | 0.0083 | **0.0364** |
| N | 4 350 | 4 350 |

The lagged spec is better identified on the variable that carries the signal and explains 4.4× more of the within-kommun variation. It is also the only version usable for forecasting, since it needs no contemporaneous data. `edu_share` is insignificant in both (|t| < 0.7) and its sign flip between them is noise, not a finding — education is a between-kommun variable, and the entity effects absorb it (§7.7).

**A naming caveat.** The `spec` values in `coefficients.parquet` are unchanged: the demoted contemporaneous spec is still called `main`, because the deployed dashboard filters on that literal string and artifacts are a published contract (§11.7). Primacy is carried by the `role` column. The rename belongs to the UI cutover commit.

| Remaining robustness spec | Specification | Why |
|---|---|---|
| Contemporaneous | `X_it` on RHS | The pre-2026-09 primary; retained to show the lag is what changes the result |
| Drop COVID | Exclude 2020 and 2021 | COVID may dominate year FE |
| Larger kommuner only | Subsample with 2024 population > 10 000 | Small kommuner have noisier growth |
| Without education | Drop beta_4 | Education stock varies slowly; check if it materially changes other betas |

If the primary coefficients are stable across these specifications, the model is robust. If they flip sign or change magnitude dramatically, document and discuss.

### 2.7 What this model is for, after the 2026-09 remediation

*Added 2026-09-07 (T2.4).*

The two-way FE model is the **within-time inference panel**: it answers "within a kommun over time, how do its structural conditions move with its tax base growth?" It is not the ranking engine and never was one. 98.2 % of the variation in relative position is *between* kommuner (§1.2 of the remediation plan), and `alpha_i` absorbs exactly that variation. Ranking and the position decomposition come from the cross-sectional estimator (`src/model/estimate_cross.py`, `artifacts/coefficients_cross.parquet`).

The two models must be presented as separate findings under separate headings. The FE panel's heading is *"Samband inom kommuner över tid"* (`SWEDISH_LABELS["within_section_title"]`), and its accompanying caveat states that these coefficients cannot rank kommuner.

The vulnerability score and risk classes in `predictions.parquet` / `ranking.parquet` are **deprecated** as of T2.4: `compute_vulnerability` emits a `DeprecationWarning`, and both artifacts are written only until the dashboard reads position and drift instead. The 2025 horizon has since closed and the forecast has been scored against it — Pearson r = +0.016, Spearman = +0.033, RMSE 1.512 pp against a naive constant-mean benchmark of 0.974 pp, and risk classes that do not separate (realised growth 4.74 % låg, 4.52 % medel, 4.68 % hög). §3.4 still argues that predictive validity is the right standard; the model failed the standard it set. Replacing that section is T4.1's job.

---

## 3. Vulnerability Score (Path A: Prediction)

### 3.1 Construction

For each kommun *i*, compute predicted growth for 2025:

$$
\widehat{\Delta\text{TaxBase}}_{i, 2025} = \hat{\alpha}_i + \bar{\gamma}_{recent} + \hat{\beta}_1 \text{Unemployment}_{i, 2024} + \hat{\beta}_2 \text{DependencyRatio}_{i, 2024} + \hat{\beta}_3 \text{PopGrowth}_{i, 2024} + \hat{\beta}_4 \text{EduShare}_{i, 2024}
$$

Where:
* `alpha_hat_i` = estimated kommun fixed effect
* `gamma_bar_recent` = mean of estimated year fixed effects for 2022, 2023, 2024 (proxy for unobserved 2025)
* `beta_hat_k` = estimated coefficients
* RHS values are most recent observed (2024)

### 3.2 Standardization to vulnerability_score

To make scores comparable and interpretable as "vulnerability":

$$
\text{vulnerability\_score}_i = -1 \times \frac{\widehat{\Delta\text{TaxBase}}_{i, 2025} - \mu_{\text{predictions}}}{\sigma_{\text{predictions}}}
$$

Where mu and sigma are mean and standard deviation across all 290 predictions. The `-1` flips the sign so that **higher score = more vulnerable** (lower predicted growth).

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
| National mean skattekraft 2024 | Unweighted mean approximately 231 000 kr (range 200 000-350 000 kr) | Pipeline computed; note: SCB's published "riksmedelvärde" (~271 000 kr) is population-weighted and therefore higher |
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
| Mean tax_base_growth_pct over 2010-2024 | Positive, between 2.5% and 5% annually (observed: 2.65 %) |
| No kommun has tax_base_growth_pct below -10% in any year | True (observed min: -4.9 %; extreme outliers indicate data error) |
| 2020 growth distribution | Lower than 2019 (COVID effect visible; observed: 2019 mean 3.2 %, 2020 mean 2.2 %) |
| Dependency ratio range | 0.5 to 1.25 across kommuner (observed: 0.508-1.241) |

### 6.4 Model fit checks

| Check | Expected | Actual (2026-04-24 review) | Status |
|---|---|---|---|
| R2 (within) | Originally expected >0.10 | **0.0083** - see 7.10 for explanation | Note: Below prior expectation |
| At least 2 of 4 betas statistically significant | At cluster-robust 5% level | 3 of 4 significant (unemployment p<0.001, dependency p<0.001, population p=0.008; education p=0.52 n.s.) | Pass |
| Sign of beta_1 (unemployment) | Negative | **-0.059** (p<0.001) | Pass |
| Sign of beta_3 (population growth) | Originally expected positive | **-0.080** (p=0.008) - negative after two-way demeaning; see 7.11 | Note: Sign reversal (explained) |
| beta_4 (edu_share) significance | May be insignificant (7.7) | **+0.019** (p=0.52) - confirmed insignificant | Pass - Expected |

**Note on 6.4 enforcement:** These model fit checks are **diagnostic, not blocking**. Unlike the data integrity checks in 6.1-6.3 (which halt the pipeline on failure), the model fit checks are informational - a low R2(within) or an unexpected coefficient sign indicates that the specification should be interpreted carefully, but does not indicate a data error. The pipeline logs these results but does not halt, because the findings are empirically valid (see 7.10 and 7.11 for detailed explanations).

---

## 7. Known Limitations (volunteer in interviews)

These limitations are documented here, displayed in the dashboard's Metod section, and should be raised proactively in interviews. Interviewers respect candidates who self-criticize before being challenged.

### 7.1 Open arbetslöshet is a register-based proxy, not AKU

The unemployment variable comes from Arbetsförmedlingen registrations, not from the AKU labor force survey. AKU is the official unemployment statistic but is unavailable at kommun level for small kommuner due to sampling. Register-based open arbetslöshet captures only those who have registered with Arbetsförmedlingen, so it underestimates true unemployment among groups less likely to register (young people not yet eligible for benefits, some immigrants, etc.). It is, however, the standard kommun-level measure used by SKR and Finansdepartementet for kommun-level analysis.

### 7.2 No causal identification claim

Two-way FE controls for time-invariant confounders and aggregate year shocks. It does not address simultaneity (low growth leads to unemployment), measurement error, or omitted time-varying variables. The model is descriptive and predictive, not causal.

### 7.3 Predictions assume structural stability

The model is trained on 2010-2024 patterns. A 2025 shock unlike anything in the training period would not be captured. COVID is in the training data, which helps for similar future shocks, but a unique event (e.g. a major industrial closure in a single kommun) would be missed.

### 7.4 Year fixed effect proxy in prediction

The 2025 year fixed effect is unobserved. We proxy with the mean of 2022-2024 estimated year FE. This is a standard shortcut but introduces uncertainty not reflected in displayed prediction intervals. A more sophisticated approach would model year FE as a time series.

### 7.5 No housing or migration variables

Migration flows (in/out flytting) and housing market variables (kommun-level house prices) could strengthen the model but were descoped to maintain the 5-day timeline. Easy extension if pursued further.

### 7.6 Skattekraft published with 2-year lag relative to income year

The skattekraft figure for year *t* reflects income earned in year *t-2*. The 2025 published number reflects 2023 income. The dashboard displays this lag explicitly in tooltips and the methodology tab. For our growth rate calculation, this is consistent across years and does not bias the analysis, but it does mean "2024 skattekraft" actually summarizes 2022 economic activity.

### 7.7 Education variable moves slowly

The within-kommun variation in education share across 15 years is modest. beta_4 may have a wide confidence interval and may not be statistically significant. This is a known feature of slow-moving demographic stocks, not a defect in the model. If beta_4 is insignificant, we report it honestly and discuss interpretation.

### 7.8 Definition change in unemployment series (2018)

SCB updated the methodology for "Andel öppet arbetslösa" in 2018, applied retroactively to 1997. Pre-2018 published values may differ slightly from current values. We use the current (post-2018) consistent series throughout.

### 7.9 Unemployment rate is the SCB-published total aggregate

The pipeline requests unemployment rates using the SCB-provided total-aggregate codes (`BakgrVar='TOT'`, `Kön='1+2'`, `UtbNiv='000'`). These codes select the already-aggregated "all backgrounds, both sexes, all education levels" series that SCB publishes directly. No client-side averaging across sub-categories is performed.

This approach was adopted during pipeline implementation when the SCB STATIV tables were restructured (see 12.2). Using the published total avoids the weighting ambiguity entirely and ensures the series matches the aggregate figures SCB publishes in its statistical news releases.

### 7.10 Low R2(within) is expected after two-way demeaning

The within R2 of 0.0083 means that the four structural variables explain only 0.83% of the residual variation **after removing entity and year fixed effects**. This does not mean the model is useless - it means the entity and year effects absorb the vast majority of variation, which is the point of two-way FE.

**Why this is expected:**
* Entity fixed effects absorb all time-invariant kommun differences (geography, industry mix, commuting patterns, historical settlement) - these explain most cross-sectional variation in tax base growth.
* Year fixed effects absorb all aggregate annual shocks (national wage growth, inflation, policy changes, COVID) - these explain most time-series variation in tax base growth.
* What remains after absorbing both layers is the **within-kommun, between-year deviation from trend** - a very small residual signal.
* The individual coefficients are still statistically significant and economically meaningful: a 1 pp increase in unemployment within a kommun is associated with a -0.059 pp decrease in tax base growth, holding all else constant.

**Implications for prediction:**
* The vulnerability score is dominated by the entity fixed effects (historical patterns), not by current structural conditions.
* The structural variables contribute a small marginal adjustment on top of the entity-specific baseline.
* This is honest and should be communicated: the model ranks kommuner primarily by their historical trajectory, with modest adjustments for current structural conditions.

**In academic context:** Two-way FE specifications commonly show low within R2 in municipal-level panels (see Wooldridge 2010 ch. 10; Angrist & Pischke 2009 ch. 5). The R2 statistic is not the right criterion for assessing whether coefficients are informative - t-statistics and coefficient stability across robustness specifications are more relevant.

### 7.11 Population growth coefficient is negative after demeaning

The population growth coefficient beta_3 = -0.080 (p = 0.008) is negative, which contradicts the intuitive expectation (and the raw positive correlation) that growing populations should be associated with growing tax bases.

**Explanation:** After two-way demeaning:
* The raw (level) positive correlation between population growth and tax base growth reflects **between-kommun** differences: thriving kommuner have both growing populations and growing tax bases.
* The **within-entity** effect captures a different dynamic: when a specific kommun experiences above-trend population growth in a specific year (holding its time-invariant characteristics constant), the per-capita tax base may temporarily dilute. This happens because population inflows (especially young families, immigrants, or students) may initially contribute less to the per-capita tax base than the existing residents.
* This within-entity negative effect is consistent with findings in the municipal finance literature where rapid population growth creates a lag between population arrivals and tax base expansion.

**This is not a data error.** The "no_education" and "lagged" robustness specifications should be consulted to verify that the sign and magnitude are stable. If beta_3 flips sign in robustness checks, this finding should be treated with caution.

### 7.12 Nominal tax base growth includes inflation

`tax_base_growth_pct` is computed from nominal SEK values (not inflation-adjusted). The year fixed effects (gamma_t) absorb the common inflation component across all kommuner, so the beta coefficients capture the association between structural variables and growth **in excess of the national average**. However, the predicted growth for 2025 - which uses a year FE proxy - will include an inflation component. Users should interpret predicted growth rates as nominal, not real.

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

### 8.1 One variable is no longer reproducible from SCB

**Unemployment for 2010–2021 is reproducible from this repository, not from SCB.** SCB withdrew the AA0003X archive group in 2026 (see 12.6); the table that served those years returns HTTP 400, as does every other path into the group, and no replacement municipality-level open-unemployment series with pre-2022 history exists anywhere in the SCB API. Those 3 480 observations are served from `data/lookup/unemployment_2010_2021.csv`, a committed snapshot of the values fetched on 2026-04-24 while the archive was still live. 2022 onwards is still fetched from SCB on every run.

This is a real reduction in the reproducibility guarantee and is stated here rather than left implicit. What can still be verified independently:

* **The snapshot is the series SCB publishes, not a divergent vintage.** The overlap years 2022–2024 exist in both the snapshot-era fetch and the live table. `scripts/freeze_unemployment_snapshot.py` re-fetches them and refuses to write the snapshot if they disagree by more than 0.05 pp. At the freeze on 2026-09-07 the maximum absolute difference across all 870 overlapping kommun-years was 0.000000 pp.
* **The snapshot is a copy, not a re-derivation.** `tests/test_fetch_unemployment.py::TestSnapshotFile::test_matches_the_committed_panel_exactly` asserts the snapshot equals the committed panel row for row, so a silent change to the historical series fails the suite.

The snapshot can only be copied forward, never regenerated from source. Treat it as a source of record with the same care as the committed artifacts.

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

This section documents technical decisions made during the implementation of the data fetching pipeline (Tasks 1.2-1.6) that affect data quality, reliability, or reproducibility. These decisions are recorded here so that future maintainers and reviewers understand the rationale.

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
* **Soft checks** (log warning): unexpected but non-fatal observations (e.g. Stockholm not the largest kommune, unemployment mean outside the narrow 3-8 % historical range but within the wider 1-15 % plausible range). These may indicate data quality issues worth investigating but do not block the pipeline.

### 11.7 Artifacts are a published contract, not build output

`pipeline.py` runs locally, never on Streamlit Cloud, and every artifact in `artifacts/` is committed to git. The deployed dashboard therefore reads whatever artifact files are on the branch — it does not regenerate them. Three consequences that are easy to miss:

1. **Committing a changed artifact changes the live site immediately.** There is no build step between the parquet and the user.
2. **Changing an artifact's *schema* breaks the live site**, because the pages hardcode column names. `pages/02_Kommunjamforelse.py` names its five decomposition columns literally, and `app.py` reads the `main` coefficient spec by name. A renamed or dropped column surfaces as a crash or, worse, a silently mislabelled chart.
3. **Artifact and UI changes must therefore land together, or the artifact must be additive.** When a model change is being staged over several commits, write the new result to a *new* file (`*_cross.parquet`) and leave the existing one untouched until the UI cuts over in one deliberate change. This is why `coefficients_cross.parquet` and `decomposition_cross.parquet` exist alongside their predecessors rather than replacing them.

The same rule applies to `data/processed/panel.parquet`: adding the ragged 2025–2026 rows was safe only because every page filters to `year == 2024` explicitly rather than taking `max(year)`.

---

## 12. SCB API Structural Changes Discovered During Implementation

This section documents the SCB PxWeb API changes encountered and adapted to during pipeline implementation. Future maintainers should consult this section first if any fetcher fails with HTTP 400 or HTTP 403 errors.

### 12.1 Value-set filter `vs:RegionKommun07EjAggr` is no longer accepted

**Symptom:** All four fetchers returned HTTP 400 on POST queries that used `"filter": "vs:RegionKommun07EjAggr"` with an empty `"values": []` list.

**Root cause:** The SCB PxWeb v1 API no longer honours the `vs:` (value-set) filter syntax for the Region dimension. The documentation still lists this filter type, but the API rejects it.

**Fix applied (all four fetchers):** At fetch time, the pipeline first calls the metadata endpoint (`GET /api/v1/...`) to retrieve all Region dimension codes. It then filters to 4-digit all-numeric codes (`len(c) == 4 and c.isdigit()`) to isolate the 290 municipality codes (county codes are 2 digits; the national total is `"00"`). The POST query then uses `"filter": "item"` with the explicit list of 290 codes. This produces identical results to the value-set filter and is robust to future value-set changes.

### 12.2 SCB STATIV AA0003 unemployment table restructure

**Symptom:** Metadata GET for the old `AA0003B/IntGr1KomKonUtb` subtable returned HTTP 400 ("table not found").

**Root cause:** SCB reorganized the STATIV unemployment tables around 2023-2024. The old subtable `AA0003B/IntGr1KomKonUtb` (and its siblings `IntGr1KomKon`, `IntGr1Kom`) were moved to an archive path `AA0003X`. A new subtable `AA0003B/IntGr1KomUtbBAS` was introduced but only covers 2022 onwards.

**Fix applied:** The `fetch_unemployment` module uses a two-table strategy:

| Year range | Table URL | Coverage |
|---|---|---|
| 2010-2021 | `AA0003X/IntGr1KomKonUtb` | 1997-2021 (archived, still accessible) |
| 2022-2024 | `AA0003B/IntGr1KomUtbBAS` | 2022-present |

Results from both sources are concatenated to form the complete series. Constants `_SNAPSHOT_LAST_YEAR = 2021` and `_LIVE_TABLE_FIRST_YEAR = 2022` control the split. The archived table referenced here was subsequently withdrawn altogether; see 12.6 for what replaced it.

**Total-code optimization:** Both tables provide total-aggregate codes (`BakgrVar='TOT'`, `Kön='1+2'`, `UtbNiv='000'`). The pipeline selects these codes directly, reducing each POST to 290 x 1 x 1 x 1 x n_years cells (well within SCB's ~150 000-cell limit). This also avoids the unweighted-mean approximation described previously in 7.9.

### 12.3 SCB UF0506 education table renamed

**Symptom:** Metadata GET for candidate URLs `UF0506B/Utbildning4`, `UF0506B/Utbildning3`, and `UF0506B/Utbildning4C` all returned HTTP 400.

**Root cause:** SCB consolidated the UF0506 education disaggregation tables. The active subtable is now `UF0506B/Utbildning` (covering 1985-2024). A backup candidate `UF0506B/UtbBefRegionR` is tried if the primary fails.

**Fix applied:** Updated `_CANDIDATE_URLS` in `fetch_education.py` to the current table names.

### 12.4 Education fetcher: per-sex-year chunking to stay within cell limit

**Symptom:** POST queries to `UF0506B/Utbildning` returned HTTP 403 (cell limit exceeded).

**Root cause:** The new education table disaggregates by Kön (sex) using only individual codes `'1'` and `'2'` (no `'1+2'` total). With 290 municipalities x 40 age codes x 8 education levels x 2 sex codes = 185 600 cells per year, the SCB limit of ~150 000 cells is exceeded.

**Fix applied:** The pipeline detects this condition (`len(sex_codes) > 1 and '1+2' not in sex_codes and len(age_codes) > 5`) and switches to `_fetch_chunked_by_sex_year`: one POST per (year, sex) combination. Each POST covers 290 x 40 x 8 x 1 = 92 800 cells, well within the limit. The two sex-specific frames are concatenated before aggregation. The `edu_share` variable (share with tertiary education, SUN codes 6+7) is computed after aggregating across sex, yielding the correct population-level share.

### 12.5 2009 skattekraft baseline required for 2010 growth computation

**Background:** The `tax_base_growth_pct` variable for year *t* is computed as `(skattekraft_t / skattekraft_{t-1} - 1) x 100`. The first year in the analysis window is 2010, so 2009 values are needed as the lag baseline.

**Fix applied:** `build_panel.py` fetches skattekraft from 2009 (constant `_FETCH_YEARS_SKATTEKRAFT`). After computing growth rates, the 2009 rows are dropped (`df >= _PANEL_START_YEAR`). The skattekraft cache therefore begins in 2009 while the panel begins in 2010. The same logic applies to population: `_FETCH_YEARS_POPULATION` includes 2009 for the population growth computation.

### 12.6 SCB withdrew the AA0003X archive group entirely

**Symptom:** `GET .../AA/AA0003/AA0003X/IntGr1KomKonUtb` returns HTTP 400. So does the group URL `.../AA/AA0003/AA0003X` itself, and so do the sibling tables `IntGr1KomKon` and `IntGr1Kom`. The group is still *listed* in the `AA0003` directory response as "Äldre tabeller som inte uppdateras", but every path into it is unreachable.

**Root cause:** SCB retired the archive rather than the single table. Unlike 12.2, 12.3 and 12.4 — which were renames and reorganisations, recoverable by pointing the fetcher at the new URL — this is a withdrawal. Verified on 2026-09-06 and re-verified 2026-09-07.

**Impact:** Open unemployment for 2010–2021 (3 480 kommun-year observations) cannot be fetched from SCB by any route. Searched and ruled out: `AA0003B` (labour market, `Tid` = 2022–2024 only), `AA0003E` (demography), `AA0003H` (education), `AM0207` RAMS (municipal series end 2018/2021), and `AM0210D` BAS (kommun-level but 2020–2024 only, and a different unemployment definition).

**Fix applied:** Option A of REMEDIATION_PLAN.md T0.2a. `fetch_unemployment` now reads 2010–2021 from the committed snapshot `data/lookup/unemployment_2010_2021.csv` and 2022 onwards from the live `AA0003B/IntGr1KomUtbBAS`. The dead `_PRIMARY_TABLE_URL` constant was removed so no code path can request the withdrawn archive. See 8.1 for the reproducibility consequence and DEVIATIONS.md 6.1 for the decision record.

**Considered and rejected (unemployment):** re-sourcing the full history from Kolada or Arbetsförmedlingen. Both are live and carry a 2010-onwards municipal series, and both rank kommuner almost identically to the SCB series (Spearman +0.926 and +0.952 against our 2024 values), but neither matches its *level*: Kolada `N03937` runs 3.65x below our series, `N01720` 0.72x above. The gap is definitional, not an error in either series — ours is a **flow** measure (registered as openly unemployed at any point during the year, over population 20-64; see KRI §3), while `N03937` is a stock-like annual average over population 18-65, itself carrying an 18-64 → 18-65 age-band change at 2023. Splicing either onto 2010–2021 would put a step change at the 2021/2022 seam, inside the within-kommun time variation the FE model reads as signal — a series break disguised as continuity, which is worse than a documented snapshot. High rank agreement means these remain viable *fallbacks* if SCB withdraws more; it does not make them drop-in replacements.

### 12.7 SCB split the population table at 2024/2025

**Symptom:** `BE0101A/BefolkningNy` metadata still resolves, but its `Tid` dimension stops at 2024 (last updated 2025-02-21) even though SCB published 2025 population in February 2026. Nothing errors — the fetcher would simply have returned a series one year shorter than available and the panel would have looked complete.

**Root cause:** SCB froze the long historical table and published 2025 in a *new parallel table*, `BE0101A/BefolkningCKM` ("Folkmängden efter region, civilstånd, ålder och kön. År 2025"). The same pattern appears across BE0101A: `FolkmangdDecCKM`, `BefolkManadCKM`, `BefolkningR1860NCKM`. This is the fifth structural change this project has absorbed, and the first that fails *silently* rather than with an HTTP error.

**Three incompatibilities between the two tables**, each of which would corrupt the panel quietly rather than loudly:

| | BefolkningNy (≤2024) | BefolkningCKM (2025) |
|---|---|---|
| ContentsCode for Folkmängd | `BE0101N1` | `000007ME` |
| `Civilstand` | eliminates (auto-summed) | does **not** eliminate |
| Open-ended age code | `100+` | `100+1` |

The sibling ContentsCode in both tables is Folkökning (population *change*, not level), so a positional or first-code guess would have silently substituted the wrong metric. Because `Civilstand` no longer eliminates, omitting it returns one row per civil status — inflating every count — and the extra response column would otherwise have been read as the value column.

**Fix applied:** `fetch_population` now probes candidate tables and routes each requested year to whichever table's `Tid` declares it, so a future split needs a new candidate URL rather than new year logic. Every table-specific detail is resolved from that table's own metadata: `_contents_code` matches on the valueText "Folkmängd", `_age_codes` picks whichever open-ended code exists, and `_build_year_query` pins `Civilstand` to its total only when the dimension does not eliminate. `_aggregate_to_age_groups` drops `Civilstand` explicitly.

**Validated:** the 2025 fetch returns 290 kommuner and a national population of 10 605 366, against 10 587 710 for 2024 — a plausible +0.17 %. Age-group totals and per-kommun year-over-year changes are all in range.

> **A fourth incompatibility, found 2026-09-07 by a live review and not caught by the validation above.** That validation compared 2025 against 2024 and asked whether the change was plausible. It never compared 2025 against **SCB's own published total for 2025**, which is what would have caught this. See §12.8.

---

### 12.8 BefolkningCKM's cells are disclosure-protected; its parts no longer sum to its totals

*Found 2026-09-07 during a live review of Phase 0.*

**Symptom:** the project's 2025 population is **10 605 366**. SCB's published total for the same 290 kommuner (`Alder=TotSA`, `Kon=TotSa`, `Civilstand=SC`) is **10 605 520** — 154 people more. The discrepancy is not national rounding: 286 of 290 kommuner differ, in **both directions**, and it is proportionally worst in the smallest kommuner.

| | shortfall as % of published |
|---|---|
| Överkalix (3 183 inhabitants) | **+1.005 %** |
| Hällefors | +0.654 % |
| median kommun | 0.000 % |
| most over-counted kommun | −0.723 % |

**Root cause:** `BefolkningCKM` applies cell-level disclosure protection that `BefolkningNy` did not. Its marginal totals exceed the sum of the categories beneath them in *every* dimension — for Stockholm 2025, `Kon=TotSa` exceeds män+kvinnor by 7, `Alder=TotSA` exceeds the sum of single years by 2, and `Civilstand=SC` exceeds the four statuses by 4. Because `fetch_population` builds each kommun's population by summing roughly 200 cells (101 single-year ages × 2 sexes), it accumulates that perturbation. Reading the same year at 5-year bands gives a third answer again, differing from the single-age sum by up to 90 people.

For 2024 and earlier this cannot happen: a live re-fetch of `BefolkningNy` confirms the sum of single ages equals the published `Alder='tot'` aggregate **exactly**, for all 290 kommuner (max abs diff 0.0000).

**Consequences, measured:**

* `population` 2025 — off by up to ±1 % in the smallest kommuner.
* `population_growth_pct` 2025 — biased by that same amount. At Överkalix that is **1.005 pp against a variable whose SD is 1.013**: one full standard deviation.
* `dependency_ratio` 2025 — the perturbation partly cancels between numerator and denominator, but not fully: against a 5-year-band computation it differs by up to 0.036 (median 0.0015) on a variable whose SD is 0.101, so ~0.35 SD at worst, again in the smallest kommuner.
* **No model result is affected today.** `complete_case_max_year` is 2024, so 2025 enters no specification: not the FE panel, not the 2024 cross-section, not the decomposition. Relative position and drift come from skattekraft alone and are untouched.

**Not yet fixed.** The fix is to stop deriving the total by summation: read `population` from the published aggregate and keep the single-age query only for the age groups it is actually needed for, or move the age groups to 5-year bands. This becomes load-bearing the moment SCB publishes 2025 unemployment (expected February 2027), because `complete_case_max_year` then moves to 2025 and these values enter the estimation sample.

---

**End of METHODOLOGY.md**