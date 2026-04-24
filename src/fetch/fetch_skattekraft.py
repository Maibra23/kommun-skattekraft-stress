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

import logging
from pathlib import Path

import pandas as pd

from src.fetch.pxweb_client import (
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

_TABLE_URL = (
    "https://api.scb.se/OV0104/v1/doris/sv/ssd/START/OE/OE0101/SkatteKraft"
)

_PROJECT_ROOT = Path(__file__).parents[2]
_CACHE_FILE: Path = _PROJECT_ROOT / "data" / "raw" / "skattekraft.json"

_CACHE_MAX_AGE_DAYS: int = 7
_EXPECTED_COMMUNES: int = 290
_DEFAULT_YEARS: list[int] = list(range(2010, 2025))

# Known ContentsCode for "skattekraft per invånare"; verified at runtime via
# metadata call.  Updated from legacy '000001LB' to 'OE0101A0' (current SCB API).
_KNOWN_CONTENTS_CODE: str = "OE0101A0"

# Swedish keyword fragments used to identify skattekraft per invånare by text
# when the known code is not found (robust to future SCB code changes).
_SKATTEKRAFT_PER_CAPITA_KEYWORDS: tuple[str, ...] = (
    "skattekraft, kronor per",
    "skattekraft per invånare",
    "skattekraft per inv",
)

_CACHE_DTYPES: dict[str, str] = {
    "kommun_kod": "str_zfill4",
    "year": "int",
    "tax_base_per_capita": "float",
}


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

    The metadata call to confirm the ContentsCode is only made when data
    actually needs to be fetched from the API, not when loading from cache.

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

    # --- Steps 1–5: Fetch or load from cache ---
    if not force_refresh and is_cache_fresh(_CACHE_FILE, _CACHE_MAX_AGE_DAYS):
        logger.info("Loading skattekraft from cache: %s", _CACHE_FILE)
        df = load_df_cache(_CACHE_FILE, _CACHE_DTYPES)
    else:
        # Step 1: Confirm ContentsCode via metadata (only when fetching)
        logger.info("Fetching OE0101 metadata from %s", _TABLE_URL)
        metadata = fetch_metadata(_TABLE_URL)
        contents_code = _discover_contents_code(metadata)
        logger.info("Using ContentsCode: %s", contents_code)
        region_codes = _discover_region_codes(metadata)
        logger.info("Using %d explicit region codes.", len(region_codes))

        logger.info(
            "Fetching skattekraft from SCB API for years %d–%d",
            min(years),
            max(years),
        )
        # Step 2: Build query per KRI §2
        query_body = _build_query(contents_code, years, region_codes)

        # Step 3: Call generic client
        df_raw = query_pxweb(_TABLE_URL, query_body)

        # Step 4: Rename and cast columns
        df = _clean_response(df_raw)

        # Step 5: Persist cache
        save_df_cache(df, _CACHE_FILE)

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

    Preference order:
      1. The known code _KNOWN_CONTENTS_CODE (exact match).
      2. A code whose valueText matches _SKATTEKRAFT_PER_CAPITA_KEYWORDS.
      3. Raises ValueError — never silently falls back to the first code,
         because OE0101 also contains skatteunderlag (total SEK) and the
         riksmedelvärde ratio, both of which would produce wrong values.

    Args:
        metadata: Table metadata dict returned by fetch_metadata.

    Returns:
        The ContentsCode string for skattekraft per invånare.

    Raises:
        ValueError: If no ContentsCode variable is found, or none of the
            available codes can be confidently identified as the per-capita
            skattekraft metric.
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
            # 1. Exact known-code match.
            if _KNOWN_CONTENTS_CODE in codes:
                logger.info("Using known ContentsCode '%s'.", _KNOWN_CONTENTS_CODE)
                return _KNOWN_CONTENTS_CODE
            # 2. Keyword match against valueTexts.
            for code, text in zip(codes, texts):
                if any(kw in text.lower() for kw in _SKATTEKRAFT_PER_CAPITA_KEYWORDS):
                    logger.info(
                        "Known code not found; matched ContentsCode '%s' (%s) by keyword.",
                        code,
                        text,
                    )
                    return code
            # 3. No safe fallback — raise rather than silently use the wrong metric.
            raise ValueError(
                f"Could not identify the skattekraft per invånare ContentsCode in "
                f"OE0101 metadata.  Available codes: {list(zip(codes, texts))}. "
                "Update _KNOWN_CONTENTS_CODE or _SKATTEKRAFT_PER_CAPITA_KEYWORDS."
            )

    raise ValueError(
        f"Could not find ContentsCode variable in OE0101 metadata at {_TABLE_URL}. "
        "Verify the table URL and check for SCB API changes."
    )


def _discover_region_codes(metadata: dict) -> list[str]:
    """Extract 4-digit municipality codes from OE0101 table metadata.

    The SCB PxWeb API no longer accepts the vs:RegionKommun07EjAggr value-set
    filter (returns HTTP 400).  This helper extracts the explicit municipality
    codes from the Region dimension metadata so that _build_query can use
    filter=item instead.

    Municipality codes are identified by being exactly 4 characters long and
    all-numeric (e.g. '0114', '0180').  County codes ('01', '25') and the
    national total ('00') are 2 characters and are excluded.

    Args:
        metadata: Table metadata dict returned by fetch_metadata.

    Returns:
        Sorted list of 4-digit municipality code strings.

    Raises:
        ValueError: If the Region dimension is absent from metadata or no
            4-digit codes are found.
    """
    all_codes = get_dimension_codes(metadata, "Region")
    if not all_codes:
        raise ValueError(
            f"Region dimension not found in OE0101 metadata at {_TABLE_URL}. "
            "Verify the table URL and check for SCB API changes."
        )
    muni_codes = sorted(c for c in all_codes if len(c) == 4 and c.isdigit())
    if not muni_codes:
        raise ValueError(
            f"No 4-digit municipality codes found in OE0101 Region dimension. "
            f"Available codes (first 10): {all_codes[:10]}."
        )
    logger.info(
        "Discovered %d municipality codes from Region metadata (e.g. %s … %s).",
        len(muni_codes),
        muni_codes[0],
        muni_codes[-1],
    )
    return muni_codes


def _build_query(contents_code: str, years: list[int], region_codes: list[str]) -> dict:
    """Build the PxWeb POST query body for OE0101/SkatteKraft.

    Uses explicit municipality codes (filter=item) instead of a value-set
    filter (vs:RegionKommun07EjAggr) because the SCB API no longer accepts
    the value-set syntax and returns HTTP 400.  The codes are discovered at
    runtime from the table metadata by _discover_region_codes.

    Args:
        contents_code: The ContentsCode value for skattekraft per invånare.
        years: List of integer years to request.
        region_codes: List of 4-digit municipality code strings from metadata.

    Returns:
        A PxWeb query dict ready for POST.
    """
    return {
        "query": [
            {
                "code": "Region",
                "selection": {
                    "filter": "item",
                    "values": region_codes,
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


def _verify(df: pd.DataFrame, years: list[int]) -> None:
    """Run sanity checks on the fetched skattekraft DataFrame.

    Checks:
        1. Exactly 290 unique kommun_kod values per year.
        2. For 2024: raises ValueError if Danderyd (0162) is not the highest.
        3. National mean for 2024 is within 200 000–350 000 SEK range.

    Both the Danderyd check and the national mean check raise ValueError
    for consistent severity — any failure indicates a data integrity problem.

    Args:
        df: Cleaned DataFrame with [kommun_kod, year, tax_base_per_capita].
        years: The requested years (used to check 290-per-year constraint).

    Raises:
        ValueError: If any check fails.
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
        raise ValueError(
            f"Expected Danderyd (0162) to have the highest 2024 skattekraft "
            f"but found {max_row['kommun_kod']}. "
            "Verify ContentsCode and data freshness."
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
