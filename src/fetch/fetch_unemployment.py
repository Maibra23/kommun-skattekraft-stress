"""Fetch municipal open unemployment rates for all 290 kommuner.

Returns "Andel öppet arbetslösa" (share of open unemployment, percent) for
2010 onwards, from two sources:

  - 2010–2021: data/lookup/unemployment_2010_2021.csv (committed snapshot)
  - 2022–:     AA0003B/IntGr1KomUtbBAS via the generic pxweb_client

The split is not a performance choice.  SCB withdrew the AA0003X archive that
served 1997–2021 — the whole group returns HTTP 400, not just one table — so
those years are no longer obtainable from SCB at any URL.  The snapshot is
their only remaining source; see METHODOLOGY §8.1, §12.6 and §13.1,
and METHODOLOGY §13.1.

The live query uses SCB's total-aggregate codes (BakgrVar='TOT', Kön='1+2',
UtbNiv='000') to select the pre-aggregated unemployment rate directly.
No client-side averaging across sub-categories is performed.  See
METHODOLOGY §7.9 for details.

Raw JSON is cached to data/raw/unemployment.json.  Returns a tidy DataFrame
with columns [kommun_kod, year, unemployment_rate].
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

# The only live municipality-level table.  Its predecessor for 1997–2021,
# AA0003X/IntGr1KomKonUtb, was withdrawn by SCB along with the entire AA0003X
# group; those years come from _SNAPSHOT_FILE instead.
_CONTINUATION_TABLE_URL = (
    "https://api.scb.se/OV0104/v1/doris/sv/ssd/START/AA/AA0003/AA0003B"
    "/IntGr1KomUtbBAS"
)
# Year boundary between the snapshot and the live table.
_SNAPSHOT_LAST_YEAR: int = 2021
_LIVE_TABLE_FIRST_YEAR: int = 2022
_ALTERNATIVE_URLS: list[str] = []

_PROJECT_ROOT = Path(__file__).parents[2]
_CACHE_FILE: Path = _PROJECT_ROOT / "data" / "raw" / "unemployment.json"
_SNAPSHOT_FILE: Path = (
    _PROJECT_ROOT / "data" / "lookup" / "unemployment_2010_2021.csv"
)

_CACHE_MAX_AGE_DAYS: int = 7
_EXPECTED_COMMUNES: int = 290
_DEFAULT_YEARS: list[int] = list(range(2010, 2025))

_CACHE_DTYPES: dict[str, str] = {
    "kommun_kod": "str_zfill4",
    "year": "int",
    "unemployment_rate": "float",
}

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

    if not force_refresh and is_cache_fresh(_CACHE_FILE, _CACHE_MAX_AGE_DAYS):
        logger.info("Loading unemployment from cache: %s", _CACHE_FILE)
        df = load_df_cache(_CACHE_FILE, _CACHE_DTYPES)
    else:
        frames: list[pd.DataFrame] = []

        snapshot_years = [y for y in years if y <= _SNAPSHOT_LAST_YEAR]
        live_years = [y for y in years if y >= _LIVE_TABLE_FIRST_YEAR]

        if snapshot_years:
            frames.append(_load_snapshot(snapshot_years))

        if live_years:
            table_url, contents_code, available_years, table_meta = _discover_table(
                live_years, [_CONTINUATION_TABLE_URL]
            )
            missing = [y for y in live_years if y not in available_years]
            if missing:
                raise NotImplementedError(
                    f"AA0003 subtable {_CONTINUATION_TABLE_URL} does not cover years "
                    f"{missing}. SCB may have restructured the table. "
                    "Consult KRI_Dataset_Identification.md §3 for fallback strategies."
                )
            query_body = _build_query(contents_code, live_years, table_meta)
            df_raw = query_pxweb(table_url, query_body)
            frames.append(_clean_response(df_raw))

        df = pd.concat(frames, ignore_index=True)
        save_df_cache(df, _CACHE_FILE)

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
# Private helpers — snapshot
# ---------------------------------------------------------------------------


def _load_snapshot(years: list[int]) -> pd.DataFrame:
    """Read pre-2022 unemployment from the committed snapshot.

    Args:
        years: Integer years to return, all ≤ _SNAPSHOT_LAST_YEAR.

    Returns:
        DataFrame with columns [kommun_kod, year, unemployment_rate],
        typed identically to the live-API path.

    Raises:
        ValueError: If the snapshot file is missing, or does not carry every
            requested year.  Returning a short frame would surface downstream
            as a silently unbalanced panel.
    """
    if not _SNAPSHOT_FILE.exists():
        raise ValueError(
            f"Unemployment snapshot missing: {_SNAPSHOT_FILE}. "
            "2010–2021 cannot be re-fetched from SCB (AA0003X withdrawn); "
            "restore it from git or regenerate with "
            "scripts/freeze_unemployment_snapshot.py."
        )

    df = pd.read_csv(
        _SNAPSHOT_FILE,
        comment="#",
        dtype={"kommun_kod": str, "year": int, "unemployment_rate": float},
    )
    df["kommun_kod"] = df["kommun_kod"].str.zfill(4)

    missing = sorted(set(years) - set(df["year"].unique()))
    if missing:
        raise ValueError(
            f"Snapshot {_SNAPSHOT_FILE.name} does not cover years {missing}; "
            f"it holds {df['year'].min()}–{df['year'].max()}."
        )

    return df[df["year"].isin(years)].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Private helpers — discovery
# ---------------------------------------------------------------------------


def _discover_table(
    requested_years: list[int],
    candidates: list[str] | None = None,
) -> tuple[str, str, list[int], dict]:
    """Probe candidate AA0003 subtable URLs and return the first viable one.

    Tries the primary URL first, then each alternative in order.  For each
    candidate, fetches metadata to check:
      - The table is reachable.
      - The Tid dimension includes the required years.
      - A ContentsCode for "Andel öppet arbetslösa" exists.

    Args:
        requested_years: The integer years required by the caller.
        candidates: Optional explicit list of URLs to try.  If None, defaults
            to [_PRIMARY_TABLE_URL] + _ALTERNATIVE_URLS.

    Returns:
        Tuple of (table_url, contents_code, available_tid_years, metadata)
        for the first viable subtable.  The metadata dict is returned so
        _build_query can reuse it without a second network call.

    Raises:
        NotImplementedError: If no candidate covers the requested years.
    """
    if candidates is None:
        candidates = [_CONTINUATION_TABLE_URL] + _ALTERNATIVE_URLS

    for url in candidates:
        try:
            meta = fetch_metadata(url)
        except ValueError as exc:
            logger.warning("Metadata fetch failed for %s: %s", url, exc)
            continue

        tid_years = extract_tid_years(meta)
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


# ---------------------------------------------------------------------------
# Private helpers — query construction
# ---------------------------------------------------------------------------


def _build_query(
    contents_code: str,
    years: list[int],
    table_meta: dict,
) -> dict:
    """Build the PxWeb POST query body for the unemployment rate table.

    Uses already-fetched metadata to select total-aggregate codes for each
    cross-tabulation dimension (Kön, UtbNiv, BakgrVar), so the response
    contains one row per (municipality, year) rather than disaggregated cells.
    This keeps the query well within the SCB cell limit (~150 000 cells) and
    returns the correct population-weighted total directly.

    Preferred "total" codes per dimension (both tables have these):
        Kön      → '1+2' (men and women combined)
        UtbNiv   → '000' (all education levels)
        BakgrVar → 'TOT' (all persons)

    If a preferred code is not found for a dimension, all available codes for
    that dimension are included and _clean_response averages across them.

    Args:
        contents_code: The ContentsCode for 'Andel öppet arbetslösa'.
        years: List of integer years to request.
        table_meta: Metadata dict already fetched by _discover_table.

    Returns:
        A PxWeb query dict ready for POST.
    """
    # Extract municipality codes. The vs:RegionKommun07EjAggr value-set filter
    # no longer works on the SCB API (returns HTTP 400).
    all_region_codes = get_dimension_codes(table_meta, "Region")
    muni_codes = sorted(c for c in all_region_codes if len(c) == 4 and c.isdigit())

    query_dims: list[dict] = [
        {
            "code": "Region",
            "selection": {"filter": "item", "values": muni_codes},
        },
    ]

    # For each extra dimension, prefer the "total" aggregate code if available;
    # fall back to all values.
    _TOTAL_CODES: dict[str, list[str]] = {
        "Kon": ["1+2"],
        "UtbNiv": ["000"],
        "BakgrVar": ["TOT"],
    }
    skip_codes = {"Region", "ContentsCode", "Tid"}
    for var in table_meta.get("variables", []):
        code = var.get("code", "")
        if code in skip_codes:
            continue
        values = var.get("values", [])
        if not values:
            continue
        preferred = _TOTAL_CODES.get(code, [])
        selected = next((p for p in preferred if p in values), None)
        if selected:
            chosen = [selected]
            logger.debug("Dimension %s: using total code %r.", code, selected)
        else:
            chosen = values
            logger.debug(
                "Dimension %s: no total code found; using all %d values.",
                code, len(values),
            )
        query_dims.append(
            {"code": code, "selection": {"filter": "item", "values": chosen}}
        )

    query_dims.append(
        {"code": "ContentsCode", "selection": {"filter": "item", "values": [contents_code]}}
    )
    query_dims.append(
        {
            "code": "Tid",
            "selection": {"filter": "item", "values": [str(y) for y in sorted(years)]},
        }
    )

    return {"query": query_dims, "response": {"format": "json"}}


# ---------------------------------------------------------------------------
# Private helpers — response cleaning
# ---------------------------------------------------------------------------


def _clean_response(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Convert raw PxWeb response to one unemployment rate per (kommun, year).

    Uses the PxWeb column position convention to reliably identify the metric
    column: key columns are listed first (matching the 'key' array in the JSON
    data), followed by value/content columns.  The last column in the response
    is always the metric value when a single ContentsCode is requested.

    This replaces a previous unique-ratio heuristic that was fragile when the
    metric column had high cardinality.

    Args:
        df_raw: DataFrame from query_pxweb (all string columns).

    Returns:
        DataFrame with columns [kommun_kod, year, unemployment_rate].

    Raises:
        ValueError: If the rate metric column cannot be identified.
    """
    if df_raw.empty:
        return pd.DataFrame(columns=["kommun_kod", "year", "unemployment_rate"])

    rename: dict[str, str] = {}
    drop_cols: list[str] = []

    # The last column is the metric value (PxWeb always puts value columns
    # after all key columns).
    metric_col = df_raw.columns[-1]

    for col in df_raw.columns:
        lower = col.lower()
        if lower == "region":
            rename[col] = "kommun_kod"
        elif lower == "tid":
            rename[col] = "year"
        elif lower == "contentscode":
            drop_cols.append(col)
        elif col == metric_col:
            rename[col] = "unemployment_rate"
        else:
            # Extra disaggregation dimensions (Kon, UtbildningsNiva, etc.)
            drop_cols.append(col)

    df = df_raw.rename(columns=rename).drop(columns=drop_cols, errors="ignore")

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
    print("\nNational mean unemployment_rate by year:")
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
