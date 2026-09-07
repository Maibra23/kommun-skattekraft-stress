# REMEDIATION_PLAN.md — Model Layer Remediation (14 tasks, 4 phases)

**Project:** Kommunal Skattekraft Stress Monitor
**Created:** 2026-09-05
**Last updated:** 2026-09-06
**Status:** In progress — **Phase 0 complete** (steps 1, 2, 2b, 3 done 2026-09-06/07). Next: the post-Phase-0 GATE, then step 4 (T1.1).
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
| F5 — insignificant `edu_share` drives 25 % of ranking | Phase 2 | Cross-section gives it a real, significant role — **measured 2026-09-07: it is not merely significant but dominant**, R² = 0.656 on its own against 0.690 for all four. The inverse also holds: `dependency_ratio`, which the within design ranked first at 59.1 %, is not separately identified between kommuner |
| F3 — collinearity never checked | Phase 2 | VIF/condition-number diagnostics added and published. **Measured 2026-09-07: the cross-sectional design is clean** (VIF 1.3–2.1); F3's high-correlation pairs are a within-design problem and do not transfer. The diagnostic closes the finding rather than confirming it |
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

### Execution order — read this before picking a task

**The phase numbers are not the execution order.** Phases group tasks by *purpose*; the sequence below orders them by *dependency and risk*. Two deliberate departures from the phase numbering:

* **T0.3 runs first.** It is cheap and independent, and the fixture should exist before the artifacts start churning.
* **Phase 1 is split.** T1.1 (the position/drift module) is pulled *forward* because T2.1 consumes it. T1.2 and T1.3 (the dashboard work) are pushed *back* behind Phase 2, because the UI renders whatever the model emits — building it before the artifact contract settles means building it twice, and Phase 2 carries the only real intellectual risk in the plan. Learn whether the premise holds before investing in presentation.

| Step | Task | Time | Rationale for this position |
|---|---|---|---|
| 1 | T0.3 baseline fixture | 1 h | Independent; makes the before/after comparison automatic |
| 2 | T0.1 `OE0101B0` + skattekraft → 2026 | 1–2 h | Additive, one ContentsCode; standalone value even if work stops here |
| 3 | T0.2 rest of panel → latest | 2–4 h | **Risk node** — SCB has restructured tables three times already |
| — | **GATE** — re-run the 2025 backtest on real data | — | Confirms or overturns the audit before spending on the fix |
| 4 | T1.1 position/drift module | 3–4 h | Pulled forward: T2.1 depends on it |
| 5 | T2.1 cross-sectional estimator | 4–6 h | **The fix**, and the gate that tests the plan's premise |
| 6 | T2.2 + T2.3 | 5 h | Parallelisable (group B) |
| 7 | T2.4 demote FE to inference panel | 2–3 h | |
| 8 | T1.2, T1.3 dashboard work | 5–8 h | Deferred until the artifact contract is stable |
| 9 | Phase 3 (optional) | 6–8 h | Only if a forward-looking number is genuinely wanted |
| 10 | Phase 4 documentation | 5–6 h | Last, when the code is settled |

**Defensible stopping points.** After step 3: current with SCB, official index in the panel, nothing half-finished. After step 7 plus T4.1: the model is fixed and the docs no longer contradict the artifacts — this is the milestone worth aiming for, the point at which the project stops telling users something untrue. Phase 3 is genuinely optional.

### How to run the remaining steps (added 2026-09-07)

Steps 1–3 and the gate are done. The Phase-2 evidence gathered before starting T2.1 changes *what* those tasks deliver but not their order — the sequencing below is the original one, with delegation revised for what each task now contains.

| Step | Task | Run it as | Why this way |
|---|---|---|---|
| **4** | T1.1 position/drift | **`[SUBAGENT]`**, unchanged | Genuinely self-contained: skattekraft only, pure functions, one artifact, clear numeric acceptance tests. It needs no Phase-2 context and touches nothing else. The one instruction it must carry: use the ragged panel's full 2010–2026 range, not `complete_case_max_year`. |
| **5** | T2.1 cross-sectional estimator | **`[SOLO]`** — do not delegate | Was already SOLO, and is now more so. The task is no longer "fit a regression"; it is a series of judgment calls about what may be claimed. A fresh agent reading `METHODOLOGY.md` would reproduce the four-driver framing the evidence block exists to prevent. |
| **6** | T2.2 + T2.3, **now merged into one pass** | **`[SOLO]`**, immediately after T2.1 | Group B's parallelism assumed two substantial independent tasks. T2.3 shrank to a formality plus the per-variable scale table that T2.2 consumes, and T2.2 now depends on T2.3's `identified` flag to know which bars to draw. Running them concurrently would race on exactly that contract. |
| **7** | T2.4 demote FE | **`[SOLO]`** | Unchanged. Quote the lagged coefficients from `coefficients.parquet`, not from this plan's prose — the rebuild moved them (see the 2026-09-07 T0.2 entry). |
| **8** | T1.2, T1.3 dashboard | **`[SOLO]`**, T1.3 may follow as **`[PARALLEL-A]`** | Deferral is now clearly right: the decomposition chart has changed shape twice since the plan was written. **This is also the artifact cutover** — the single commit where the deployed pages move from `decomposition.parquet`/`coefficients.parquet` onto the `*_cross.parquet` files. Steps 5–7 deliberately add artifacts without touching the old ones so the live site keeps working; do not cut over piecemeal. |
| **9** | Phase 3 | optional | Reassess after step 7. With two identified variables rather than four, the drift forecaster has less to work with than the audit's r = +0.364 suggested; that figure was computed with all four. Its own gate (Spearman > 0.25) still decides. |
| **10** | Phase 4 | **`[SOLO]`** for T4.1 | T4.1 grew: it now carries the dependency-ratio inversion, which is the most user-visible correction in the plan. |

**One scope question deliberately left open.** Education alone carries R² = 0.656 of 0.690 and correlates +0.810 with the index, so the "why" this phase ships is close to a restatement. Whether that is informative enough to be the product's explanatory layer is a real question — but it is a *new scope* question, not a repair to this plan. Ship the honest version through step 7 first, then decide. Do not let it turn into re-selecting variables mid-phase, which is how the original specification drifted.

**The dashboard must work at every commit.** It is deployed on Streamlit Cloud and reads committed artifacts with no build step (METHODOLOGY §11.7). Steps 5–7 therefore only *add* artifacts (`coefficients_cross.parquet`, `decomposition_cross.parquet`, `diagnostics.parquet`); step 8 is the one commit that repoints the pages. This preserves the plan's own "defensible stopping points" principle — stopping after step 7 leaves a working site showing the old model, not a broken one.

### Keeping this document current

**Every completed task updates this file in the same commit as the code.** Tick §10, and append an entry to the status log in §13 recording what was done, what was found, and anything that surprised you. A plan that drifts from the repository is worse than no plan, because it is trusted.

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

### T0.2a — SCB withdrew the AA0003X archive · RESOLVED (option A, 2026-09-07)
**Phase:** 0 · **Time:** 2–4 h once decided · **`[SOLO]`** · **Status:** done — see the status log entry for 2026-09-07
**Files:** `src/fetch/fetch_unemployment.py`, `data/lookup/unemployment_2010_2021.csv`, `scripts/freeze_unemployment_snapshot.py`, `tests/test_fetch_unemployment.py`, `docs/METHODOLOGY.md` 8.1 + 12.6, `docs/DEVIATIONS.md` 6.1
**Blocked:** T0.2, and therefore the T0.1 panel rebuild — **both now unblocked**

**What happened.** `https://.../AA/AA0003/AA0003X` now returns HTTP 400 — the whole archive group, not just one table. `IntGr1KomKonUtb`, `IntGr1KomKon` and `IntGr1Kom` are all gone. `AA0003B/IntGr1KomUtbBAS` still exists but its `Tid` dimension is exactly `['2022','2023','2024']`. No replacement municipality-level open-unemployment series with history exists anywhere under AA0003 (checked AA0003B, AA0003E, AA0003H — the long series there are demography and education, not labour market).

**Consequence.** Open unemployment for **2010–2021 can no longer be fetched from SCB at all**. Those 3 480 observations survive only in the committed `data/processed/panel.parquet`, fetched in May 2026. `METHODOLOGY.md` 8 claims the pipeline is reproducible from source; for this variable that is now false.

**Severity is lower than it looks, because of this plan.** The loss falls on the long historical panel, which is what the two-way FE model consumes — the model this plan demotes in T2.4. The cross-sectional specification that Phase 2 makes primary needs the *latest* year, which is available (2022–2024). Phase 1's position and drift work uses skattekraft alone and is unaffected. Had this happened before the audit it would have been critical; under the remediation it degrades a component already being reduced in importance.

**Options.**

| | Approach | Cost | Consequence |
|---|---|---|---|
| **A** *(recommended)* | Snapshot 2010–2021 from the committed panel into `data/lookup/` with provenance; fetcher reads the snapshot below 2022 and the API above | 2–3 h | Panel preserved. Reproducibility becomes "from repo" not "from SCB" — honest if documented. Validate by checking 2022–2024 snapshot rows still match the live API. |
| **B** | Truncate the panel to 2022+ | 1 h | Three years. Destroys the panel model. Not viable. |
| **C** | Re-source from Arbetsförmedlingen, the upstream origin of the STATIV series | 6–10 h | Restores true reproducibility, but a different vintage and possibly a different definition — a series break mid-panel, which is worse than a documented snapshot. |
| **D** | Drop unemployment entirely | 2 h | Loses the second-strongest variable (β × within-SD = −0.111). Not advisable. |

**Recommendation: A**, with the overlap check as the validation that the snapshot is the same series SCB still publishes. Log it in `DEVIATIONS.md` and correct `METHODOLOGY.md` 8 in the same change — the reproducibility claim must not outlive its truth.

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
**Depends on:** — · **Runs first** (see §2 execution order). Reads only committed artifacts; must complete before T0.2 regenerates them.

**What:** Capture the audit's headline numbers from the **current** committed artifacts as a locked JSON fixture, with a test that asserts them.

**Why:** Phases 1–3 replace the model layer, and the first pipeline run after T0.2 regenerates all five artifacts. Those artifacts are tracked in git, so the audit's evidence is preserved at commit `3dcaab7` and recoverable with a checkout — this fixture is not about preventing loss. It is about making the before/after comparison **automatic and continuously asserted**, so that "the new specification is better, not merely different" is a claim the test suite checks rather than one a future reader has to re-derive by hand from a chat transcript.

**How:** Record at minimum: the four main-spec coefficients and p-values; R²(within) = 0.0083; the variance decomposition (dependency 59.1 %, education 25.1 %, unemployment 15.1 %, entity FE 8.8 %, population −8.2 %); β × within-SD for each variable; the 2025 backtest (r = 0.016, Spearman 0.033, RMSE 1.512 vs naive 0.974); and the three risk-class means. Test asserts to 3 decimal places against the committed artifacts and is marked `@pytest.mark.baseline` so it can be excluded once the old model is retired.

**Definition of done:** Fixture committed; test passes against current artifacts; a one-line comment in the fixture points to this plan and the audit URL.

---

## 5. PHASE 1 — The Descriptive Spine

*Rank stability is 0.992 year-over-year. The most useful, most defensible thing this project can show requires no model at all — let the model become the "why" rather than the "what".*

> **Sequencing note.** This phase is split across the execution order (§2). **T1.1 runs at step 4**, before Phase 2, because T2.1 consumes its output. **T1.2 and T1.3 run at step 8**, after Phase 2, because the dashboard renders whatever the model emits.

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

> **This task also owns the artifact cutover and the chart corrections (added 2026-09-07).** As originally written it covers page *hierarchy* only. But Phase 2 changes what the charts should contain, and nothing in the UI follows the artifacts automatically — every chart hardcodes variable names and reads the `main` spec by name. This is the step where the deployed site moves onto the new artifacts, so the following must land here, together, in one commit:
>
> | Location | Now | Must become |
> |---|---|---|
> | `pages/02_Kommunjamforelse.py:341-346` | five hardcoded decomposition bars (unemployment, dependency, population, education, residual) | read `decomposition_cross.parquet`; draw bars only for **identified** components plus residual; show the others in a secondary "ingår i modellen, går inte att särskilja" line with their CIs |
> | `app.py:223-330` "Variabler & vikter" | bar chart + table of **raw β**, sorted by coefficient | **β × SD** with CIs, from `coefficients_cross.parquet`. Raw β on incomparable scales renders −5.55 as a longer bar than +1.18 when the real effect is 15× smaller — the same misreading as F6 |
> | `app.py:136-156` | hand-drawn SVG of four variables feeding a regression box | must not depict four equal drivers; two are not separately identified |
> | `app.py:237` | reads the `main` coefficient spec | `lagged` is primary after T2.4 |
> | `pages/01_Riksoversikt.py:100`, `02_Kommunjamforelse.py:175,407`, and the model-layer three | hardcoded `year == 2024` | read `complete_case_max_year` from `artifacts/data_provenance.json`; 2024 is correct today and silently becomes wrong when SCB publishes 2025 unemployment |
>
> **Sequencing constraint:** the site is deployed on Streamlit Cloud reading committed artifacts, so it must work at every commit (METHODOLOGY §11.7). T2.1 and T2.2 add `*_cross.parquet` files without touching the old ones precisely so that this task is the single point where the pages switch over. Do not cut over piecemeal.

**Definition of done** *(extended 2026-09-07)*: All three pages render; no Swedish literals outside `labels.py`; choropleth toggle works; existing `tests/test_choropleth.py` passes or is updated; every row of the table above is addressed; no page reads a hardcoded analysis year; the deployed app works against the committed artifacts at this commit.

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

> **Evidence added 2026-09-07, before this task starts. This block changes what the task delivers — read it before writing any code.**
>
> The cross-section was run on the rebuilt panel for 2021–2024 (`tax_base_index_riket` on the four structural variables, HC3, no entity effects), then diagnosed with standard errors, VIF and incremental R².
>
> **1. The premise holds in every year, not just the one the audit tested.** R² = 0.702, 0.712, 0.723, 0.690. The Phase-2 gate (R² > 0.60) is safe from four independent directions, so the *fit* claim in this task carries less risk than the plan assumed.
>
> **2. Only two of the four variables are separately identified.** Standardised to effect-per-SD on the index (whose own SD is 13.2 points), 2024:
>
> | Variable | β × SD | 95 % CI (SD units) | across 2021–24 |
> |---|---|---|---|
> | `edu_share` | **+10.03** | [+6.36, +13.70] | always significant, stable |
> | `unemployment_rate` | −2.69 | [−3.84, −1.53] | always significant, stable |
> | `dependency_ratio` | −0.64 | **[−2.44, +1.15]** | spans zero every year |
> | `population_growth_pct` | −0.56 | **[−1.98, +0.85]** | spans zero every year |
>
> **3. The two unidentified variables add essentially nothing.** Incremental R² from dropping each: education −0.295, unemployment −0.031, dependency −0.001, population growth −0.001. Nested fits: all four 0.690, the two identified only 0.688, **education alone 0.656**. Education's raw correlation with the index is +0.810.
>
> **4. It is not collinearity, and pooling does not rescue it.** VIF is 1.3–2.1 in every year, well inside tolerance — the audit's F3 concern is real for the *within* design but does not bite here. `dependency_ratio` is imprecise because it barely varies (SD = 0.116), so a per-unit coefficient spans 8.6 SDs of the actual data. Pooling 2010–2024 does not help: its SE goes 7.91 → 8.12, because a between-kommun question has effective **N = 290**, not 4 350, and kommun-clustered SEs correctly say so. Pooled, `dependency_ratio` even flips sign (+5.80) while still spanning zero.
>
> **Correction to an earlier note.** A previous version of this block called the coefficients "unstable" and pointed at `dependency_ratio` swinging −4.91 → −9.88 → −5.55. That diagnosis was wrong: it was written without checking the standard errors, which are 7–9, so those CIs overlap almost entirely. The variable is not unstable, it is **not identified**. The distinction matters — instability would argue for pooling; non-identification argues for not reporting the number as a driver at all.
>
> **What this changes about the task.** The five points below replace the "How" and "Definition of done" as originally written:
>
> 1. **Report β × SD as the primary quantity**, keeping raw β for reproducibility. Raw coefficients on incomparable scales are what make `dependency_ratio`'s −5.55 look larger than `edu_share`'s +1.18 when its actual effect is 15× smaller. This is audit finding F6 ("vikter") in another form.
> 2. **Apply an identification bar, fixed before reading the results.** A variable is presented as a driver only if its CI excludes zero in the primary spec *and* its sign holds across 2021–2024. On current evidence education and unemployment pass; dependency ratio and population growth fail. Failing variables stay in the model as controls, labelled *"ingår i modellen, går inte att särskilja"* — never rendered as decomposition bars.
> 3. **Report the year range, not one arbitrary year.** Because the CIs overlap across years, the honest headline is "education: +6.4 to +13.7 index points per SD, stable 2021–2024", with the latest year as the point estimate. This dissolves the single-year-versus-pooled question: neither is the headline, the range is.
> 4. **Do not assert all four signs in the test suite.** The original DoD ("test asserts sign and rough magnitude of all four coefficients") would lock noise into the suite for two variables. Assert instead: R² > 0.60 in every year 2021–2024; education and unemployment CIs exclude zero with the expected signs in every year; and **that dependency ratio and population growth span zero**, so the honest finding is itself regression-tested and someone is told if it ever changes.
> 5. **Say plainly what the model does not support.** The dashboard currently shows dependency ratio as the largest contributor. Between kommuner it explains essentially nothing. Publishing that correction is worth as much as publishing the positive result.
>
> **The interpretive risk is larger than this task's original caution allowed for.** With education carrying 0.656 of 0.690 on its own and correlating +0.810 with the index, "kommuner whose residents are more educated have a higher tax base" is true, robust, and close to a restatement rather than an insight. Strengthen the caution below rather than merely carrying it over. Whether a near-mechanical attribution is informative enough to serve as the product's "why" is a scope question — take it up after this task lands, and do not let it expand into re-selecting variables mid-phase.

**Caution — the central interpretive risk of this whole plan, and it is now measured:** R² = 0.69 is not merely "partly mechanical", it is *mostly one near-mechanical relationship*. Education alone gives R² = 0.656 of the 0.690, and correlates +0.810 with the index. Education share, dependency ratio and unemployment are jointly determined with income levels; this is *association within a cross-section*, not causation. Every coefficient shipped from this module must be labelled descriptive. Carry `METHODOLOGY.md` §7.2 forward and strengthen it with these numbers. If anyone starts saying "raising education by 1 pp would raise the tax base by 1.28 index points", the plan has failed.

**Definition of done** *(revised 2026-09-07 — see the evidence block above)*:
- `artifacts/coefficients_cross.parquet` with both specs: raw β, **β × SD**, robust SE, p-values, CIs (in raw and SD units), R², and a boolean `identified` column applying the bar in point 2.
- Latest-year R² > 0.60, **and** R² > 0.60 in each of 2021–2024.
- Test asserts: education and unemployment CIs exclude zero with the expected signs in every year 2021–2024; **dependency ratio and population growth span zero** in the latest year.
- Artifact records the across-year range for every variable, not only the latest point estimate.
- Module docstring states the descriptive-not-causal constraint **and** that two of four variables are not separately identified.

---

### T2.2 — Level decomposition
**Phase:** 2 · **Time:** 3–4 h · **`[SUBAGENT]`**
**Files:** `src/model/decompose.py` (rewrite), `tests/test_decompose.py` (rewrite)
**Depends on:** T2.1

**What:** Replace the growth-gap decomposition with a decomposition of each kommun's *position* gap versus riket, using the cross-sectional coefficients.

**Why:** The current decomposition answers "why did Filipstad grow 1.8 pp below average in 2024?" — a question about a noisy, non-persistent quantity where the residual dominates. The new one answers "why does Filipstad sit at index 76?", which is stable, is what users actually ask, and where the four variables explain ~69 % rather than ~1 %.

**How:** Same additive structure as the existing module (`β_k × (X_ki − X̄_k)`, residual absorbs the rest, exact sum check to 1e-10 — keep that check, it is good). The change is the target and the coefficient source. The residual should shrink dramatically; if it does not, stop and investigate before proceeding.

> **Revised 2026-09-07 — this is no longer a four-bar chart.** T2.1's evidence block shows only `edu_share` and `unemployment_rate` are separately identified; `dependency_ratio` and `population_growth_pct` have CIs spanning zero in every year and add 0.001 each to R². A four-component decomposition would render two bars that are indistinguishable from noise, and would do so *confidently*, because the additive identity always sums to 100 % regardless of whether the components mean anything. The sum check cannot catch this.
>
> Decompose into **two identified components plus the residual**. Keep the unidentified variables in the fitted model as controls — dropping them changes R² by 0.002 and would misstate the specification — but do not give them bars. Show them in a secondary "included, not separately identified" line with their CIs.
>
> The headline finding to publish is an inversion: the dashboard currently shows `dependency_ratio` as the largest contributor, inherited from the within/FE variance decomposition where the audit measured it at 59.1 %. **Between kommuner it explains essentially nothing.** That correction is the most user-visible thing this phase produces.

> **Write a new artifact; do not overwrite `decomposition.parquet` (added 2026-09-07).** The dashboard is deployed on Streamlit Cloud and reads committed artifacts directly — `pipeline.py` never runs there. `pages/02_Kommunjamforelse.py` names its five decomposition columns literally, so replacing the file at step 6 would break or silently mislabel the live site until the UI is fixed at step 8, several hours of work later. Write **`artifacts/decomposition_cross.parquet`** instead, mirroring T2.1's `coefficients_cross.parquet`, and leave the old artifact in place until T1.2 cuts the pages over in one deliberate change. See METHODOLOGY §11.7.

**Definition of done** *(revised 2026-09-07)*:
- `artifacts/decomposition_cross.parquet` decomposes the position gap into the **identified** components plus residual; components sum exactly. The pre-existing `decomposition.parquet` is left untouched for the deployed UI until step 8.
- Unidentified variables appear in the artifact flagged as controls, not as attributed components.
- Mean |residual| share of total gap **< 40 %**. Two identified variables carry R² = 0.688, so this should hold comfortably; if it does not, the target or the coefficients are wrong.
- Test covers the sum identity, a hand-computed single-kommun case, and that no unidentified variable is emitted as an attributed component.

---

### T2.3 — Collinearity diagnostics
**Phase:** 2 · **Time:** 2 h · **`[PARALLEL-B]`**
**Files:** `src/model/diagnostics.py` (new), `tests/test_diagnostics.py` (new)
**Depends on:** T2.1

**What:** Compute and persist VIF, the design-matrix condition number, and the pairwise correlation matrix — for both the within and cross-sectional designs.

**Why:** Closes audit finding F3. Three of six within-kommun pairs exceed |0.65| (dependency × education +0.714, unemployment × dependency −0.703, unemployment × education −0.655) and this was never checked. Collinearity bites *harder* in the cross-section, so shipping T2.1 without this diagnostic would be a regression in rigour, not an improvement. The decomposition chart currently splits what is substantially one rural-ageing-low-education factor into four bars, and users deserve to be told.

**How:** Standard VIF via auxiliary regressions. Flag VIF > 5 as a warning, > 10 as severe. Write `artifacts/diagnostics.parquet`. Diagnostic severity, not blocking (per §11.6 policy).

> **Reframed 2026-09-07 — the premise above is wrong for the cross-section, and the task is now cheaper and more important than it looks.**
>
> This task was written expecting collinearity to be the threat. Measured: **VIF is 1.3–2.1 in every year 2021–2024**, condition number ~510–540, and the strongest cross-sectional pair is education × population growth at +0.567. Collinearity does *not* bite here. The audit's F3 concern was measured on the **within** design (three pairs above |0.65|) and does not transfer.
>
> So this diagnostic will **clear** the cross-sectional design rather than condemn it — which is still worth publishing, because F3 is an open audit finding and "we checked and it is fine" closes it honestly. Keep computing it for both designs; the within numbers are the ones that will show the problem.
>
> **But the real diagnostic this phase needs is not collinearity — it is identification and scale.** `dependency_ratio` is unusable between kommuner because its SD is 0.116, not because it correlates with anything. Extend this module to emit, per variable: SD, β × SD, the CI in SD units, and the `identified` boolean. That is what T2.2 and the UI must consume to avoid rendering noise as bars.
>
> **Consider folding this into T2.1** rather than running it as a separate parallel task. The content shrank (the collinearity half is a formality now) and the half that matters is the same computation T2.1 already needs. Left as a separate task here only so the audit trail against F3 stays legible; merging is a reasonable call for whoever executes it.

**Definition of done** *(revised 2026-09-07)*: Artifact written for both designs; test asserts VIF is computed for all four variables, that the known high-correlation pairs are flagged **in the within design**, and that the cross-sectional design reports VIF below the warning threshold. Per-variable SD, β × SD, CI in SD units and `identified` are emitted for the cross-sectional design.

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
| §7.10, §9, Metod tab | Dependency ratio presented as the dominant driver (59.1 % of prediction variance) | **Added 2026-09-07 — the largest user-visible correction in this plan.** That 59.1 % is from the *within* design. Between kommuner, `dependency_ratio` has a CI spanning zero in every year 2021–2024 and adds **0.001** to R². The ordering inverts: `edu_share` alone gives R² = 0.656 of 0.690, `unemployment_rate` adds 0.031, and dependency and population growth add 0.001 each. State plainly that two of four variables are not separately identified between kommuner, and why (dependency's SD is 0.116 — it barely varies across kommuner). |
| New §7 | — | **The attribution is close to a restatement, and must say so.** `edu_share` correlates +0.810 with the index. "Kommuner whose residents are more educated have a higher tax base" is robust and near-mechanical. Users must not read the education bar as a lever. |

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

> **Four more strings, found 2026-09-07 by reading the UI rather than the plan.** Each is currently shown to users and each becomes false during Phase 2. They are label text, so they belong here rather than in T1.2:
>
> 4. **`method_model_name`** — `"Tvåvägs fixed effects panelmodell"`, rendered as the model tag on the landing page (`app.py:126`). After T2.4 the FE model is the within-time inference panel, not the headline. The primary is the cross-sectional specification.
> 5. **`kpi_r2_tooltip`** — explains R²(within) and reassures that *"Lågt värde är förväntat"*. That metric is demoted in Phase 2; the headline fit becomes cross-sectional R² ≈ 0.69. Keeping a tooltip that explains away a low number, next to a high one, is worse than no tooltip.
> 6. **`decomp_explanation` and `explain_decomp_text`** — both describe contributions to *growth* (`"bidrar med 0,3 procentenheter lägre skattekraftstillväxt"`). T2.2 changes the target to **position**, so these are wrong on the quantity, independently of the identification question. The worked example needs rewriting in index points.
> 7. **`landing_model_explanation`** — describes four structural variables feeding a model that produces *"en tillväxtprognos för 2025"*. The 2025 horizon has closed, the forecast scored r = 0.016 against it, and two of the four variables are not separately identified.
>
> **Do not soften item 6 into vagueness.** The honest replacement states what the decomposition now attributes and what it cannot: education and unemployment separate kommuner; dependency ratio and population growth do not, between kommuner, however large their bars used to look.

**Definition of done** *(extended 2026-09-07)*: All seven changed; no forecast language survives that the backtest does not support; no user-facing string describes a metric or model that Phase 2 demoted.

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
| ~~**B**~~ | ~~T2.3~~ | **dissolved 2026-09-07.** T2.3 shrank to a formality plus the per-variable scale table that T2.2 must consume to know which components to attribute. They now share a contract, so running them concurrently would race on it. Merged into one sequential `[SOLO]` pass at step 6. |
| **C** | T3.3 | after T3.2 |
| **D** | T4.2, T4.3 | after T4.1; disjoint files |

Everything else is sequential. When in doubt, run sequentially — this plan's whole premise is that a wrong specification propagated silently, and concurrent edits to a shared contract are how that recurs.

---

## 10. Progress Tracker

Ordered by execution sequence (§2), not by phase number.
Markers: `[ ]` not started · `[~]` in progress · `[x]` done · `[-]` skipped.

```
STEP  TASK                                            PHASE  DELEGATION
 [x] 1   T0.3  Freeze audit baseline fixture             0    [SOLO]  done 2026-09-06
 [x] 2   T0.1  Fetch OE0101B0 + skattekraft to 2026      0    [SOLO]  done 2026-09-07 (DoD met at rebuild)
 [x] 2b  T0.2a AA0003X withdrawn — option A snapshot     0    [SOLO]  done 2026-09-07
 [x] 3   T0.2  Extend full panel, handle ragged years    0    [SOLO]  done 2026-09-07
 [x] --- GATE  Re-run 2025 backtest on real data              PASSED 2026-09-07
 [ ] 4   T1.1  Position and drift module                 1    [SUBAGENT]  <- NEXT
 [ ] 5   T2.1  Cross-sectional estimator                 2    [SOLO]
 ---     GATE  Cross-sectional R2 > 0.60
 [ ] 6   T2.2 + T2.3  Decomposition + diagnostics        2    [SOLO]  merged 2026-09-07
 [ ] 7   T2.4  Demote FE to inference panel              2    [SOLO]
 [ ] 8a  T1.2  Dashboard leads with position/drift       1    [SOLO]
 [ ] 8b  T1.3  Show SCB index alongside                  1    [PARALLEL-A]
 [ ] 9a  T3.1  Rolling-origin backtest harness           3    [SUBAGENT]   optional
 [ ] 9b  T3.2  5-year drift forecaster                   3    [SOLO]       optional
 [ ] 9c  T3.3  Publish backtest in UI                    3    [PARALLEL-C] optional
 ---     GATE  Out-of-sample Spearman > 0.25, else do not ship forecast
 [ ] 10a T4.1  Rewrite METHODOLOGY.md                    4    [SOLO]
 [ ] 10b T4.2  Reframe user-facing language              4    [PARALLEL-D]
 [ ] 10c T4.3  Log deviation                             4    [PARALLEL-D]
```

**Estimated total:** 35–48 hours. Steps 1–7 (23–32 h) deliver a coherent, defensible product; Phase 3 is genuinely optional.

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

## 13. Status Log

Append one entry per completed task, in the same commit as the code. Record what changed, what was found, and anything that contradicted this plan — the plan is only useful while it matches the repository.

---

### 2026-09-06 — Plan resequenced

**Change:** Added the execution order to §2. Phase numbers group tasks by purpose; the execution order sequences them by dependency and risk. T0.3 moved to first; Phase 1 split, with T1.1 pulled ahead of Phase 2 and T1.2/T1.3 deferred behind it.

**Correction to T0.3's stated rationale:** the original text claimed that without the fixture "there is no way to demonstrate that the new specification is better." That overstated the risk. `artifacts/` and `data/processed/panel.parquet` are tracked in git, so the audit's evidence survives at `3dcaab7` regardless. The fixture's real value is making the comparison automatic rather than manual.

---

### 2026-09-06 — T0.3 complete · baseline fixture frozen

**Done.** `scripts/freeze_audit_baseline.py` recomputes every headline audit number from the committed artifacts plus one live SCB query, and writes `tests/fixtures/audit_baseline_2026-09-04.json`. `tests/test_audit_baseline.py` adds 13 tests asserting those findings still hold. Full suite: 104 passed, no regressions.

**Independent confirmation.** The audit's figures were originally computed with ad-hoc scripts using `urllib`. The fixture regenerates them through the project's own `src/fetch/pxweb_client`, a different code path, and reproduces them exactly: R2(within) = 0.0083, backtest r = 0.016, RMSE 1.512 vs naive 0.974, realised 2025 growth mean 4.60 % (sd 0.98). The audit's conclusions are not an artefact of how they were measured.

**Design decision.** The realised 2025 growth vector (290 values) is stored *inside* the fixture so the backtest recomputes offline. No test in the suite touches the network; the generator script is the only place that does.

**Notes for whoever runs this next.**
- The suite is marked `baseline`, registered in `pyproject.toml`. Exclude it once the pre-remediation model retires: `pytest -m "not baseline"`.
- `test_entity_effects_do_not_dominate` deliberately encodes the audit's contradiction of `METHODOLOGY.md` 7.10. **It is expected to be deleted by T4.1**, when the claim it contradicts is corrected. Do not "fix" it before then.
- `scripts/freeze_audit_baseline.py` bootstraps `sys.path`; the package is not installed editable in every environment here. Tests do not need this — pytest inserts the rootdir.
- On this machine `linearmodels` lives only in `/usr/local/bin/python3.11`; the default `python3` is 3.9.6 without it. Run pytest and the script with the 3.11 interpreter.

---

### 2026-09-06 — T0.1 code complete · panel rebuild blocked by a fourth SCB restructure

**Done and green.** `fetch_skattekraft` now requests `OE0101A0` and `OE0101B0` in one query and covers 2010–2026. `tests/test_fetch_skattekraft.py` adds 15 tests; suite is 119 passed. `KRI_Dataset_Identification.md` 2 documents all three ContentsCodes, which two are used, and the weighted-vs-unweighted denominator trap.

Live fetch verified every DoD spot check: 4 930 rows (290 x 17), zero nulls in the index, Danderyd 191, Filipstad 76, Högsby 73 for 2026.

**Two decisions beyond the written task.**
- *Value columns are mapped by ContentsCode, not position.* The previous `_clean_response` took "whatever is not Region or Tid" as the metric. Safe with one metric; with two it would silently swap skattekraft for the index if SCB reordered the response.
- *Added `_cache_shortfall`.* The task said "delete the stale cache", which works once, on one machine. A cache written before today is *fresh* by the 7-day rule but predates both the new column and 2026, so it would silently yield a null index. The guard checks schema and year coverage, not just age.

**Blocked.** `build_panel` cannot complete: SCB has withdrawn the AA0003X archive path entirely. See T0.2a above for the diagnosis and the four options. `panel.parquet` is untouched — the failed run wrote nothing — so `tax_base_index_riket` is **not yet in the panel** and T0.1's DoD is only partly met. Step 2 is marked `[~]`, not `[x]`.

**Do not run `pipeline.py` until T0.2a is resolved.** The four `data/raw` caches other than skattekraft are absent, so any run will refetch, hit the same wall, and — worse — a partial success could overwrite `panel.parquet` with a truncated series. The 2010–2021 unemployment data exists in exactly one place: the committed parquet.

*(Superseded 2026-09-07 — T0.2a is resolved and `pipeline.py` is safe to run. The cache claim was also wrong on at least one machine; see the entry below.)*

---

### 2026-09-07 — T0.2a resolved · option A · 2010–2021 frozen as a snapshot

**Decision.** Option A, as recommended. `data/lookup/unemployment_2010_2021.csv` now holds the 3 480 withdrawn observations with a provenance header; `fetch_unemployment` reads it below 2022 and queries the live `AA0003B` table above. `_PRIMARY_TABLE_URL` is deleted, so no code path can request the dead archive. `tests/test_fetch_unemployment.py` adds 9 tests; suite is **128 passed**, no regressions, and the T0.3 baseline fixture still passes untouched.

**The options were tested before choosing, not just argued.**
- *A:* the overlap years 2022–2024 were re-fetched live and compared to the committed panel across all 870 kommun-years — **max abs diff 0.000000 pp**. A cold `fetch_unemployment(force_refresh=True)` then reproduced all 4 350 rows with zero changed values. The snapshot is the same series SCB still publishes.
- *B:* measured, not estimated — truncating to 2022+ costs **80 % of observations**, leaves 3 years, and leaves **zero** 5-year drift windows. It would make T1.1 and T3.2 impossible, which is worse than the plan's own "destroys the panel model" wording implies.
- *C/E:* Kolada carries a 2010–2025 municipal series (`N03937`), so the "no long series exists anywhere" framing was too strong — but it is not the same construct. Against our 2024 values: Spearman **+0.926** yet a **3.65x** level gap; the STATIV-sourced `N01720` is **+0.952** but **0.72x** and starts only in 2017. High rank agreement, wrong levels. Splicing either at the 2021/2022 seam injects a step change into exactly the within-kommun variation the FE model reads as signal.

**A reason for A that the plan did not record.** Option A is the only option that preserves the T0.3 baseline fixture. C or E would have changed every historical unemployment value while the model specification was also changing — two moving parts in the before/after comparison the whole remediation rests on. That, more than the cost estimate, is what settles it.

**Two corrections to the previous entry.**
- *The `data/raw` caches are not absent.* On the Windows working copy all five are present, and `unemployment.json` holds a complete, correct 2010–2024 series identical to the panel. The previous entry was written in a different environment (note its `/usr/local/bin/python3.11` path). The claim was environment-specific and read as universal.
- *That copy is untracked.* `git ls-files data/raw/` returns only `.gitkeep`, so the second copy is one `git clean -fdx` from gone and does not exist in any clone. It was never the safety net it appeared to be — an argument for freezing the snapshot sooner, not later.

**Deliberately not done in this change.** The panel rebuild. T0.2a and the rebuild have different blast radii: this change is provable offline without regenerating a single artifact, while the rebuild regenerates all five and will trip the row-count checks in 6.1–6.3 that hardcode 4 350. Bundling them would make a rebuild failure indistinguishable from a snapshot-logic failure. Step 3 is next and completes T0.1's DoD in the same run.

**Notes for whoever runs this next.**
- Unemployment now maxes out at **2024** (`AA0003B` `Tid` = 2022–2024; SCB has not published 2025). Skattekraft reaches 2026. The ragged-panel handling in T0.2 is therefore mandatory, not hypothetical — the panel cannot be balanced at the top end.
- `_verify` logs a pre-existing warning that the mean rate (11.63 %) sits outside its historical 3–8 % band. This predates the change and is unrelated to it — it reflects the STATIV denominator question in 7.9, not the snapshot. Worth resolving on its own terms, not folded into a data-source fix.
- The snapshot is a source of record. `scripts/freeze_unemployment_snapshot.py` exists to document how it was made and to re-run the overlap validation; it must never be used to "refresh" the file from a fetch, because the fetch it would need no longer exists.

---

### 2026-09-07 — T0.2 and T0.1 complete · Phase 0 closed · panel is 290 × 17

**Done.** `python pipeline.py --force-refresh` runs end to end from a cold cache in 270 s. The panel is **4 930 rows (290 × 17, 2010–2026)**, ragged by design, with `artifacts/data_provenance.json` recording each source's coverage. Suite is **157 passed** — including all 13 T0.3 baseline tests, unchanged.

**T0.1's DoD is now met, and one part of it would have silently failed.** `tax_base_index_riket` was being merged into the panel and then dropped again, because `_FINAL_COLUMNS` did not list it. The rebuild alone would have produced a panel with no index column and no error. Fixed; all spot checks now pass against the written parquet: Danderyd 191, Filipstad 76, Högsby 73 for 2026, zero nulls in the index.

**A fifth SCB restructure, and the first that fails silently.** T0.2 assumed the remaining fetchers just needed wider year ranges. Population did not: SCB froze `BE0101A/BefolkningNy` at 2024 and published 2025 in a new parallel table, `BefolkningCKM`. Metadata for the old table still resolves, so nothing errors — the fetcher would simply have returned a series one year short while looking complete. The two tables disagree in three ways, each silent: a different ContentsCode for Folkmängd (whose sibling is Folkökning, population *change*), `Civilstand` no longer eliminating (omitting it multiplies every count by the number of civil statuses), and the open-ended age code spelled `100+1` rather than `100+`. `fetch_population` now routes years by each table's declared `Tid` and resolves every code from that table's own metadata rather than hardcoding. METHODOLOGY 12.7 documents it.

**Actual source coverage** — the plan guessed the sources would differ; they differ more than expected:

| Source | Max year | Notes |
|---|---|---|
| skattekraft | **2026** | already fetched by T0.1 |
| population | **2025** | needed the new table |
| education | **2025** | year range widened only |
| unemployment | **2024** | live table caps here; SCB has not published 2025 |

**The binding constraint is unemployment, and that shapes Phase 2.** `complete_case_max_year` is **2024**. T2.1's cross-section must be estimated on 2024 — not on the panel's maximum year, which is 2026 where three of four structural variables are null. The provenance artifact exists so that consumer does not have to guess; METHODOLOGY 2.3.1 states the rule.

**Verified the rebuild changed nothing historical.** All 4 350 pre-existing rows compare identically against the previous panel except `edu_share`, which differs by at most **5e-11** (relative 5.5e-12) — float summation order from fetching one more year, not a data change. The main spec's estimation sample is still the 2010–2024 complete cases (N=4 350), which is why the audit baseline still passes: the main coefficients are the audit's coefficients, and `predictions.parquet` and `decomposition.parquet` are unchanged to within 6e-11.

**One artifact did change materially, and it is the one Phase 2 cares about.** Of the 19 rows in `coefficients.parquet`, the four **lagged**-spec rows moved; the other 15 are identical. The cause is not noise: the lagged spec regresses growth on one-year-lagged regressors, so 2025's realised skattekraft growth can now be paired with 2024's regressors. Its sample grew from **N=4 060 (2011–2024) to N=4 350 (2011–2025)** — a full extra year.

| lagged spec | before | after |
|---|---|---|
| `unemployment_rate` | −0.0989 (t = −6.08) | **−0.1063 (t = −7.32)** |
| `dependency_ratio` | −4.335 (t = −5.14) | −3.805 (t = −4.88) |
| `edu_share` | +0.0061 (t = +0.20) | −0.0071 (t = −0.29) |

This is a strengthening of the finding T2.4 rests on, not a contradiction of it — but **T2.4's written figures are now stale**: it says "unemployment strengthens from −0.059 to −0.099, t from −3.8 to −6.1". The current numbers are −0.106 and t = −7.3. Whoever executes T2.4 should quote the artifact, not the plan text. `edu_share` also flipped sign in this spec while remaining thoroughly insignificant either way (|t| < 0.3), which is worth a sentence in T4.1 rather than any change of substance.

**Notes for whoever runs this next.**
- `pipeline.py` logging crashes on Windows consoles when it prints `β` (cp1252). Cosmetic — the pipeline itself completes and exits 0 — but run it as `PYTHONIOENCODING=utf-8 python pipeline.py` to keep the log readable.
- `_verify` in `fetch_unemployment` still warns that the mean rate (11.63 %) is outside its 3–8 % band. Pre-existing and unrelated to these changes: the STATIV measure is a *flow* (anyone registered at any point in the year, over population 20-64), so it is legitimately higher than an AKU-style stock. The warning band is wrong, not the data — worth correcting on its own.
- `labels.py` now states the ragged coverage in the Metod tab. It previously said "290 kommuner, 15 år, 4 350 observationer", which the rebuild made false.
- `PRD.md` and `REVIEW_2026-04-24.md` still quote the old 4 350 / 15-year figures. Left as written: both are historical records of what was planned and reviewed at the time, and DEVIATIONS is where departures belong.

**One latent trap left deliberately in place.** Every downstream consumer hardcodes `year == 2024` rather than deriving it — `estimate.py:120`, `predict.py:92`, `decompose.py:74`, `01_Riksoversikt.py:100`, `02_Kommunjamforelse.py:175` and `:407`. That is *currently correct*, because 2024 is `complete_case_max_year`, and it is why the ragged panel broke nothing. It stops being correct the moment SCB publishes 2025 unemployment: the complete-case year moves to 2025 and every one of those call sites silently keeps reporting 2024. They were not refactored here because T2.1 and T2.2 rewrite the model-layer three, and rewriting the UI two before the artifact contract settles means doing it twice (the same reasoning that defers T1.2/T1.3). **Whoever does T2.1 should read `complete_case_max_year` from `artifacts/data_provenance.json` rather than adding a sixth hardcoded 2024.**

---

### 2026-09-07 — post-Phase-0 GATE passed · the audit holds on real data

The gate asked whether the 2025 backtest, re-run on data SCB has now actually published, confirms or overturns the audit. **It confirms it.** Realised 2025 skattekraft growth is in the panel, so this run reads committed data only — a third independent path after the audit's ad-hoc scripts and T0.3's fetch-layer reproduction. All three agree to four decimal places.

| Metric | Audit (2026-09-04) | This run | |
|---|---|---|---|
| Pearson r | +0.016 | **+0.0156** | match |
| Spearman ρ | +0.033 | **+0.0333** | match |
| RMSE, model | 1.512 pp | **1.5117 pp** | match |
| RMSE, naive constant mean | 0.974 pp | **0.9738 pp** | match |

The shipped forecast still loses to guessing the national mean, by 55 %. Predicted dispersion is 0.33 pp against a realised 0.98 pp — three times too narrow, exactly as the audit found. Risk classes remain unseparated and mis-ordered against realised growth: låg 4.74 %, medel 4.52 %, hög 4.68 %. "Hög risk" did not grow more slowly than "låg risk"; it grew faster.

**Consequence:** the plan's premise stands, nothing needs re-auditing, and Phase 1 is cleared to start. Step 4 (T1.1, the position and drift module) is next, and it now has 2026 skattekraft and the official SCB index available to build on.

---

### 2026-09-07 — data status confirmed before Phase 1 · AKU ruled out · Phase 2 previewed

Recorded so the state of the data is approvable at a glance rather than reconstructed from three commits.

**Where the data actually stands.** Complete through **2024** for all five variable groups; through **2025** for four of five; through **2026** for skattekraft alone. `complete_case_max_year` = 2024. Full table and rationale in METHODOLOGY 2.3.2.

**The single gap is unemployment 2025, and it is SCB's gap, not ours.** No municipal open-unemployment figure for 2025 exists at SCB in any table. The STATIV annual refresh appears to land in February (the live table was updated 2026-02-13 carrying 2022–2024), so 2025 should arrive around **February 2027**.

**AKU was investigated and ruled out — permanently, on geography.** `AM0401N/NAKUBefolkningLK` is quarterly and runs to 2026K2, which makes it a standing temptation whenever the 2025 gap becomes inconvenient. Its `Region` dimension holds 26 values: Sweden, a "rest of country" aggregate, the 21 counties, and **exactly three municipalities** (Stockholm, Malmö, Göteborg). Three of 290. AKU samples ~29 500 individuals and publishes margins of error as first-class content codes; municipal estimates for small kommuner are not producible from it at any level of effort. `AM0401N` is itself the "Regional data" folder, so nothing municipal sits beneath it. Written up in KRI 3 known-issue 3 so it is not re-investigated.

**The cost of waiting is measured, not assumed.** Spearman(position_t, position_t+1) = 0.991; 0.929 at ten years. Moving the cross-section from 2024 to 2025 would move the median kommun **2 rank places out of 290**. Meanwhile the descriptive spine — the part users see — is computed from skattekraft alone and already runs to 2026, so Phase 1 is unaffected by the gap entirely.

**Phase 2 previewed while the question was open.** The cross-sectional specification was run for 2021–2024: R² = 0.702, 0.712, 0.723, 0.690. The plan's Phase-2 gate (R² > 0.60) is therefore safe in every recent year, not merely the one the audit tested.

> **Corrected the same day.** This entry first reported that "individual coefficients are not stable", citing `dependency_ratio` swinging −4.91 → −9.88 → −5.55. **That was wrong, and it was wrong because it was written without checking the standard errors.** They are 7–9, so those CIs overlap almost entirely and every year shares a common value. The variable is not unstable — it is **not identified**, in any year, in either specification. The corrected diagnosis and its consequences are in T2.1's evidence block; the mistaken framing is left visible here rather than deleted, because a plan that quietly rewrites its own errors is worth less than one that shows them.

**Net effect on the plan: none of the sequencing changes.** Phase 1 is clear to start, Phase 2's premise is better supported than before, and the one open data gap neither blocks nor materially alters either.

---

### 2026-09-07 — UI consequences traced · artifact contract made additive

Phase 2's redesign was specified against the model layer. Reading the UI afterwards showed the plan had no owner for the changes it forces there, and one sequencing trap that would have taken the live site down.

**Nothing in the UI follows the artifacts.** Every chart hardcodes variable names and reads specs by name: `pages/02_Kommunjamforelse.py:341-346` lists its five decomposition bars literally, `app.py:237` reads the `main` coefficient spec, `app.py:136-156` hand-draws an SVG of four variables feeding a regression box. Changing the model changes none of these automatically. T1.2 was written as a page-*hierarchy* task and T4.2 as three label fixes; neither covered the chart contents. Both now carry explicit inventories.

**The trap: this dashboard is deployed and reads committed artifacts.** `pipeline.py` runs locally only, `artifacts/*.parquet` are tracked in git, and Streamlit Cloud serves whatever is on the branch with no build step. T2.2's original DoD said it would write `artifacts/decomposition.parquet` — overwriting the live file at step 6, while the pages that read it are not fixed until step 8. Between those commits the deployed site would crash on missing columns or, worse, keep rendering bars under the wrong labels.

**Fix: make the staging additive.** T2.1 already wrote to a new file (`coefficients_cross.parquet`); T2.2 was inconsistent with its own sibling and now writes `decomposition_cross.parquet`. Steps 5–7 add artifacts and touch nothing the live site reads; **step 8 is the single cutover commit**. This also protects the plan's "defensible stopping points" principle — stopping after step 7 now leaves a working dashboard showing the old model, rather than a broken one. Recorded as METHODOLOGY §11.7, because the constraint outlives this plan.

**Four more user-facing strings found, added to T4.2.** `method_model_name` still calls the model "Tvåvägs fixed effects panelmodell" (demoted by T2.4); `kpi_r2_tooltip` explains away a low R²(within) that Phase 2 replaces with a high cross-sectional one; `decomp_explanation` and `explain_decomp_text` describe contributions to *growth* when T2.2 changes the target to *position*; and `landing_model_explanation` still advertises a 2025 forecast that has since scored r = 0.016 against realised data.

**One latent bug promoted to T1.2's DoD.** Six call sites hardcode `year == 2024` rather than reading `complete_case_max_year`. Correct today, silently wrong the moment SCB publishes 2025 unemployment.

---

**End of REMEDIATION_PLAN.md**
