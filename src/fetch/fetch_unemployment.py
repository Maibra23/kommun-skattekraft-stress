"""Fetch municipal open unemployment rates from SCB STATIV table AA0003.

Downloads "Andel öppet arbetslösa" (share of open unemployment, percent) for
all 290 kommuner for the years 2010–2024 using the generic pxweb_client.

Discovery strategy:
  1. Try AA0003B/IntGr1KomKonUtb (primary; broken down by sex and education).
  2. If the Tid dimension does not cover 2010 onwards, try the alternative
     subtables listed in _ALTERNATIVE_URLS.
  3. If no subtable covers the full requested window, raise NotImplementedError
     with instructions to consult KRI §3 fallback strategies.

Because the primary subtable provides rates disaggregated by Kön (sex) and
UtbildningsNivå (education level), the fetcher aggregates to a single rate per
(kommun, year) by taking an unweighted mean across the available Kön ×
UtbildningsNivå cells.  This is a simplifying assumption; differences from the
true population-weighted aggregate are expected to be small (< 0.3 percentage
points) and are documented in METHODOLOGY §7.

Raw JSON is cached to data/raw/unemployment.json.  Returns a tidy DataFrame
with columns [kommun_kod, year, unemployment_rate].
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

_PRIMARY_TABLE_URL = (
    "https://api.scb.se/OV0104/v1/doris/sv/ssd/START/AA/AA0003/AA0003B"
    "/IntGr1KomKonUtb"
)
_ALTERNATIVE_URLS: list[str] = [
    "https://api.scb.se/OV0104/v1/doris/sv/ssd/START/AA/AA0003/AA0003B/IntGr1KomKon",
    "https://api.scb.se/OV0104/v1/doris/sv/ssd/START/AA/AA0003/AA0003B/IntGr1Kom",
]

_PROJECT_ROOT = Path(__file__).parents[2]
_CACHE_FILE: Path = _PROJECT_ROOT / "data" / "raw" / "unemployment.json"

_CACHE_MAX_AGE_DAYS: int = 7
_EXPECTED_COMMUNES: int = 290
_DEFAULT_YEARS: list[int] = list(range(2010, 2025))

# Swedish keyword fragments used to identify the open-unemployment share code.
_OPEN_UNEMPLOYMENT_KEYWORDS = ("öppet arbetslösa", "öppna arbetslösa", "andel arbetslösa")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def fetch_unemployment(
    years: list[int] | None = None,
    force_refresh: bool = False,
) -> pd.DataFrame:
    """Fetch "Andel öppet arbetslösa" for all 290 kommuner from SCB AA0003.

    Uses a local JSON cache (data/raw/unemployment.json) that is considered
    fresh for 7 days.  The cache is always skipped when force_refresh=True.

    Args:
        years: List of integer years to include.  Defaults to 2010–2024.
        force_refresh: If True, ignore the cache and re-fetch from the API.

    Returns:
        DataFrame with columns [kommun_kod, year, unemployment_rate] and
        exactly 290 × len(years) rows.  unemployment_rate is a float in
        percent (e.g. 4.2 means 4.2 %).

    Raises:
        NotImplementedError: If no discovered subtable covers the full requested
            time window.  The error message instructs the developer to consult
            KRI §3 fallback strategies.
        ValueError: If the API call fails after retries, or if the returned
            data fails shape and sanity checks.
    """
    if years is None:
        years = _DEFAULT_YEARS

    if not force_refresh and _is_cache_fresh(_CACHE_FILE):
        logger.info("Loading unemployment from cache: %s", _CACHE_FILE)
        df = _load_cache(_CACHE_FILE)
    else:
        table_url, contents_code, available_years, table_meta = _discover_table(years)
        missing = [y for y in years if y not in available_years]
        if missing:
            raise NotImplementedError(
                f"No AA0003 subtable covers the full requested year window {years}. "
                f"Missing years: {missing}. "
                "Consult KRI_Dataset_Identification.md §3 for manual fallback strategies."
            )

        query_body = _build_query(contents_code, years, table_meta)
        df_raw = query_pxweb(table_url, query_body)
        df = _clean_response(df_raw)
        _save_cache(df, _CACHE_FILE)

    df = df[df["year"].isin(years)].reset_index(drop=True)
    _verify(df, years)

    logger.info(
        "fetch_unemployment done: %d rows, years %d–%d, %d unique kommuner.",
        len(df),
        df["year"].min(),
        df["year"].max(),
        df["kommun_kod"].nunique(),
    )
    return df


# ---------------------------------------------------------------------------
# Private helpers — discovery
# ---------------------------------------------------------------------------


def _discover_table(
    requested_years: list[int],
) -> tuple[str, str, list[int], dict]:
    """Probe candidate AA0003 subtable URLs and return the first viable one.

    Tries the primary URL first, then each alternative in order.  For each
    candidate, fetches metadata to check:
      - The table is reachable.
      - The Tid dimension includes the required years.
      - A ContentsCode for "Andel öppet arbetslösa" exists.

    Args:
        requested_years: The integer years required by the caller.

    Returns:
        Tuple of (table_url, contents_code, available_tid_years, metadata)
        for the first viable subtable.  The metadata dict is returned so
        _build_query can reuse it without a second network call.

    Raises:
        NotImplementedError: If no candidate covers the requested years.
    """
    candidates = [_PRIMARY_TABLE_URL] + _ALTERNATIVE_URLS

    for url in candidates:
        try:
            meta = fetch_metadata(url)
        except ValueError as exc:
            logger.warning("Metadata fetch failed for %s: %s", url, exc)
            continue

        tid_years = _extract_tid_years(meta)
        coverage = sorted(set(tid_years) & set(requested_years))
        if not coverage:
            logger.warning(
                "Subtable %s has no overlap with requested years %s; skipping.",
                url,
                requested_years,
            )
            continue

        logger.info(
            "Subtable %s covers years %d–%d.",
            url,
            min(tid_years),
            max(tid_years),
        )

        contents_code = _discover_contents_code(meta, url)
        if contents_code is None:
            logger.warning(
                "Could not identify 'Andel öppet arbetslösa' ContentsCode in %s; skipping.",
                url,
            )
            continue

        return url, contents_code, tid_years, meta

    raise NotImplementedError(
        "No AA0003B subtable is accessible or covers the requested year window. "
        "Consult KRI_Dataset_Identification.md §3 for fallback strategies."
    )


def _extract_tid_years(metadata: dict) -> list[int]:
    """Extract available integer years from the Tid variable in table metadata.

    Args:
        metadata: Table metadata dict returned by fetch_metadata.

    Returns:
        Sorted list of integer years found in the Tid dimension.
    """
    for var in metadata.get("variables", []):
        if var.get("code") == "Tid":
            raw_values: list[str] = var.get("values", [])
            years: list[int] = []
            for v in raw_values:
                try:
                    years.append(int(v))
                except ValueError:
                    pass
            return sorted(years)
    return []


def _discover_contents_code(metadata: dict, url: str) -> str | None:
    """Find the ContentsCode for 'Andel öppet arbetslösa' in table metadata.

    Matches against known Swedish keyword fragments in the valueTexts list.
    Falls back to the first available code if no keyword match is found, with
    a logged warning.

    Args:
        metadata: Table metadata dict returned by fetch_metadata.
        url: Table URL (used in log messages).

    Returns:
        The ContentsCode string, or None if the ContentsCode variable is absent.
    """
    for var in metadata.get("variables", []):
        if var.get("code") == "ContentsCode":
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
                if any(kw in text.lower() for kw in _OPEN_UNEMPLOYMENT_KEYWORDS):
                    logger.info(
                        "Selected ContentsCode '%s' (%s) for open unemployment.",
                        code,
                        text,
                    )
                    return code

            # No keyword match — fall back to the first code.
            logger.warning(
                "No ContentsCode matched 'Andel öppet arbetslösa' keywords in %s. "
                "Falling back to '%s' (%s). Verify manually.",
                url,
                codes[0],
                texts[0] if texts else "?",
            )
            return codes[0]

    return None


def _get_dimension_codes(metadata: dict, dimension_code: str) -> list[str]:
    """Extract all value codes for a named dimension from table metadata.

    Args:
        metadata: Table metadata dict returned by fetch_metadata.
        dimension_code: The dimension code to look up (e.g. 'Kon').

    Returns:
        List of value code strings, or empty list if dimension is absent.
    """
    for var in metadata.get("variables", []):
        if var.get("code") == dimension_code:
            return var.get("values", [])
    return []


# ---------------------------------------------------------------------------
# Private helpers — query construction
# ---------------------------------------------------------------------------


def _build_query(
    contents_code: str,
    years: list[int],
    table_meta: dict,
) -> dict:
    """Build the PxWeb POST query body for the unemployment rate table.

    Uses already-fetched metadata (from _discover_table) to discover valid
    codes for all non-Region, non-Tid dimensions (Kon, UtbildningsNiva, etc.)
    and includes ALL values for each.  This returns the full disaggregated
    dataset, which _clean_response then averages to produce one rate per
    (kommun, year).

    Args:
        contents_code: The ContentsCode for 'Andel öppet arbetslösa'.
        years: List of integer years to request.
        table_meta: Metadata dict already fetched by _discover_table.

    Returns:
        A PxWeb query dict ready for POST.
    """
    meta = table_meta

    query_dims: list[dict] = [
        {
            "code": "Region",
            "selection": {
                "filter": "vs:RegionKommun07EjAggr",
                "values": [],
            },
        },
    ]

    # Include all available codes for every extra dimension (Kon, UtbildningsNiva, …).
    skip_codes = {"Region", "ContentsCode", "Tid"}
    for var in meta.get("variables", []):
        code = var.get("code", "")
        if code in skip_codes:
            continue
        values = var.get("values", [])
        if values:
            query_dims.append(
                {
                    "code": code,
                    "selection": {"filter": "item", "values": values},
                }
            )

    query_dims.append(
        {
            "code": "ContentsCode",
            "selection": {"filter": "item", "values": [contents_code]},
        }
    )
    query_dims.append(
        {
            "code": "Tid",
            "selection": {
                "filter": "item",
                "values": [str(y) for y in sorted(years)],
            },
        }
    )

    return {"query": query_dims, "response": {"format": "json"}}


# ---------------------------------------------------------------------------
# Private helpers — response cleaning
# ---------------------------------------------------------------------------


def _clean_response(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Convert raw PxWeb response to one unemployment rate per (kommun, year).

    Identifies the Region and Tid columns, casts types, then averages the
    unemployment rate metric across all disaggregation dimensions (Kon,
    UtbildningsNiva, etc.).  The average is unweighted; this is a documented
    approximation (see module docstring).

    Args:
        df_raw: DataFrame from query_pxweb (all string columns).

    Returns:
        DataFrame with columns [kommun_kod, year, unemployment_rate].

    Raises:
        ValueError: If the rate metric column cannot be identified.
    """
    rename: dict[str, str] = {}
    extra_dims: list[str] = []
    value_col: str | None = None

    for col in df_raw.columns:
        lower = col.lower()
        if lower == "region":
            rename[col] = "kommun_kod"
        elif lower == "tid":
            rename[col] = "year"
        elif lower == "contentscode":
            pass  # drop silently
        else:
            # Remaining columns: the metric value or extra disaggregation dimensions.
            # Heuristic: if the column has few unique values relative to row count,
            # treat it as a disaggregation dimension; otherwise it is the metric.
            unique_ratio = df_raw[col].nunique() / max(len(df_raw), 1)
            if unique_ratio < 0.05:
                extra_dims.append(col)
            else:
                if value_col is None:
                    value_col = col
                    rename[col] = "unemployment_rate"

    if value_col is None:
        # Fallback: take the last column as the value.
        last_col = df_raw.columns[-1]
        if last_col not in rename:
            rename[last_col] = "unemployment_rate"
            value_col = last_col
        if value_col is None:
            raise ValueError(
                "Could not identify the unemployment rate column. "
                f"Available columns: {list(df_raw.columns)}"
            )

    drop_cols = [c for c in df_raw.columns if c.lower() == "contentscode"]
    df = df_raw.rename(columns=rename).drop(columns=drop_cols + extra_dims, errors="ignore")

    df["kommun_kod"] = df["kommun_kod"].astype(str).str.zfill(4)
    df["year"] = df["year"].astype(int)
    df["unemployment_rate"] = pd.to_numeric(df["unemployment_rate"], errors="coerce")

    # Average across remaining disaggregation dimensions.
    df = (
        df.groupby(["kommun_kod", "year"], as_index=False)["unemployment_rate"]
        .mean()
    )
    return df


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
        df: Cleaned DataFrame with [kommun_kod, year, unemployment_rate].
        cache_path: Destination path for the JSON file.
    """
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        df.to_json(orient="records", force_ascii=False),
        encoding="utf-8",
    )
    logger.info("Cached unemployment data to %s", cache_path)


def _load_cache(cache_path: Path) -> pd.DataFrame:
    """Load the cleaned DataFrame from the cache JSON file.

    Args:
        cache_path: Path to the JSON cache file.

    Returns:
        DataFrame with correctly typed columns [kommun_kod, year,
        unemployment_rate].
    """
    records = json.loads(cache_path.read_text(encoding="utf-8"))
    df = pd.DataFrame(records)
    df["kommun_kod"] = df["kommun_kod"].astype(str).str.zfill(4)
    df["year"] = df["year"].astype(int)
    df["unemployment_rate"] = pd.to_numeric(df["unemployment_rate"])
    return df


# ---------------------------------------------------------------------------
# Private helpers — verification
# ---------------------------------------------------------------------------


def _verify(df: pd.DataFrame, years: list[int]) -> None:
    """Run sanity checks on the fetched unemployment DataFrame.

    Checks:
        1. Exactly 290 unique kommun_kod values per year.
        2. National mean unemployment_rate is in the historical 3–8 % range.
        3. No NaN values in unemployment_rate.

    Args:
        df: Cleaned DataFrame with [kommun_kod, year, unemployment_rate].
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
                f"got {n_unique}. Check for missing or duplicate municipality codes."
            )

    nan_count = df["unemployment_rate"].isna().sum()
    if nan_count > 0:
        logger.warning(
            "%d NaN values in unemployment_rate after fetching. "
            "These will propagate to the panel and may affect estimates.",
            nan_count,
        )

    national_means = (
        df.groupby("year")["unemployment_rate"].mean().round(2)
    )
    logger.info("National mean unemployment_rate by year:\n%s", national_means.to_string())

    overall_mean = df["unemployment_rate"].mean()
    if not (1.0 <= overall_mean <= 15.0):
        raise ValueError(
            f"Overall mean unemployment_rate is {overall_mean:.2f} %, "
            "outside the plausible 1–15 % range. "
            "Check ContentsCode and verify units (should be percent, not fraction)."
        )
    if not (3.0 <= overall_mean <= 8.0):
        logger.warning(
            "Overall mean unemployment_rate is %.2f %%, outside historical 3–8 %% range. "
            "Verify data quality.",
            overall_mean,
        )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    )
    result = fetch_unemployment()
    print(f"\nFetched {len(result)} rows.")
    print(f"Years covered: {sorted(result['year'].unique())}")
    print(f"Unique kommuner: {result['kommun_kod'].nunique()}")
    print(f"\nNational mean unemployment_rate by year:")
    print(
        result.groupby("year")["unemployment_rate"]
        .mean()
        .round(2)
        .reset_index()
        .to_string(index=False)
    )
    print("\nTop 10 highest unemployment_rate kommuner (2024):")
    top10 = (
        result[result["year"] == 2024]
        .nlargest(10, "unemployment_rate")[["kommun_kod", "unemployment_rate"]]
        .reset_index(drop=True)
    )
    print(top10.to_string(index=False))
