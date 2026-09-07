"""Cross-sectional estimator — why a kommun sits where it sits.

The two-way fixed-effects model in ``estimate.py`` asks *within a kommun over
time, what moves its tax-base growth?* The product asks a different question:
*why does Filipstad sit at index 76 while Danderyd sits at 191?* That is a
between-kommun question, and entity fixed effects remove between-kommun
variation by construction — 98.3 % of the variation in relative position,
per the 2026-09-04 audit. This module estimates that variation instead of
deleting it. Same four variables, no entity effects, R2 ~0.69 against 0.008.

**Descriptive, not causal.** Nothing here identifies a causal effect, and the
high R2 makes it tempting to forget that. Education share, dependency ratio
and unemployment are jointly determined with income levels: a kommun whose
residents earn more attracts more educated residents, and more educated
residents raise recorded income. Education alone carries R2 = 0.656 of the
0.690 and correlates +0.810 with the index, so the headline association is
close to a restatement rather than a mechanism. "Raising education by 1 pp
would raise the tax base" is exactly the claim this module does not support.
See METHODOLOGY §7.2.

**Two of the four variables are not separately identified**, which is a
finding rather than a defect. Measured over 2021–2024:

  * ``edu_share`` and ``unemployment_rate`` have confidence intervals
    excluding zero in every year, with stable signs. They are reported as
    drivers.
  * ``dependency_ratio`` and ``population_growth_pct`` have intervals
    spanning zero in every year and each add ~0.001 to R2. They stay in the
    model as controls — dropping them would misstate the specification — but
    are never rendered as attributed components. ``dependency_ratio`` is
    imprecise because it barely varies between kommuner (SD 0.116), not
    because of collinearity: VIF is 1.3–2.1 throughout.

This inverts what the dashboard currently shows. The deployed decomposition
names ``dependency_ratio`` the largest contributor, inherited from the
within/FE variance decomposition where the audit measured it at 59.1 %.
Between kommuner it explains essentially nothing.

Coefficients are reported primarily as **β × SD**, the effect of a
one-standard-deviation move in units of the index. Raw betas sit on
incomparable scales and make ``dependency_ratio``'s −5.55 look larger than
``edu_share``'s +1.18 when its actual effect is ~15× smaller — audit finding
F6 ("vikter") in another form. Raw betas are kept for reproducibility.

Writes ``artifacts/coefficients_cross.parquet``. The FE model's
``coefficients.parquet`` is deliberately left alone: the deployed Streamlit
dashboard reads committed artifacts directly and is cut over in one
deliberate change at T1.2 (METHODOLOGY §11.7).

Implements REMEDIATION_PLAN.md T2.1.
"""

import logging
from pathlib import Path

import pandas as pd

from src.provenance import analysis_year
import statsmodels.api as sm

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_PANEL_PATH: Path = _PROJECT_ROOT / "data" / "processed" / "panel.parquet"
_OUTPUT_PATH: Path = _PROJECT_ROOT / "artifacts" / "coefficients_cross.parquet"

#: SCB's published index, riket = 100. The ranking's actual subject.
Y_VAR = "tax_base_index_riket"

X_VARS: list[str] = [
    "edu_share",
    "unemployment_rate",
    "dependency_ratio",
    "population_growth_pct",
]

#: Unemployment ends in 2024, so the complete-case panel does too. Position
#: alone runs to 2026; this model cannot. See artifacts/data_provenance.json.
LATEST_YEAR: int = analysis_year()

#: Four years is enough to show the intervals overlap and the signs hold,
#: without reaching back into a materially different labour market.
ESTIMATION_YEARS: tuple[int, ...] = tuple(range(LATEST_YEAR - 3, LATEST_YEAR + 1))


# ---------------------------------------------------------------------------
# Estimation
# ---------------------------------------------------------------------------


def _design(panel: pd.DataFrame, year: int) -> pd.DataFrame:
    """Return the complete-case cross-section for one year."""
    return (
        panel.loc[panel["year"] == year, ["kommun_kod", Y_VAR] + X_VARS]
        .dropna()
        .reset_index(drop=True)
    )


def fit_year(panel: pd.DataFrame, year: int):
    """Fit the single-year cross-section with HC3 robust standard errors.

    This is the interpretable headline specification. No entity effects — the
    between-kommun variation is the estimand, not a nuisance.

    Args:
        panel: The kommun-year panel.
        year: Year to estimate.

    Returns:
        Fitted statsmodels ``RegressionResults``.
    """
    df = _design(panel, year)
    X = sm.add_constant(df[X_VARS], has_constant="add")
    return sm.OLS(df[Y_VAR], X).fit(cov_type="HC3")


def fit_pooled(panel: pd.DataFrame, years: tuple[int, ...] = ESTIMATION_YEARS):
    """Fit the pooled specification: year effects only, kommun-clustered SE.

    A stability check, not the headline. Pooling does not sharpen a
    between-kommun question — the effective sample is 290 kommuner, not
    290 × years, and clustering on kommun correctly says so.

    Args:
        panel: The kommun-year panel.
        years: Years to pool.

    Returns:
        Fitted statsmodels ``RegressionResults``.
    """
    df = pd.concat([_design(panel, y).assign(year=y) for y in years], ignore_index=True)
    year_dummies = pd.get_dummies(df["year"], prefix="year", drop_first=True).astype(
        float
    )
    X = sm.add_constant(
        pd.concat([df[X_VARS], year_dummies], axis=1), has_constant="add"
    )
    return sm.OLS(df[Y_VAR], X).fit(
        cov_type="cluster", cov_kwds={"groups": df["kommun_kod"]}
    )


# ---------------------------------------------------------------------------
# Coefficient table
# ---------------------------------------------------------------------------


def _rows_for(results, sds: pd.Series, spec: str, year, n_obs: int) -> list[dict]:
    """Tidy one fitted result into per-variable records on both scales."""
    ci = results.conf_int()
    records = []
    for var in X_VARS:
        sd = float(sds[var])
        lower, upper = float(ci.loc[var, 0]), float(ci.loc[var, 1])
        beta = float(results.params[var])
        records.append(
            {
                "spec": spec,
                "year": year,
                "variable": var,
                "coefficient": beta,
                "std_error": float(results.bse[var]),
                "p_value": float(results.pvalues[var]),
                "lower_ci": lower,
                "upper_ci": upper,
                "x_sd": sd,
                "beta_sd": beta * sd,
                "lower_ci_sd": lower * sd,
                "upper_ci_sd": upper * sd,
                "r_squared": float(results.rsquared),
                "n_obs": n_obs,
            }
        )
    return records


def _apply_identification_bar(table: pd.DataFrame, latest_year: int) -> pd.DataFrame:
    """Flag which variables may be presented as drivers.

    The bar is fixed before the results are read: a variable qualifies only if
    its interval excludes zero in the primary (latest-year) spec *and* its
    sign is the same in every estimated year. Failing variables remain in the
    model as controls.
    """
    out = table.copy()
    yearly = out[out["spec"].str.startswith("year_")]
    identified = {}
    for var in X_VARS:
        rows = yearly[yearly["variable"] == var]
        primary = rows[rows["year"] == latest_year].iloc[0]
        excludes_zero = primary["lower_ci"] * primary["upper_ci"] > 0
        sign_holds = len(set(rows["coefficient"].map(lambda b: b > 0))) == 1
        identified[var] = bool(excludes_zero and sign_holds)
    out["identified"] = out["variable"].map(identified)
    return out


def _attach_across_year_range(table: pd.DataFrame) -> pd.DataFrame:
    """Record each variable's β × SD range across years.

    Because the yearly intervals overlap, the honest headline is the range —
    "education: +6.4 to +13.7 index points per SD, stable 2021–2024" — with
    the latest year as the point estimate, not one year presented alone.
    """
    out = table.copy()
    yearly = out[out["spec"].str.startswith("year_")].groupby("variable")["beta_sd"]
    out["beta_sd_range_low"] = out["variable"].map(yearly.min())
    out["beta_sd_range_high"] = out["variable"].map(yearly.max())
    return out


def build_coefficient_table(
    panel: pd.DataFrame, years: tuple[int, ...] = ESTIMATION_YEARS
) -> pd.DataFrame:
    """Estimate every spec and return the tidy coefficient table.

    Args:
        panel: The kommun-year panel.
        years: Years to estimate individually and to pool.

    Returns:
        One row per (spec, variable), carrying raw and standardised
        coefficients, intervals on both scales, fit, and the ``identified``
        flag.
    """
    records: list[dict] = []
    for year in years:
        df = _design(panel, year)
        records += _rows_for(
            fit_year(panel, year), df[X_VARS].std(), f"year_{year}", year, len(df)
        )

    pooled_df = pd.concat([_design(panel, y) for y in years], ignore_index=True)
    records += _rows_for(
        fit_pooled(panel, years),
        pooled_df[X_VARS].std(),
        "pooled",
        pd.NA,
        len(pooled_df),
    )

    table = pd.DataFrame(records)
    table = _apply_identification_bar(table, latest_year=max(years))
    return _attach_across_year_range(table)


def run_estimation_cross() -> pd.DataFrame:
    """Read the panel, estimate, write the artifact.

    Returns:
        The written DataFrame.
    """
    logger.info("Loading panel from %s", _PANEL_PATH)
    panel = pd.read_parquet(_PANEL_PATH)

    table = build_coefficient_table(panel)

    for year in ESTIMATION_YEARS:
        r2 = table.loc[table["spec"] == f"year_{year}", "r_squared"].iloc[0]
        logger.info("Cross-section %d — R2 = %.4f", year, r2)

    latest = table[table["spec"] == f"year_{LATEST_YEAR}"]
    for _, row in latest.iterrows():
        logger.info(
            "  %-24s β=%+.4f  β×SD=%+.2f  CI(SD)=[%+.2f, %+.2f]  %s",
            row["variable"],
            row["coefficient"],
            row["beta_sd"],
            row["lower_ci_sd"],
            row["upper_ci_sd"],
            "driver" if row["identified"] else "control (not identified)",
        )

    _OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    table.to_parquet(_OUTPUT_PATH, index=False)
    logger.info("Cross-sectional coefficients written to %s", _OUTPUT_PATH)
    return table


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    )
    run_estimation_cross()
