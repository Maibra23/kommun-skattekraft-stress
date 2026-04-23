"""Fetch municipal tax base (skattekraft) per capita from SCB table OE0101.

Downloads beskattningsbar förvärvsinkomst per invånare for all 290 kommuner
for the years 2010–2024 using the generic pxweb_client and caches the raw
response to data/raw/skattekraft.json.  Returns a tidy DataFrame with columns
[kommun_kod, year, tax_base_per_capita].

Cache policy: data/raw/skattekraft.json is reused if younger than 7 days.
Pass force_refresh=True to bypass the cache and re-fetch from the API.

Note on reference year: skattekraft for year t is based on income from year
t-2 (e.g. 2024 skattekraft reflects 2022 income). Document this in tooltips.
"""

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

_TABLE_URL = (
    "https://api.scb.se/OV0104/v1/doris/sv/ssd/START/OE/OE0101/SkatteKraft"
)

_PROJECT_ROOT = Path(__file__).parents[2]
_CACHE_FILE: Path = _PROJECT_ROOT / "data" / "raw" / "skattekraft.json"

_CACHE_MAX_AGE_DAYS: int = 7
_EXPECTED_COMMUNES: int = 290
_DEFAULT_YEARS: list[int] = list(range(2010, 2025))

# Known ContentsCode for "skattekraft per invånare"; verified at runtime via
# metadata call and falls back to auto-discovery if this code changes.
_KNOWN_CONTENTS_CODE: str = "000001LB"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def fetch_skattekraft(
    years: list[int] | None = None,
    force_refresh: bool = False,
) -> pd.DataFrame:
    """Fetch skattekraft per invånare for all 290 kommuner from SCB OE0101.

    Uses a local JSON cache (data/raw/skattekraft.json) that is considered
    fresh for 7 days.  The cache is always skipped when force_refresh=True.

    Args:
        years: List of integer years to include.  Defaults to 2010–2024.
        force_refresh: If True, ignore the cache and re-fetch from the API.

    Returns:
        DataFrame with columns [kommun_kod, year, tax_base_per_capita] and
        exactly 290 × len(years) rows.  kommun_kod is a zero-padded 4-digit
        string; year is int; tax_base_per_capita is float (SEK).

    Raises:
        ValueError: If the API call fails after retries, or if the returned
            data fails the expected-shape and sanity checks.
    """
    if years is None:
        years = _DEFAULT_YEARS

    # --- Step 1: Confirm ContentsCode via metadata ---
    logger.info("Fetching OE0101 metadata from %s", _TABLE_URL)
    metadata = fetch_metadata(_TABLE_URL)
    contents_code = _discover_contents_code(metadata)
    logger.info("Using ContentsCode: %s", contents_code)

    # --- Steps 2–5: Fetch or load from cache ---
    if not force_refresh and _is_cache_fresh(_CACHE_FILE):
        logger.info("Loading skattekraft from cache: %s", _CACHE_FILE)
        df = _load_cache(_CACHE_FILE)
    else:
        logger.info(
            "Fetching skattekraft from SCB API for years %d–%d",
            min(years),
            max(years),
        )
        # Step 2: Build query per KRI §2
        query_body = _build_query(contents_code, years)

        # Step 3: Call generic client
        df_raw = query_pxweb(_TABLE_URL, query_body)

        # Step 4: Rename and cast columns
        df = _clean_response(df_raw)

        # Step 5: Persist cache
        _save_cache(df, _CACHE_FILE)

    # Filter to exactly the requested years (cache may cover a wider range).
    df = df[df["year"].isin(years)].reset_index(drop=True)

    # --- Step 6: Verify and return ---
    _verify(df, years)

    logger.info(
        "fetch_skattekraft done: %d rows, years %d–%d, %d unique kommuner.",
        len(df),
        df["year"].min(),
        df["year"].max(),
        df["kommun_kod"].nunique(),
    )
    return df


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _discover_contents_code(metadata: dict) -> str:
    """Find the ContentsCode for skattekraft per invånare in table metadata.

    Prefers the known code _KNOWN_CONTENTS_CODE; falls back to the first
    available code with a warning if the known one is absent.

    Args:
        metadata: Table metadata dict returned by fetch_metadata.

    Returns:
        The ContentsCode string (e.g. '000001LB').

    Raises:
        ValueError: If no ContentsCode variable is found in the metadata.
    """
    for variable in metadata.get("variables", []):
        if variable.get("code") == "ContentsCode":
            codes: list[str] = variable.get("values", [])
            texts: list[str] = variable.get("valueTexts", [])
            if not codes:
                break
            logger.info(
                "Available OE0101 ContentsCodes: %s",
                list(zip(codes, texts)),
            )
            if _KNOWN_CONTENTS_CODE in codes:
                return _KNOWN_CONTENTS_CODE
            logger.warning(
                "Known ContentsCode '%s' not in metadata; using '%s' instead.",
                _KNOWN_CONTENTS_CODE,
                codes[0],
            )
            return codes[0]

    raise ValueError(
        f"Could not find ContentsCode variable in OE0101 metadata at {_TABLE_URL}. "
        "Verify the table URL and check for SCB API changes."
    )


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


def _build_query(contents_code: str, years: list[int]) -> dict:
    """Build the PxWeb POST query body for OE0101/SkatteKraft.

    Args:
        contents_code: The ContentsCode value for skattekraft per invånare.
        years: List of integer years to request.

    Returns:
        A PxWeb query dict ready for POST.
    """
    return {
        "query": [
            {
                "code": "Region",
                "selection": {
                    # vs:RegionKommun07EjAggr selects all 290 kommuner
                    # without any aggregation groups.
                    "filter": "vs:RegionKommun07EjAggr",
                    "values": [],  # empty = all members of the value set
                },
            },
            {
                "code": "ContentsCode",
                "selection": {
                    "filter": "item",
                    "values": [contents_code],
                },
            },
            {
                "code": "Tid",
                "selection": {
                    "filter": "item",
                    "values": [str(y) for y in sorted(years)],
                },
            },
        ],
        "response": {"format": "json"},
    }


def _clean_response(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Rename and cast columns from a raw PxWeb response DataFrame.

    Detects the Region, Tid, and value columns by name (case-insensitive)
    and drops the ContentsCode column if present.

    Args:
        df_raw: DataFrame returned by query_pxweb (all string columns).

    Returns:
        DataFrame with columns [kommun_kod, year, tax_base_per_capita].
    """
    rename: dict[str, str] = {}
    drop_cols: list[str] = []

    for col in df_raw.columns:
        col_lower = col.lower()
        if col_lower == "region":
            rename[col] = "kommun_kod"
        elif col_lower == "tid":
            rename[col] = "year"
        elif col_lower == "contentscode":
            drop_cols.append(col)
        else:
            # The remaining column is the content metric (skattekraft value).
            rename[col] = "tax_base_per_capita"

    df = df_raw.rename(columns=rename).drop(columns=drop_cols, errors="ignore")

    df["kommun_kod"] = df["kommun_kod"].str.zfill(4)
    df["year"] = df["year"].astype(int)
    df["tax_base_per_capita"] = pd.to_numeric(
        df["tax_base_per_capita"], errors="coerce"
    )

    return df[["kommun_kod", "year", "tax_base_per_capita"]]


def _save_cache(df: pd.DataFrame, cache_path: Path) -> None:
    """Persist the cleaned DataFrame to the cache JSON file.

    Args:
        df: Cleaned DataFrame with [kommun_kod, year, tax_base_per_capita].
        cache_path: Destination path for the JSON file.
    """
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        df.to_json(orient="records", force_ascii=False),
        encoding="utf-8",
    )
    logger.info("Cached skattekraft data to %s", cache_path)


def _load_cache(cache_path: Path) -> pd.DataFrame:
    """Load the cleaned DataFrame from the cache JSON file.

    Args:
        cache_path: Path to the JSON cache file.

    Returns:
        DataFrame with correctly typed columns [kommun_kod, year,
        tax_base_per_capita].
    """
    records = json.loads(cache_path.read_text(encoding="utf-8"))
    df = pd.DataFrame(records)
    df["kommun_kod"] = df["kommun_kod"].astype(str).str.zfill(4)
    df["year"] = df["year"].astype(int)
    df["tax_base_per_capita"] = pd.to_numeric(df["tax_base_per_capita"])
    return df


def _verify(df: pd.DataFrame, years: list[int]) -> None:
    """Run sanity checks on the fetched skattekraft DataFrame.

    Checks:
        1. Exactly 290 unique kommun_kod values per year.
        2. For 2024: logs the highest value and its kommune code (expected:
           Danderyd 0162, ~496 000 SEK); warns if another kommune is highest.
        3. National mean for 2024 is within 200 000–350 000 SEK range.

    Args:
        df: Cleaned DataFrame with [kommun_kod, year, tax_base_per_capita].
        years: The requested years (used to check 290-per-year constraint).

    Raises:
        ValueError: If any hard check fails.
    """
    for year in years:
        year_df = df[df["year"] == year]
        n_unique = year_df["kommun_kod"].nunique()
        if n_unique != _EXPECTED_COMMUNES:
            raise ValueError(
                f"Expected {_EXPECTED_COMMUNES} unique kommun_kod values for "
                f"year {year}, got {n_unique}. Check for missing or duplicate "
                "municipality codes in the API response."
            )

    if 2024 not in years:
        logger.info("Year 2024 not in requested range; skipping 2024 checks.")
        return

    df_2024 = df[df["year"] == 2024]
    max_idx = df_2024["tax_base_per_capita"].idxmax()
    max_row = df_2024.loc[max_idx]
    national_mean = df_2024["tax_base_per_capita"].mean()

    logger.info(
        "2024 highest skattekraft: kommun_kod=%s  value=%.0f SEK",
        max_row["kommun_kod"],
        max_row["tax_base_per_capita"],
    )
    logger.info("2024 national mean skattekraft: %.0f SEK", national_mean)

    if max_row["kommun_kod"] != "0162":
        logger.warning(
            "Expected Danderyd (0162) to have the highest 2024 skattekraft "
            "but found %s. Verify ContentsCode and data freshness.",
            max_row["kommun_kod"],
        )

    if not (200_000 <= national_mean <= 350_000):
        raise ValueError(
            f"2024 national mean skattekraft is {national_mean:.0f} SEK, "
            "outside the expected range 200 000–350 000 SEK. "
            "Possible wrong ContentsCode or unexpected data scale."
        )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    )
    result = fetch_skattekraft()
    print(f"\nFetched {len(result)} rows.")
    print(f"Years covered: {sorted(result['year'].unique())}")
    print(f"Unique kommuner: {result['kommun_kod'].nunique()}")
    print("\nTop 5 by 2024 skattekraft per invånare:")
    top5 = (
        result[result["year"] == 2024]
        .nlargest(5, "tax_base_per_capita")[["kommun_kod", "tax_base_per_capita"]]
        .reset_index(drop=True)
    )
    print(top5.to_string(index=False))
    print("\nBottom 5 by 2024 skattekraft per invånare:")
    bot5 = (
        result[result["year"] == 2024]
        .nsmallest(5, "tax_base_per_capita")[["kommun_kod", "tax_base_per_capita"]]
        .reset_index(drop=True)
    )
    print(bot5.to_string(index=False))
