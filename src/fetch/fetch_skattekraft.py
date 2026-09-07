"""Fetch municipal tax base (skattekraft) from SCB table OE0101.

Downloads two metrics for all 290 kommuner in a single query and caches the
result to data/raw/skattekraft.json.  Returns a tidy DataFrame with columns
[kommun_kod, year, tax_base_per_capita, tax_base_index_riket]:

  * ``tax_base_per_capita`` (OE0101A0) — beskattningsbar förvärvsinkomst per
    invånare, SEK, current prices.
  * ``tax_base_index_riket`` (OE0101B0) — andel av riksmedelvärdet, percent.
    SCB's own published index with riket = 100; the figure Regionfakta and
    other secondary sources republish.

The index is **population-weighted** (riksmedelvärde ~271 000 kr for 2026),
whereas this project's own cross-municipality mean is unweighted (~231 000 kr
for 2024).  The two denominators must never be mixed in one chart; see
METHODOLOGY 7.13.  The index is fetched as a soft dependency: if SCB withdraws
it the column is left null rather than failing the pipeline.

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
# Coverage runs through the latest year SCB publishes.  Skattekraft for a
# budget year is released the preceding December, so 2026 has been available
# since December 2025.  See REMEDIATION_PLAN.md finding F2.
_DEFAULT_YEARS: list[int] = list(range(2010, 2027))

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

# ContentsCode for "andel av riksmedelvärdet, procent" — SCB's published
# index, riket = 100.  Soft dependency: absence degrades to a null column.
_KNOWN_INDEX_CONTENTS_CODE: str = "OE0101B0"

_INDEX_KEYWORDS: tuple[str, ...] = (
    "andel av riksmedelvärdet",
    "andel av riksmedel",
)

# Plausible bounds for the index, in percent of the national mean.  The
# observed 2026 range is roughly 73 (Högsby) to 191 (Danderyd); the wider
# bounds here catch a scale error (fraction instead of percent) without
# tripping on legitimate outliers.
_INDEX_MIN: float = 40.0
_INDEX_MAX: float = 400.0

# The published index is SCB's own rounding of 100 x kommun / riksmedelvärde to
# whole percent, so it can sit at most 0.5 from the unrounded value.  Measured
# 2026-09-07 against SCB's published riket: worst deviation 0.500 across all
# 290 kommuner in both 2024 and 2026, and 0.55 when riket is estimated from the
# kommuner themselves rather than fetched.  0.75 leaves room for the estimator
# without admitting a real disagreement.
_MAX_INDEX_ROUNDING_DEVIATION: float = 0.75

# Plausible bounds for the riksmedelvärde the index implies.  Observed 173 063
# SEK for 2010 and 270 859 for 2026, so these are wide enough to survive a
# decade of nominal growth while still catching a changed index base.
_IMPLIED_RIKET_MIN: float = 100_000.0
_IMPLIED_RIKET_MAX: float = 500_000.0

_CACHE_DTYPES: dict[str, str] = {
    "kommun_kod": "str_zfill4",
    "year": "int",
    "tax_base_per_capita": "float",
    "tax_base_index_riket": "float",
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
        years: List of integer years to include.  Defaults to 2010–2026.
        force_refresh: If True, ignore the cache and re-fetch from the API.

    Returns:
        DataFrame with columns [kommun_kod, year, tax_base_per_capita,
        tax_base_index_riket] and exactly 290 × len(years) rows.  kommun_kod
        is a zero-padded 4-digit string; year is int; both metrics are float.

    Raises:
        ValueError: If the API call fails after retries, or if the returned
            data fails the expected-shape and sanity checks.
    """
    if years is None:
        years = _DEFAULT_YEARS

    # --- Steps 1–5: Fetch or load from cache ---
    cached = None
    if not force_refresh and is_cache_fresh(_CACHE_FILE, _CACHE_MAX_AGE_DAYS):
        logger.info("Loading skattekraft from cache: %s", _CACHE_FILE)
        candidate = load_df_cache(_CACHE_FILE, _CACHE_DTYPES)
        stale_reason = _cache_shortfall(candidate, years)
        if stale_reason is None:
            cached = candidate
        else:
            logger.info("Ignoring cache: %s. Re-fetching from SCB.", stale_reason)

    if cached is not None:
        df = cached
    else:
        # Step 1: Confirm ContentsCode via metadata (only when fetching)
        logger.info("Fetching OE0101 metadata from %s", _TABLE_URL)
        metadata = fetch_metadata(_TABLE_URL)
        contents_code = _discover_contents_code(metadata)
        index_code = _discover_index_code(metadata) or _KNOWN_INDEX_CONTENTS_CODE
        logger.info(
            "Using ContentsCodes: %s (per capita), %s (index)",
            contents_code,
            index_code,
        )
        region_codes = _discover_region_codes(metadata)
        logger.info("Using %d explicit region codes.", len(region_codes))

        logger.info(
            "Fetching skattekraft from SCB API for years %d–%d",
            min(years),
            max(years),
        )
        # Step 2: Build query per KRI §2
        query_body = _build_query(
            [contents_code, index_code], years, region_codes
        )

        # Step 3: Call generic client
        df_raw = query_pxweb(_TABLE_URL, query_body)

        # Step 4: Rename and cast columns
        df = _clean_response(df_raw, contents_code, index_code)

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


def _cache_shortfall(df: pd.DataFrame, years: list[int]) -> str | None:
    """Return why a cached frame is unusable, or None if it is usable.

    A cache written before REMEDIATION_PLAN.md T0.1 predates the
    tax_base_index_riket column and stops at 2024.  Age alone cannot detect
    that, so the schema and the requested year coverage are checked too —
    otherwise a fresh-but-obsolete cache silently yields a null index column.

    Args:
        df: Frame loaded from the JSON cache.
        years: Years the caller requested.

    Returns:
        A human-readable reason string, or None when the cache is usable.
    """
    missing = [col for col in _CACHE_DTYPES if col not in df.columns]
    if missing:
        return f"cached frame is missing column(s) {missing}"

    cached_years = set(df["year"].unique())
    absent = sorted(set(years) - cached_years)
    if absent:
        return f"cached frame does not cover year(s) {absent}"

    return None


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


def _discover_index_code(metadata: dict) -> str | None:
    """Find the ContentsCode for andel av riksmedelvärdet, if published.

    Unlike the per-capita metric this is a soft dependency: a missing index
    degrades the panel by one column rather than breaking the pipeline, so
    this returns None instead of raising.

    Args:
        metadata: Table metadata dict returned by fetch_metadata.

    Returns:
        The ContentsCode string for the index, or None if not found.
    """
    for variable in metadata.get("variables", []):
        if variable.get("code") != "ContentsCode":
            continue
        codes: list[str] = variable.get("values", [])
        texts: list[str] = variable.get("valueTexts", [])

        if _KNOWN_INDEX_CONTENTS_CODE in codes:
            return _KNOWN_INDEX_CONTENTS_CODE

        for code, text in zip(codes, texts):
            if any(kw in text.lower() for kw in _INDEX_KEYWORDS):
                logger.info(
                    "Known index code absent; matched '%s' (%s) by keyword.",
                    code,
                    text,
                )
                return code

    logger.warning(
        "OE0101 does not publish an index metric matching %s or %s. "
        "tax_base_index_riket will be null.",
        _KNOWN_INDEX_CONTENTS_CODE,
        _INDEX_KEYWORDS,
    )
    return None


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


def _build_query(
    contents_codes: list[str], years: list[int], region_codes: list[str]
) -> dict:
    """Build the PxWeb POST query body for OE0101/SkatteKraft.

    Uses explicit municipality codes (filter=item) instead of a value-set
    filter (vs:RegionKommun07EjAggr) because the SCB API no longer accepts
    the value-set syntax and returns HTTP 400.  The codes are discovered at
    runtime from the table metadata by _discover_region_codes.

    Args:
        contents_codes: ContentsCode values to request, in column order.
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
                    "values": list(contents_codes),
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


def _clean_response(
    df_raw: pd.DataFrame, per_capita_code: str, index_code: str
) -> pd.DataFrame:
    """Rename and cast columns from a raw PxWeb response DataFrame.

    Value columns are located by their ContentsCode rather than by position.
    With two metrics requested, positional detection would silently swap
    skattekraft for the index if SCB reordered the response.

    Args:
        df_raw: DataFrame returned by query_pxweb (all string columns).
        per_capita_code: ContentsCode of skattekraft per invånare (required).
        index_code: ContentsCode of andel av riksmedelvärdet (optional — a
            null column is produced if absent from the response).

    Returns:
        DataFrame with columns [kommun_kod, year, tax_base_per_capita,
        tax_base_index_riket].

    Raises:
        ValueError: If the Region, Tid or per-capita column is missing.
    """
    lookup = {col.lower(): col for col in df_raw.columns}

    region_col = lookup.get("region")
    year_col = lookup.get("tid")
    if region_col is None or year_col is None:
        raise ValueError(
            f"Response missing Region or Tid column. Got: {list(df_raw.columns)}."
        )

    if per_capita_code not in df_raw.columns:
        raise ValueError(
            f"Response missing the skattekraft per invånare column "
            f"'{per_capita_code}'. Got: {list(df_raw.columns)}. "
            "Refusing to guess which column holds the metric."
        )

    df = pd.DataFrame(
        {
            "kommun_kod": df_raw[region_col].astype(str).str.zfill(4),
            "year": df_raw[year_col].astype(int),
            "tax_base_per_capita": pd.to_numeric(
                df_raw[per_capita_code], errors="coerce"
            ).astype("float64"),
        }
    )

    if index_code in df_raw.columns:
        df["tax_base_index_riket"] = pd.to_numeric(
            df_raw[index_code], errors="coerce"
        ).astype("float64")
    else:
        logger.warning(
            "Index metric '%s' absent from response; "
            "tax_base_index_riket will be null.",
            index_code,
        )
        df["tax_base_index_riket"] = float("nan")

    return df


def _verify(df: pd.DataFrame, years: list[int]) -> None:
    """Run sanity checks on the fetched skattekraft DataFrame.

    Checks:
        1. Exactly 290 unique kommun_kod values per year.
        2. For 2024: raises ValueError if Danderyd (0162) is not the highest.
        3. National mean for 2024 is within 200 000–350 000 SEK range.
        4. If present, the riksmedelvärde index lies within plausible percent
           bounds — this catches a fraction-vs-percent scale error.

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

    _verify_index(df_2024)
    _verify_index_matches_per_capita(df)


def _verify_index_matches_per_capita(df: pd.DataFrame) -> None:
    """Check SCB's published index against SCB's own per-capita values.

    The two metrics arrive as separate ContentsCodes from one table, and one
    is a deterministic function of the other: index = 100 × kommun / riket.
    The riksmedelvärde is not fetched — it is implied by the 290 kommuner
    already in hand, so this costs no extra query. Estimating it as the median
    of ``100 × per_capita / index`` reproduced SCB's published riket to within
    0.008 % on the 2010–2026 panel (251 418 against 251 437 for 2024).

    What it catches: an index expressed as a fraction rather than a percent, a
    ContentsCode read positionally so that values are paired with the wrong
    kommun, and any future redefinition of the index base. Per METHODOLOGY
    §11.6 this is a hard check.

    Skipped when the index column is absent or entirely null — it is a soft
    dependency (see the module docstring).

    Args:
        df: Cleaned frame with tax_base_per_capita and, optionally,
            tax_base_index_riket.

    Raises:
        ValueError: If any kommun-year deviates by more than SCB's own
            rounding of the index to whole percent.
    """
    if "tax_base_index_riket" not in df.columns:
        return
    usable = df.dropna(subset=["tax_base_per_capita", "tax_base_index_riket"])
    usable = usable[usable["tax_base_index_riket"] > 0]
    if usable.empty:
        return

    for year, chunk in usable.groupby("year"):
        implied_riket = (
            100.0 * chunk["tax_base_per_capita"] / chunk["tax_base_index_riket"]
        ).median()

        # The ratio test below is scale-invariant: dividing every index by 100
        # rescales the implied riket and the identity still holds.  Anchor it,
        # so a fraction-vs-percent index or a changed base is caught here too
        # rather than only by the range check on one year.
        if not (_IMPLIED_RIKET_MIN <= implied_riket <= _IMPLIED_RIKET_MAX):
            raise ValueError(
                f"Year {year}: the index implies a riksmedelvärde of "
                f"{implied_riket:,.0f} SEK, outside the plausible "
                f"{_IMPLIED_RIKET_MIN:,.0f}–{_IMPLIED_RIKET_MAX:,.0f} range. "
                "OE0101B0 is probably no longer a percent of the "
                "riksmedelvärde, or the two ContentsCodes have been swapped."
            )

        deviation = (
            chunk["tax_base_index_riket"]
            - 100.0 * chunk["tax_base_per_capita"] / implied_riket
        ).abs()
        worst = deviation.max()
        logger.info(
            "Index cross-check %s: implied riksmedelvärde %.0f, worst deviation "
            "%.3f (limit %.2f)",
            year,
            implied_riket,
            worst,
            _MAX_INDEX_ROUNDING_DEVIATION,
        )
        if worst > _MAX_INDEX_ROUNDING_DEVIATION:
            offender = chunk.loc[deviation.idxmax()]
            raise ValueError(
                f"Year {year}: the published index disagrees with the published "
                f"per-capita values by {worst:.3f} percentage points at kommun "
                f"{offender['kommun_kod']} (index {offender['tax_base_index_riket']}, "
                f"implied {100.0 * offender['tax_base_per_capita'] / implied_riket:.2f}), "
                f"above the {_MAX_INDEX_ROUNDING_DEVIATION} limit that SCB's own "
                "rounding explains. Verify that each ContentsCode is mapped by "
                "code rather than by position, and that OE0101B0 is still a "
                "percent of the riksmedelvärde."
            )


def _verify_index(df_2024: pd.DataFrame) -> None:
    """Check the riksmedelvärde index for scale and range errors.

    Skipped silently when the column is absent or entirely null, because the
    index is a soft dependency (see module docstring).

    Args:
        df_2024: Cleaned 2024 slice of the skattekraft frame.

    Raises:
        ValueError: If index values fall outside plausible percent bounds.
    """
    if "tax_base_index_riket" not in df_2024.columns:
        logger.info("No index column present; skipping index checks.")
        return

    index = df_2024["tax_base_index_riket"].dropna()
    if index.empty:
        logger.warning("Index column is entirely null for 2024; skipping checks.")
        return

    logger.info(
        "2024 riksmedelvärde index: range [%.0f, %.0f], median %.0f",
        index.min(),
        index.max(),
        index.median(),
    )

    if index.min() < _INDEX_MIN or index.max() > _INDEX_MAX:
        raise ValueError(
            f"2024 riksmedelvärde index spans [{index.min():.2f}, "
            f"{index.max():.2f}], outside plausible percent bounds "
            f"[{_INDEX_MIN}, {_INDEX_MAX}]. SCB publishes this as a percent "
            "of the national mean; a fraction indicates a scale error."
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
