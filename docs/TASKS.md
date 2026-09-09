# TASKS.md — Implementation Tasks (16 tasks, 5 days)

**Project:** Skattekraftspanelen (specified as "Kommunal Skattekraft Stress Monitor")

> **Renamed 2026-09-09.** Task text below is kept verbatim as the historical record and
> still refers to the old name and the retired vulnerability ranking.
**References:** `PRD.md` (master spec), `METHODOLOGY.md` (model and formulas), `KRI_Dataset_Identification.md` (data sources and pxweb queries)

---

## How to Use This Document

Each task has the same structure:

* **Task number and title**
* **Day** (1 to 5)
* **Estimated time**
* **Actor:** Developer
* **What:** what this task produces
* **Why:** why it matters
* **How:** technical approach
* **Prompt:** ready-to-paste prompt for the chosen tool, with explicit context references
* **Definition of done:** what passes acceptance

### Division of labor (locked principle)

* **Backend tasks** include: scaffolding, data pipeline logic, backend modules, generation from scratch, tests.
* **Frontend tasks** include: interactive UI iteration, visual debugging, polishing the Streamlit pages, choropleth tuning.

### Critical reminders embedded in every prompt

1. **Two layer language rule.** Code in English. User-facing text in Swedish via `SWEDISH_LABELS`.
2. **Reference PRD.md and METHODOLOGY.md by section, not by paraphrase.** Tools should read the source.
3. **No hardcoded paths.** Always use `pathlib.Path` relative to project root.

### Context loading

Always reference the three context files when working on a task:
- `PRD.md` (master spec)
- `METHODOLOGY.md` (model and formulas)
- `KRI_Dataset_Identification.md` (data sources and pxweb queries)

---

## Day 1: Scaffolding and Data Pipeline (10 to 12 hours)

### TASK 1.1 — Project scaffold and dependency setup
**Day:** 1 · **Time:** 1 hour · **Actor:** Backend

**What:** Create the full folder structure from PRD §3, write `pyproject.toml`, `requirements.txt`, `.gitignore`, `.streamlit/config.toml`, an empty `README.md` with Swedish title and English abstract placeholder, and stub files for every module.

**Why:** A clean scaffold prevents path confusion later. Stub files mean every subsequent task knows where to write.

**How:** Single shell + file generation pass. No business logic.

**Implementation notes:**
```
Read /docs/PRD.md sections 1, 2, 3, and 11.

Create the complete project scaffold for "kommun-skattekraft-stress" exactly as specified in PRD §3. This means:

1. Create every directory listed (data/raw, data/processed, data/geo, data/lookup, artifacts, src/fetch, src/clean, src/model, src/ui, pages, tests, docs, notebooks).

2. Add a .gitkeep file in every otherwise-empty directory so Git tracks them.

3. Write pyproject.toml using the dependencies from PRD §2 and Python >=3.11,<3.12.

4. Write requirements.txt pinning the same dependencies for Streamlit Cloud deployment.

5. Write .gitignore covering: __pycache__/, *.pyc, .venv/, .streamlit/secrets.toml, data/raw/*.json (but NOT data/raw/.gitkeep), data/raw/pipeline.log, .ipynb_checkpoints/, .DS_Store.

6. Write .streamlit/config.toml with theme primary color #C4A35A (gold), background #F7F8FA, secondary background #FFFFFF, text #1A1A2E, font "Source Sans 3, sans-serif", and server.headless = true.

7. Write README.md with Swedish title "Kommunal Skattekraft Stress Monitor" and a 3-line English abstract placeholder. Include badge placeholders for Streamlit Cloud URL and license.

8. Create stub files (each containing only a docstring describing its purpose in English) for every Python file listed in PRD §3.

9. Move docs/PRD.md, docs/TASKS.md, docs/METHODOLOGY.md, docs/KRI_Dataset_Identification.md from their current location into the new docs/ folder.

CRITICAL: All file content (docstrings, comments, README) in English. The README's title and one-line description are the only Swedish strings.

After scaffolding, run `tree -I '__pycache__|.venv'` and report the resulting structure.
```

**Definition of done:**
* `tree` output matches PRD §3
* `pip install -e .` succeeds in a fresh venv
* `git status` shows a clean tree ready for first commit

---

### TASK 1.2 — pxweb client (generic POST + chunking)
**Day:** 1 · **Time:** 1.5 hours · **Actor:** Backend

**What:** Implement `src/fetch/pxweb_client.py` with a generic `query_pxweb(table_url: str, query_body: dict) -> pd.DataFrame` function and a chunking helper.

**Why:** All four fetchers will reuse this. Keeping it in one module simplifies error handling and rate-limit management.

**How:** `requests.post()` with retries, exponential backoff, JSON parsing into a flat dataframe.

**Implementation notes:**
```
Read /docs/PRD.md §2 and /docs/KRI_Dataset_Identification.md §1 and §2.

Implement src/fetch/pxweb_client.py.

Requirements:
- Function `query_pxweb(table_url: str, query_body: dict) -> pd.DataFrame`
  - POSTs to the table URL with JSON body
  - Sets Content-Type header
  - Retries 3 times with exponential backoff (1s, 2s, 4s) on 429 or 5xx
  - Parses the SCB pxweb JSON response into a tidy long-format DataFrame
  - Returns DataFrame with columns: one per query dimension (Region, Tid, etc.) + 'value'
  - Raises ValueError on non-recoverable errors with a clear English message
- Function `fetch_metadata(table_url: str) -> dict` returning the GET response (used to confirm ContentsCode values)
- Function `chunk_query_by_year(table_url: str, base_query: dict, years: list[int]) -> pd.DataFrame`
  - Splits a query into per-year sub-queries when total cells would exceed 100 000
  - Concatenates results
  - Used for BE0101 (population by single-year age) per KRI §4
- Logging via Python logging module (English messages); log every POST with table URL, year range, and row count returned
- Type hints throughout
- English docstrings using Google style

Add unit-style smoke tests in tests/test_pxweb_client.py that mock requests.post and verify retry behavior on 429.
```

**Definition of done:**
* Module importable
* `pytest tests/test_pxweb_client.py` passes
* No hardcoded URLs

---

### TASK 1.3 — Skattekraft fetcher
**Day:** 1 · **Time:** 1 hour · **Actor:** Backend

**What:** `src/fetch/fetch_skattekraft.py` fetches OE0101 skattekraft for all 290 kommuner, 2010 to 2024, and saves to `data/raw/skattekraft.json`.

**Why:** Dependent variable. Smallest, simplest table — get this working first to validate the pxweb_client.

**How:** Use generic client. Confirm ContentsCode via metadata call.

**Implementation notes:**
```
Read /docs/KRI_Dataset_Identification.md §2 carefully. Read /docs/PRD.md §4.

Implement src/fetch/fetch_skattekraft.py.

Requirements:
- Function `fetch_skattekraft(years: list[int] = None, force_refresh: bool = False) -> pd.DataFrame`
- Default years = list(range(2010, 2025))
- Endpoint: https://api.scb.se/OV0104/v1/doris/sv/ssd/START/OE/OE0101/SkatteKraft
- Step 1: Call fetch_metadata to confirm the exact ContentsCode for "skattekraft per invånare"
- Step 2: Build the query body per KRI §2
- Step 3: Call query_pxweb
- Step 4: Rename columns to: kommun_kod (4-digit zero-padded string), year (int), tax_base_per_capita (float in SEK)
- Step 5: Save raw JSON to data/raw/skattekraft.json (idempotent: if file exists and is fresh per KRI §10, skip the API call unless force_refresh=True)
- Step 6: Return the cleaned DataFrame

Implement the verification check from KRI §2:
- assert exactly 290 unique kommun_kod values per year
- log highest 2024 value and which kommun_kod (should be Danderyd 0162, ~496000)
- log national mean for 2024 (should be ~271000)
- if checks fail, raise ValueError with diagnostic message

Add a `if __name__ == "__main__":` block that runs the fetch and prints a summary.

CRITICAL: All variable names, log messages, error messages in English.
```

**Definition of done:**
* `python -m src.fetch.fetch_skattekraft` runs end-to-end
* Returns 4 350-row DataFrame
* Sanity checks pass

---

### TASK 1.4 — Population fetcher (with chunking)
**Day:** 1 · **Time:** 2 hours · **Actor:** Backend

**What:** `src/fetch/fetch_population.py` fetches BE0101 population by single-year age, sex, kommun, 2009 to 2024 (16 years to allow 2010 growth calculation), chunked by year. Saves to `data/raw/population_{year}.json` and returns aggregated panel.

**Why:** Source for both `dependency_ratio` and `population_growth_pct`. Largest data pull, requires chunking.

**How:** Loop over years, one pxweb query per year.

**Implementation notes:**
```
Read /docs/KRI_Dataset_Identification.md §4 carefully.

Implement src/fetch/fetch_population.py.

Requirements:
- Function `fetch_population(years: list[int] = None, force_refresh: bool = False) -> pd.DataFrame`
- Default years = list(range(2009, 2025))
- Use chunk_query_by_year from pxweb_client for the chunking
- Step 1: Confirm subtable URL via metadata. Try BE0101A/BefolkningNy first; if metadata fails, try BE0101A/FolkmangdNov.
- Step 2: For each year, query: all 290 kommuner, all single-year ages 0-100+ (handle 100+ as a special string code), both sexes, content code BE0101N1.
- Step 3: Save per-year raw JSON.
- Step 4: Aggregate to: kommun_kod (zfill 4), year (int), age_group (one of '0-19', '20-64', '65+'), population (int).
- Step 5: Return long-format DataFrame.

Verification per KRI §4:
- 290 unique kommun_kod per year
- National total 2024 ~10.55 million (sum across all kommun and age groups for sex=both)
- Stockholm (0180) is largest
- Log any anomalies

CRITICAL: English code, English logs, type hints, docstrings.
```

**Definition of done:**
* Function returns aggregated DataFrame with expected row count (290 × 16 × 3 = 13 920)
* Verification passes

---

### TASK 1.5 — Unemployment fetcher (with metadata fallback strategy)
**Day:** 1 · **Time:** 2 hours · **Actor:** Backend

**What:** `src/fetch/fetch_unemployment.py` fetches "Andel öppet arbetslösa" per kommun for 2010 to 2024.

**Why:** Independent variable. Trickiest because the AA0003B subtable may have limited time coverage; needs metadata-driven discovery.

**How:** Probe metadata, identify the right subtable, fetch, document fallback path if primary fails.

**Implementation notes:**
```
Read /docs/KRI_Dataset_Identification.md §3 carefully, including the fallback strategies.

Implement src/fetch/fetch_unemployment.py.

Requirements:
- Function `fetch_unemployment(years: list[int] = None, force_refresh: bool = False) -> pd.DataFrame`
- Default years = list(range(2010, 2025))
- Discovery sequence:
  1. Call fetch_metadata on https://api.scb.se/OV0104/v1/doris/sv/ssd/START/AA/AA0003/AA0003B/IntGr1KomKonUtb
  2. Check if the Tid dimension covers 2010 onwards. If yes, proceed.
  3. If not, call fetch_metadata on alternative subtables. Document any fallback used in a log message.
  4. If no subtable covers the full window, raise NotImplementedError with a clear message instructing the developer to consult KRI §3 fallback strategies.
- Find the ContentsCode for "Andel öppet arbetslösa" (the share, not the count)
- Aggregate over Kon (sex) and Utbildningsniva (education level) to get a single value per (kommun, year)
- Output columns: kommun_kod, year, unemployment_rate (float, percent)

Verification per KRI §3:
- 290 kommuner per year
- National mean in 3-8% range
- Higher values in Norrland kommuner than Stockholm region
- Log diagnostic on failure

CRITICAL: This is the riskiest fetcher. If you hit a dead end, do NOT silently produce wrong data. Raise a clear error and write the diagnostic to the log.
```

**Definition of done:**
* Returns 4 350-row DataFrame OR raises a clear error indicating which fallback to invoke manually
* If fallback was used, README of `data/raw/` notes which path was taken

---

### TASK 1.6 — Education fetcher
**Day:** 1 · **Time:** 1.5 hours · **Actor:** Backend

**What:** `src/fetch/fetch_education.py` fetches UF0506 education share for ages 25-64, eftergymnasial 3+ år, all kommuner, 2010 to 2024.

**Why:** Fourth control variable. Slow-moving but theoretically important.

**How:** Sum SUN codes 6 and 7, divide by population 25-64.

**Implementation notes:**
```
Read /docs/KRI_Dataset_Identification.md §5.

Implement src/fetch/fetch_education.py.

Requirements:
- Function `fetch_education(years: list[int] = None, force_refresh: bool = False) -> pd.DataFrame`
- Default years = 2010 to 2024
- Confirm subtable URL via metadata
- Query: all 290 kommuner, age 25-64, both sexes (or sum across), UtbildningsNiva codes 6 and 7
- Compute edu_share as percent: 100 * (count_with_eftergymnasial_3plus / total_25_64)
- Output columns: kommun_kod, year, edu_share (float, percent)

Verification per KRI §5:
- 290 kommuner per year
- National mean ~30%
- Lund and Stockholm at the top, rural Norrland at the bottom

CRITICAL: English code throughout.
```

**Definition of done:**
* Returns 4 350-row DataFrame
* Verification passes

---

### TASK 1.7 — Kommun code harmonization lookup
**Day:** 1 · **Time:** 1 hour · **Actor:** Backend

**What:** Generate `data/lookup/kommunkod_harmonization.csv` with all 290 kommun codes valid for 2024, and implement `src/clean/harmonize_kommunkod.py` to validate and harmonize.

**Why:** Defends against silent data loss from code mismatches across SCB tables.

**How:** Hard-code the 290 codes from SCB's published list, validate every fetched DataFrame against it.

**Implementation notes:**
```
Read /docs/PRD.md §4 and /docs/KRI_Dataset_Identification.md §7.

Step 1: Generate data/lookup/kommunkod_harmonization.csv

The CSV must have columns: kod (4-digit zero-padded string), namn (Swedish), lan_kod (2-digit zero-padded), lan_namn (Swedish), valid_from (year, integer), valid_to (year, integer or 9999 for "current").

Use the official SCB list of 290 kommuner valid in 2024. The 4-digit codes start with län codes:
01 Stockholm, 03 Uppsala, 04 Södermanland, 05 Östergötland, 06 Jönköping, 07 Kronoberg, 08 Kalmar, 09 Gotland, 10 Blekinge, 12 Skåne, 13 Halland, 14 Västra Götaland, 17 Värmland, 18 Örebro, 19 Västmanland, 20 Dalarna, 21 Gävleborg, 22 Västernorrland, 23 Jämtland, 24 Västerbotten, 25 Norrbotten.

If you do not have the full 290-row list memorized, generate a script src/clean/generate_kommunkod_lookup.py that fetches the list from SCB's pxweb (use any small table with Region dimension and "RegionKommun07EjAggr" filter to extract code+name pairs), and call that script to produce the CSV. This is the cleanest path.

Step 2: Implement src/clean/harmonize_kommunkod.py

Function `validate_and_harmonize(df: pd.DataFrame, code_col: str = "kommun_kod") -> pd.DataFrame`:
- Loads lookup CSV
- Asserts every code in df is in the lookup
- Asserts no duplicates within a (code, year) pair
- Adds kommun_name and lan_name columns from lookup
- Raises ValueError with a list of unrecognized codes if validation fails
- English error messages with diagnostic content

Add tests/test_harmonize.py covering: valid input, unknown code, duplicate (kod, year).
```

**Definition of done:**
* CSV has exactly 290 rows
* `validate_and_harmonize` works on a synthetic test DataFrame
* Tests pass

---

### TASK 1.8 — Build panel
**Day:** 1 · **Time:** 1.5 hours · **Actor:** Backend

**What:** `src/clean/build_panel.py` and `src/clean/compute_derived.py` merge all four fetchers' outputs, compute derived variables (`tax_base_growth_pct`, `dependency_ratio`, `population_growth_pct`), and save `data/processed/panel.parquet`.

**Why:** Single canonical input for modeling. Materially reduces downstream complexity.

**How:** Sequential merge on `(kommun_kod, year)`, derived variable computation, harmonization validation, parquet write.

**Implementation notes:**
```
Read /docs/METHODOLOGY.md §2 and /docs/PRD.md §4.

Implement two modules:

1. src/clean/compute_derived.py with three functions:
   - `compute_dependency_ratio(pop_long: pd.DataFrame) -> pd.DataFrame`
     Input: long-format population (kommun_kod, year, age_group, population)
     Output: wide (kommun_kod, year, dependency_ratio)
     Formula: (pop_0_19 + pop_65plus) / pop_20_64
   - `compute_population_growth(pop_long: pd.DataFrame) -> pd.DataFrame`
     Sums population across age groups, computes year-over-year percent change per kommun
     Output: (kommun_kod, year, population, population_growth_pct)
   - `compute_tax_base_growth(skattekraft: pd.DataFrame) -> pd.DataFrame`
     Year-over-year percent change in tax_base_per_capita per kommun
     Output: (kommun_kod, year, tax_base_per_capita, tax_base_growth_pct)

2. src/clean/build_panel.py with one function:
   - `build_panel() -> pd.DataFrame`
     Calls all four fetchers, applies harmonize_kommunkod to each, computes derived variables, merges all on (kommun_kod, year), drops 2009 (only used to compute 2010 growth), writes data/processed/panel.parquet, returns the DataFrame.

Final panel columns:
kommun_kod, kommun_name, lan_kod, lan_name, year, tax_base_per_capita, tax_base_growth_pct, unemployment_rate, dependency_ratio, population, population_growth_pct, edu_share

Expected shape: 290 × 15 = 4350 rows. Validate this and raise if mismatched.

Run sanity checks from METHODOLOGY §6.1 and §6.3 inline; log results; raise on hard failures.

CRITICAL: All English. Type hints. Docstrings.
```

**Definition of done:**
* `python -m src.clean.build_panel` produces `data/processed/panel.parquet`
* Parquet file loads with `pd.read_parquet` and has 4 350 rows
* All sanity checks pass

---

## Day 2: Modeling (6 to 8 hours)

### TASK 2.1 — Exploratory analysis notebook
**Day:** 2 · **Time:** 2 hours · **Actor:** Frontend

**What:** `notebooks/01_exploratory.ipynb` with descriptive statistics, distributions, correlation matrix, top-and-bottom rankings, missing value report.

**Why:** Catches data quality issues before they bite in the regression. Demonstrates analytical thoroughness.

**How:** Standard EDA workflow on `data/processed/panel.parquet`.

**Implementation notes:**
```
@PRD.md @METHODOLOGY.md @KRI_Dataset_Identification.md

Create notebook cells in 01_exploratory.ipynb that load data/processed/panel.parquet and produce, in order:

1. Markdown cell: "Exploratory Data Analysis — Kommunal Skattekraft Stress Monitor" with date and a one-paragraph English description.

2. Imports: pandas, numpy, matplotlib, seaborn (for EDA only, NOT in production code per PRD §2 exclusions).

3. Load panel.parquet and show .info() and .describe().

4. Missing value report: count and percent missing per column, per year.

5. Distribution plots: histogram for each numeric variable.

6. Top 10 / bottom 10 kommuner by 2024 tax_base_per_capita. Verify Danderyd at top per METHODOLOGY §6.1.

7. Top 10 / bottom 10 by 2010-2024 mean tax_base_growth_pct.

8. Correlation matrix of (tax_base_growth_pct, unemployment_rate, dependency_ratio, population_growth_pct, edu_share). Heatmap.

9. Time series of national means (one line per variable) showing 2020 COVID dip in growth.

10. Scatter: tax_base_growth_pct vs each independent variable, with smoother.

11. Markdown summary: any data anomalies, suggestions for the model.

CRITICAL: This is exploratory; comments and markdown can be longer/freer. Variable names still English. Plot titles English (this is a developer notebook, not user-facing).
```

**Definition of done:**
* All cells execute without error
* No surprises that would invalidate the model

---

### TASK 2.2 — Estimate the panel regression
**Day:** 2 · **Time:** 2 hours · **Actor:** Backend

**What:** `src/model/estimate.py` with `estimate_panel_model()`. Runs main spec + 4 robustness specs. Saves model object and coefficients table to artifacts.

**Why:** The empirical core of the project.

**How:** `linearmodels.PanelOLS` with `entity_effects=True, time_effects=True`, clustered SEs.

**Implementation notes:**
```
Read /docs/METHODOLOGY.md §2.

Implement src/model/estimate.py.

Requirements:
- Function `estimate_main(panel: pd.DataFrame) -> linearmodels.panel.results.PanelEffectsResults`
  - Set MultiIndex (kommun_kod, year)
  - Drop rows with any missing values in y or X
  - Y = tax_base_growth_pct
  - X = [unemployment_rate, dependency_ratio, population_growth_pct, edu_share]
  - Estimate PanelOLS(y, X, entity_effects=True, time_effects=True)
  - Use cov_type='clustered', cluster_entity=True
  - Return fitted results object
- Function `estimate_robustness(panel: pd.DataFrame) -> dict[str, results]`
  - Returns dict with keys: 'lagged', 'no_covid', 'large_only', 'no_education'
  - 'lagged': RHS variables lagged one year
  - 'no_covid': drop years 2020 and 2021
  - 'large_only': only kommuner with 2024 population > 10000
  - 'no_education': drop edu_share from RHS
- Function `extract_coefficients(results) -> pd.DataFrame`
  - Returns DataFrame with columns: variable, coefficient, std_error, t_stat, p_value, lower_ci, upper_ci
- Function `save_model_artifacts(main_results, robustness_results, output_dir: Path) -> None`
  - Pickles main_results to artifacts/model_results.pkl
  - Saves coefficients to artifacts/coefficients.parquet (one row per variable per spec, with a 'spec' column)
- Top-level function `run_estimation()` orchestrating all of the above
- Add `if __name__ == "__main__":` block

Logging: log every spec's R², within R², N, T, and significance of each coefficient.

CRITICAL: All English code. Add tests/test_estimate.py with a small synthetic panel.
```

**Definition of done:**
* `python -m src.model.estimate` runs end-to-end
* `artifacts/model_results.pkl` and `artifacts/coefficients.parquet` written
* R² values within plausible range (METHODOLOGY §6.4)

---

### TASK 2.3 — Predict and compute vulnerability
**Day:** 2 · **Time:** 1.5 hours · **Actor:** Backend

**What:** `src/model/predict.py` generates `predicted_growth_2025` for all 290 kommuner, computes `vulnerability_score`, assigns `risk_class`, saves `artifacts/predictions.parquet` and `artifacts/ranking.parquet`.

**Why:** This is what the dashboard's Riksöversikt page displays.

**How:** Apply METHODOLOGY §3 formulas.

**Implementation notes:**
```
Read /docs/METHODOLOGY.md §3 carefully.

Implement src/model/predict.py.

Requirements:
- Function `predict_2025(main_results, panel: pd.DataFrame) -> pd.DataFrame`
  - Extract estimated kommun fixed effects (alpha_i) and year fixed effects (gamma_t)
  - Compute gamma_recent = mean of estimated year FE for 2022, 2023, 2024
  - For each kommun, take 2024 values of independent variables
  - Apply formula in METHODOLOGY §3.1
  - Return DataFrame: kommun_kod, kommun_name, lan_name, predicted_growth_2025
- Function `compute_vulnerability(predictions: pd.DataFrame) -> pd.DataFrame`
  - Compute vulnerability_score per METHODOLOGY §3.2 (z-score, sign-flipped)
  - Assign risk_class per METHODOLOGY §3.3 (quintile-based)
  - Compute vulnerability_rank (1 = most vulnerable)
  - Return DataFrame with all columns: kommun_kod, kommun_name, lan_name, predicted_growth_2025, vulnerability_score, vulnerability_rank, risk_class
- Function `run_prediction()` orchestrating, loading from artifacts, saving to artifacts/predictions.parquet AND artifacts/ranking.parquet (the second is sorted by vulnerability_rank ascending)
- Risk class as Categorical with order ["lag", "medel", "hog"]
- All English

Validation:
- Exactly 290 rows in output
- 58 kommuner in "hog", 174 in "medel", 58 in "lag" (allow ±2 for ties)
- Mean of predicted_growth_2025 within 1 percentage point of mean tax_base_growth_pct over 2010-2024

Add tests/test_predict.py with synthetic main_results and panel.
```

**Definition of done:**
* Both artifact files written
* Validation passes

---

### TASK 2.4 — Decomposition
**Day:** 2 · **Time:** 1 hour · **Actor:** Backend

**What:** `src/model/decompose.py` computes structural decomposition for each kommun's 2024 growth gap vs national mean. Saves `artifacts/decomposition.parquet`.

**Why:** Powers the Kommunjämförelse page (Path B output).

**How:** Apply METHODOLOGY §4.1 formula.

**Implementation notes:**
```
Read /docs/METHODOLOGY.md §4 carefully.

Implement src/model/decompose.py.

Requirements:
- Function `decompose_2024_gaps(main_results, panel: pd.DataFrame) -> pd.DataFrame`
  - Filter panel to year=2024
  - National mean of tax_base_growth_pct, unemployment_rate, dependency_ratio, population_growth_pct, edu_share
  - For each kommun, compute:
    - decomp_unemployment = beta_unemp * (kommun_unemp - national_mean_unemp)
    - decomp_dependency = beta_dep * (kommun_dep - national_mean_dep)
    - decomp_population = beta_pop * (kommun_pop_growth - national_mean_pop_growth)
    - decomp_education = beta_edu * (kommun_edu - national_mean_edu)
    - decomp_residual = (kommun_actual_growth - national_mean_growth) - sum of above four contributions
    - total_gap = sum of all five (should equal kommun_actual_growth - national_mean_growth)
  - Output: kommun_kod, kommun_name, total_gap, decomp_unemployment, decomp_dependency, decomp_population, decomp_education, decomp_residual
- Function `run_decomposition()` orchestrating, saving to artifacts/decomposition.parquet
- Validation: for each kommun, sum of components equals total_gap (within float precision)

Add tests/test_decompose.py with synthetic data confirming decomposition sums correctly.

CRITICAL: English code.
```

**Definition of done:**
* `artifacts/decomposition.parquet` written
* Per-row sum-equality validation passes
* Tests pass

---

### TASK 2.5 — Pipeline orchestrator
**Day:** 2 · **Time:** 0.5 hour · **Actor:** Backend

**What:** `pipeline.py` runs all of the above in sequence, with logging and `--force-refresh` flag.

**Why:** One-command reproducibility.

**Implementation notes:**
```
Read /docs/KRI_Dataset_Identification.md §8 and §10.

Implement pipeline.py at the project root.

Requirements:
- argparse with --force-refresh flag (default False)
- Configure logging to both stdout and data/raw/pipeline.log
- Sequence:
  1. fetch_skattekraft(force_refresh=args.force_refresh)
  2. fetch_population(force_refresh=...)
  3. fetch_unemployment(force_refresh=...)
  4. fetch_education(force_refresh=...)
  5. build_panel()
  6. estimate.run_estimation()
  7. predict.run_prediction()
  8. decompose.run_decomposition()
- Time each step, log "Step X completed in Y seconds"
- Final log: "Pipeline completed. Total time: Y seconds. Artifacts written to artifacts/."
- On exception: log full traceback, exit 1
- Idempotency: if all artifacts/ files exist and are newer than data/processed/panel.parquet, skip steps 6-8 unless --force-refresh
```

**Definition of done:**
* `python pipeline.py` runs cleanly when data is cached (under 30 seconds)
* `python pipeline.py --force-refresh` re-runs everything (2-5 minutes)

---

## Day 3: Streamlit App (8 to 10 hours)

### TASK 3.1 — UI primitives: CSS, components, sidebar, chart theme, labels
**Day:** 3 · **Time:** 2 hours · **Actor:** Backend

**What:** Implement `src/ui/css.py`, `src/ui/components.py`, `src/ui/sidebar.py`, `src/ui/chart_theme.py`, `src/ui/labels.py` per the SHAI design reference adapted to KSS.

**Why:** Every page reuses these. Build once.

**How:** Direct port from the SHAI reference, with KSS branding and `SWEDISH_LABELS` from PRD §9.

**Implementation notes:**
```
Read /docs/PRD.md §6, §7, §9, §10. The SHAI reference design is described there in full.

Implement five files in src/ui/:

1. css.py
   - COLORS dict per PRD §6.1
   - DIVERGING_SCALE list per PRD §6.1
   - GLOBAL_CSS string with: Google Fonts @import (Source Sans 3 + IBM Plex Mono), :root CSS variables, Streamlit chrome hiding (per SHAI ref §5), card styling, hero, KPI card, sidebar, tables, footer note. Replace any "shai-" prefixed branding text with "KSS" but keep CSS class names with "shai-" prefix to avoid renaming.
   - inject_css() function that writes <style>{GLOBAL_CSS}</style> via st.html()

2. labels.py
   - SWEDISH_LABELS dict per PRD §9 (copy verbatim)
   - format_sek(value), format_pct(value, decimals=1), format_signed_pct(value, decimals=1) per PRD §9

3. components.py
   - page_title(eyebrow, title, subtitle, year) -> str (HTML)
   - kpi_card(label, value, unit, delta=None, delta_direction="flat", variant="default", tooltip=None) -> str
   - render_kpi_row(cards: list[str]) -> None (uses st.columns)
   - card_header(title, subtitle="", tag="") -> str
   - risk_pill(level: str) -> str  (level in "lag"/"medel"/"hog", returns Swedish label inside pill)
   - footer_note(source: str, version: str) -> str
   All return raw HTML. All Swedish text comes from SWEDISH_LABELS. Delta direction colors per PRD §6.6 (note inversion vs SHAI: up=green, down=red because higher growth = better for kommun).

4. sidebar.py
   - render_sidebar(page_key: str) -> dict
     Returns {"selected_year": int, "selected_risks": list[str]}
     Brand block with KSS branding
     Navigation links to "/" (Översikt), "/Riksoversikt", "/Kommunjamforelse"
     Active link highlighted per SHAI ref §6
     Year pills (single select), default 2024
     Risk filter pills (multi select), default = all three
     Risk legend
     Footer with "KÄLLA: SCB · OE0101, BE0101, AA0003, UF0506" and version "v1.0"

5. chart_theme.py
   - CHART_PALETTE per PRD §6.1
   - get_chart_layout(title="", height=400, xaxis_title="", yaxis_title="", showlegend=True) -> dict
     Returns Plotly layout dict per SHAI ref §8

CRITICAL: 
- ALL user-facing strings MUST come from SWEDISH_LABELS dict. Never hardcode Swedish in component logic.
- ALL function names, parameter names, docstrings in English.
```

**Definition of done:**
* All five files importable
* Manual smoke test: `streamlit run app.py` shows styled empty page (even before content is added)

---

### TASK 3.2 — Choropleth module
**Day:** 3 · **Time:** 1.5 hours · **Actor:** Backend

**What:** `src/ui/choropleth.py` adapted from the SHAI reference for our `vulnerability_score`.

**Why:** Centerpiece of the Riksöversikt page.

**How:** Port the SHAI Folium implementation, swap data fields to KSS fields, swap legend to Swedish from `SWEDISH_LABELS`.

**Implementation notes:**
```
Read the choropleth reference document attached to this project (the SHAI choropleth complete reference, sections 1-3) and /docs/PRD.md §6.7. Read /docs/KRI_Dataset_Identification.md §6 for the GeoJSON source.

Implement src/ui/choropleth.py.

Adapt the SHAI implementation to KSS:
- Keep the Folium + GeoJSON polygon approach
- Keep DIVERGING_SCALE (import from src.ui.css)
- Keep zoom-gated kommun labels
- Keep tooltip styling
- Replace data field references:
  - SHAI 'z_c' -> KSS 'vulnerability_score'
  - SHAI 'version_c' -> KSS 'predicted_growth_2025'
  - SHAI 'rank_c' -> KSS 'vulnerability_rank'
  - SHAI 'risk_c' -> KSS 'risk_class'
  - SHAI 'transaction_price_sek', 'median_income', 'unemployment_rate' -> drop these and replace with kommun-relevant fields: 'tax_base_per_capita', 'unemployment_rate', 'population'
- Swedish tooltip aliases come from SWEDISH_LABELS (Kommun, Riskklass, Sårbarhetsindex, Prognos 2025, Rang, Skattekraft, Arbetslöshet, Befolkning)
- Caption uses SWEDISH_LABELS["map_legend_caption"]
- vmin/vmax for the LinearColormap: ±2.5 (z-score range)

GeoJSON path: data/geo/kommuner.geojson. Add a Day-0 instruction comment at the top of the module: "Run scripts/download_geojson.py once before first use to populate data/geo/."

Function signature:
render_choropleth(
    data: pd.DataFrame,  # must contain kommun_kod, vulnerability_score, predicted_growth_2025, vulnerability_rank, risk_class, kommun_name, tax_base_per_capita, unemployment_rate, population
    height: int = 480,
    key: str = "kss_choropleth",
) -> None

CRITICAL:
- All function/variable names English
- All user-visible text Swedish via SWEDISH_LABELS
- Comments and docstrings English
```

**Then create scripts/download_geojson.py:**

**Implementation notes (continuation):**
```
Create scripts/download_geojson.py:

Downloads the kommun-level GeoJSON from okfse/sweden-geojson. Tries the GitHub raw content URL first; if that fails, prints instructions for manual download via swemaps.

After downloading:
- Validate exactly 290 features
- Validate property keys can be normalized to 4-digit kommun_kod
- Save to data/geo/kommuner.geojson

Idempotent: skip download if file exists and has 290 features.
```

**Definition of done:**
* `python scripts/download_geojson.py` populates `data/geo/kommuner.geojson` with 290 features
* `from src.ui.choropleth import render_choropleth` imports cleanly

---

### TASK 3.3 — Landing page (`app.py`)
**Day:** 3 · **Time:** 2 hours · **Actor:** Frontend

**What:** Build `app.py` per PRD §7 (Page 1).

**Why:** First impression. Every section per spec.

**How:** Iterate visually with `streamlit run app.py` open.

**Implementation notes:**
```
@PRD.md @METHODOLOGY.md

Build app.py as the landing page per PRD §7 Page 1. Follow this section order strictly:

1. st.set_page_config per PRD §6.4
2. inject_css() from src.ui.css
3. render_sidebar("landing") from src.ui.sidebar
4. Hero block: navy gradient with gold border. Use SWEDISH_LABELS["eyebrow_landing"], ["title_landing"], and the lead text from PRD §7 Page 1.
5. Stat strip (4 cells): "290 KOMMUNER", "15 ÅR PANEL", "4 STRUKTURVARIABLER", "FIXED EFFECTS". Numbers in IBM Plex Mono per design.
6. Modellöversikt: SVG flow showing 3 input boxes (Arbetslöshet, Demografi, Utbildning) -> Regressionsmodell box -> 3 output boxes (Prognos, Rangordning, Dekomponering). Inline SVG per SHAI reference §9 pattern.
7. Variabler & vikter: this is the KEY adaptation from SHAI. Instead of weighted index weights, show the regression coefficients as horizontal bars. Load artifacts/coefficients.parquet (filter to spec='main'), display each variable with its beta and significance star. Variable labels from SWEDISH_LABELS. Bars colored by sign: positive=green, negative=red.
8. Pipeline steps (4 steps with gold arrow connectors): Datainsamling -> Rensning -> Estimering -> Prognos. Step boxes per SHAI ref.
9. Navigation cards (2): "Riksöversikt" and "Kommunjämförelse". Each is an st.page_link in a styled card with description.
10. Källor & metod credibility block: source pills SCB OE0101, SCB BE0101, SCB AA0003, SCB UF0506.
11. footer_note(source=SWEDISH_LABELS["footer_source"], version="v1.0")

CRITICAL REMINDERS:
- ALL visible text MUST be in Swedish via SWEDISH_LABELS dict.
- ZERO English text visible to user. If you find yourself typing Swedish into the page directly, stop and add the key to SWEDISH_LABELS instead.
- Variable names, function names, comments: English.
- Use components from src.ui.components.
- Charts: use get_chart_layout from src.ui.chart_theme for consistent styling.
- Run streamlit run app.py and visually verify each section against PRD §7 description.

Iterate visually. After each major section, take a screenshot and check against PRD spec.
```

**Definition of done:**
* All 11 sections present
* Zero English visible to user
* Visually matches SHAI design

---

### TASK 3.4 — Riksöversikt page
**Day:** 3 · **Time:** 2 hours · **Actor:** Frontend

**What:** Build `pages/01_Riksoversikt.py` per PRD §7 Page 2.

**Why:** Headline analytical output.

**How:** Iterate visually with the choropleth as centerpiece.

**Implementation notes:**
```
@PRD.md @METHODOLOGY.md

Build pages/01_Riksoversikt.py per PRD §7 Page 2.

Sections:
1. st.set_page_config + inject_css + render_sidebar("national")
2. page_title(eyebrow=SWEDISH_LABELS["eyebrow_national"], title=SWEDISH_LABELS["title_national"], subtitle="Skattekraftens prognosticerade utveckling 2025, alla 290 kommuner", year=2025)
3. Load artifacts/predictions.parquet, artifacts/ranking.parquet, artifacts/coefficients.parquet using @st.cache_data
4. KPI row (4 cards via render_kpi_row):
   - kpi_card(SWEDISH_LABELS["kpi_median_prognosis"], value=format_pct(median_predicted_growth), variant="default")
   - kpi_card(SWEDISH_LABELS["kpi_high_risk_count"], value=str(count_hog_risk), variant="danger")
   - kpi_card(SWEDISH_LABELS["kpi_largest_decline"], value=format_signed_pct(min_predicted) + " · " + worst_kommun, variant="danger")
   - kpi_card(SWEDISH_LABELS["kpi_model_r2"], value=format_pct(within_r2 * 100), variant="default")
5. Two-column layout (3:2 split): left = card containing render_choropleth, right = card containing histogram of predicted_growth_2025 (Plotly with get_chart_layout). Both wrapped in st.container(border=True) with card_header.
6. Rangordning card (full width): sortable st.dataframe with columns Rang, Kommun, Län, Prognos 2025 (%), Riskklass (with risk_pill colored display). Add download_button for CSV.
7. footer_note

Apply selected_year and selected_risks from sidebar to filter the table and the histogram (NOT the choropleth — choropleth always shows latest predictions).

CRITICAL:
- ZERO English visible text. All from SWEDISH_LABELS.
- Numeric formatting via format_sek / format_pct.
- All Plotly charts use get_chart_layout for consistent styling.
- Code English throughout.

Run and visually verify. Test the choropleth tooltips show Swedish content. Test CSV download.
```

**Definition of done:**
* All sections render
* Choropleth interactive with Swedish tooltips
* CSV download works

---

### TASK 3.5 — Kommunjämförelse page
**Day:** 3 · **Time:** 1.5 hours · **Actor:** Frontend

**What:** Build `pages/02_Kommunjamforelse.py` per PRD §7 Page 3.

**Implementation notes:**
```
@PRD.md @METHODOLOGY.md

Build pages/02_Kommunjamforelse.py per PRD §7 Page 3.

Sections:
1. set_page_config + inject_css + render_sidebar("kommun")
2. page_title(eyebrow=..., title=SWEDISH_LABELS["title_kommun"], subtitle="Strukturell dekomponering för vald kommun")
3. Load artifacts/predictions.parquet, artifacts/decomposition.parquet, data/processed/panel.parquet (cached)
4. st.selectbox with SWEDISH_LABELS["label_kommun_select"], options sorted by vulnerability_rank ascending (most vulnerable first), default to first (most vulnerable). Display format: "Filipstad (Värmland) — Rang 12"
5. KPI row (4 cards) for selected kommun:
   - "Skattekraft 2024": format_sek(latest skattekraft)
   - "Tillväxt 2024": format_signed_pct(actual 2024 growth) with delta_direction up/down based on sign
   - "Prognos 2025": format_signed_pct(predicted)
   - "Sårbarhetsrang": "X / 290"
6. Historisk trend card: Plotly line chart, two lines (selected kommun in COLORS["secondary"] blue, national average in COLORS["text_secondary"] gray dashed), x = 2010-2024, y = tax_base_per_capita.
7. Dekomponering card: horizontal Plotly bar chart. One bar per component: contrib_unemployment, contrib_dependency, contrib_population, contrib_education, contrib_residual. Bar labels from SWEDISH_LABELS["contrib_*"]. Color by sign: positive=COLORS["low_risk"] green, negative=COLORS["high_risk"] red.
8. Peer comparison card: table of 5 closest kommuner by vulnerability_score. Columns: Kommun, Län, Prognos 2025, Sårbarhetsrang.
9. Methodology link card: st.link_button to GitHub METHODOLOGY.md raw URL with text SWEDISH_LABELS["btn_show_method"]
10. footer_note

CRITICAL:
- All Swedish via SWEDISH_LABELS
- Historisk trend MUST use Swedish month abbreviations if displayed
- All numbers Swedish-formatted
- Code English

Visually verify each section.
```

**Definition of done:**
* All sections render
* Selecting different kommuner updates everything
* Historical chart shows kommun vs national clearly

---

### TASK 3.6 — Visual polish and accessibility pass
**Day:** 3 · **Time:** 1 hour · **Actor:** Frontend

**What:** Final pass across all three pages: visual consistency, hover states, accessibility.

**Implementation notes:**
```
@PRD.md (especially §6 design system, §8 acceptance criteria)

Conduct a visual polish pass on app.py, pages/01_Riksoversikt.py, pages/02_Kommunjamforelse.py.

Checklist (verify on each page):
1. Sidebar visible with KSS branding, gold accent bar, navigation
2. Sidebar pills styled: active = gold bg + navy text; inactive = transparent + white
3. Streamlit menu, footer, default header all hidden
4. Page title block with eyebrow (gold uppercase), title (28px), subtitle, year display (right side)
5. KPI cards: left accent bar, label uppercase 10.5px, value 32px tabular-nums, delta with arrow + color
6. Cards: white bg, 1px border #EEF0F3, 4px radius, 22-24px padding, header with bottom border
7. Charts: Source Sans 3 font, navy hover bg, dotted Y gridlines
8. Choropleth: zoom-gated labels work, tooltip styled with white card and Swedish content
9. Tables: uppercase headers 10.5px, IBM Plex Mono numeric cells
10. Footer note: centered with KÄLLA label and version code chip

Check ZERO English visible text. Quick sweep:
- All chart axis titles Swedish?
- All Plotly hovertemplate text Swedish?
- All dataframe column headers Swedish?
- All error/warning messages Swedish (if any are triggered)?
- All button labels Swedish?

Add @media (prefers-reduced-motion: reduce) styles per SHAI ref §13.
Add aria-hidden="true" to decorative SVGs.

Iterate until acceptance criteria PRD §8 pass.
```

**Definition of done:**
* PRD §8 acceptance criteria all pass on all three pages

---

## Day 4: Documentation, Tests, Deployment (4 to 6 hours)

### TASK 4.1 — README and documentation
**Day:** 4 · **Time:** 2 hours · **Actor:** Frontend (writing benefits from interactive editing)

**What:** Polish `README.md` (Swedish, with English abstract). Embed screenshots. Link to dashboard.

**Implementation notes:**
```
@PRD.md @METHODOLOGY.md @KRI_Dataset_Identification.md

Polish README.md.

Structure:
1. Title (Swedish): "Kommunal Skattekraft Stress Monitor"
2. Live demo badge with Streamlit Cloud URL (placeholder until deployed)
3. English abstract (3-4 sentences) for international readers
4. Swedish description (1 paragraph)
5. Sections in Swedish:
   - "Om projektet" — what and why
   - "Modell" — short explanation pointing to METHODOLOGY.md for details (link)
   - "Datakällor" — bullet list with SCB table IDs
   - "Köra lokalt" — install + pipeline + streamlit run instructions (commands in code blocks; commands themselves are English of course)
   - "Filstruktur" — high-level tree
   - "Begränsningar" — link to METHODOLOGY.md §7
   - "Källor" — list with URLs
6. Three screenshots: landing page, Riksöversikt with choropleth, Kommunjämförelse with decomposition.
7. License (MIT recommended)

CRITICAL: Section headings and prose Swedish. Code commands and code-block content English. File names English.

Use markdown that renders well on GitHub (syntax highlighting, tables, badges).
```

**Definition of done:**
* README renders cleanly on GitHub
* Screenshots present
* Install commands copy-paste-runnable

---

### TASK 4.2 — Test suite completion
**Day:** 4 · **Time:** 1 hour · **Actor:** Backend

**What:** Ensure `pytest` covers harmonization, derived computation, decomposition. Add a smoke test that loads each artifact.

**Implementation notes:**
```
Read /docs/PRD.md §8 (acceptance criteria, code quality).

Audit existing tests in tests/. Ensure these test files exist and pass:
- test_pxweb_client.py (from Task 1.2)
- test_harmonize.py (from Task 1.7)
- test_estimate.py (from Task 2.2)
- test_predict.py (from Task 2.3)
- test_decompose.py (from Task 2.4)

Add tests/test_artifacts.py with smoke tests:
- artifacts/predictions.parquet exists, 290 rows, expected columns
- artifacts/ranking.parquet exists, 290 rows, sorted by vulnerability_rank
- artifacts/decomposition.parquet exists, 290 rows
- artifacts/coefficients.parquet exists, has 'spec' column with 5 unique values

Run pytest, ensure all pass. Add a pytest configuration in pyproject.toml if needed.

CRITICAL: Test code in English. Test function names start with test_.
```

**Definition of done:**
* `pytest` exits 0
* All 6 test files present

---

### TASK 4.3 — Streamlit Cloud deployment
**Day:** 4 · **Time:** 1 hour · **Actor:** Frontend (visual deployment workflow)

**What:** Deploy to Streamlit Community Cloud. Get the public URL. Update README badge.

**Implementation notes:**
```
Manual deployment steps:

1. Verify all artifacts/ files committed
2. Verify data/geo/kommuner.geojson committed
3. Verify requirements.txt has all deployed dependencies
4. Push to GitHub main branch
5. Go to streamlit.io/cloud, log in with GitHub
6. New app -> select repo kommun-skattekraft-stress, branch main, main file path app.py
7. Advanced settings: Python 3.11
8. Deploy
9. Wait for build (3-5 minutes typically)
10. Test the deployed URL: navigate all 3 pages, choropleth loads, no errors
11. Update README.md with the actual Streamlit Cloud URL
12. Commit and push the README update

If build fails:
- Check the build logs in Streamlit Cloud
- Common issues: missing dependency in requirements.txt, file path case sensitivity, GeoJSON file too large
- Fix locally, push, redeploy
```

**Definition of done:**
* Public URL live
* All 3 pages load
* Cold start under 5 seconds after warm

---

### TASK 4.4 — Interview prep document (your private notes)
**Day:** 4 · **Time:** 1 hour · **Actor:** Yourself (no AI needed)

**What:** Personal notes for interview pitches. Not committed to repo.

**Content to prepare:**
* 30-second pitch (one sentence per role cluster from METHODOLOGY §10 and PRD audience)
* 2-minute walkthrough of the app
* 5-minute deep-dive: model spec, identification limitations, why two-way FE, why prediction not causal
* List of 5 likely interview questions with bullet-point answers
* Practice opening the dashboard from scratch (cold start) and narrating

**Definition of done:**
* You can deliver each version without referencing notes

---

## Day 5: Buffer (2 to 4 hours, only if needed)

Use Day 5 only for:
* Bugs surfaced after Streamlit deployment
* Polish requested by trusted reviewers
* Additional robustness checks if reviewers question methodology
* Drafting accompanying job application cover letter referencing the project

Do NOT use Day 5 to add features. Scope creep at the end of a portfolio project is the most common mistake. The dashboard as scoped in PRD is sufficient.

---

## Summary Table

| # | Task | Day | Hours | Actor |
|---|---|---|---|---|
| 1.1 | Project scaffold | 1 | 1 | Backend |
| 1.2 | pxweb client | 1 | 1.5 | Backend |
| 1.3 | Skattekraft fetcher | 1 | 1 | Backend |
| 1.4 | Population fetcher | 1 | 2 | Backend |
| 1.5 | Unemployment fetcher | 1 | 2 | Backend |
| 1.6 | Education fetcher | 1 | 1.5 | Backend |
| 1.7 | Kommunkod harmonization | 1 | 1 | Backend |
| 1.8 | Build panel | 1 | 1.5 | Backend |
| 2.1 | Exploratory notebook | 2 | 2 | Frontend |
| 2.2 | Estimate regression | 2 | 2 | Backend |
| 2.3 | Predict + vulnerability | 2 | 1.5 | Backend |
| 2.4 | Decomposition | 2 | 1 | Backend |
| 2.5 | Pipeline orchestrator | 2 | 0.5 | Backend |
| 3.1 | UI primitives | 3 | 2 | Backend |
| 3.2 | Choropleth module | 3 | 1.5 | Backend |
| 3.3 | Landing page | 3 | 2 | Frontend |
| 3.4 | Riksöversikt page | 3 | 2 | Frontend |
| 3.5 | Kommunjämförelse page | 3 | 1.5 | Frontend |
| 3.6 | Visual polish | 3 | 1 | Frontend |
| 4.1 | README | 4 | 2 | Frontend |
| 4.2 | Tests completion | 4 | 1 | Backend |
| 4.3 | Deploy | 4 | 1 | Frontend |
| 4.4 | Interview prep | 4 | 1 | You |

**Total backend tasks:** 12
**Total frontend tasks:** 7
**Total your direct hours:** 1 (interview prep) + supervision time
**Total project hours:** ≈ 28 hours over 5 days

---

**End of TASKS.md**