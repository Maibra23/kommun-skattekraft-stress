"""Fetch municipal education attainment shares from SCB table UF0506.

Downloads the share of population aged 25–64 with post-secondary education of
3 or more years (SUN 2000 levels 6 = eftergymnasial 3+ år, 7 = forskarutbildning)
for all 290 kommuner for the years 2010–2024 using the generic pxweb_client.

Strategy:
  1. Confirm the subtable URL via metadata (tries UF0506B/Utbildning4 first,
     then a broader UF0506 search).
  2. Query population counts for ALL education levels (1–7) for ages 25–64,
     both sexes combined.  This lets us compute the share robustly without
     relying on a separate denominator query.
  3. Compute edu_share = 100 × (count_level_6 + count_level_7) / total_count.
  4. Cache raw JSON to data/raw/education.json.
  5. Return a tidy DataFrame with columns [kommun_kod, year, edu_share].

SUN 2000 education level codes used in UF0506:
  1 = förgymnasial utbildning kortare än 9 år
  2 = förgymnasial utbildning 9 år
  3 = gymnasial utbildning kortare än 3 år
  4 = gymnasial utbildning 3 år
  5 = eftergymnasial utbildning kortare än 3 år
  6 = eftergymnasial utbildning 3 år eller längre   ← numerator
  7 = forskarutbildning                              ← numerator

Expected national mean edu_share ≈ 30 % (METHODOLOGY §6).
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

_CANDIDATE_URLS: list[str] = [
    "https://api.scb.se/OV0104/v1/doris/sv/ssd/START/UF/UF0506/UF0506B/Utbildning4",
    "https://api.scb.se/OV0104/v1/doris/sv/ssd/START/UF/UF0506/UF0506A/Utbildning3",
    "https://api.scb.se/OV0104/v1/doris/sv/ssd/START/UF/UF0506/UF0506C/Utbildning4C",
]

_PROJECT_ROOT = Path(__file__).parents[2]
_CACHE_FILE: Path = _PROJECT_ROOT / "data" / "raw" / "education.json"

_CACHE_MAX_AGE_DAYS: int = 7
_EXPECTED_COMMUNES: int = 290
_DEFAULT_YEARS: list[int] = list(range(2010, 2025))

# SUN 2000 codes for the numerator (eftergymnasial 3+ år + forskarutbildning)
_HIGH_EDU_LEVELS: frozenset[str] = frozenset({"6", "7"})

# Age bracket code(s) for 25–64; SCB may encode as "25-64" or as separate years.
_AGE_25_64_CODES: list[str] = ["25-64"]

# Sex code for total (both sexes combined); SCB convention is "1+2".
_SEX_TOTAL_CODES: list[str] = ["1+2"]

# Keywords to identify the population count ContentsCode.
_COUNT_KEYWORDS: tuple[str, ...] = ("antal", "befolkning", "folkmängd", "count", "persons")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def fetch_education(
    years: list[int] | None = None,
    force_refresh: bool = False,
) -> pd.DataFrame:
    """Fetch education attainment share for all 290 kommuner from SCB UF0506.

    Queries population counts by education level for ages 25–64 and computes
    the share of the population with post-secondary education of 3+ years
    (SUN 2000 levels 6 and 7).

    Uses a local JSON cache (data/raw/education.json) that is considered fresh
    for 7 days.  The cache is always skipped when force_refresh=True.

    Args:
        years: List of integer years to include.  Defaults to 2010–2024.
        force_refresh: If True, ignore the cache and re-fetch from the API.

    Returns:
        DataFrame with columns [kommun_kod, year, edu_share] and exactly
        290 × len(years) rows.  edu_share is a float in percent (e.g. 32.4
        means 32.4 %).

    Raises:
        ValueError: If no accessible subtable is found, the API call fails,
            or the returned data fails shape and sanity checks.
    """
    if years is None:
        years = _DEFAULT_YEARS

    if not force_refresh and _is_cache_fresh(_CACHE_FILE):
        logger.info("Loading education from cache: %s", _CACHE_FILE)
        df = _load_cache(_CACHE_FILE)
    else:
        table_url, contents_code, edu_level_codes, age_codes, sex_codes = (
            _discover_table()
        )
        query_body = _build_query(
            contents_code, edu_level_codes, age_codes, sex_codes, years
        )
        df_raw = query_pxweb(table_url, query_body)
        df = _compute_edu_share(df_raw)
        _save_cache(df, _CACHE_FILE)

    df = df[df["year"].isin(years)].reset_index(drop=True)
    _verify(df, years)

    logger.info(
        "fetch_education done: %d rows, years %d–%d, %d unique kommuner.",
        len(df),
        df["year"].min(),
        df["year"].max(),
        df["kommun_kod"].nunique(),
    )
    return df


# ---------------------------------------------------------------------------
# Private helpers — discovery
# ---------------------------------------------------------------------------


def _discover_table() -> tuple[str, str, list[str], list[str], list[str]]:
    """Probe candidate UF0506 subtable URLs and return query parameters.

    For each candidate URL, fetches metadata and checks:
      - The table is reachable.
      - A ContentsCode for population counts is present.
      - The UtbildningsNiva dimension includes codes 6 and 7.
      - An age dimension covering 25–64 exists.

    Returns:
        Tuple of (table_url, contents_code, edu_level_codes, age_codes,
        sex_codes) where:
          - edu_level_codes: all available UtbildningsNiva codes (full list,
            to allow computing the denominator).
          - age_codes: list of age codes covering 25–64.
          - sex_codes: list of sex/total codes.

    Raises:
        ValueError: If no candidate subtable is accessible or usable.
    """
    for url in _CANDIDATE_URLS:
        try:
            meta = fetch_metadata(url)
        except ValueError as exc:
            logger.warning("Metadata fetch failed for %s: %s", url, exc)
            continue

        logger.info("Probing education subtable: %s", url)

        edu_codes = _get_dimension_codes(meta, "UtbildningsNiva")
        if not edu_codes:
            edu_codes = _get_dimension_codes(meta, "UtbildningNiva")
        if not edu_codes:
            logger.warning("No UtbildningsNiva dimension in %s; skipping.", url)
            continue
        if not _HIGH_EDU_LEVELS.issubset(set(edu_codes)):
            logger.warning(
                "UtbildningsNiva codes in %s do not include levels 6 and 7 (%s); skipping.",
                url,
                edu_codes,
            )
            continue

        age_codes = _resolve_age_codes(meta)
        if not age_codes:
            logger.warning("No 25-64 age codes found in %s; skipping.", url)
            continue

        sex_codes = _resolve_sex_codes(meta)

        contents_code = _discover_contents_code(meta, url)
        if contents_code is None:
            logger.warning(
                "No suitable ContentsCode found in %s; skipping.", url
            )
            continue

        logger.info(
            "Selected education subtable: %s  ContentsCode=%s  edu_levels=%s",
            url,
            contents_code,
            edu_codes,
        )
        return url, contents_code, edu_codes, age_codes, sex_codes

    raise ValueError(
        "No accessible UF0506 subtable found.  Tried: "
        + ", ".join(_CANDIDATE_URLS)
        + ".  Verify subtable names via SCB API browser."
    )


def _get_dimension_codes(metadata: dict, dimension_code: str) -> list[str]:
    """Extract all value codes for a named dimension from table metadata.

    Args:
        metadata: Table metadata dict returned by fetch_metadata.
        dimension_code: The dimension code to look up.

    Returns:
        List of value code strings, or empty list if dimension is absent.
    """
    for var in metadata.get("variables", []):
        if var.get("code") == dimension_code:
            return var.get("values", [])
    return []


def _resolve_age_codes(metadata: dict) -> list[str]:
    """Find age codes covering the 25–64 bracket in table metadata.

    First looks for the aggregate code '25-64'.  If absent, returns all
    available single-year age codes in the 25–64 range so the caller can
    query them individually.

    Args:
        metadata: Table metadata dict returned by fetch_metadata.

    Returns:
        List of age code strings to include in the query.
    """
    for var in metadata.get("variables", []):
        code = var.get("code", "")
        if code.lower() not in ("alder", "ålder", "age"):
            continue
        values: list[str] = var.get("values", [])
        # Prefer the aggregate bracket code.
        for preferred in _AGE_25_64_CODES:
            if preferred in values:
                return [preferred]
        # Fall back to individual single-year ages in the 25–64 range.
        single_year = [
            v for v in values
            if v.isdigit() and 25 <= int(v) <= 64
        ]
        if single_year:
            return single_year
    return []


def _resolve_sex_codes(metadata: dict) -> list[str]:
    """Find the sex / total code from table metadata.

    Prefers the combined-total code ('1+2').  Falls back to querying all
    available sex codes if the total is not present.

    Args:
        metadata: Table metadata dict returned by fetch_metadata.

    Returns:
        List of sex code strings to include in the query.
    """
    for var in metadata.get("variables", []):
        code = var.get("code", "")
        if code.lower() not in ("kon", "kön", "sex"):
            continue
        values: list[str] = var.get("values", [])
        for preferred in _SEX_TOTAL_CODES:
            if preferred in values:
                return [preferred]
        return values
    return []


def _discover_contents_code(metadata: dict, url: str) -> str | None:
    """Find the population count ContentsCode in table metadata.

    Matches against known keywords in the valueTexts list.  Falls back to
    the first available code if no keyword match is found.

    Args:
        metadata: Table metadata dict returned by fetch_metadata.
        url: Table URL (used in log messages).

    Returns:
        The ContentsCode string, or None if the variable is absent.
    """
    for var in metadata.get("variables", []):
        if var.get("code") != "ContentsCode":
            continue
        codes: list[str] = var.get("values", [])
        texts: list[str] = var.get("valueTexts", [])
        if not codes:
            return None

        logger.info(
            "Available ContentsCode(s) for %s: %s",
            url,
            list(zip(codes, texts)),
        )

        for code, text in zip(codes, texts):
            if any(kw in text.lower() for kw in _COUNT_KEYWORDS):
                logger.info("Selected ContentsCode '%s' (%s).", code, text)
                return code

        logger.warning(
            "No keyword match for ContentsCode in %s; using first: '%s' (%s).",
            url,
            codes[0],
            texts[0] if texts else "?",
        )
        return codes[0]

    return None


# ---------------------------------------------------------------------------
# Private helpers — query construction
# ---------------------------------------------------------------------------


def _build_query(
    contents_code: str,
    edu_level_codes: list[str],
    age_codes: list[str],
    sex_codes: list[str],
    years: list[int],
) -> dict:
    """Build the PxWeb POST query body for UF0506 education counts.

    Queries ALL education levels so that the response contains both the
    numerator (levels 6+7) and the denominator (all levels summed).

    Args:
        contents_code: The ContentsCode for population counts.
        edu_level_codes: All available UtbildningsNiva codes (used as-is).
        age_codes: Age codes covering the 25–64 bracket.
        sex_codes: Sex / total codes to include.
        years: List of integer years to request.

    Returns:
        A PxWeb query dict ready for POST.
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
                "code": "UtbildningsNiva",
                "selection": {
                    "filter": "item",
                    "values": edu_level_codes,
                },
            },
            {
                "code": "Alder",
                "selection": {
                    "filter": "item",
                    "values": age_codes,
                },
            },
            {
                "code": "Kon",
                "selection": {
                    "filter": "item",
                    "values": sex_codes if sex_codes else ["1+2"],
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


# ---------------------------------------------------------------------------
# Private helpers — share computation
# ---------------------------------------------------------------------------


def _compute_edu_share(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Compute edu_share from raw PxWeb response with all education levels.

    Identifies the UtbildningsNiva, Region, and Tid columns, then computes:
        edu_share = 100 × (sum of count for levels 6+7) / (sum of all counts)
    per (kommun_kod, year).

    Args:
        df_raw: Raw DataFrame from query_pxweb (all string columns).

    Returns:
        DataFrame with columns [kommun_kod, year, edu_share].

    Raises:
        ValueError: If required columns cannot be identified.
    """
    rename: dict[str, str] = {}
    edu_col: str | None = None
    value_col: str | None = None
    drop_cols: list[str] = []

    for col in df_raw.columns:
        lower = col.lower()
        if lower == "region":
            rename[col] = "kommun_kod"
        elif lower == "tid":
            rename[col] = "year"
        elif lower in ("utbildningsniva", "utbildningniva"):
            rename[col] = "edu_level"
            edu_col = col
        elif lower in ("alder", "ålder"):
            drop_cols.append(col)
        elif lower in ("kon", "kön"):
            drop_cols.append(col)
        elif lower == "contentscode":
            drop_cols.append(col)
        else:
            if value_col is None:
                rename[col] = "count"
                value_col = col

    if value_col is None:
        raise ValueError(
            "Could not identify the population count column in UF0506 response. "
            f"Available columns: {list(df_raw.columns)}"
        )
    if edu_col is None:
        raise ValueError(
            "Could not identify the UtbildningsNiva dimension column. "
            f"Available columns: {list(df_raw.columns)}"
        )

    df = df_raw.rename(columns=rename).drop(columns=drop_cols, errors="ignore")

    df["kommun_kod"] = df["kommun_kod"].astype(str).str.zfill(4)
    df["year"] = df["year"].astype(int)
    df["count"] = pd.to_numeric(df["count"], errors="coerce").fillna(0)

    # Compute numerator and denominator per (kommun, year).
    df["is_high_edu"] = df["edu_level"].isin(_HIGH_EDU_LEVELS)

    agg = df.groupby(["kommun_kod", "year"]).agg(
        total=("count", "sum"),
        high_edu=("count", lambda s: s[df.loc[s.index, "is_high_edu"]].sum()),
    ).reset_index()

    agg["edu_share"] = (agg["high_edu"] / agg["total"].replace(0, float("nan"))) * 100

    return agg[["kommun_kod", "year", "edu_share"]]


# ---------------------------------------------------------------------------
# Private helpers — cache management
# ---------------------------------------------------------------------------


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


def _save_cache(df: pd.DataFrame, cache_path: Path) -> None:
    """Persist the cleaned DataFrame to the cache JSON file.

    Args:
        df: Cleaned DataFrame with [kommun_kod, year, edu_share].
        cache_path: Destination path for the JSON file.
    """
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        df.to_json(orient="records", force_ascii=False),
        encoding="utf-8",
    )
    logger.info("Cached education data to %s", cache_path)


def _load_cache(cache_path: Path) -> pd.DataFrame:
    """Load the cleaned DataFrame from the cache JSON file.

    Args:
        cache_path: Path to the JSON cache file.

    Returns:
        DataFrame with correctly typed columns [kommun_kod, year, edu_share].
    """
    records = json.loads(cache_path.read_text(encoding="utf-8"))
    df = pd.DataFrame(records)
    df["kommun_kod"] = df["kommun_kod"].astype(str).str.zfill(4)
    df["year"] = df["year"].astype(int)
    df["edu_share"] = pd.to_numeric(df["edu_share"])
    return df


# ---------------------------------------------------------------------------
# Private helpers — verification
# ---------------------------------------------------------------------------


def _verify(df: pd.DataFrame, years: list[int]) -> None:
    """Run sanity checks on the fetched education DataFrame.

    Checks:
        1. Exactly 290 unique kommun_kod values per year.
        2. National mean edu_share is approximately 30 % (within 10–60 %).
        3. edu_share values are all in the valid range 0–100.

    Args:
        df: Cleaned DataFrame with [kommun_kod, year, edu_share].
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

    out_of_range = df[(df["edu_share"] < 0) | (df["edu_share"] > 100)]
    if not out_of_range.empty:
        raise ValueError(
            f"edu_share values outside [0, 100] detected for "
            f"{len(out_of_range)} rows. Verify ContentsCode and query."
        )

    national_mean = df["edu_share"].mean()
    logger.info(
        "National mean edu_share: %.1f %% (expected ~30 %%)", national_mean
    )
    if not (10.0 <= national_mean <= 60.0):
        raise ValueError(
            f"National mean edu_share is {national_mean:.1f} %, "
            "outside the plausible 10–60 % range. "
            "Verify that the ContentsCode returns counts (not shares) and "
            "that levels 6 and 7 are correctly identified."
        )
    if not (20.0 <= national_mean <= 45.0):
        logger.warning(
            "National mean edu_share is %.1f %%, outside expected ~30 %% range. "
            "Verify data quality.",
            national_mean,
        )

    if 2024 in years:
        df_2024 = df[df["year"] == 2024]
        top5 = df_2024.nlargest(5, "edu_share")[["kommun_kod", "edu_share"]]
        bot5 = df_2024.nsmallest(5, "edu_share")[["kommun_kod", "edu_share"]]
        logger.info("Top 5 edu_share 2024:\n%s", top5.to_string(index=False))
        logger.info("Bottom 5 edu_share 2024:\n%s", bot5.to_string(index=False))
        if "1281" not in top5["kommun_kod"].values:
            logger.warning(
                "Expected Lund (1281) in top 5 edu_share for 2024; found %s.",
                top5["kommun_kod"].tolist(),
            )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    )
    result = fetch_education()
    print(f"\nFetched {len(result)} rows.")
    print(f"Years covered: {sorted(result['year'].unique())}")
    print(f"Unique kommuner: {result['kommun_kod'].nunique()}")
    print(f"\nNational mean edu_share by year:")
    print(
        result.groupby("year")["edu_share"]
        .mean()
        .round(1)
        .reset_index()
        .to_string(index=False)
    )
    print("\nTop 10 edu_share kommuner (2024):")
    top10 = (
        result[result["year"] == 2024]
        .nlargest(10, "edu_share")[["kommun_kod", "edu_share"]]
        .reset_index(drop=True)
    )
    print(top10.to_string(index=False))
    print(f"\nExpected row count (290 × 15 yrs): {290 * 15}")
    print(f"Actual row count: {len(result)}")
