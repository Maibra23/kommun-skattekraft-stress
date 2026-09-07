"""Merge all cleaned data sources into the ragged kommun-year panel DataFrame.

Calls all four fetchers, applies harmonize_kommunkod to each, computes derived
variables (tax_base_growth_pct, dependency_ratio, population_growth_pct), merges
on (kommun_kod, year), drops the 2009 rows (used only for computing 2010 growth),
validates the result, runs the METHODOLOGY §6.1 and §6.3 sanity checks, and
writes data/processed/panel.parquet plus artifacts/data_provenance.json.

**The panel is deliberately unbalanced at the top end.** The four SCB sources
refresh on different cadences and no longer share an end year: skattekraft runs
to 2026, population and education to 2025, unemployment to 2024. Truncating
every source to the shortest would throw away the newest skattekraft, which is
the whole point of extending coverage. Instead the panel is anchored on
skattekraft and the shorter sources are left null in the years they do not
reach. `PanelOLS` tolerates unbalanced panels and estimation `.dropna()`
handles the rest.

Any consumer that needs all four structural variables must read
`complete_case_max_year` from the provenance artifact rather than assuming the
panel's own maximum year. See REMEDIATION_PLAN.md T0.2 and METHODOLOGY §2.3.1.

Final panel columns:
    kommun_kod, kommun_name, lan_kod, lan_name, year,
    tax_base_per_capita, tax_base_growth_pct, tax_base_index_riket,
    unemployment_rate,
    dependency_ratio, population, population_growth_pct,
    edu_share
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.clean.compute_derived import (
    compute_dependency_ratio,
    compute_population_growth,
    compute_tax_base_growth,
)
from src.clean.harmonize_kommunkod import validate_and_harmonize
from src.fetch.fetch_education import fetch_education
from src.fetch.fetch_population import fetch_population
from src.fetch.fetch_skattekraft import fetch_skattekraft
from src.fetch.fetch_unemployment import fetch_unemployment

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).parents[2]
_OUTPUT_PATH: Path = _PROJECT_ROOT / "data" / "processed" / "panel.parquet"

_PROVENANCE_PATH: Path = _PROJECT_ROOT / "artifacts" / "data_provenance.json"

_EXPECTED_COMMUNES: int = 290
_PANEL_START_YEAR: int = 2010
# Each source is fetched to its own maximum; the panel has no fixed end year.
# 2009 is fetched for skattekraft and population only to seed the 2010 growth
# rates, then dropped.  See REMEDIATION_PLAN.md T0.2.
_FETCH_YEARS_SKATTEKRAFT: list[int] = list(range(2009, 2027))  # to 2026
_FETCH_YEARS_POPULATION: list[int] = list(range(2009, 2026))  # to 2025
_FETCH_YEARS_UNEMPLOYMENT: list[int] = list(range(2010, 2025))  # to 2024
_FETCH_YEARS_EDUCATION: list[int] = list(range(2010, 2026))  # to 2025

# The variable that defines whether a kommun-year row exists at all.
_SPINE_COLUMN: str = "tax_base_growth_pct"

# Variables required by the cross-sectional model; their common coverage sets
# complete_case_max_year in the provenance artifact.
_STRUCTURAL_COLUMNS: list[str] = [
    "unemployment_rate",
    "dependency_ratio",
    "population_growth_pct",
    "edu_share",
]

_FINAL_COLUMNS: list[str] = [
    "kommun_kod",
    "kommun_name",
    "lan_kod",
    "lan_name",
    "year",
    "tax_base_per_capita",
    "tax_base_growth_pct",
    "tax_base_index_riket",
    "unemployment_rate",
    "dependency_ratio",
    "population",
    "population_growth_pct",
    "edu_share",
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_panel(force_refresh: bool = False) -> pd.DataFrame:
    """Fetch, clean, merge, validate, and write the balanced panel DataFrame.

    Args:
        force_refresh: If True, bypass all raw-data caches and re-fetch from
            SCB API.  Passed through to all fetcher modules.

    Returns:
        Balanced panel DataFrame with 4 350 rows and the columns listed in
        _FINAL_COLUMNS.

    Raises:
        ValueError: If any fetcher output fails harmonization, if the merged
            panel does not have exactly 4 350 rows, or if any METHODOLOGY §6
            sanity check fails.
    """
    # --- Step 1: Fetch raw data ---
    logger.info("Step 1/7: Fetching skattekraft (OE0101) …")
    df_skatt = fetch_skattekraft(years=_FETCH_YEARS_SKATTEKRAFT, force_refresh=force_refresh)

    logger.info("Step 2/7: Fetching population (BE0101) …")
    df_pop = fetch_population(years=_FETCH_YEARS_POPULATION, force_refresh=force_refresh)

    logger.info("Step 3/7: Fetching unemployment (AA0003) …")
    df_unemp = fetch_unemployment(years=_FETCH_YEARS_UNEMPLOYMENT, force_refresh=force_refresh)

    logger.info("Step 4/7: Fetching education (UF0506) …")
    df_edu = fetch_education(years=_FETCH_YEARS_EDUCATION, force_refresh=force_refresh)

    # --- Step 5: Harmonize codes ---
    logger.info("Step 5/7: Harmonizing municipality codes …")
    df_skatt = validate_and_harmonize(df_skatt)
    # Population is long-format (3 age-group rows per municipality-year).
    # Validate municipality codes using a deduplicated (municipality, year)
    # slice to avoid false duplicate errors.  Name columns are sourced from
    # df_skatt, so the harmonized population DataFrame is not used in the merge.
    validate_and_harmonize(df_pop[["kommun_kod", "year"]].drop_duplicates())
    df_unemp = validate_and_harmonize(df_unemp)
    df_edu = validate_and_harmonize(df_edu)

    # --- Step 6: Compute derived variables ---
    logger.info("Step 6/7: Computing derived variables …")
    df_dep_ratio = compute_dependency_ratio(df_pop)
    df_pop_growth = compute_population_growth(df_pop)
    df_skatt_growth = compute_tax_base_growth(df_skatt[["kommun_kod", "year", "tax_base_per_capita"]])

    # Drop the 2009 seed rows (needed only for the 2010 growth calc)
    df_dep_ratio = df_dep_ratio[df_dep_ratio["year"] >= _PANEL_START_YEAR]
    df_pop_growth = df_pop_growth[df_pop_growth["year"] >= _PANEL_START_YEAR]
    df_skatt_growth = df_skatt_growth[df_skatt_growth["year"] >= _PANEL_START_YEAR]

    # --- Step 4: Extract name columns from harmonized skattekraft ---
    name_cols = df_skatt[["kommun_kod", "kommun_name", "lan_kod", "lan_name"]].drop_duplicates()

    # --- Step 7a: Merge all on (kommun_kod, year) ---
    logger.info("Step 7/7: Merging, validating, and writing panel …")
    sources = {
        "skattekraft": df_skatt_growth.merge(
            df_skatt[["kommun_kod", "year", "tax_base_index_riket"]],
            on=["kommun_kod", "year"],
            how="left",
        ),
        "population": df_dep_ratio.merge(
            df_pop_growth, on=["kommun_kod", "year"], how="outer"
        ),
        "education": df_edu[["kommun_kod", "year", "edu_share"]],
        "unemployment": df_unemp[["kommun_kod", "year", "unemployment_rate"]],
    }

    panel = _merge_panel(sources, name_cols)
    provenance = _build_provenance(sources)

    # --- Validate and write ---
    logger.info("Validating and writing panel …")
    _validate_panel(panel, provenance)

    _OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(_OUTPUT_PATH, index=False, engine="pyarrow")
    _write_provenance(provenance, len(panel))
    logger.info(
        "Panel written to %s  (%d rows × %d columns, years %d–%d, "
        "complete through %d)",
        _OUTPUT_PATH,
        len(panel),
        len(panel.columns),
        panel["year"].min(),
        panel["year"].max(),
        provenance["complete_case_max_year"],
    )
    return panel


# ---------------------------------------------------------------------------
# Private helpers — merge and provenance
# ---------------------------------------------------------------------------


def _merge_panel(
    sources: dict[str, pd.DataFrame], name_cols: pd.DataFrame
) -> pd.DataFrame:
    """Merge the four sources into one ragged panel, anchored on skattekraft.

    Every join is a left join onto skattekraft, so a source that stops early
    yields nulls rather than removing kommun-years.  An inner join here would
    silently truncate the panel to the shortest source — the specific failure
    this function exists to prevent.

    Args:
        sources: Frames keyed by source name; 'skattekraft' is the anchor and
            must carry the spine column.
        name_cols: One row per kommun with the name and län columns.

    Returns:
        Panel in canonical column order, sorted by (kommun_kod, year), with
        rows lacking the spine variable dropped.
    """
    panel = sources["skattekraft"]
    for name, frame in sources.items():
        if name == "skattekraft":
            continue
        panel = panel.merge(frame, on=["kommun_kod", "year"], how="left")

    panel = panel.merge(name_cols, on="kommun_kod", how="left")
    panel = panel[panel["year"] >= _PANEL_START_YEAR]
    panel = panel.dropna(subset=[_SPINE_COLUMN])

    for column in _FINAL_COLUMNS:
        if column not in panel.columns:
            panel[column] = pd.NA

    return (
        panel[_FINAL_COLUMNS]
        .sort_values(["kommun_kod", "year"])
        .reset_index(drop=True)
    )


def _build_provenance(sources: dict[str, pd.DataFrame]) -> dict:
    """Record each source's year coverage so consumers can state what they used.

    The four SCB series refresh on different cadences, so the panel's own
    maximum year is not the year at which every variable exists. Anything that
    needs all four structural variables — the cross-sectional estimator above
    all — must read `complete_case_max_year` rather than `max(panel.year)`.

    Args:
        sources: The same frames passed to _merge_panel.

    Returns:
        A JSON-serialisable provenance dict.
    """
    per_source = {
        name: {
            "min_year": int(frame["year"].min()),
            "max_year": int(frame["year"].max()),
            "n_kommuner": int(frame["kommun_kod"].nunique()),
        }
        for name, frame in sources.items()
    }

    complete_case_max = min(s["max_year"] for s in per_source.values())
    panel_max = max(s["max_year"] for s in per_source.values())

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sources": per_source,
        "panel_max_year": panel_max,
        "complete_case_max_year": complete_case_max,
        "balanced": complete_case_max == panel_max,
        "note": (
            "The panel is ragged at the top end: sources end in different "
            "years. Use complete_case_max_year for any analysis needing all "
            "four structural variables. See REMEDIATION_PLAN.md T0.2."
        ),
    }


def _write_provenance(provenance: dict, n_rows: int) -> None:
    """Write the provenance dict to artifacts/data_provenance.json."""
    payload = {**provenance, "panel_rows": n_rows}
    _PROVENANCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _PROVENANCE_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    logger.info("Provenance written to %s", _PROVENANCE_PATH)


# ---------------------------------------------------------------------------
# Private helpers — validation
# ---------------------------------------------------------------------------


def _validate_panel(panel: pd.DataFrame, provenance: dict) -> None:
    """Run shape, completeness, and sanity checks on the final panel.

    Implements METHODOLOGY §6.1 (skattekraft level checks) and §6.3 (growth
    rate sanity) in-line.

    The panel is expected to be ragged at the top end, so this does not assert
    a fixed row count.  Instead it asserts the shape invariants that must hold
    regardless of how far each source reaches: every year carries all 290
    kommuner, and no variable has gaps *inside* the window it does cover.  A
    null unemployment rate in 2026 is expected; one in 2015 is a merge failure.

    Args:
        panel: The merged panel DataFrame.
        provenance: Output of _build_provenance, giving each source's coverage.

    Raises:
        ValueError: If any check fails.
    """
    n_municipalities = panel["kommun_kod"].nunique()
    if n_municipalities != _EXPECTED_COMMUNES:
        raise ValueError(
            f"Panel has {n_municipalities} unique municipalities; "
            f"expected {_EXPECTED_COMMUNES}."
        )

    # Every year must carry every kommun — raggedness is across variables,
    # never across municipalities within a year.
    per_year = panel.groupby("year")["kommun_kod"].nunique()
    short_years = per_year[per_year != _EXPECTED_COMMUNES]
    if not short_years.empty:
        raise ValueError(
            "These years do not carry all "
            f"{_EXPECTED_COMMUNES} municipalities:\n{short_years.to_string()}"
        )

    if panel["year"].min() != _PANEL_START_YEAR:
        raise ValueError(
            f"Panel starts at {panel['year'].min()}; expected {_PANEL_START_YEAR}."
        )

    # No gaps inside each variable's own coverage window.
    for column, source in [
        ("unemployment_rate", "unemployment"),
        ("edu_share", "education"),
        ("dependency_ratio", "population"),
        ("population_growth_pct", "population"),
    ]:
        covered = panel[panel["year"] <= provenance["sources"][source]["max_year"]]
        n_missing = int(covered[column].isnull().sum())
        if n_missing:
            raise ValueError(
                f"{column} has {n_missing} missing values inside its coverage "
                f"window (through {provenance['sources'][source]['max_year']}). "
                "This is a merge failure, not a ragged tail."
            )

    if not provenance["balanced"]:
        logger.info(
            "Panel is ragged by design: complete through %d, extends to %d. "
            "Consumers needing all four structural variables must use the "
            "complete-case year.",
            provenance["complete_case_max_year"],
            provenance["panel_max_year"],
        )

    # §6.1 — Skattekraft level checks
    df_2024 = panel[panel["year"] == 2024]

    highest_kod = df_2024.loc[df_2024["tax_base_per_capita"].idxmax(), "kommun_kod"]
    highest_val = df_2024["tax_base_per_capita"].max()
    national_mean_2024 = df_2024["tax_base_per_capita"].mean()

    logger.info(
        "§6.1 Skattekraft check — highest 2024: %s (%.0f SEK), national mean: %.0f SEK",
        highest_kod,
        highest_val,
        national_mean_2024,
    )

    if highest_kod != "0162":
        raise ValueError(
            f"METHODOLOGY §6.1 check failed: expected Danderyd (0162) to have the "
            f"highest 2024 skattekraft but found {highest_kod}."
        )

    if not (200_000 <= national_mean_2024 <= 350_000):
        raise ValueError(
            f"METHODOLOGY §6.1 check failed: 2024 national mean skattekraft is "
            f"{national_mean_2024:.0f} SEK, outside expected 200 000–350 000 SEK."
        )

    # §6.3 — Growth rate sanity
    mean_growth = panel["tax_base_growth_pct"].mean()
    min_growth = panel["tax_base_growth_pct"].min()

    logger.info(
        "§6.3 Growth check — overall mean: %.2f %%, min: %.2f %%",
        mean_growth,
        min_growth,
    )

    if not (2.5 <= mean_growth <= 5.0):
        logger.warning(
            "§6.3: Mean tax_base_growth_pct is %.2f %%, outside expected 2.5–5.0 %% range.",
            mean_growth,
        )

    if min_growth < -10.0:
        raise ValueError(
            f"METHODOLOGY §6.3 check failed: minimum tax_base_growth_pct is "
            f"{min_growth:.2f} %% — below -10 %%, which indicates a data error."
        )

    # Dependency ratio range check (§6.3)
    dep_min = panel["dependency_ratio"].min()
    dep_max = panel["dependency_ratio"].max()
    logger.info("Dependency ratio range: [%.3f, %.3f]", dep_min, dep_max)
    if not (0.4 <= dep_min and dep_max <= 1.5):
        logger.warning(
            "Dependency ratio range [%.3f, %.3f] is outside the expected [0.5, 1.2] "
            "from METHODOLOGY §6.3. Review population data.",
            dep_min,
            dep_max,
        )

    logger.info("All panel validation checks passed.")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import logging as _logging
    _logging.basicConfig(
        level=_logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    )
    panel = build_panel()
    print(f"\nPanel shape: {panel.shape}")
    print(f"Columns: {list(panel.columns)}")
    print(f"\nDtypes:\n{panel.dtypes.to_string()}")
    print(f"\nMissing values:\n{panel.isnull().sum().to_string()}")
    print(f"\nSample (first 3 rows):\n{panel.head(3).to_string(index=False)}")
    print(f"\nYear range: {panel['year'].min()}–{panel['year'].max()}")
    print(f"Municipalities: {panel['kommun_kod'].nunique()}")
    print(f"\nSanity: Danderyd 2024 skattekraft = "
          f"{panel.loc[(panel['kommun_kod']=='0162') & (panel['year']==2024), 'tax_base_per_capita'].iloc[0]:,.0f} SEK")
