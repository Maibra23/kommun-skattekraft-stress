# KRI_Dataset_Identification.md — Dataset Identification & Audit

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

### Coverage
* **Time:** 1995 to 2025 (annual)
* **Geography:** All 290 kommuner + national total
* **Unit:** SEK per inhabitant, current prices

### Query parameters
```python
query_body = {
    "query": [
        {
            "code": "Region",
            "selection": {
                "filter": "vs:RegionKommun07EjAggr",  # 290 kommuner, no aggregations
                "values": []  # empty = all
            }
        },
        {
            "code": "ContentsCode",
            "selection": {
                "filter": "item",
                "values": ["000001LB"]  # skattekraft per invånare; verify code on first call
            }
        },
        {
            "code": "Tid",
            "selection": {
                "filter": "item",
                "values": ["2010", "2011", "2012", "2013", "2014",
                           "2015", "2016", "2017", "2018", "2019",
                           "2020", "2021", "2022", "2023", "2024"]
            }
        }
    ],
    "response": {"format": "json"}
}
```

**Important:** The exact `ContentsCode` value (e.g. `000001LB`) must be confirmed by an initial GET to the table metadata endpoint. The fetcher in `src/fetch/pxweb_client.py` should fetch metadata first, then construct the query.

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
290 kommuner × 15 years = **4 350 rows**

### Known issues
1. **Reference year vs income year:** Skattekraft for year t is based on income from year t-2. The 2025 published number reflects 2023 income. Document this explicitly in tooltips.
2. **Cell limit:** pxweb caps cells per query at ~150,000. 290 × 1 metric × 15 years = 4 350 cells, well under limit. No chunking needed.
3. **Kommun code changes:** None within 2010–2024 window. (Knivsta separated from Uppsala in 2003, before window.) Verified.

### Join key
`region` (4-digit kommun code, zero-padded). Use `kommun_kod` as the column name after rename.

### Refresh cadence
Annual, typically published in December for the following budget year (skattekraft 2026 published Dec 2025).

### Verification check (Day 1)
After fetching, verify:
* Exactly 290 unique `kommun_kod` values per year
* `Danderyd` (kod 0162) has the highest 2024 value
* National mean of 2024 values approximately matches SCB's reported 271 000 SEK (2024 figure)

---

## 3. Variable: `unemployment_rate` (Öppen arbetslöshet)

### Identification
* **Authority:** SCB STATIV (data originally from Arbetsförmedlingen)
* **Statistic name:** Integration och arbetsmarknad — andel öppet arbetslösa
* **Table ID:** AA0003 (subtable family: AA0003B)
* **Web reference:** `https://www.statistikdatabasen.scb.se/pxweb/sv/ssd/START__AA__AA0003__AA0003B/`
* **API endpoint base:** `https://api.scb.se/OV0104/v1/doris/sv/ssd/START/AA/AA0003/AA0003B/`

### Definition
"Andelen personer som någon gång under året registrerats som öppet arbetslösa i sökandekategori för öppen arbetslöshet, dividerat med befolkningen 20–64 år."

### Coverage
* **Time:** Per the table description, AA0003B contains data only for the 2022–2023 web preview, but the underlying STATIV database holds data from 1997 forward. **Action: confirm full series availability via metadata call on Day 1.** If pre-2022 data is not exposed via this specific subtable, fall back to the older STATIV table or use the alternative endpoint.
* **Geography:** All 290 kommuner
* **Unit:** Percent (share)

### Fallback strategy if AA0003B does not provide 2010–2021
1. **Primary alternative:** Pull from older STATIV-derived table (search SCB pxweb for "Andel öppet arbetslösa" with longer time series; an integration table starting 1997 is documented to exist).
2. **Secondary alternative:** Compute manually from Arbetsförmedlingen's monthly statistics aggregated to annual mean. Adds complexity.
3. **Last resort:** Restrict time window to 2014–2024 and document the trade-off in METHODOLOGY §7.

### Query parameters (template, adjust after metadata check)
```python
query_body = {
    "query": [
        {"code": "Region", "selection": {"filter": "vs:RegionKommun07EjAggr", "values": []}},
        {"code": "ContentsCode", "selection": {"filter": "item", "values": ["<TBD from metadata>"]}},
        {"code": "Tid", "selection": {"filter": "item", "values": [str(y) for y in range(2010, 2025)]}}
    ],
    "response": {"format": "json"}
}
```

### Expected row count
290 × 15 = **4 350 rows** (assuming full series available)

### Known issues
1. **Definition change in 2018:** SCB updated the methodology — "från och med uppdatering år 2018 av nya uppgifter från 1997 och framåt justerades även innehållet i Andel öppet arbetslösa." Pre-2018 values may differ slightly from post-2018 series. The table notes this; we accept it and document.
2. **Series break with RAMS / BAS transition:** RAMS was discontinued in 2022, replaced by BAS (Befolkningens arbetsmarknadsstatus). For our use case, we use the STATIV-derived "Andel öppet arbetslösa" which draws from Arbetsförmedlingen registrations directly, avoiding the RAMS/BAS break.
3. **Not the same as AKU:** AKU (Arbetskraftsundersökningarna) is the official survey-based unemployment rate but is unavailable at kommun level for small kommuner. The STATIV register-based measure is what's actually usable. Volunteer this limitation in interviews (METHODOLOGY §7).

### Join key
`region` → `kommun_kod` (4-digit, zero-padded).

### Refresh cadence
Annual, published mid-year for previous reference year.

### Verification check (Day 1)
* All 290 kommuner present per year
* National mean should be in plausible range (3–8% historically)
* Norrland and Bergslagen kommuner should generally show higher values than Stockholm/Mälardalen

---

## 4. Variable: `dependency_ratio` and `population_growth_pct` (from BE0101)

### Identification
* **Authority:** SCB
* **Statistic name:** Befolkningsstatistik — folkmängd efter region, ålder, kön, civilstånd
* **Table ID:** BE0101 (specifically the population by region and age subtable)
* **Web reference:** `https://www.statistikdatabasen.scb.se/pxweb/sv/ssd/START__BE__BE0101/`
* **Likely subtable:** `BE0101A/BefolkningNy` or `BE0101A/FolkmangdNov` (verify via metadata)
* **API endpoint base:** `https://api.scb.se/OV0104/v1/doris/sv/ssd/START/BE/BE0101/BE0101A/`

### Definition
Folkmängd by kommun, single-year age, sex. We aggregate to age groups for our derived variables.

### Coverage
* **Time:** 1968 onwards (we use 2009–2024 to compute population_growth_pct for 2010–2024)
* **Geography:** All 290 kommuner + aggregations
* **Unit:** Number of persons

### Query parameters
```python
query_body = {
    "query": [
        {"code": "Region", "selection": {"filter": "vs:RegionKommun07EjAggr", "values": []}},
        {"code": "Alder", "selection": {"filter": "item", "values": [
            # All single-year ages 0 through 100+
            *[str(a) for a in range(0, 100)], "100+"
        ]}},
        {"code": "Kon", "selection": {"filter": "item", "values": ["1", "2"]}},  # both sexes
        {"code": "ContentsCode", "selection": {"filter": "item", "values": ["BE0101N1"]}},  # folkmangd
        {"code": "Tid", "selection": {"filter": "item", "values": [str(y) for y in range(2009, 2025)]}}
    ],
    "response": {"format": "json"}
}
```

### Expected row count and chunking
* 290 kommuner × 101 ages × 2 sexes × 16 years = **937 280 cells**
* **Exceeds pxweb cell limit (~150 000).** MUST chunk.
* **Chunking strategy:** Iterate over years, one year per query → 290 × 101 × 2 = 58 580 cells per query. Well under limit. 16 sequential queries.

Alternative chunking: query age groups (0-19, 20-64, 65+) directly if the table allows aggregation. Reduces complexity downstream.

### Derived variables
* `dependency_ratio_t = (pop_aged_0_19_t + pop_aged_65plus_t) / pop_aged_20_64_t`
* `population_total_t = sum over all ages`
* `population_growth_pct_t = (population_total_t / population_total_{t-1} - 1) * 100`

### Join key
`region` → `kommun_kod`.

### Refresh cadence
Annual, published February for previous year-end.

### Verification check (Day 1)
* National total approximately matches SCB published 10.55 million (2024 year-end)
* Stockholm kommun (kod 0180) is largest by population
* Bjurholm (kod 2403) or similar small Norrland kommun is among smallest
* `dependency_ratio` is roughly 0.7–0.9 nationally, with rural kommuner higher

---

## 5. Variable: `edu_share` (Andel eftergymnasialt utbildade)

### Identification
* **Authority:** SCB
* **Statistic name:** Befolkningens utbildning
* **Table ID:** UF0506
* **Web reference:** `https://www.statistikdatabasen.scb.se/pxweb/sv/ssd/START__UF__UF0506/`
* **Likely subtable:** `UF0506B/Utbildning4` or similar (verify via metadata)
* **API endpoint base:** `https://api.scb.se/OV0104/v1/doris/sv/ssd/START/UF/UF0506/`

### Definition
Andel av befolkningen 25–64 år med eftergymnasial utbildning 3 år eller längre, per kommun.

### Coverage
* **Time:** Annual, available for full 2010–2024 window (typically published spring of following year)
* **Geography:** All 290 kommuner
* **Unit:** Percent (share)

### Query parameters (template)
```python
query_body = {
    "query": [
        {"code": "Region", "selection": {"filter": "vs:RegionKommun07EjAggr", "values": []}},
        {"code": "UtbildningsNiva", "selection": {"filter": "item", "values": ["6", "7"]}},  # eftergymnasial 3+ år
        {"code": "Alder", "selection": {"filter": "item", "values": ["25-64"]}},
        {"code": "Kon", "selection": {"filter": "item", "values": ["1+2"]}},  # total
        {"code": "ContentsCode", "selection": {"filter": "item", "values": ["<TBD>"]}},
        {"code": "Tid", "selection": {"filter": "item", "values": [str(y) for y in range(2010, 2025)]}}
    ],
    "response": {"format": "json"}
}
```

**Action Day 1:** Confirm exact code values via metadata. The actual UtbildningsNiva codes (SUN 2000) are: 1 = förgymnasial <9 år, 2 = förgymnasial 9 år, 3 = gymnasial <3 år, 4 = gymnasial 3 år, 5 = eftergymnasial <3 år, 6 = eftergymnasial 3+ år, 7 = forskarutbildning. We sum codes 6+7.

### Expected row count
290 × 15 = **4 350 rows** (after summing the two utbildningsnivå codes)

### Known issues
1. **Slow-moving:** Education stocks change slowly within a kommun. Within-kommun variation across 15 years is modest. β₄ may have wide confidence interval. Document in METHODOLOGY §6.
2. **Definition stable:** SUN 2000 has been used consistently across the time window. No series break.

### Join key
`region` → `kommun_kod`.

### Refresh cadence
Annual, typically published April–May.

### Verification check (Day 1)
* Lund kommun (kod 1281) and Stockholm should have highest values
* Rural Norrland kommuner should have lowest
* National mean approximately 30% (verify against SCB published statistic)

---

## 6. Geographic boundaries: `kommuner.geojson`

### Source
* **Repository:** `okfse/sweden-geojson` on GitHub
* **URL:** `https://github.com/okfse/sweden-geojson`
* **License:** Permissive (per repository README — verify before use)
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
Kommun boundaries can change over time. While 2010–2024 has been mostly stable, any code that joins multiple SCB tables across years must defend against:
* New codes appearing
* Old codes disappearing
* Renames (rare)

### Reference list
SCB publishes the official kommun code list at:
`https://www.scb.se/hitta-statistik/regional-statistik-och-kartor/regionala-indelningar/lan-och-kommuner/`

### Implementation
* Static CSV at `data/lookup/kommunkod_harmonization.csv` with columns: `kod`, `namn`, `lan_kod`, `lan_namn`, `valid_from`, `valid_to`
* For 2010–2024 window, expect 290 stable codes. If pipeline detects unexpected codes during cleaning, raise an error and require manual reconciliation (don't silently drop).

---

## 8. Pipeline orchestration: full data flow

```
┌─────────────────────────────────────────────────────────────┐
│ pipeline.py (run locally, writes artifacts to repo)         │
└─────────────────────────────────────────────────────────────┘
        │
        ├─→ src/fetch/fetch_skattekraft.py
        │     POST OE0101/SkatteKraft
        │     → data/raw/skattekraft.json
        │
        ├─→ src/fetch/fetch_population.py
        │     POST BE0101/... (chunked by year)
        │     → data/raw/population_{year}.json (16 files)
        │
        ├─→ src/fetch/fetch_unemployment.py
        │     POST AA0003/...
        │     → data/raw/unemployment.json
        │
        ├─→ src/fetch/fetch_education.py
        │     POST UF0506/...
        │     → data/raw/education.json
        │
        ├─→ src/clean/build_panel.py
        │     - Load all raw JSON
        │     - Harmonize kommun_kod (zfill, validate against lookup)
        │     - Compute dependency_ratio, population_growth_pct, tax_base_growth_pct
        │     - Merge into single dataframe with key (kommun_kod, year)
        │     → data/processed/panel.parquet
        │
        ├─→ src/model/estimate.py
        │     - Load panel.parquet
        │     - Estimate two-way FE PanelOLS
        │     - Save model object and coefficients
        │     → artifacts/model_results.pkl
        │     → artifacts/coefficients.parquet
        │
        ├─→ src/model/predict.py
        │     - Use estimated betas + 2024 values
        │     - Generate predicted_growth_2025 for all 290 kommuner
        │     - Compute vulnerability_score (z-score, sign-flipped)
        │     - Assign risk_class (quintile-based)
        │     → artifacts/predictions.parquet
        │     → artifacts/ranking.parquet
        │
        └─→ src/model/decompose.py
              - For each kommun, decompose 2024 gap vs national mean
              - Contribution = (kommun_value - national_mean) * beta
              → artifacts/decomposition.parquet
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
* **Slow on fresh:** 2–5 minutes including pxweb calls (depends on SCB API responsiveness)

---

**End of KRI_Dataset_Identification.md**