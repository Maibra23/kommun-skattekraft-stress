# KRI_Dataset_Identification.md - Dataset Identification & Audit

**Project:** Kommunal Skattekraft Stress Monitor
**Purpose:** Implementation-ready audit of every data source. For each variable: source authority, full URL, pxweb table ID, query parameters, response schema, expected row count, known data quality issues, refresh cadence, and join keys.

This document is the contract between the data sources and the pipeline. If a fetcher behaves differently from what is documented here, the documentation is updated, not the assumption.

---

## 1. Source Authority Map

| Source | Domain | Auth required | Format |
|---|---|---|---|
| SCB Statistikdatabasen (pxweb v1) | `api.scb.se/OV0104/v1/doris/sv/ssd/...` | No | JSON (POST) |
| SCB Statistikdatabasen (web UI) | `statistikdatabasen.scb.se/pxweb/sv/ssd/...` | No | HTML (browser only) |
| okfse/sweden-geojson (boundary file) | `github.com/okfse/sweden-geojson` | No | GeoJSON |

All SCB tables are accessed via the same pxweb v1 API pattern:
```
POST https://api.scb.se/OV0104/v1/doris/sv/ssd/START/{topic}/{table_id}
Content-Type: application/json
Body: { "query": [...], "response": { "format": "json" } }
```

The `{topic}` segment of the URL must match the table family (e.g. OE for offentlig ekonomi, BE for befolkning, AM for arbetsmarknad, AA for arbetsmarknad/integration, UF for utbildning).

---

## 2. Variable: `tax_base_per_capita` (Skattekraft per invånare)

### Identification
* **Authority:** SCB
* **Statistic name:** Skatteunderlag och skattekraft
* **Table ID:** OE0101 (subtable: SkatteKraft)
* **Web reference:** `https://www.statistikdatabasen.scb.se/pxweb/sv/ssd/START__OE__OE0101/SkatteKraft/`
* **API endpoint:** `https://api.scb.se/OV0104/v1/doris/sv/ssd/START/OE/OE0101/SkatteKraft`

### Definition (Swedish, from SCB)
"Skattekraften beräknas som skatteunderlag i kronor per invånare vid taxeringsårets ingång."

### Available ContentsCodes (all three, verified against live metadata 2026-09-06)

| Code | SCB label | Used? | Panel column |
|---|---|---|---|
| `OE0101A5` | Skatteunderlag, kronor | No | — (total SEK, not per capita) |
| `OE0101A0` | Skattekraft, kronor per invånare | **Yes** | `tax_base_per_capita` |
| `OE0101B0` | Andel av riksmedelvärdet, procent | **Yes** (added T0.1) | `tax_base_index_riket` |

`OE0101B0` is SCB's own published index with riket = 100 — the figure Regionfakta
and other secondary sources republish. It went unused until the 2026-09-04 audit
(finding F1); see `REMEDIATION_PLAN.md` T0.1.

**Weighting caution.** SCB's riksmedelvärde is **population-weighted** (≈271 000 kr
for 2026). This project's own cross-municipality mean is **unweighted** (≈230 660 kr
for 2024). The index and the pipeline's national mean therefore rest on different
denominators and must never be combined in one chart. See `METHODOLOGY.md` §7.13.

The index is a **soft dependency**: `_discover_index_code` returns `None` rather than
raising if SCB withdraws the metric, leaving the column null. The per-capita metric
is a hard dependency and raises.

### Coverage
* **Time:** 1995 to 2026 (annual). Skattekraft for a budget year is published the
  preceding December, so 2026 has been available since December 2025. The pipeline
  fetches 2009–2026 (2009 as the growth baseline).
* **Geography:** All 290 kommuner + national total
* **Unit:** SEK per inhabitant (current prices); percent of national mean for the index

### Query parameters
```python
# Step 1: GET metadata to discover region codes and confirm ContentsCode
metadata = fetch_metadata(TABLE_URL)
region_codes = sorted(
    c for c in get_dimension_codes(metadata, "Region")
    if len(c) == 4 and c.isdigit()  # 290 municipality codes; excludes county/national totals
)

# Step 2: POST query with explicit codes
query_body = {
    "query": [
        {
            "code": "Region",
            "selection": {
                "filter": "item",                  # explicit list (vs: filter is deprecated)
                "values": region_codes              # 290 four-digit codes from metadata
            }
        },
        {
            "code": "ContentsCode",
            "selection": {
                "filter": "item",
                "values": ["OE0101A0"]              # skattekraft per invånare (confirmed via metadata)
            }
        },
        {
            "code": "Tid",
            "selection": {
                "filter": "item",
                "values": [str(y) for y in range(2009, 2025)]  # 2009 needed for 2010 growth baseline
            }
        }
    ],
    "response": {"format": "json"}
}
```

**Important:** The `vs:RegionKommun07EjAggr` value-set filter was deprecated by SCB and returns HTTP 400. The pipeline discovers explicit 4-digit municipality codes from the metadata at runtime. The `ContentsCode` `OE0101A0` is confirmed against metadata; if SCB changes it, the fetcher falls back to keyword matching on "skattekraft, kronor per" in the value texts. Year 2009 is included to compute the 2010 growth rate baseline; it is dropped from the final panel.

### Response schema
```json
{
  "columns": [
    {"code": "Region", "text": "region", "type": "d"},
    {"code": "ContentsCode", "text": "...", "type": "c"},
    {"code": "Tid", "text": "år", "type": "t"},
    {"code": "Skattekraft", "text": "skattekraft per invånare", "type": "c"}
  ],
  "data": [
    {"key": ["0114", "000001LB", "2024"], "values": ["..."]}
  ]
}
```

### Expected row count
290 kommuner x 16 years (2009-2024) = **4 640 rows** from API; after dropping 2009 growth-baseline rows, the final panel contains 290 x 15 = **4 350 rows**.

### Known issues
1. **Reference year vs income year:** Skattekraft for year t is based on income from year t-2. The 2025 published number reflects 2023 income. Document this explicitly in tooltips.
2. **Cell limit:** pxweb caps cells per query at ~150,000. 290 x 1 metric x 16 years = 4 640 cells, well under limit. No chunking needed.
3. **Kommun code changes:** None within 2010-2024 window. (Knivsta separated from Uppsala in 2003, before window.) Verified.
4. **Value-set filter deprecated:** `vs:RegionKommun07EjAggr` returns HTTP 400 as of 2024. Pipeline uses explicit 290 codes from metadata. See METHODOLOGY 12.1.
5. **ContentsCode change:** The legacy code `000001LB` was replaced by `OE0101A0`. Pipeline confirms code at runtime via metadata.

### Join key
`region` (4-digit kommun code, zero-padded). Use `kommun_kod` as the column name after rename.

### Refresh cadence
Annual, typically published in December for the following budget year (skattekraft 2026 published Dec 2025).

### Verification check (Day 1)
After fetching, verify:
* Exactly 290 unique `kommun_kod` values per year
* `Danderyd` (kod 0162) has the highest 2024 value (observed: 481 069 SEK)
* Unweighted mean of 2024 values within 200 000-350 000 SEK range (observed: 230 660 SEK). Note: SCB's published "riksmedelvärde" (~271 000 SEK) is population-weighted and therefore higher than the unweighted municipality mean

---

## 3. Variable: `unemployment_rate` (Öppen arbetslöshet)

### Identification
* **Authority:** SCB STATIV (data originally from Arbetsförmedlingen)
* **Statistic name:** Integration och arbetsmarknad - andel öppet arbetslösa
* **Table ID:** AA0003 (one live subtable plus a committed snapshot - see coverage below)
* **API endpoints:**
  * **2010-2021:** none. `AA0003X/IntGr1KomKonUtb` served these years until SCB withdrew the entire AA0003X group in 2026; served from `data/lookup/unemployment_2010_2021.csv` instead. See METHODOLOGY 12.6.
  * **2022-:** `https://api.scb.se/OV0104/v1/doris/sv/ssd/START/AA/AA0003/AA0003B/IntGr1KomUtbBAS` (current table, 2022-2024 as of 2026-09-07)

### Definition
"Andelen personer som någon gång under året registrerats som öppet arbetslösa i sökandekategori för öppen arbetslöshet, dividerat med befolkningen 20-64 år."

This is a **flow measure** (registered at any point during the year), not a point-in-time stock. Values are therefore higher than AKU survey-based unemployment.

### Coverage
* **Time:** 2010-2024. SCB reorganized the STATIV tables around 2023-2024 (old subtable moved to the `AA0003X` archive path, new `AA0003B/IntGr1KomUtbBAS` covering 2022+, see METHODOLOGY 12.2), then in 2026 withdrew the `AA0003X` group altogether (METHODOLOGY 12.6). 2022 onwards is live; 2010-2021 is no longer fetchable from SCB.
* **Geography:** All 290 kommuner
* **Unit:** Percent (share of population 20-64)

### Snapshot + live strategy (implemented)
The pipeline splits the requested year range at the 2021/2022 boundary:

| Year range | Source | Coverage |
|---|---|---|
| 2010-2021 | `data/lookup/unemployment_2010_2021.csv` | committed snapshot; **withdrawn from SCB, cannot be re-fetched** |
| 2022- | `AA0003B/IntGr1KomUtbBAS` | 2022-2024 as of 2026-09-07 |

Both frames are concatenated. Constants `_SNAPSHOT_LAST_YEAR = 2021` and `_LIVE_TABLE_FIRST_YEAR = 2022` in `fetch_unemployment.py` control the split.

The snapshot is a **source of record**: it holds 3 480 kommun-year observations that exist nowhere else. It can be copied forward but never regenerated. `scripts/freeze_unemployment_snapshot.py` documents its provenance and re-runs the 2022-2024 overlap validation that shows it is the same series SCB still publishes (max abs diff 0.000000 pp at the 2026-09-07 freeze). See DEVIATIONS 6.1 for why this was chosen over re-sourcing from Kolada or Arbetsförmedlingen.

### Query parameters (per table)
```python
# Step 1: GET metadata to discover region codes
metadata = fetch_metadata(table_url)
region_codes = sorted(
    c for c in get_dimension_codes(metadata, "Region")
    if len(c) == 4 and c.isdigit()
)

# Step 2: POST query using total-aggregate codes to avoid cell limit
query_body = {
    "query": [
        {"code": "Region", "selection": {"filter": "item", "values": region_codes}},
        {"code": "Kon", "selection": {"filter": "item", "values": ["1+2"]}},       # both sexes (SCB total)
        {"code": "UtbNiv", "selection": {"filter": "item", "values": ["000"]}},     # all education levels (SCB total)
        {"code": "BakgrVar", "selection": {"filter": "item", "values": ["TOT"]}},   # all backgrounds (SCB total)
        {"code": "ContentsCode", "selection": {"filter": "item", "values": ["<from metadata>"]}},
        {"code": "Tid", "selection": {"filter": "item", "values": [str(y) for y in subset_years]}}
    ],
    "response": {"format": "json"}
}
```

**Total-code optimization:** Using `Kön='1+2'`, `UtbNiv='000'`, `BakgrVar='TOT'` selects the pre-aggregated SCB total directly. This reduces each POST to 290 x 1 x 1 x 1 x n_years cells (well within the ~150 000 cell limit) and avoids any need for client-side averaging.

### Expected row count
290 x 15 = **4 350 rows** (concatenated from both tables)

### Known issues
1. **Definition change in 2018:** SCB updated the methodology - "från och med uppdatering år 2018 av nya uppgifter från 1997 och framåt justerades även innehållet i Andel öppet arbetslösa." Pre-2018 values may differ slightly from post-2018 series. The table notes this; we accept it and document.
2. **STATIV table restructure (2023-2024), then withdrawal (2026):** The old `AA0003B/IntGr1KomKonUtb` subtable (and its siblings `IntGr1KomKon`, `IntGr1Kom`) was moved to archive path `AA0003X`; the new `AA0003B/IntGr1KomUtbBAS` covers only 2022+. In 2026 SCB withdrew `AA0003X` entirely — every path into the group returns HTTP 400 — so 2010-2021 now comes from a committed snapshot. See METHODOLOGY 12.2 and 12.6.
3. **Not the same as AKU:** AKU (Arbetskraftsundersökningarna) is the official survey-based unemployment rate but is unavailable at kommun level for small kommuner. The STATIV register-based measure is a flow measure (higher values than AKU). Volunteer this limitation in interviews (METHODOLOGY 7).
4. **Value-set filter deprecated:** `vs:RegionKommun07EjAggr` returns HTTP 400. Pipeline uses explicit codes from metadata. See METHODOLOGY 12.1.

### Join key
`region` to `kommun_kod` (4-digit, zero-padded).

### Refresh cadence
Annual, published mid-year for previous reference year.

### Verification check (Day 1)
* All 290 kommuner present per year
* National mean in plausible range for register-based flow measure: 8-15 % (observed: 11.6 % mean across 2010-2024). Note: this is higher than AKU point-in-time unemployment (3-8 %) because the STATIV measure counts anyone registered as unemployed at any point during the year
* Norrland and Bergslagen kommuner should generally show higher values than Stockholm/Mälardalen

---

## 4. Variable: `dependency_ratio` and `population_growth_pct` (from BE0101)

### Identification
* **Authority:** SCB
* **Statistic name:** Befolkningsstatistik - folkmängd efter region, ålder, kön, civilstånd
* **Table ID:** BE0101 (specifically the population by region and age subtable)
* **Web reference:** `https://www.statistikdatabasen.scb.se/pxweb/sv/ssd/START__BE__BE0101/`
* **Likely subtable:** `BE0101A/BefolkningNy` or `BE0101A/FolkmangdNov` (verify via metadata)
* **API endpoint base:** `https://api.scb.se/OV0104/v1/doris/sv/ssd/START/BE/BE0101/BE0101A/`

### Definition
Folkmängd by kommun, single-year age, sex. We aggregate to age groups for our derived variables.

### Coverage
* **Time:** 1968 onwards (we use 2009-2024 to compute population_growth_pct for 2010-2024)
* **Geography:** All 290 kommuner + aggregations
* **Unit:** Number of persons

### Query parameters
```python
# Step 1: GET metadata to discover region codes and resolve table URL
# Primary: BE0101A/BefolkningNy; fallback: BE0101A/FolkmangdNov
table_url, metadata = _resolve_table_url()
region_codes = sorted(
    c for c in get_dimension_codes(metadata, "Region")
    if len(c) == 4 and c.isdigit()
)

# Step 2: POST one query per year (chunked to stay under cell limit)
query_body = {
    "query": [
        {"code": "Region", "selection": {"filter": "item", "values": region_codes}},
        {"code": "Alder", "selection": {"filter": "item", "values": [
            *[str(a) for a in range(0, 100)], "100+"
        ]}},
        {"code": "Kon", "selection": {"filter": "item", "values": ["1", "2"]}},
        {"code": "ContentsCode", "selection": {"filter": "item", "values": ["BE0101N1"]}},
        {"code": "Tid", "selection": {"filter": "item", "values": [str(year)]}}  # one year at a time
    ],
    "response": {"format": "json"}
}
```

### Expected row count and chunking
* 290 kommuner x 101 ages x 2 sexes x 16 years = **937 280 cells total**
* **Exceeds pxweb cell limit (~150 000).** Chunked by year.
* **Chunking strategy:** One year per POST to 290 x 101 x 2 = 58 580 cells per query. Well under limit. 16 sequential queries with per-year caching (`data/raw/population_{year}.json`).
* After fetching, single-year ages are aggregated to three broad age groups: `0-19`, `20-64`, `65+` (summing across both sexes). This produces 290 x 3 age groups per year.

### Derived variables
* `dependency_ratio_t = (pop_aged_0_19_t + pop_aged_65plus_t) / pop_aged_20_64_t`
* `population_total_t = sum over all ages`
* `population_growth_pct_t = (population_total_t / population_total_{t-1} - 1) * 100`

### Join key
`region` to `kommun_kod`.

### Refresh cadence
Annual, published February for previous year-end.

### Known issues
1. **Value-set filter deprecated:** `vs:RegionKommun07EjAggr` returns HTTP 400. Pipeline uses explicit codes from metadata. See METHODOLOGY 12.1.
2. **Table URL may change:** Primary table `BefolkningNy` has a fallback to `FolkmangdNov`. The fetcher tries both.
3. **Long-format output:** The aggregated DataFrame has 3 rows per (municipality, year) - one per age group. The `validate_and_harmonize` step in `build_panel.py` uses a deduplicated slice to avoid false duplicate errors.

### Verification check (Day 1)
* National total approximately matches SCB published 10.55 million (observed 2024: 10 587 710)
* Stockholm kommun (kod 0180) is largest by population (observed: 995 574)
* Bjurholm (kod 2403) or similar small Norrland kommun is among smallest
* `dependency_ratio` range approximately 0.5-1.25 nationally (observed: 0.508-1.241), with rural kommuner higher

---

## 5. Variable: `edu_share` (Andel eftergymnasialt utbildade)

### Identification
* **Authority:** SCB
* **Statistic name:** Befolkningens utbildning
* **Table ID:** UF0506
* **Web reference:** `https://www.statistikdatabasen.scb.se/pxweb/sv/ssd/START__UF__UF0506/`
* **Current subtable:** `UF0506B/Utbildning` (1985-2024). Fallback: `UF0506B/UtbBefRegionR`
* **API endpoint:** `https://api.scb.se/OV0104/v1/doris/sv/ssd/START/UF/UF0506/UF0506B/Utbildning`

### Definition
Andel av befolkningen 25-64 år med eftergymnasial utbildning 3 år eller längre (SUN 2020 codes 6+7), per kommun.

### Coverage
* **Time:** Annual, available for full 2010-2024 window (typically published spring of following year)
* **Geography:** All 290 kommuner
* **Unit:** Number of persons per (kommun, age, sex, education level) cell; pipeline computes percent share

### Query parameters
```python
# Step 1: GET metadata to discover region codes, education codes, age codes, sex codes
metadata = fetch_metadata(table_url)
region_codes = sorted(
    c for c in get_dimension_codes(metadata, "Region")
    if len(c) == 4 and c.isdigit()
)
# Education codes for SUN 6+7 (eftergymnasial 3+ år + forskarutbildning)
# Age codes for 25-64 range (individual year codes, e.g. "25", "26", ..., "64")
# Sex codes: "1" (men) and "2" (women) - no combined "1+2" code in current table

# Step 2: POST query - chunked by (year, sex) to stay under cell limit
# Per chunk: 290 x 40 ages x 8 edu levels x 1 sex = 92 800 cells (under 150 000 limit)
for year in years:
    for sex_code in ["1", "2"]:
        query_body = {
            "query": [
                {"code": "Region", "selection": {"filter": "item", "values": region_codes}},
                {"code": "UtbildningsNiva", "selection": {"filter": "item", "values": edu_codes}},
                {"code": "Alder", "selection": {"filter": "item", "values": age_codes}},
                {"code": "Kon", "selection": {"filter": "item", "values": [sex_code]}},
                {"code": "ContentsCode", "selection": {"filter": "item", "values": [contents_code]}},
                {"code": "Tid", "selection": {"filter": "item", "values": [str(year)]}}
            ],
            "response": {"format": "json"}
        }
```

**Per-sex-year chunking:** The current `UF0506B/Utbildning` table has no combined sex code (`1+2`). With 290 x 40 ages x 8 education levels x 2 sexes = 185 600 cells per year, the SCB cell limit (~150 000) is exceeded. The pipeline detects this and fetches one (year, sex) pair at a time (92 800 cells each), then aggregates across sex to compute `edu_share`. See METHODOLOGY 12.4.

**Education share formula:** `edu_share = sum(population with SUN 6+7) / sum(population with any SUN code)`, computed per (kommun, year) after aggregating across all age codes in the 25-64 range and both sexes.

### Expected row count
290 x 15 = **4 350 rows** (after aggregation to edu_share per kommun-year)

### Known issues
1. **Slow-moving:** Education stocks change slowly within a kommun. Within-kommun variation across 15 years is modest. beta_4 may have wide confidence interval. Document in METHODOLOGY 7.7.
2. **Definition stable:** SUN 2020 has been used consistently across the time window. No series break.
3. **Table renamed (2024):** Old subtable names `Utbildning4`, `Utbildning3`, `Utbildning4C` all return HTTP 400. Current table is `UF0506B/Utbildning`. See METHODOLOGY 12.3.
4. **Value-set filter deprecated:** `vs:RegionKommun07EjAggr` returns HTTP 400. Pipeline uses explicit codes from metadata. See METHODOLOGY 12.1.
5. **No combined sex code:** Unlike older tables, `Utbildning` has only `Kön='1','2'` (no `'1+2'`). Requires per-sex chunking. See METHODOLOGY 12.4.

### Join key
`region` to `kommun_kod`.

### Refresh cadence
Annual, typically published April-May.

### Verification check (Day 1)
* Lund kommun (kod 1281) and Stockholm should have highest values
* Rural Norrland kommuner should have lowest
* National mean approximately 19-20 % for SUN codes 6+7 only (observed: 19.5 %). Note: the broader "all post-secondary" figure (~30 %) includes SUN code 5 (eftergymnasial <3 år), which we exclude

---

## 6. Geographic boundaries: `kommuner.geojson`

### Source
* **Repository:** `okfse/sweden-geojson` on GitHub
* **URL:** `https://github.com/okfse/sweden-geojson`
* **License:** Permissive (per repository README - verify before use)
* **Recommended file:** the kommun-level GeoJSON file in the repository (file path varies; use the highest-resolution version that fits under 10 MB).

### Alternative source (fallback)
* **Package:** `swemaps` on PyPI (https://github.com/stefur/swemaps)
* **Usage:** `pip install swemaps`, then load via `swemaps.get_path("kommun")`.
* GeoParquet format, includes `table_to_geojson()` convenience function.
* Coordinate system: WGS 84 (EPSG:4326), already converted from SWEREF 99 TM.

### Properties needed
* `id` or `kommun_kod`: 4-digit code, zero-padded, joinable to `kommun_kod` in panel data
* `name` or `kommun`: kommun name
* `geometry`: Polygon or MultiPolygon, WGS 84

### Storage
Place in `data/geo/kommuner.geojson`. Commit to repo (small file; verify under 15 MB).

### Verification (Day 0 or early Day 1)
* File loads without error
* Exactly 290 features
* Codes harmonize with SCB kommun_kod after `.zfill(4)`

---

## 7. Kommun code harmonization

### Why needed
Kommun boundaries can change over time. While 2010-2024 has been mostly stable, any code that joins multiple SCB tables across years must defend against:
* New codes appearing
* Old codes disappearing
* Renames (rare)

### Reference list
SCB publishes the official kommun code list at:
`https://www.scb.se/hitta-statistik/regional-statistik-och-kartor/regionala-indelningar/lan-och-kommuner/`

### Implementation
* Static CSV at `data/lookup/kommunkod_harmonization.csv` with columns: `kod`, `namn`, `lan_kod`, `lan_namn`, `valid_from`, `valid_to`
* For 2010-2024 window, expect 290 stable codes. If pipeline detects unexpected codes during cleaning, raise an error and require manual reconciliation (don't silently drop).

---

## 8. Pipeline orchestration: full data flow

```
+-------------------------------------------------------------+
| pipeline.py (run locally, writes artifacts to repo)         |
+-------------------------------------------------------------+
        |
        | to  src/fetch/fetch_skattekraft.py
        |     POST OE0101/SkatteKraft
        |     to data/raw/skattekraft.json
        |
        | to  src/fetch/fetch_population.py
        |     POST BE0101/... (chunked by year)
        |     to data/raw/population_{year}.json (16 files)
        |
        | to  src/fetch/fetch_unemployment.py
        |     POST AA0003/...
        |     to data/raw/unemployment.json
        |
        | to  src/fetch/fetch_education.py
        |     POST UF0506/...
        |     to data/raw/education.json
        |
        | to  src/clean/build_panel.py
        |     - Load all raw JSON
        |     - Harmonize kommun_kod (zfill, validate against lookup)
        |     - Compute dependency_ratio, population_growth_pct, tax_base_growth_pct
        |     - Merge into single dataframe with key (kommun_kod, year)
        |     to data/processed/panel.parquet
        |
        | to  src/model/estimate.py
        |     - Load panel.parquet
        |     - Estimate two-way FE PanelOLS
        |     - Save model object and coefficients
        |     to artifacts/model_results.pkl
        |     to artifacts/coefficients.parquet
        |
        | to  src/model/predict.py
        |     - Use estimated betas + 2024 values
        |     - Generate predicted_growth_2025 for all 290 kommuner
        |     - Compute vulnerability_score (z-score, sign-flipped)
        |     - Assign risk_class (quintile-based)
        |     to artifacts/predictions.parquet
        |     to artifacts/ranking.parquet
        |
        + to  src/model/decompose.py
              - For each kommun, decompose 2024 gap vs national mean
              - Contribution = (kommun_value - national_mean) * beta
              to artifacts/decomposition.parquet
```

---

## 9. Data quality monitoring (built into pipeline)

Every fetch and clean step logs:
* Rows fetched
* Unique kommun_kod count (must be 290 for full SCB pulls)
* Year range
* Missing value count per column
* Any kommun_kod not in harmonization lookup (raises error)

Save log to `data/raw/pipeline.log` for traceability.

---

## 10. Re-running the pipeline

`python pipeline.py` should be:
* **Idempotent:** Running twice produces the same artifacts
* **Cached:** If `data/raw/` files exist and were fetched within 7 days, reuse them. CLI flag `--force-refresh` to override.
* **Fast on cached:** Under 30 seconds when all raw data is cached
* **Slow on fresh:** 2-5 minutes including pxweb calls (depends on SCB API responsiveness)

---

**End of KRI_Dataset_Identification.md**