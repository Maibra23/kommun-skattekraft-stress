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
_OPEN_ENDED_AGE_CODES: tuple[str, ...] = ("100+", "100+1", "100+5", "100+10")

# Age-group boundaries.  Every selected age code must lie wholly inside one of
# these, or the code that assigns it to a group raises rather than guessing.
_GROUP_BOUNDARIES: tuple[int, int] = (20, 65)

# 5-year bands, when the table offers a complete set.  BefolkningCKM's cells
# are disclosure-protected (METHODOLOGY §12.8), and summing 21 protected cells
# per kommun accumulates roughly a quarter of the error of summing 202.  SCB
# spells the first band '-4' rather than '0-4'.
_FIVE_YEAR_STARTS: tuple[int, ...] = tuple(range(0, 100, 5))

# Age codes carrying the publisher's own all-ages total.
_TOTAL_AGE_CODES: tuple[str, ...] = ("tot", "TotSA", "TOT1")
#: Sex and civil-status codes carrying the publisher's own totals.
_TOTAL_SEX_CODES: tuple[str, ...] = ("TotSa",)
_TOTAL_CIVIL_CODES: tuple[str, ...] = ("SC", "TOT")

# Tolerances for the published-total check (METHODOLOGY §6.2, §12.8).  Measured
# 2026-09-07 against SCB: the worst kommun deviates 0.447 % on 5-year bands and
# 1.005 % on single years, while the national deviation is 0.0012 %.  These
# bounds pass disclosure noise on either aggregation and fail every structural
# break seen so far — a quadrupling from an unsummed Civilstand (+300 %), a
# missing age band (about -6 %), or Folkökning read in place of Folkmängd.
_MAX_KOMMUN_TOTAL_DEVIATION_PCT: float = 1.5
_MAX_NATIONAL_TOTAL_DEVIATION_PCT: float = 0.05


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
        df_raw = None
        if not force_refresh and is_cache_fresh(cache_path, _CACHE_MAX_AGE_DAYS):
            candidate = load_df_cache(cache_path)
            if _cache_matches_query(candidate, _age_codes(routing[year][1])):
                logger.info(
                    "Loading population year %d from cache: %s", year, cache_path
                )
                df_raw = candidate
            else:
                logger.info(
                    "Ignoring the %d population cache: it was fetched with "
                    "different age codes than the current query requests.",
                    year,
                )

        if df_raw is None:
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
    _verify_against_published_totals(
        df, fetch_population_total(years=years, force_refresh=force_refresh)
    )

    logger.info(
        "fetch_population done: %d rows, years %d–%d, %d unique kommuner.",
        len(df),
        df["year"].min(),
        df["year"].max(),
        df["kommun_kod"].nunique(),
    )
    return df


def fetch_population_total(
    years: list[int] | None = None,
    force_refresh: bool = False,
) -> pd.DataFrame:
    """Fetch SCB's own published population total for all 290 kommuner.

    This is the authoritative total, not a number assembled here. It exists
    because `BefolkningCKM` protects its cells: no client-side sum reproduces
    the published figure, and the discrepancy reaches 1 % in the smallest
    kommuner — one full SD of `population_growth_pct`. See METHODOLOGY §12.8.

    Per-year raw JSON is cached at data/raw/population_total_{year}.json.

    Args:
        years: Integer years to include. Defaults to 2009–2025.
        force_refresh: If True, ignore caches and re-fetch from the API.

    Returns:
        DataFrame with columns [kommun_kod, year, population], one row per
        municipality-year.

    Raises:
        ValueError: If a year is carried by no table, or a table declares no
            all-ages total code.
    """
    if years is None:
        years = _DEFAULT_YEARS

    routing = _resolve_tables(years)

    frames: list[pd.DataFrame] = []
    for year in years:
        cache_path = _total_cache_path(year)
        if not force_refresh and is_cache_fresh(cache_path, _CACHE_MAX_AGE_DAYS):
            logger.info(
                "Loading published population total %d from cache: %s", year, cache_path
            )
            df_raw = load_df_cache(cache_path)
        else:
            table_url, table_meta = routing[year]
            region_codes = sorted(
                c for c in get_dimension_codes(table_meta, "Region")
                if len(c) == 4 and c.isdigit()
            )
            logger.info(
                "Fetching published population total %d from %s.", year, table_url
            )
            df_raw = query_pxweb(
                table_url, _build_total_query(table_meta, region_codes, year)
            )
            save_df_cache(df_raw, cache_path)

        frames.append(_total_from_raw(df_raw))

    df = pd.concat(frames, ignore_index=True)
    return df[df["year"].isin(years)].reset_index(drop=True)


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
    """Return the age codes to request: 5-year bands if offered, else single years.

    Whichever set is returned partitions 0–100+ exactly once — bands are never
    mixed with the single years they contain, and no band spanning 20 or 65 is
    ever selected.

    Bands are preferred because `BefolkningCKM` protects its cells: summing 21
    of them per kommun accumulates about a quarter of the error of summing 202
    (measured 0.447 % against 1.005 % in the worst kommun). `BefolkningNy`
    offers no bands and needs none — its parts sum to its published total
    exactly. See METHODOLOGY §12.8.

    Args:
        meta: Table metadata dict.

    Returns:
        List of age codes present in the table.

    Raises:
        ValueError: If neither a band set nor an open-ended single-year code
            can be identified.
    """
    available = set(_dimension_values(meta, "Alder"))

    bands = _five_year_band_codes(available)
    if bands is not None:
        return bands

    open_ended = next((c for c in _OPEN_ENDED_AGE_CODES if c in available), None)
    if open_ended is None:
        raise ValueError(
            "No open-ended age code (tried "
            f"{', '.join(_OPEN_ENDED_AGE_CODES)}) in the BE0101 Alder dimension."
        )
    return [a for a in _SINGLE_YEAR_AGES if a in available] + [open_ended]


def _five_year_band_codes(available: set[str]) -> list[str] | None:
    """Return the complete 5-year band set, or None if the table lacks one.

    All-or-nothing on purpose: a partial band set would leave a hole in the
    population, which is worse than the noise the bands exist to reduce.

    Args:
        available: The Alder codes this table declares.

    Returns:
        Bands covering 0–100+ in order, or None.
    """
    codes: list[str] = []
    for low in _FIVE_YEAR_STARTS:
        candidates = (f"{low}-{low + 4}", "-4" if low == 0 else f"{low}-{low + 4}")
        picked = next((c for c in candidates if c in available), None)
        if picked is None:
            return None
        codes.append(picked)

    open_ended = next(
        (c for c in ("100+5", "100+", "100+1") if c in available), None
    )
    if open_ended is None:
        return None
    return codes + [open_ended]


def _age_bounds(age_code: str) -> tuple[int, int]:
    """Return the inclusive (low, high) ages a code covers.

    Args:
        age_code: A single year ('30'), a band ('20-24', '-4') or an
            open-ended top code ('100+', '100+5').

    Returns:
        (low, high); high is 200 for open-ended codes.

    Raises:
        ValueError: If the code is not an age code at all.
    """
    if age_code.startswith("100+"):
        return 100, 200
    if age_code.startswith("-"):
        return 0, int(age_code[1:])
    if "-" in age_code:
        low, high = age_code.split("-", 1)
        return int(low), int(high)
    if age_code.isdigit():
        return int(age_code), int(age_code)
    raise ValueError(f"Not an age code: {age_code!r}")


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


def _build_total_query(meta: dict, region_codes: list[str], year: int) -> dict:
    """Build the query for the publisher's own all-ages population total.

    This is the number SCB publishes for the kommun, not a number we assemble.
    It exists because `BefolkningCKM` protects its cells, so no client-side sum
    reproduces it: the published total exceeds the sum of the categories
    beneath it in every dimension (METHODOLOGY §12.8).

    Each dimension is pinned to the table's own total code where one exists;
    where none does — `BefolkningNy` offers no sex total — every value is
    requested and summed, which is exact for that table.

    Args:
        meta: Metadata for the table carrying this year.
        region_codes: 4-digit municipality codes to request.
        year: The single year to request.

    Returns:
        A PxWeb query dict ready to POST.

    Raises:
        ValueError: If the table declares no all-ages total code.
    """
    ages = _dimension_values(meta, "Alder")
    total_age = next((c for c in _TOTAL_AGE_CODES if c in ages), None)
    if total_age is None:
        raise ValueError(
            "No all-ages total code (tried "
            f"{', '.join(_TOTAL_AGE_CODES)}) in the BE0101 Alder dimension; "
            f"available: {ages[:8]}…"
        )

    sexes = _dimension_values(meta, "Kon")
    total_sex = next((c for c in _TOTAL_SEX_CODES if c in sexes), None)

    dims: list[dict] = [
        {"code": "Region", "selection": {"filter": "item", "values": region_codes}},
        {"code": "Alder", "selection": {"filter": "item", "values": [total_age]}},
        {
            "code": "Kon",
            "selection": {
                "filter": "item",
                "values": [total_sex] if total_sex else list(sexes),
            },
        },
    ]

    if not _eliminates(meta, "Civilstand"):
        civil = _dimension_values(meta, "Civilstand")
        total_civil = next((c for c in _TOTAL_CIVIL_CODES if c in civil), None)
        if total_civil is None:
            raise ValueError(
                "Civilstand does not eliminate and offers no total code; "
                f"available: {_dimension_pairs(meta, 'Civilstand')}"
            )
        dims.append(
            {"code": "Civilstand", "selection": {"filter": "item", "values": [total_civil]}}
        )

    dims.append(
        {
            "code": "ContentsCode",
            "selection": {"filter": "item", "values": [_contents_code(meta)]},
        }
    )
    dims.append({"code": "Tid", "selection": {"filter": "item", "values": [str(year)]}})

    return {"query": dims, "response": {"format": "json"}}


def _total_from_raw(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Reduce a published-total response to [kommun_kod, year, population].

    Sums whatever rows the response carries per kommun-year, which is one row
    when the table offers a sex total and two when it does not.

    Args:
        df_raw: Raw DataFrame from query_pxweb (all string columns).

    Returns:
        DataFrame with columns [kommun_kod, year, population].

    Raises:
        ValueError: If the value column cannot be identified.
    """
    dimension_columns = {"region", "alder", "kon", "tid", "contentscode", "civilstand"}
    value_col = next(
        (c for c in df_raw.columns if c.lower() not in dimension_columns), None
    )
    if value_col is None:
        raise ValueError(
            "Could not identify the population value column in the BE0101 total "
            f"response. Available columns: {list(df_raw.columns)}"
        )

    region_col = next(c for c in df_raw.columns if c.lower() == "region")
    year_col = next(c for c in df_raw.columns if c.lower() == "tid")

    df = pd.DataFrame(
        {
            "kommun_kod": df_raw[region_col].astype(str).str.zfill(4),
            "year": df_raw[year_col].astype(int),
            "population": pd.to_numeric(df_raw[value_col], errors="coerce")
            .fillna(0)
            .astype(int),
        }
    )
    return df.groupby(["kommun_kod", "year"], as_index=False)["population"].sum()


def _verify_against_published_totals(
    df_groups: pd.DataFrame, df_totals: pd.DataFrame
) -> None:
    """Check the age-group sum against the publisher's own total.

    This is the check that would have caught METHODOLOGY §12.8 the day it
    landed. §12.7's validation compared 2025 against 2024 and asked whether the
    change was plausible; a year-over-year plausibility test cannot see an
    error that is 0.0015 % nationally and 1 % in one kommun.

    Per METHODOLOGY §11.6 this is a hard check: a client-side sum that
    disagrees with the publisher is a structural integrity failure, not an
    oddity worth a warning.

    Args:
        df_groups: Long age-group frame [kommun_kod, year, age_group, population].
        df_totals: Published totals [kommun_kod, year, population].

    Raises:
        ValueError: If any kommun or the national total deviates beyond the
            tolerances measured in METHODOLOGY §12.8.
    """
    summed = (
        df_groups.groupby(["kommun_kod", "year"], as_index=False)["population"]
        .sum()
        .rename(columns={"population": "summed"})
    )
    merged = summed.merge(df_totals, on=["kommun_kod", "year"], how="inner")
    if merged.empty:
        raise ValueError(
            "No overlap between the age-group frame and the published totals; "
            "the total query returned nothing comparable."
        )

    merged["deviation_pct"] = (
        100.0 * (merged["summed"] - merged["population"]).abs() / merged["population"]
    )

    for year, chunk in merged.groupby("year"):
        national = 100.0 * abs(
            chunk["summed"].sum() - chunk["population"].sum()
        ) / chunk["population"].sum()
        worst = chunk.loc[chunk["deviation_pct"].idxmax()]
        logger.info(
            "Published-total check %d: national %.4f %% (limit %.2f), worst kommun "
            "%s %.4f %% (limit %.2f)",
            year,
            national,
            _MAX_NATIONAL_TOTAL_DEVIATION_PCT,
            worst["kommun_kod"],
            worst["deviation_pct"],
            _MAX_KOMMUN_TOTAL_DEVIATION_PCT,
        )

        if national > _MAX_NATIONAL_TOTAL_DEVIATION_PCT:
            raise ValueError(
                f"Year {year}: the summed age groups differ from SCB's published "
                f"total by {national:.4f} % nationally, above the "
                f"{_MAX_NATIONAL_TOTAL_DEVIATION_PCT} % limit. Verify the "
                "ContentsCode, the age codes and whether every dimension is "
                "either eliminated or pinned to its total. See METHODOLOGY §12.8."
            )
        if worst["deviation_pct"] > _MAX_KOMMUN_TOTAL_DEVIATION_PCT:
            raise ValueError(
                f"Year {year}: kommun {worst['kommun_kod']} differs from SCB's "
                f"published total by {worst['deviation_pct']:.4f} % "
                f"({int(worst['summed'])} summed against {int(worst['population'])} "
                f"published), above the {_MAX_KOMMUN_TOTAL_DEVIATION_PCT} % limit. "
                "See METHODOLOGY §12.8."
            )


def _age_code_to_group(age_code: str) -> str:
    """Map an age code — single year or band — to a broad age group label.

    Args:
        age_code: Raw age code from the SCB API: a single year ('0', '19'), a
            band ('-4', '20-24') or an open-ended top code. BefolkningCKM
            spells the open-ended codes '100+1' and '100+5'.

    Returns:
        One of '0-19', '20-64', or '65+'.

    Raises:
        ValueError: If the code spans a group boundary. A 10-year band such as
            '60-69' would otherwise put 65–69 year-olds into the working-age
            denominator and quietly deflate every dependency ratio.
    """
    low, high = _age_bounds(age_code)

    def group_of(age: int) -> str:
        if age < _GROUP_BOUNDARIES[0]:
            return "0-19"
        return "20-64" if age < _GROUP_BOUNDARIES[1] else "65+"

    low_group, high_group = group_of(low), group_of(min(high, 200))
    if low_group != high_group:
        raise ValueError(
            f"Age code {age_code!r} straddles a group boundary "
            f"({low_group} to {high_group}); it cannot be assigned to one "
            "age group. Select bands that lie wholly inside 0-19, 20-64 or 65+."
        )
    return low_group


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


def _cache_matches_query(df_raw: pd.DataFrame, expected_ages: list[str]) -> bool:
    """Whether a cached raw response was fetched with the current age codes.

    Freshness by age is not enough once the query shape can change: a cache
    written with single-year codes is still young, but aggregating it would
    silently keep the noisier arithmetic that METHODOLOGY §12.8 exists to
    avoid. Same class of bug as the stale skattekraft cache guarded in T0.1.

    Args:
        df_raw: The cached raw response.
        expected_ages: The age codes the current query would request.

    Returns:
        True when the cache carries exactly the expected age codes.
    """
    age_col = next((c for c in df_raw.columns if c.lower() == "alder"), None)
    if age_col is None:
        return False
    return set(df_raw[age_col].astype(str)) == set(expected_ages)


def _total_cache_path(year: int) -> Path:
    """Return the cache path for one year's published population total.

    Args:
        year: The integer year.

    Returns:
        Path object pointing to data/raw/population_total_{year}.json.
    """
    return _CACHE_DIR / f"population_total_{year}.json"


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
