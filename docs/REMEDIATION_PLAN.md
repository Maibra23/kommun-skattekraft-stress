# REMEDIATION_PLAN.md — Model Layer Remediation (14 tasks, 4 phases)

**Project:** Kommunal Skattekraft Stress Monitor
**Created:** 2026-09-05
**Status:** Not started
**Trigger:** Skattekraft Model Audit, 2026-09-04
**Audit report:** https://claude.ai/code/artifact/b3dfec90-7359-45fa-91d8-ea137080eb42

**References:** `METHODOLOGY.md` (current model and formulas — several sections are corrected by this plan), `PRD.md` §4–5 (variable and model spec — §5 is unlocked by this plan), `KRI_Dataset_Identification.md` (SCB tables and queries), `DEVIATIONS.md` (log of departures from plan).

---

## 1. Why This Plan Exists

### 1.1 The one-sentence diagnosis

**The estimator and the product are pointed at different variance.** Two-way fixed effects removes between-kommun variation by construction; the product is a between-kommun ranking. The model therefore discards 98.3 % of the variation the ranking is about and fits the remaining 1.7 %, which is close to white noise.

This is a **specification mismatch, not a bug and not an architecture failure.** No restructuring of the repository is required. The mismatch lives entirely in `src/model/` (777 lines across three files) and the three test files that encode the old estimand. The fetch layer, panel builder, kommunkod harmonisation, artifact contract, and dashboard shell (~6 500 lines) are sound and stay.

### 1.2 The evidence

Measured from SCB OE0101 (2005–2026, all 290 kommuner) and the committed artifacts, on 2026-09-04:

| Finding | Value | Implication |
|---|---|---|
| Share of variance in relative position that is **between** kommuner | **98.3 %** | Entity FE deletes almost all usable signal |
| Rank stability of relative position, 1 year | **0.992** | The cross-section is near-frozen |
| Rank stability of relative position, 10 years | **0.915** | Filipstad: index 75 (2010) → 76 (2026) |
| Year-to-year persistence of growth rate | **−0.06** | The current target is serially unpredictable |
| Current model, R²(within) | **0.0083** | Symptom of the mismatch, not a curiosity |
| Current model, out-of-sample 2025 forecast | **r = 0.016** | Loses to a constant national-mean guess (RMSE 1.51 vs 0.97 pp) |
| Risk classes vs realised 2025 growth | hög 4.68 %, medel 4.52 %, låg 4.74 % | No separation, wrong order |
| Vulnerability score vs **past** 5-yr drift | **−0.653** | It is a backward-looking descriptor … |
| Vulnerability score vs **future** 2-yr drift | **−0.165** | … presented to users as a forecast |

### 1.3 The constructive test — why the fix is known to work

Same four variables, same panel, cross-sectional specification instead of within:

| Specification | Result |
|---|---|
| Current: two-way FE on 1-yr growth | R²(within) = **0.008** |
| Cross-section on relative position (riket = 100), 2024 | R² = **0.692** |
| 5-yr drift in relative position, in-sample | R² = 0.291 |
| **5-yr drift, honest out-of-sample** (fit 2014→19, test 2019→24) | **r = +0.364**, Spearman +0.315 |
| Current 1-yr growth forecast, out-of-sample | r = +0.016 |

The four theory-driven variables explain **83× more** of the variation the ranking is about, and forecast medium-term drift **~23× better** than the current setup forecasts next-year growth. **Variable selection was never the problem. The estimand was.**

### 1.4 What this plan does and does not fix

| Audit finding | Fixed by | How |
|---|---|---|
| F2 — 2025 horizon closed, two releases behind SCB | Phase 0 | Extend to 2026, backtest becomes possible |
| F1 — SCB's official index `OE0101B0` unused | Phase 0 + 1 | Fetched and made the descriptive spine |
| **Estimand mismatch (Finding 0, this plan)** | **Phase 2** | Re-point the model at the cross-section |
| F5 — insignificant `edu_share` drives 25 % of ranking | Phase 2 | Cross-section gives it a real, significant role |
| F3 — collinearity never checked | Phase 2 | VIF/condition-number diagnostics added and published |
| F4 — regressors mis-timed vs t−2 income lag | Phase 2 | Lagged spec promoted to primary FE spec |
| F6 — "vikter" mislabels coefficients | Phase 4 | Relabelled |
| §7.10 states FE dominate the score (they contribute 8.8 %) | Phase 4 | Corrected in docs and Metod tab |
| Forecast framing not supported by backtest | Phase 3 + 4 | Demoted, backtested, or dropped |

**Explicitly not fixed, by design:** causal identification. The cross-sectional specification is *descriptive attribution*, not causal decomposition — dependency ratio, education and unemployment are jointly determined with income levels, and collinearity bites harder in the cross-section, not less. `METHODOLOGY.md` §7.2 must be carried over verbatim and strengthened. Do not let the higher R² tempt anyone into causal language.

---

## 2. How to Use This Document

Each task carries:

* **ID and title** · **Phase** · **Estimated time** · **Delegation** (see §3)
* **Files:** exactly which paths are created or modified
* **Depends on:** blocking task IDs
* **What / Why / How:** the change, the audit finding it closes, the technical approach
* **Definition of done:** objective acceptance criteria

### Rules that carry over from the existing project

1. **Two-layer language rule.** Code, comments and column names in English. All user-facing text in Swedish via `SWEDISH_LABELS` in `src/ui/labels.py`. No Swedish string literals in page files.
2. **Reference docs by section, not paraphrase.** Read `METHODOLOGY.md` and `PRD.md` directly.
3. **No hardcoded paths.** `pathlib.Path` relative to project root.
4. **Immutability.** Functions return new DataFrames; never mutate an input in place.
5. **Many small files.** 200–400 lines typical, 800 max. Extract rather than extend.
6. **TDD.** Write the failing test first, then the implementation. Hard checks raise; diagnostic checks log (existing severity policy, `METHODOLOGY.md` §11.6).
7. **Determinism.** Pipeline must reproduce artifacts byte-identically given the same cached SCB data.

### Progress tracking

Update the checklist in §8 as tasks complete. Append every deviation to `DEVIATIONS.md` — that file's audit trail is one of this project's genuine strengths and it must not lapse.

---

## 3. Delegation Model

Tasks are marked with one of:

* **`[SOLO]`** — do in the main session. Touches shared contracts, or requires judgment calls that need the full conversation context.
* **`[SUBAGENT]`** — safe to delegate to a single fresh agent. Self-contained: clear inputs, clear outputs, no shared-state edits.
* **`[PARALLEL-n]`** — belongs to a group of independent tasks that can run as concurrent subagents. Tasks sharing the same `n` have no file overlap and no ordering dependency between them.

Two hard rules for delegation:

* **Never delegate two tasks that write the same file.** The parallel groups below are already checked for file-disjointness.
* **A subagent gets the audit context or it will re-derive the wrong conclusion.** Every delegated prompt must open with: *"Read `docs/REMEDIATION_PLAN.md` §1 before starting."* A cold agent that reads only `METHODOLOGY.md` will faithfully reproduce the mismatched specification, because `METHODOLOGY.md` still documents it until Phase 4.

---

## 4. PHASE 0 — Data Foundation

*Unblocks everything else. Nothing in Phases 1–3 can be validated until 2025 and 2026 are in the panel.*

### T0.1 — Fetch SCB's official index and extend coverage to 2026
**Phase:** 0 · **Time:** 1–2 h · **`[SOLO]`**
**Files:** `src/fetch/fetch_skattekraft.py`, `src/clean/build_panel.py`, `docs/KRI_Dataset_Identification.md` §2
**Depends on:** —

**What:** Add `OE0101B0` ("Andel av riksmedelvärdet, procent") to the skattekraft query alongside the existing `OE0101A0`, and extend `_FETCH_YEARS_SKATTEKRAFT` through 2026.

**Why:** Closes audit findings F1 and F2. SCB publishes an official riket = 100 index — the exact figure Regionfakta republishes — and the pipeline has never read it. It is one extra value in the `ContentsCode` array of a POST the pipeline already makes. Extending to 2026 converts the untestable 2025 "forecast" into a scoreable one and puts the project back level with its own source.

**How:** `ContentsCode` selection becomes `["OE0101A0", "OE0101B0"]`. The PxWeb response gains a column; `_clean_response` must map it to a new panel column `tax_base_index_riket` (integer percent, SCB-rounded). Note the cell-limit maths is unaffected: 290 × 2 metrics × 18 years = 10 440 cells, far under ~150 000. Delete the stale skattekraft cache so the new metric is actually fetched.

**Caution:** SCB's published index is **population-weighted** (riksmedelvärde ≈ 271 000 kr for 2026), while the pipeline's own unweighted mean is ≈ 231 000 kr. These are different denominators and must never be mixed in one chart. `METHODOLOGY.md` §7.13 already documents this; keep both series and label each explicitly.

**Definition of done:**
- `data/processed/panel.parquet` has a `tax_base_index_riket` column, non-null for every kommun-year.
- Riket check: skattekraft 251 437 (2024), 262 711 (2025), 270 969 (2026).
- Spot check: Danderyd index 191 (2026), Filipstad 76, Högsby 73.
- `KRI_Dataset_Identification.md` §2 lists all three ContentsCodes and states which are used.

---

### T0.2 — Extend the full panel to 2026 and rebuild
**Phase:** 0 · **Time:** 2–4 h · **`[SOLO]`**
**Files:** `src/clean/build_panel.py`, `src/fetch/fetch_population.py`, `src/fetch/fetch_unemployment.py`, `src/fetch/fetch_education.py`, `pipeline.py`
**Depends on:** T0.1

**What:** Push every fetcher's year range to the latest available and rebuild the panel. Handle the near-certainty that the four SCB series have **different end years**.

**Why:** The four sources refresh on different cadences (skattekraft December, befolkning February, utbildning April–May, STATIV mid-year). The panel is currently balanced only because 2024 happened to be available everywhere.

**How:** Do **not** force a balanced panel by truncating to the shortest series — that throws away the newest skattekraft, which is the whole point of Phase 0. Instead: let the panel be ragged, record `max_year` per source in a small provenance dict written to `artifacts/`, and make each downstream consumer state which year it uses. `PanelOLS` tolerates unbalanced panels; the estimation `.dropna()` already handles it. Update the row-count sanity checks in §6.1–6.3 of `METHODOLOGY.md`, which currently hardcode 4 350.

**Watch for:** `AA0003B/IntGr1KomUtbBAS` (unemployment, 2022+) and `UF0506B/Utbildning` may have moved again — `METHODOLOGY.md` §12 documents three separate SCB restructures in this project's short life. Budget time for a fourth. Metadata GET first, always; never assume a table URL.

**Definition of done:**
- Panel covers 2010 through each source's true maximum year.
- Provenance artifact records `max_year` per source.
- All §6.1–6.3 sanity checks pass with updated expected counts.
- `python pipeline.py` runs end to end from cold cache.

---

### T0.3 — Freeze the audit baseline as a regression fixture
**Phase:** 0 · **Time:** 1 h · **`[SUBAGENT]`**
**Files:** `tests/fixtures/audit_baseline_2026-09-04.json` (new), `tests/test_audit_baseline.py` (new)
**Depends on:** —  *(can run before or during T0.1/T0.2 — reads only committed artifacts)*

**What:** Capture the audit's headline numbers from the **current** committed artifacts as a locked JSON fixture, with a test that asserts them.

**Why:** Phases 1–3 replace the model layer. Without a frozen baseline there is no way to demonstrate that the new specification is better rather than merely different, and the audit's numbers exist only in a chat transcript and a published artifact.

**How:** Record at minimum: the four main-spec coefficients and p-values; R²(within) = 0.0083; the variance decomposition (dependency 59.1 %, education 25.1 %, unemployment 15.1 %, entity FE 8.8 %, population −8.2 %); β × within-SD for each variable; the 2025 backtest (r = 0.016, Spearman 0.033, RMSE 1.512 vs naive 0.974); and the three risk-class means. Test asserts to 3 decimal places against the committed artifacts and is marked `@pytest.mark.baseline` so it can be excluded once the old model is retired.

**Definition of done:** Fixture committed; test passes against current artifacts; a one-line comment in the fixture points to this plan and the audit URL.

---

## 5. PHASE 1 — The Descriptive Spine

*Rank stability is 0.992 year-over-year. The most useful, most defensible thing this project can show requires no model at all. Build that first, and let the model become the "why" rather than the "what".*

### T1.1 — Relative position and drift module
**Phase:** 1 · **Time:** 3–4 h · **`[SUBAGENT]`**
**Files:** `src/model/position.py` (new), `tests/test_position.py` (new)
**Depends on:** T0.1, T0.2

**What:** A new module computing, per kommun-year: relative position (riket = 100, both SCB's published index and a finer unrounded ratio version), and drift over 1, 3, 5 and 10-year windows. Writes `artifacts/position.parquet`.

**Why:** This is the product's new spine. It answers the actual user question — *where does my kommun stand and which way is it moving?* — with 0.99 rank reliability and zero model risk. The audit showed the current vulnerability score correlates −0.65 with past drift; drift is what the score was really measuring all along, so compute it directly and honestly instead of inferring it through a misfired regression.

**How:** Keep SCB's `tax_base_index_riket` as the headline (it is the official, population-weighted, citable figure that matches Regionfakta) and compute an unrounded `relative_position` = kommun ÷ unweighted cross-kommun mean × 100 for internal analysis, since SCB's integer rounding is too coarse for drift over short windows. Drift is a simple difference in position, in index points — *not* a growth rate. Pure functions, no I/O outside the writer.

**Definition of done:**
- `artifacts/position.parquet`: one row per kommun-year, columns `kommun_kod`, `year`, `tax_base_index_riket`, `relative_position`, `drift_1y`, `drift_3y`, `drift_5y`, `drift_10y`.
- Test asserts Spearman(position_t, position_t+1) > 0.98 and > 0.90 at 10 years.
- Test asserts riket-level index is 100 in every year.

---

### T1.2 — Make position and drift the dashboard's lead
**Phase:** 1 · **Time:** 4–6 h · **`[SOLO]`**
**Files:** `app.py`, `pages/01_Riksoversikt.py`, `pages/02_Kommunjamforelse.py`, `src/ui/labels.py`, `src/ui/choropleth.py`
**Depends on:** T1.1

**What:** Restructure the three pages so relative position and drift are the primary view, and the model output becomes secondary explanation.

**Why:** Currently a model-derived score with r = 0.02 predictive power is the headline and the reliable descriptive fact is absent. Inverting that is the single largest honesty improvement available, and it costs no analytical capability.

**How:** Landing page leads with position + drift. Choropleth gets a layer toggle: *nuvarande position* / *5-årig förflyttning* / *sårbarhetsindex*. Kommun detail page leads with "Din kommun ligger på index 76 av riksmedelvärdet, en förflyttning på −1,2 indexenheter sedan 2019." Every new string goes through `SWEDISH_LABELS`.

**Caution:** The colour semantics differ between layers and must not be shared. Position is a *level* (sequential scale). Drift is *signed* (diverging scale, zero at white). Reusing the vulnerability palette for drift will mislead.

**Definition of done:** All three pages render; no Swedish literals outside `labels.py`; choropleth toggle works; existing `tests/test_choropleth.py` passes or is updated.

---

### T1.3 — Show SCB's index next to the project's own score
**Phase:** 1 · **Time:** 1–2 h · **`[PARALLEL-A]`**
**Files:** `pages/02_Kommunjamforelse.py`, `src/ui/labels.py`
**Depends on:** T1.1

**What:** On the kommun page, display SCB's official `andel av riksmedelvärdet` beside the project's own measures, with a short note on how they differ.

**Why:** Closes audit finding F1. Users — controllers, credit analysts — arrive already knowing the Regionfakta figure. Correlation between the vulnerability score and SCB's index is only −0.56, so a kommun can look fine on one and poor on the other (Årjäng: index 75, 7th-poorest in Sweden, but ranked 176/290 "medel"). Showing both anchors the user and makes the case for what a forward-looking measure adds.

**Definition of done:** Kommun page shows SCB index for the latest year with source attribution; note explains level vs change and weighted vs unweighted.

---

## 6. PHASE 2 — Re-point the Model at the Cross-Section

*The core of the remediation. This is where Finding 0 is actually closed.*

### T2.1 — Cross-sectional estimator
**Phase:** 2 · **Time:** 4–6 h · **`[SOLO]`**
**Files:** `src/model/estimate_cross.py` (new), `tests/test_estimate_cross.py` (new)
**Depends on:** T0.2, T1.1

**What:** Estimate relative position on the four structural variables in the cross-section, for the latest year and pooled across years with year effects only (no entity effects).

**Why:** This is the fix. The same four variables reach R² = 0.692 on the cross-section versus 0.0083 within — 83× more of the variation the ranking is about. Entity FE was deleting the signal; removing it recovers it.

**How:** Two specifications. (a) Single-year OLS on the latest year, HC3 robust SE — the interpretable headline. (b) Pooled across years with year effects and kommun-clustered SE — for stability checking. **Do not add entity effects to either**; that would reintroduce the exact mismatch this task exists to remove. Expected signs from the audit run: dependency −6.08, unemployment −1.41, education +1.28, population growth −0.72.

**Caution — the central interpretive risk of this whole plan:** R² = 0.69 is partly mechanical. Education share, dependency ratio and unemployment are jointly determined with income levels; this is *association within a cross-section*, not causation. Every coefficient shipped from this module must be labelled descriptive. Carry `METHODOLOGY.md` §7.2 forward and strengthen it. If anyone starts saying "raising education by 1 pp would raise the tax base by 1.28 index points", the plan has failed.

**Definition of done:**
- `artifacts/coefficients_cross.parquet` with both specs, coefficients, robust SE, p-values, CIs, R².
- Latest-year R² > 0.60.
- Test asserts sign and rough magnitude of all four coefficients.
- Module docstring states the descriptive-not-causal constraint.

---

### T2.2 — Level decomposition
**Phase:** 2 · **Time:** 3–4 h · **`[SUBAGENT]`**
**Files:** `src/model/decompose.py` (rewrite), `tests/test_decompose.py` (rewrite)
**Depends on:** T2.1

**What:** Replace the growth-gap decomposition with a decomposition of each kommun's *position* gap versus riket, using the cross-sectional coefficients.

**Why:** The current decomposition answers "why did Filipstad grow 1.8 pp below average in 2024?" — a question about a noisy, non-persistent quantity where the residual dominates. The new one answers "why does Filipstad sit at index 76?", which is stable, is what users actually ask, and where the four variables explain ~69 % rather than ~1 %.

**How:** Same additive structure as the existing module (`β_k × (X_ki − X̄_k)`, residual absorbs the rest, exact sum check to 1e-10 — keep that check, it is good). The change is the target and the coefficient source. The residual should shrink dramatically; if it does not, stop and investigate before proceeding.

**Definition of done:**
- `artifacts/decomposition.parquet` decomposes position gap; components sum exactly.
- Mean |residual| share of total gap **< 40 %** (currently the residual dominates).
- Test covers the sum identity and a hand-computed single-kommun case.

---

### T2.3 — Collinearity diagnostics
**Phase:** 2 · **Time:** 2 h · **`[PARALLEL-B]`**
**Files:** `src/model/diagnostics.py` (new), `tests/test_diagnostics.py` (new)
**Depends on:** T2.1

**What:** Compute and persist VIF, the design-matrix condition number, and the pairwise correlation matrix — for both the within and cross-sectional designs.

**Why:** Closes audit finding F3. Three of six within-kommun pairs exceed |0.65| (dependency × education +0.714, unemployment × dependency −0.703, unemployment × education −0.655) and this was never checked. Collinearity bites *harder* in the cross-section, so shipping T2.1 without this diagnostic would be a regression in rigour, not an improvement. The decomposition chart currently splits what is substantially one rural-ageing-low-education factor into four bars, and users deserve to be told.

**How:** Standard VIF via auxiliary regressions. Flag VIF > 5 as a warning, > 10 as severe. Write `artifacts/diagnostics.parquet`. Diagnostic severity, not blocking (per §11.6 policy).

**Definition of done:** Artifact written for both designs; test asserts VIF is computed for all four variables and that the known high-correlation pairs are flagged.

---

### T2.4 — Demote the FE model to an inference panel
**Phase:** 2 · **Time:** 2–3 h · **`[SOLO]`**
**Files:** `src/model/estimate.py`, `src/model/predict.py`, `src/ui/labels.py`
**Depends on:** T2.1

**What:** Keep the two-way FE model. Promote the `lagged` specification to primary. Stop letting either generate the ranking.

**Why:** The FE model is *correctly estimated* and answers a real question — "within a kommun over time, what is the association between unemployment and tax-base growth?" That finding is worth showing. It is simply not a ranking engine, and the audit showed it never was one. Promoting the lagged spec closes finding F4: every regressor's within-kommun correlation peaks at t−1 or later (unemployment −0.450 at t−1 vs −0.179 contemporaneous), which is what the t−2 income lag in §7.6 implies. The lagged spec is better identified — unemployment strengthens from −0.059 to −0.099, t from −3.8 to −6.1 — and is the only version usable for real forecasting, since it needs no contemporaneous data.

**How:** Swap which spec is labelled "main" in `estimate.py`. Retain the contemporaneous spec as a robustness check. In the UI, present FE results under a clearly separated heading — *"Samband inom kommuner över tid"* — physically distinct from the ranking. Delete or gate `compute_vulnerability`'s role as the headline ranking (see T3.x for its fate).

**Definition of done:** Lagged spec is primary in `coefficients.parquet`; UI separates the within-time finding from the cross-sectional ranking; `METHODOLOGY.md` §2.6 updated to reflect the promotion (full doc rewrite is T4.1).

---

## 7. PHASE 3 — Forecasting, If Retained

*Optional. Phases 0–2 deliver a complete, honest, useful product without any forecast. Only proceed if a forward-looking number is genuinely wanted — and only on these terms.*

### T3.1 — Rolling-origin backtest harness
**Phase:** 3 · **Time:** 3–4 h · **`[SUBAGENT]`**
**Files:** `src/model/backtest.py` (new), `tests/test_backtest.py` (new)
**Depends on:** T0.2

**What:** A reusable harness that fits on data up to year *T* and scores against realised outcomes at *T+h*, across every available origin.

**Why:** Build this **before** any new forecaster, not after. The current project shipped a forecast that had never been scored, and the audit found r = 0.016 — the single most damaging finding. A forecaster without a backtest harness is how that happens. Writing the harness first makes the failure mode structurally impossible to repeat.

**How:** Report per origin and pooled: Pearson r, Spearman ρ, RMSE, bias, and RMSE of the naive constant-mean benchmark. **The naive benchmark is mandatory in every report** — the current model's RMSE of 1.51 pp only reveals itself as a failure next to the naive 0.97 pp.

**Definition of done:** Harness runs for any (target, horizon, estimator) triple; test covers a synthetic case with known answer; naive benchmark always emitted.

---

### T3.2 — Medium-horizon drift forecaster
**Phase:** 3 · **Time:** 3–4 h · **`[SOLO]`**
**Files:** `src/model/predict.py` (rewrite), `tests/test_predict.py` (rewrite)
**Depends on:** T3.1, T2.1

**What:** Forecast **5-year drift in relative position**, not 1-year growth. Ship with prediction intervals and the backtest result attached.

**Why:** One-year growth is not recoverable — persistence is −0.06 and no model will fix that; this is a property of the data, not of the estimator. Five-year drift is genuinely forecastable at out-of-sample r ≈ 0.36 / Spearman ≈ 0.32. Modest, but real, and roughly 23× the current signal.

**How:** Fit drift over [T−5, T] on structural variables at T−5; apply to current values. Intervals from the backtest's empirical error distribution, **not** from the regression's nominal SE — nominal intervals will be far too narrow, exactly as the current model's predicted SD (0.33 pp) was three times too narrow against realised (0.98 pp).

**Definition of done:**
- `artifacts/predictions.parquet` carries drift forecast, empirical interval, and horizon.
- Out-of-sample Spearman > 0.25 on held-out origins, or **the task fails and the forecast is not shipped.**
- Predicted dispersion within 30 % of realised dispersion in backtest.

---

### T3.3 — Publish the backtest in the UI
**Phase:** 3 · **Time:** 2 h · **`[PARALLEL-C]`**
**Files:** `pages/01_Riksoversikt.py`, `src/ui/labels.py`
**Depends on:** T3.2

**What:** A permanent, visible panel showing the forecast's own track record: out-of-sample correlation, error distribution, and comparison to the naive benchmark.

**Why:** A dashboard that shows its own hit rate is worth more than one showing an untested number. This is also the standing defence against the plan's own failure mode — if the forecast degrades, users see it.

**Definition of done:** Panel visible without interaction; states horizon, sample, metric, and naive comparison in Swedish via `SWEDISH_LABELS`.

---

## 8. PHASE 4 — Documentation and Framing Truth-Up

*Do this last, when the code is settled — but do not skip it. Several of these strings are currently shown to users and are factually wrong.*

### T4.1 — Rewrite METHODOLOGY.md for the new specification
**Phase:** 4 · **Time:** 3–4 h · **`[SOLO]`**
**Files:** `docs/METHODOLOGY.md`
**Depends on:** Phases 1–3 complete

**What:** Substantial revision. Specific corrections required:

| Section | Current text | Required change |
|---|---|---|
| §7.10 | "The vulnerability score is dominated by the entity fixed effects" | **Factually wrong and shown to users in the Metod tab.** Entity FE contribute **8.8 %** of prediction variance; structural conditions ~91 %. Correct it, and add the between/within variance finding (98.3 %) as the reason the specification changed. |
| §3.4 | "Prediction does not require causal identification … predictive validity is the right standard" | The argument is sound; the model failed the standard it set. Replace with the backtest result. |
| §7.6 | t−2 lag "does not bias the analysis" | True for the growth calculation, false for X–Y pairing. Document the lag-correlation table and the promotion of the lagged spec. |
| §2 | Two-way FE as the model | Now one of two models. Cross-section is primary for ranking; FE is the within-time inference panel. |
| §6.4 | Model fit checks expecting R²(within) > 0.10 | Replace with cross-sectional R² and out-of-sample backtest thresholds. |
| §7.13 | Unweighted statistics | Expand — the project now carries both SCB's weighted index and its own unweighted mean. |
| New | — | A §7 limitation on cross-sectional collinearity and the descriptive-not-causal constraint. |

**Why:** `METHODOLOGY.md` is described in its own header as the basis for what the dashboard tells users. Until it is corrected, a cold Claude session — or a subagent — reading it will faithfully rebuild the mismatched specification.

**Definition of done:** Every row above addressed; no remaining claim contradicted by `artifacts/`; audit URL cited.

---

### T4.2 — Reframe user-facing language
**Phase:** 4 · **Time:** 2 h · **`[PARALLEL-D]`**
**Files:** `README.md`, `src/ui/labels.py`
**Depends on:** T4.1

**What:** Three specific changes:

1. **`labels.py:128`** — `"landing_vars_title": "Variabler & vikter"` → **"Variabler & koefficienter"**. Closes finding F6. The model has no weights; the table beneath already correctly says *Koefficientvärden*. For controllers and credit analysts, "vikter" implies an assignable scheme they could argue with, which misdescribes and undersells the method.
2. **README** — drop *"förväntad skattekraftsutveckling fram till 2025"*. The horizon has closed; SCB published it. Replace with the position/drift framing, and state the model is descriptive.
3. **Risk-class labels** — the quintile cut is *relative*: exactly 58 kommuner are always "hög risk", even in a year when every tax base grows healthily. `METHODOLOGY.md` §9 says this; the red map colouring implies otherwise. Label as *"lägsta femtedelen"*, not fiscal distress.

**Definition of done:** All three changed; no forecast language survives that the backtest does not support.

---

### T4.3 — Log the deviation
**Phase:** 4 · **Time:** 30 min · **`[PARALLEL-D]`**
**Files:** `docs/DEVIATIONS.md`
**Depends on:** T4.1

**What:** New section recording that `PRD.md` §5 "Empirical Model (Locked)" was deliberately unlocked, with the evidence and reasoning.

**Why:** That file's honesty is one of this project's real assets. The largest specification change in the project's history must not be the one that goes unlogged. Follow the existing Original plan / Deviation / Resolution format.

**Definition of done:** Entry references this plan, the audit URL, and the between/within variance evidence.

---

## 9. Parallel Execution Groups

Checked for file-disjointness. Tasks in the same group may run as concurrent subagents.

| Group | Tasks | Precondition |
|---|---|---|
| **A** | T1.3 | after T1.1; disjoint from T1.2 only if T1.2 has not yet touched `02_Kommunjamforelse.py` — **otherwise run sequentially** |
| **B** | T2.3 | after T2.1; disjoint from T2.2 |
| **C** | T3.3 | after T3.2 |
| **D** | T4.2, T4.3 | after T4.1; disjoint files |

Everything else is sequential. When in doubt, run sequentially — this plan's whole premise is that a wrong specification propagated silently, and concurrent edits to a shared contract are how that recurs.

---

## 10. Progress Tracker

```
PHASE 0 — Data foundation
  [ ] T0.1  Fetch OE0101B0 + extend to 2026          [SOLO]
  [ ] T0.2  Extend full panel, handle ragged years    [SOLO]
  [ ] T0.3  Freeze audit baseline fixture             [SUBAGENT]

PHASE 1 — Descriptive spine
  [ ] T1.1  Position and drift module                 [SUBAGENT]
  [ ] T1.2  Dashboard leads with position/drift       [SOLO]
  [ ] T1.3  Show SCB index alongside                  [PARALLEL-A]

PHASE 2 — Re-point at the cross-section
  [ ] T2.1  Cross-sectional estimator                 [SOLO]
  [ ] T2.2  Level decomposition                       [SUBAGENT]
  [ ] T2.3  Collinearity diagnostics                  [PARALLEL-B]
  [ ] T2.4  Demote FE to inference panel              [SOLO]

PHASE 3 — Forecasting (optional)
  [ ] T3.1  Rolling-origin backtest harness           [SUBAGENT]
  [ ] T3.2  5-year drift forecaster                   [SOLO]
  [ ] T3.3  Publish backtest in UI                    [PARALLEL-C]

PHASE 4 — Documentation
  [ ] T4.1  Rewrite METHODOLOGY.md                    [SOLO]
  [ ] T4.2  Reframe user-facing language              [PARALLEL-D]
  [ ] T4.3  Log deviation                             [PARALLEL-D]
```

**Estimated total:** 35–48 hours. Phases 0–2 alone (23–32 h) deliver a coherent, defensible product; Phase 3 is genuinely optional.

---

## 11. Gates

Do not proceed past a gate until it passes.

| Gate | Condition | If it fails |
|---|---|---|
| **After Phase 0** | Panel covers 2026; `tax_base_index_riket` populated; riket values match SCB exactly | SCB tables restructured again — consult `METHODOLOGY.md` §12 and fix fetchers before continuing |
| **After Phase 2** | Cross-sectional R² > 0.60; decomposition residual < 40 % of gap; VIF computed | Do not ship. The premise of the plan is that the cross-section carries the signal; if it does not, stop and re-audit |
| **After Phase 3** | Out-of-sample Spearman > 0.25 | **Do not ship the forecast.** Deliver Phases 0–2 only. This is an acceptable outcome, not a failure |
| **After Phase 4** | No claim in `METHODOLOGY.md` contradicted by `artifacts/` | Fix the doc, not the artifact |

---

## 12. Reproducing the Audit Numbers

Every figure in §1 was computed from the repository at commit `66ee2a3` plus live SCB queries on 2026-09-04. To reproduce independently:

* **Backtest of the 2025 forecast** — fetch `OE0101A0` for 2024–2025, all 290 kommuner; compute `(sk_2025/sk_2024 − 1) × 100`; correlate with `artifacts/predictions.parquet::predicted_growth_2025`. Compare RMSE against the constant-mean benchmark.
* **Between/within variance split** — build relative position (kommun ÷ cross-kommun mean × 100) for 2010–2026; compare the variance of kommun means to total stacked variance.
* **Variance decomposition of the score** — unpickle `artifacts/model_results.pkl`, take `estimated_effects` grouped by entity, form each `β_k · X_k,2024` component, and compute `cov(component, total) / var(total)`. Shares sum to exactly 100 %.
* **Standardised importance** — `β_k × SD_within(X_k)`, where within-SD is computed after entity demeaning.
* **Lag structure** — within-kommun correlation of `tax_base_growth_pct` with `X` shifted 0–3 years.

Note `linearmodels` is required to unpickle `model_results.pkl`; on this machine the interpreter carrying it is `/usr/local/bin/python3.11`, not the default `python3` (3.9.6, no linearmodels).

---

**End of REMEDIATION_PLAN.md**
