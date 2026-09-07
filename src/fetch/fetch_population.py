"""Fetch municipal population data from SCB table BE0101.

Downloads folkmängd by single-year age and sex for all 290 kommuner for the
years 2009–2024 (16 years; 2009 required to compute 2010 growth) using the
generic pxweb_client.  Queries are chunked one year at a time to stay under
the PxWeb cell limit (~150 000 cells per request).

Raw per-year responses are cached to data/raw/population_{year}.json.
Returns a tidy long-format DataFrame with columns:
    [kommun_kod, year, age_group, population]
where age_group is one of '0-19', '20-64', '65+'.

These columns feed:
  - dependency_ratio = (pop_0_19 + pop_65plus) / pop_20_64
  - population_growth_pct = year-over-year percent change in total population

Note: this module implements its own per-year loop with per-year caching
rather than using chunk_query_by_year from pxweb_client.  The per-year cache
files (data/raw/population_{year}.json) enable incremental re-fetching of
individual years without re-downloading the full 16-year series.
"""

import logging
from pathlib import Path

import pandas as pd

from src.fetch.pxweb_client import (
    extract_tid_years,
    fetch_metadata,
    get_dimension_codes,
    is_cache_fresh,
    load_df_cache,
    query_pxweb,
    save_df_cache,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# SCB froze BefolkningNy at 2024 and published 2025 in a new parallel table,
# BefolkningCKM, with the same dimensions but different codes.  Years are routed
# to whichever table's Tid actually carries them; nothing about the split is
# hardcoded to a year.  See METHODOLOGY §12.7.
_PRIMARY_TABLE_URL = (
    "https://api.scb.se/OV0104/v1/doris/sv/ssd/START/BE/BE0101/BE0101A/BefolkningNy"
)
_RECENT_TABLE_URL = (
    "https://api.scb.se/OV0104/v1/doris/sv/ssd/START/BE/BE0101/BE0101A/BefolkningCKM"
)
_FALLBACK_TABLE_URL = (
    "https://api.scb.se/OV0104/v1/doris/sv/ssd/START/BE/BE0101/BE0101A/FolkmangdNov"
)
_TABLE_CANDIDATES: list[str] = [
    _PRIMARY_TABLE_URL,
    _RECENT_TABLE_URL,
    _FALLBACK_TABLE_URL,
]

_PROJECT_ROOT = Path(__file__).parents[2]
_CACHE_DIR: Path = _PROJECT_ROOT / "data" / "raw"

_CACHE_MAX_AGE_DAYS: int = 7
_EXPECTED_COMMUNES: int = 290
_DEFAULT_YEARS: list[int] = list(range(2009, 2026))

# Single-year age codes.  The open-ended top code is spelled '100+' in
# BefolkningNy and '100+1' in BefolkningCKM (the suffix marks the one-year
# grouping); _age_codes picks whichever the table offers.
_SINGLE_YEAR_AGES: list[str] = [str(a) for a in range(0, 100)]
_OPEN_ENDED_AGE_CODES: tuple[str, ...] = ("100+", "100+1")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def fetch_population(
    years: list[int] | None = None,
    force_refresh: bool = False,
) -> pd.DataFrame:
    """Fetch population data for all 290 kommuner from SCB BE0101.

    Queries single-year age data for both sexes, then aggregates to three
    broad age groups (0-19, 20-64, 65+).  Each year is fetched as a separate
    PxWeb POST to stay under the cell limit (290 x 101 ages x 2 sexes = 58 580
    cells per year, well under the 150 000-cell limit).

    Per-year raw JSON is cached at data/raw/population_{year}.json.

    Args:
        years: List of integer years to include.  Defaults to 2009–2024.
        force_refresh: If True, ignore per-year caches and re-fetch from API.

    Returns:
        Long-format DataFrame with columns [kommun_kod, year, age_group,
        population].  Exactly 290 x len(years) x 3 rows.

    Raises:
        ValueError: If API calls fail after retries, or shape / sanity checks fail.
    """
    if years is None:
        years = _DEFAULT_YEARS

    routing = _resolve_tables(years)

    frames: list[pd.DataFrame] = []
    for year in years:
        cache_path = _year_cache_path(year)
        if not force_refresh and is_cache_fresh(cache_path, _CACHE_MAX_AGE_DAYS):
            logger.info("Loading population year %d from cache: %s", year, cache_path)
            df_raw = load_df_cache(cache_path)
        else:
            table_url, table_meta = routing[year]
            region_codes = sorted(
                c for c in get_dimension_codes(table_meta, "Region")
                if len(c) == 4 and c.isdigit()
            )
            year_query = _build_year_query(table_meta, region_codes, year)
            logger.info("Fetching population year %d from %s.", year, table_url)
            df_raw = query_pxweb(table_url, year_query)
            save_df_cache(df_raw, cache_path)

        df_agg = _aggregate_to_age_groups(df_raw)
        frames.append(df_agg)

    df = pd.concat(frames, ignore_index=True)
    df = df[df["year"].isin(years)].reset_index(drop=True)

    _verify(df, years)

    logger.info(
        "fetch_population done: %d rows, years %d–%d, %d unique kommuner.",
        len(df),
        df["year"].min(),
        df["year"].max(),
        df["kommun_kod"].nunique(),
    )
    return df


# ---------------------------------------------------------------------------
# Private helpers — table discovery
# ---------------------------------------------------------------------------


def _resolve_tables(years: list[int]) -> dict[int, tuple[str, dict]]:
    """Map each requested year to the BE0101A subtable that carries it.

    Probes the candidate tables once each and routes by their declared Tid
    dimension, so a future SCB split needs a new candidate URL rather than new
    year logic.  Earlier candidates win when several tables offer the same year.

    Args:
        years: Integer years the caller needs.

    Returns:
        Dict mapping each requested year to (table_url, metadata).

    Raises:
        ValueError: If no candidate table is reachable, or if some requested
            year is carried by none of them.
    """
    routing: dict[int, tuple[str, dict]] = {}
    reachable = 0

    for url in _TABLE_CANDIDATES:
        try:
            meta = fetch_metadata(url)
        except ValueError as exc:
            logger.warning("Metadata unavailable for %s (%s); trying next.", url, exc)
            continue
        if "variables" not in meta:
            continue

        reachable += 1
        available = set(extract_tid_years(meta))
        claimed = sorted(y for y in years if y in available and y not in routing)
        for year in claimed:
            routing[year] = (url, meta)
        if claimed:
            logger.info(
                "BE0101 subtable %s serves years %d–%d.", url, min(claimed), max(claimed)
            )

    if reachable == 0:
        raise ValueError(
            "No BE0101A subtable is accessible "
            f"(tried {', '.join(_TABLE_CANDIDATES)}). "
            "Verify SCB API availability and subtable names."
        )

    missing = sorted(set(years) - routing.keys())
    if missing:
        raise ValueError(
            f"No BE0101A subtable carries population for years {missing}. "
            "SCB may have published them in a new table — add its URL to "
            "_TABLE_CANDIDATES. See METHODOLOGY §12.7."
        )

    return routing


def _contents_code(meta: dict) -> str:
    """Return the ContentsCode for Folkmängd (population count) in this table.

    Resolved from metadata rather than hardcoded: BefolkningNy calls it
    BE0101N1 and BefolkningCKM calls it 000007ME.  The sibling code in both
    tables is Folkökning (population *change*), which would be silently wrong.

    Args:
        meta: Table metadata dict.

    Returns:
        The ContentsCode string for the population count.

    Raises:
        ValueError: If no Folkmängd code is present.
    """
    for var in meta.get("variables", []):
        if var.get("code") != "ContentsCode":
            continue
        for code, text in zip(var.get("values", []), var.get("valueTexts", [])):
            if text.strip().lower().startswith("folkmängd"):
                return code

    raise ValueError(
        "No 'Folkmängd' ContentsCode found in the BE0101 table metadata. "
        f"Available: {_dimension_pairs(meta, 'ContentsCode')}"
    )


def _age_codes(meta: dict) -> list[str]:
    """Return this table's 101 single-year age codes, 0 through 100+.

    Aggregate bands (TOT1, 5-9, …) are excluded: requesting them alongside
    single years would double-count the population.

    Args:
        meta: Table metadata dict.

    Returns:
        List of age codes present in the table.

    Raises:
        ValueError: If the open-ended top code cannot be identified.
    """
    available = set(_dimension_values(meta, "Alder"))
    open_ended = next((c for c in _OPEN_ENDED_AGE_CODES if c in available), None)
    if open_ended is None:
        raise ValueError(
            "No open-ended age code (tried "
            f"{', '.join(_OPEN_ENDED_AGE_CODES)}) in the BE0101 Alder dimension."
        )
    return [a for a in _SINGLE_YEAR_AGES if a in available] + [open_ended]


def _dimension_values(meta: dict, code: str) -> list[str]:
    """Return the declared values of one dimension, or [] if it is absent."""
    for var in meta.get("variables", []):
        if var.get("code") == code:
            return var.get("values", [])
    return []


def _dimension_pairs(meta: dict, code: str) -> list[tuple[str, str]]:
    """Return (value, valueText) pairs for one dimension, for error messages."""
    for var in meta.get("variables", []):
        if var.get("code") == code:
            return list(zip(var.get("values", []), var.get("valueTexts", [])))
    return []


def _eliminates(meta: dict, code: str) -> bool:
    """Whether a dimension is summed automatically when left out of the query."""
    for var in meta.get("variables", []):
        if var.get("code") == code:
            return bool(var.get("elimination"))
    return False


# ---------------------------------------------------------------------------
# Private helpers — query construction
# ---------------------------------------------------------------------------


def _build_year_query(meta: dict, region_codes: list[str], year: int) -> dict:
    """Build the PxWeb query for one year, using that table's own codes.

    Uses explicit municipality codes (filter=item) instead of a value-set
    filter (vs:RegionKommun07EjAggr) because the SCB API no longer accepts
    the value-set syntax (returns HTTP 400).

    Civilstand is selected explicitly only when the table does not eliminate
    it.  BefolkningNy eliminates it (so leaving it out sums civil statuses);
    BefolkningCKM does not, and omitting it there would return one row per
    civil status and quadruple the counts.

    Args:
        meta: Metadata for the table this year will be fetched from.
        region_codes: 4-digit municipality codes to request.
        year: The single year to request.

    Returns:
        A PxWeb query dict ready to POST.
    """
    dims: list[dict] = [
        {"code": "Region", "selection": {"filter": "item", "values": region_codes}},
        {"code": "Alder", "selection": {"filter": "item", "values": _age_codes(meta)}},
        {"code": "Kon", "selection": {"filter": "item", "values": ["1", "2"]}},
    ]

    if not _eliminates(meta, "Civilstand"):
        civil_values = _dimension_values(meta, "Civilstand")
        total = next((c for c in ("SC", "TOT") if c in civil_values), None)
        if total is None:
            raise ValueError(
                "Civilstand does not eliminate and offers no total code; "
                f"available: {_dimension_pairs(meta, 'Civilstand')}"
            )
        dims.append(
            {"code": "Civilstand", "selection": {"filter": "item", "values": [total]}}
        )

    dims.append(
        {
            "code": "ContentsCode",
            "selection": {"filter": "item", "values": [_contents_code(meta)]},
        }
    )
    dims.append(
        {"code": "Tid", "selection": {"filter": "item", "values": [str(year)]}}
    )

    return {"query": dims, "response": {"format": "json"}}


# ---------------------------------------------------------------------------
# Private helpers — raw response aggregation
# ---------------------------------------------------------------------------


def _age_code_to_group(age_code: str) -> str:
    """Map a single-year age code string to a broad age group label.

    Args:
        age_code: Raw age code from the SCB API (e.g. '0', '19', '65', '100+').
            BefolkningCKM spells the open-ended code '100+1'.

    Returns:
        One of '0-19', '20-64', or '65+'.
    """
    if age_code.startswith("100+"):
        return "65+"
    age = int(age_code)
    if age <= 19:
        return "0-19"
    if age <= 64:
        return "20-64"
    return "65+"


def _aggregate_to_age_groups(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Convert a raw PxWeb response DataFrame to age-group aggregates.

    Sums population counts across both sexes (Kon=1 and Kon=2) and maps
    the 101 single-year age codes to three broad age groups.

    Args:
        df_raw: Raw DataFrame from query_pxweb (all string columns).

    Returns:
        Aggregated DataFrame with columns [kommun_kod, year, age_group,
        population].

    Raises:
        ValueError: If expected dimension columns are missing.
    """
    # Dimension columns that must never be read as the value column.  Civilstand
    # appears only in BefolkningCKM, which does not eliminate it; without this
    # it would be renamed to population_raw alongside the real value column.
    _DROP_DIMENSIONS = {"contentscode", "civilstand"}

    rename: dict[str, str] = {}
    value_col_raw: str | None = None

    for col in df_raw.columns:
        lower = col.lower()
        if lower == "region":
            rename[col] = "kommun_kod"
        elif lower == "alder":
            rename[col] = "age_raw"
        elif lower == "kon":
            rename[col] = "sex"
        elif lower == "tid":
            rename[col] = "year"
        elif lower in _DROP_DIMENSIONS:
            pass  # drop
        else:
            value_col_raw = col
            rename[col] = "population_raw"

    if value_col_raw is None:
        raise ValueError(
            "Could not identify the population value column in the BE0101 response. "
            f"Available columns: {list(df_raw.columns)}"
        )

    df = df_raw.rename(columns=rename).drop(
        columns=[c for c in df_raw.columns if c.lower() in _DROP_DIMENSIONS],
        errors="ignore",
    )

    df["kommun_kod"] = df["kommun_kod"].astype(str).str.zfill(4)
    df["year"] = df["year"].astype(int)
    df["population_raw"] = (
        pd.to_numeric(df["population_raw"], errors="coerce").fillna(0).astype(int)
    )
    df["age_group"] = df["age_raw"].map(_age_code_to_group)

    agg = (
        df.groupby(["kommun_kod", "year", "age_group"], as_index=False)[
            "population_raw"
        ]
        .sum()
        .rename(columns={"population_raw": "population"})
    )
    return agg


# ---------------------------------------------------------------------------
# Private helpers — cache management
# ---------------------------------------------------------------------------


def _year_cache_path(year: int) -> Path:
    """Return the cache path for a single year's raw population JSON.

    Args:
        year: The integer year.

    Returns:
        Path object pointing to data/raw/population_{year}.json.
    """
    return _CACHE_DIR / f"population_{year}.json"


# ---------------------------------------------------------------------------
# Private helpers — verification
# ---------------------------------------------------------------------------


def _verify(df: pd.DataFrame, years: list[int]) -> None:
    """Run sanity checks on the aggregated population DataFrame.

    Checks:
        1. Exactly 290 unique kommun_kod values per year.
        2. Exactly three age groups per (kommun, year).
        3. National total 2024 is approximately 10.55 million.
        4. Stockholm (0180) is the largest kommune in 2024.

    Args:
        df: Aggregated DataFrame with [kommun_kod, year, age_group, population].
        years: The requested years list.

    Raises:
        ValueError: If hard checks fail.
    """
    expected_groups = {"0-19", "20-64", "65+"}
    for year in years:
        year_df = df[df["year"] == year]
        n_unique = year_df["kommun_kod"].nunique()
        if n_unique != _EXPECTED_COMMUNES:
            raise ValueError(
                f"Expected {_EXPECTED_COMMUNES} unique kommun_kod for year {year}, "
                f"got {n_unique}."
            )
        present_groups = set(year_df["age_group"].unique())
        if present_groups != expected_groups:
            missing = expected_groups - present_groups
            raise ValueError(
                f"Missing age groups {missing} for year {year}. "
                "The API response may have omitted some age bands — "
                "verify the Alder dimension codes and '100+' handling."
            )

    if 2024 not in years:
        logger.info("Year 2024 not in range; skipping 2024 verification checks.")
        return

    df_2024 = df[df["year"] == 2024]
    national_total = df_2024["population"].sum()
    logger.info(
        "National total population 2024: %d (expected ~10 550 000)", national_total
    )
    if not (9_000_000 <= national_total <= 12_000_000):
        raise ValueError(
            f"National total population 2024 is {national_total:,}, "
            "outside the expected range 9 000 000 – 12 000 000. "
            "Verify ContentsCode BE0101N1 and API response."
        )

    df_2024_total = df_2024.groupby("kommun_kod")["population"].sum()
    largest_kod = df_2024_total.idxmax()
    logger.info(
        "Largest 2024 kommune by population: %s (%d persons)",
        largest_kod,
        int(df_2024_total.max()),
    )
    if largest_kod != "0180":
        logger.warning(
            "Expected Stockholm (0180) to be largest but found %s. "
            "Verify kommune code mapping.",
            largest_kod,
        )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    )
    result = fetch_population()
    print(f"\nFetched {len(result)} rows.")
    print(f"Years covered: {sorted(result['year'].unique())}")
    print(f"Unique kommuner: {result['kommun_kod'].nunique()}")
    print(f"Age groups: {sorted(result['age_group'].unique())}")
    print("\n2024 national population by age group:")
    summary = (
        result[result["year"] == 2024]
        .groupby("age_group")["population"]
        .sum()
        .reset_index()
    )
    print(summary.to_string(index=False))
    print(f"\nExpected row count (290 × 16 yrs × 3 groups): {290 * 16 * 3}")
    print(f"Actual row count: {len(result)}")
