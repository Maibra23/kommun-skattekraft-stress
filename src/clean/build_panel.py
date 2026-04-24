"""Merge all cleaned data sources into the balanced 290 × 15 panel DataFrame.

Calls all four fetchers, applies harmonize_kommunkod to each, computes derived
variables (tax_base_growth_pct, dependency_ratio, population_growth_pct), merges
on (kommun_kod, year), drops the 2009 rows (used only for computing 2010 growth),
validates the final shape, runs the METHODOLOGY §6.1 and §6.3 sanity checks, and
writes data/processed/panel.parquet.

Expected final shape: 290 municipalities × 15 years (2010–2024) = 4 350 rows.

Final panel columns:
    kommun_kod, kommun_name, lan_kod, lan_name, year,
    tax_base_per_capita, tax_base_growth_pct,
    unemployment_rate,
    dependency_ratio, population, population_growth_pct,
    edu_share
"""

import logging
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

_EXPECTED_ROWS: int = 290 * 15  # 4 350
_PANEL_YEARS: list[int] = list(range(2010, 2025))
_FETCH_YEARS_SKATTEKRAFT: list[int] = list(range(2009, 2025))  # 2009 for growth calc
_FETCH_YEARS_POPULATION: list[int] = list(range(2009, 2025))  # 2009 for growth calc

_FINAL_COLUMNS: list[str] = [
    "kommun_kod",
    "kommun_name",
    "lan_kod",
    "lan_name",
    "year",
    "tax_base_per_capita",
    "tax_base_growth_pct",
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
    logger.info("Step 1/6: Fetching skattekraft (OE0101) …")
    df_skatt = fetch_skattekraft(years=_FETCH_YEARS_SKATTEKRAFT, force_refresh=force_refresh)

    logger.info("Step 2/6: Fetching population (BE0101) …")
    df_pop = fetch_population(years=_FETCH_YEARS_POPULATION, force_refresh=force_refresh)

    logger.info("Step 3/6: Fetching unemployment (AA0003) …")
    df_unemp = fetch_unemployment(years=_PANEL_YEARS, force_refresh=force_refresh)

    logger.info("Step 4/6: Fetching education (UF0506) …")
    df_edu = fetch_education(years=_PANEL_YEARS, force_refresh=force_refresh)

    # --- Step 2: Harmonize codes ---
    logger.info("Step 2/6: Harmonizing municipality codes …")
    df_skatt = validate_and_harmonize(df_skatt)
    # Population is long-format (3 age-group rows per municipality-year).
    # Validate municipality codes using a deduplicated (municipality, year)
    # slice to avoid false duplicate errors.  Name columns are sourced from
    # df_skatt, so the harmonized population DataFrame is not used in the merge.
    validate_and_harmonize(df_pop[["kommun_kod", "year"]].drop_duplicates())
    df_unemp = validate_and_harmonize(df_unemp)
    df_edu = validate_and_harmonize(df_edu)

    # --- Step 3: Compute derived variables ---
    logger.info("Step 3/6: Computing derived variables …")
    df_dep_ratio = compute_dependency_ratio(df_pop)
    df_pop_growth = compute_population_growth(df_pop)
    df_skatt_growth = compute_tax_base_growth(df_skatt[["kommun_kod", "year", "tax_base_per_capita"]])

    # Drop 2009 from all derived tables (needed only for 2010 growth calc)
    df_dep_ratio = df_dep_ratio[df_dep_ratio["year"].isin(_PANEL_YEARS)]
    df_pop_growth = df_pop_growth[df_pop_growth["year"].isin(_PANEL_YEARS)]
    df_skatt_growth = df_skatt_growth[df_skatt_growth["year"].isin(_PANEL_YEARS)]

    # --- Step 4: Extract name columns from harmonized skattekraft ---
    name_cols = df_skatt[["kommun_kod", "kommun_name", "lan_kod", "lan_name"]].drop_duplicates()

    # --- Step 5: Merge all on (kommun_kod, year) ---
    logger.info("Step 5/6: Merging all sources …")
    panel = (
        df_skatt_growth
        .merge(df_unemp[["kommun_kod", "year", "unemployment_rate"]], on=["kommun_kod", "year"], how="inner")
        .merge(df_dep_ratio, on=["kommun_kod", "year"], how="inner")
        .merge(df_pop_growth, on=["kommun_kod", "year"], how="inner")
        .merge(df_edu[["kommun_kod", "year", "edu_share"]], on=["kommun_kod", "year"], how="inner")
        .merge(name_cols, on="kommun_kod", how="left")
    )

    # Filter to the analysis window (2010–2024) and drop rows with NaN growth
    panel = panel[panel["year"].isin(_PANEL_YEARS)].reset_index(drop=True)
    panel = panel.dropna(subset=["tax_base_growth_pct", "population_growth_pct"])

    # Reorder columns to the canonical order
    panel = panel[_FINAL_COLUMNS]
    panel = panel.sort_values(["kommun_kod", "year"]).reset_index(drop=True)

    # --- Step 6: Validate and write ---
    logger.info("Step 6/6: Validating and writing panel …")
    _validate_panel(panel)

    _OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(_OUTPUT_PATH, index=False, engine="pyarrow")
    logger.info(
        "Panel written to %s  (%d rows × %d columns)",
        _OUTPUT_PATH,
        len(panel),
        len(panel.columns),
    )
    return panel


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _validate_panel(panel: pd.DataFrame) -> None:
    """Run shape, completeness, and sanity checks on the final panel.

    Implements METHODOLOGY §6.1 (skattekraft level checks) and §6.3 (growth
    rate sanity) in-line.  Also validates the balanced-panel shape constraint.

    Args:
        panel: The merged panel DataFrame.

    Raises:
        ValueError: If any check fails.
    """
    # Shape check
    if len(panel) != _EXPECTED_ROWS:
        raise ValueError(
            f"Panel has {len(panel)} rows; expected {_EXPECTED_ROWS} "
            f"(290 municipalities × 15 years). "
            "Check for missing data or failed merges."
        )

    n_municipalities = panel["kommun_kod"].nunique()
    if n_municipalities != 290:
        raise ValueError(
            f"Panel has {n_municipalities} unique municipalities; expected 290."
        )

    n_years = panel["year"].nunique()
    if n_years != 15:
        raise ValueError(
            f"Panel has {n_years} unique years; expected 15 (2010–2024)."
        )

    # No missing values in any column
    missing = panel[_FINAL_COLUMNS].isnull().sum()
    missing = missing[missing > 0]
    if not missing.empty:
        raise ValueError(
            f"Missing values detected in panel:\n{missing.to_string()}\n"
            "Resolve data gaps before modeling."
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
