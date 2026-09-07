"""Compute derived panel variables from raw fetcher outputs.

Three functions cover all derived variables needed by the regression model:

  - compute_dependency_ratio: pivots long-format population to wide and
    computes (pop_0_19 + pop_65plus) / pop_20_64 per (kommun, year).

  - compute_population_growth: takes SCB's published population totals and
    computes year-over-year percent change per kommun.  It falls back to
    summing the age groups only when no totals are supplied, which is exact
    for BefolkningNy but not for the disclosure-protected BefolkningCKM —
    see METHODOLOGY §12.8.

  - compute_tax_base_growth: computes year-over-year percent change in
    tax_base_per_capita per kommun.

All computations are within-municipality (grouped by kommun_kod) to prevent
cross-municipality contamination.  NaN is produced for the first available
year of growth variables (since no prior year exists); the caller is expected
to drop the 2009 rows after merging.
"""

import logging

import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_dependency_ratio(pop_long: pd.DataFrame) -> pd.DataFrame:
    """Compute municipality-level dependency ratio from long-format population.

    The dependency ratio measures the share of the population that is outside
    the primary working-age range (20–64):
        dependency_ratio = (pop_0_19 + pop_65plus) / pop_20_64

    A ratio of 0.80 means 80 dependents per 100 working-age persons.

    Args:
        pop_long: Long-format DataFrame with columns
            [kommun_kod, year, age_group, population].
            age_group must take values from {'0-19', '20-64', '65+'}.

    Returns:
        Wide-format DataFrame with columns [kommun_kod, year, dependency_ratio].
        Rows with missing or zero pop_20_64 produce NaN dependency_ratio and
        are logged as a warning.

    Raises:
        ValueError: If required age groups are not all present in pop_long.
    """
    required_groups = {"0-19", "20-64", "65+"}
    present_groups = set(pop_long["age_group"].unique())
    missing = required_groups - present_groups
    if missing:
        raise ValueError(
            f"Missing age groups in pop_long: {missing}. "
            "Expected all of {'0-19', '20-64', '65+'}."
        )

    wide = pop_long.pivot_table(
        index=["kommun_kod", "year"],
        columns="age_group",
        values="population",
        aggfunc="sum",
    ).reset_index()

    # Rename columns from age_group strings to valid Python identifiers.
    wide = wide.rename(
        columns={
            "0-19": "pop_0_19",
            "20-64": "pop_20_64",
            "65+": "pop_65plus",
        }
    )

    zero_working_age = wide["pop_20_64"] == 0
    if zero_working_age.any():
        n = zero_working_age.sum()
        logger.warning(
            "%d rows have pop_20_64 = 0; dependency_ratio will be NaN for those.", n
        )

    wide["dependency_ratio"] = (wide["pop_0_19"] + wide["pop_65plus"]) / wide[
        "pop_20_64"
    ].replace(0, float("nan"))

    logger.info(
        "compute_dependency_ratio: %d rows, mean=%.3f, range=[%.3f, %.3f]",
        len(wide),
        wide["dependency_ratio"].mean(),
        wide["dependency_ratio"].min(),
        wide["dependency_ratio"].max(),
    )
    return wide[["kommun_kod", "year", "dependency_ratio"]]


def compute_population_growth(
    pop_long: pd.DataFrame, totals: pd.DataFrame | None = None
) -> pd.DataFrame:
    """Compute total population and year-over-year growth per municipality.

    Prefers SCB's published total when `totals` is supplied, and only falls
    back to summing the age groups when it is not. The distinction is not
    cosmetic: `BefolkningCKM` protects its cells, so its parts do not sum to
    its published total, and in the smallest kommuner the summed figure is off
    by up to 1 % — one full SD of the growth rate this function returns. For
    Överkalix 2025 that is −1.56 % summed against −0.56 % published. See
    METHODOLOGY §12.8.

        population_growth_pct_t = (pop_total_t / pop_total_{t-1} - 1) × 100

    The first year in the data for each municipality produces NaN for
    population_growth_pct (no prior year available).

    Args:
        pop_long: Long-format DataFrame with columns
            [kommun_kod, year, age_group, population].
        totals: Optional published totals [kommun_kod, year, population]. When
            given it must cover every municipality-year in `pop_long`.

    Returns:
        DataFrame with columns [kommun_kod, year, population, population_growth_pct].
        population is total persons (int); population_growth_pct is float (percent).

    Raises:
        ValueError: If `totals` is given but does not cover every row.
    """
    if totals is None:
        total = pop_long.groupby(["kommun_kod", "year"], as_index=False)[
            "population"
        ].sum()
        logger.info(
            "compute_population_growth: no published totals supplied; summing age "
            "groups. Exact for BefolkningNy, not for BefolkningCKM (METHODOLOGY §12.8)."
        )
    else:
        keys = pop_long[["kommun_kod", "year"]].drop_duplicates()
        total = keys.merge(
            totals[["kommun_kod", "year", "population"]],
            on=["kommun_kod", "year"],
            how="left",
        )
        missing = total["population"].isna()
        if missing.any():
            sample = total.loc[missing, ["kommun_kod", "year"]].head(5).to_dict("records")
            raise ValueError(
                f"{int(missing.sum())} municipality-years have no published total, "
                f"e.g. {sample}. Fetch the totals for every year in the panel."
            )
        total["population"] = total["population"].astype(int)

    total = total.sort_values(["kommun_kod", "year"])

    total["population_growth_pct"] = total.groupby("kommun_kod")[
        "population"
    ].pct_change() * 100.0

    nan_count = total["population_growth_pct"].isna().sum()
    logger.info(
        "compute_population_growth: %d rows, %d NaN (expected one per municipality "
        "for the earliest year in the series).",
        len(total),
        nan_count,
    )
    return total[["kommun_kod", "year", "population", "population_growth_pct"]]


def compute_tax_base_growth(skattekraft: pd.DataFrame) -> pd.DataFrame:
    """Compute year-over-year growth in tax base per capita per municipality.

    Formula:
        tax_base_growth_pct_t = (tax_base_per_capita_t / tax_base_per_capita_{t-1}
                                  - 1) × 100

    The first available year for each municipality produces NaN.

    Args:
        skattekraft: DataFrame with columns [kommun_kod, year, tax_base_per_capita].
            tax_base_per_capita must be a positive float (SEK per inhabitant).

    Returns:
        DataFrame with columns [kommun_kod, year, tax_base_per_capita,
        tax_base_growth_pct].
    """
    df = skattekraft.sort_values(["kommun_kod", "year"]).copy()

    df["tax_base_growth_pct"] = df.groupby("kommun_kod")[
        "tax_base_per_capita"
    ].pct_change() * 100.0

    nan_count = df["tax_base_growth_pct"].isna().sum()
    logger.info(
        "compute_tax_base_growth: %d rows, %d NaN (expected one per municipality).",
        len(df),
        nan_count,
    )
    return df[["kommun_kod", "year", "tax_base_per_capita", "tax_base_growth_pct"]]
