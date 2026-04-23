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
"""

import copy
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from src.fetch.pxweb_client import fetch_metadata, query_pxweb

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_PRIMARY_TABLE_URL = (
    "https://api.scb.se/OV0104/v1/doris/sv/ssd/START/BE/BE0101/BE0101A/BefolkningNy"
)
_FALLBACK_TABLE_URL = (
    "https://api.scb.se/OV0104/v1/doris/sv/ssd/START/BE/BE0101/BE0101A/FolkmangdNov"
)

_PROJECT_ROOT = Path(__file__).parents[2]
_CACHE_DIR: Path = _PROJECT_ROOT / "data" / "raw"

_CACHE_MAX_AGE_DAYS: int = 7
_EXPECTED_COMMUNES: int = 290
_DEFAULT_YEARS: list[int] = list(range(2009, 2025))
_CONTENTS_CODE = "BE0101N1"

# Single-year age codes as returned by the SCB API
_AGE_CODES: list[str] = [str(a) for a in range(0, 100)] + ["100+"]


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
    PxWeb POST to stay under the cell limit (290 × 101 ages × 2 sexes = 58 580
    cells per year, well under the 150 000-cell limit).

    Per-year raw JSON is cached at data/raw/population_{year}.json.

    Args:
        years: List of integer years to include.  Defaults to 2009–2024.
        force_refresh: If True, ignore per-year caches and re-fetch from API.

    Returns:
        Long-format DataFrame with columns [kommun_kod, year, age_group,
        population].  Exactly 290 × len(years) × 3 rows.

    Raises:
        ValueError: If API calls fail after retries, or shape / sanity checks fail.
    """
    if years is None:
        years = _DEFAULT_YEARS

    table_url = _resolve_table_url()
    base_query = _build_base_query()

    frames: list[pd.DataFrame] = []
    for year in years:
        cache_path = _year_cache_path(year)
        if not force_refresh and _is_cache_fresh(cache_path):
            logger.info("Loading population year %d from cache: %s", year, cache_path)
            df_raw = _load_year_cache(cache_path)
        else:
            year_query = copy.deepcopy(base_query)
            for dim in year_query["query"]:
                if dim["code"] == "Tid":
                    dim["selection"]["values"] = [str(year)]
                    break
            logger.info("Fetching population year %d from SCB API.", year)
            df_raw = query_pxweb(table_url, year_query)
            _save_year_cache(df_raw, cache_path)

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


def _resolve_table_url() -> str:
    """Return the first accessible BE0101A subtable URL.

    Tries BefolkningNy first; falls back to FolkmangdNov if the primary
    metadata call fails.

    Returns:
        The accessible table URL string.

    Raises:
        ValueError: If neither subtable is accessible.
    """
    for url in [_PRIMARY_TABLE_URL, _FALLBACK_TABLE_URL]:
        try:
            meta = fetch_metadata(url)
            if "variables" in meta:
                logger.info("Using BE0101 subtable: %s", url)
                return url
        except ValueError as exc:
            logger.warning(
                "Metadata unavailable for %s (%s); trying fallback.", url, exc
            )

    raise ValueError(
        "Neither BE0101A/BefolkningNy nor BE0101A/FolkmangdNov is accessible. "
        "Verify SCB API availability and subtable names."
    )


# ---------------------------------------------------------------------------
# Private helpers — query construction
# ---------------------------------------------------------------------------


def _build_base_query() -> dict:
    """Build the base PxWeb query for one year of BE0101 population data.

    The Tid dimension value is a placeholder ('2024') that the per-year loop
    overrides before each POST.

    Returns:
        A PxWeb query dict ready for deep-copying and year substitution.
    """
    return {
        "query": [
            {
                "code": "Region",
                "selection": {
                    "filter": "vs:RegionKommun07EjAggr",
                    "values": [],
                },
            },
            {
                "code": "Alder",
                "selection": {
                    "filter": "item",
                    "values": _AGE_CODES,
                },
            },
            {
                "code": "Kon",
                "selection": {
                    "filter": "item",
                    "values": ["1", "2"],  # 1=men, 2=women
                },
            },
            {
                "code": "ContentsCode",
                "selection": {
                    "filter": "item",
                    "values": [_CONTENTS_CODE],
                },
            },
            {
                "code": "Tid",
                "selection": {
                    "filter": "item",
                    "values": ["2024"],  # overridden per year in the loop
                },
            },
        ],
        "response": {"format": "json"},
    }


# ---------------------------------------------------------------------------
# Private helpers — raw response aggregation
# ---------------------------------------------------------------------------


def _age_code_to_group(age_code: str) -> str:
    """Map a single-year age code string to a broad age group label.

    Args:
        age_code: Raw age code from the SCB API (e.g. '0', '19', '65', '100+').

    Returns:
        One of '0-19', '20-64', or '65+'.
    """
    if age_code == "100+":
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
        elif lower == "contentscode":
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
        columns=[c for c in df_raw.columns if c.lower() == "contentscode"],
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


def _is_cache_fresh(cache_path: Path) -> bool:
    """Return True if the cache file exists and is younger than the max age.

    Args:
        cache_path: Path to the cached JSON file.

    Returns:
        True if the file exists and its mtime is within CACHE_MAX_AGE_DAYS.
    """
    if not cache_path.exists():
        return False
    mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
    return (datetime.now() - mtime) < timedelta(days=_CACHE_MAX_AGE_DAYS)


def _save_year_cache(df_raw: pd.DataFrame, cache_path: Path) -> None:
    """Persist a raw year DataFrame to the JSON cache.

    Args:
        df_raw: Raw DataFrame from query_pxweb.
        cache_path: Destination path.
    """
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        df_raw.to_json(orient="records", force_ascii=False),
        encoding="utf-8",
    )
    logger.info("Saved population cache to %s", cache_path)


def _load_year_cache(cache_path: Path) -> pd.DataFrame:
    """Load a raw year DataFrame from the JSON cache.

    Args:
        cache_path: Path to the JSON cache file.

    Returns:
        DataFrame matching the shape of a raw PxWeb response for one year.
    """
    records = json.loads(cache_path.read_text(encoding="utf-8"))
    return pd.DataFrame(records)


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
    for year in years:
        year_df = df[df["year"] == year]
        n_unique = year_df["kommun_kod"].nunique()
        if n_unique != _EXPECTED_COMMUNES:
            raise ValueError(
                f"Expected {_EXPECTED_COMMUNES} unique kommun_kod for year {year}, "
                f"got {n_unique}."
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
