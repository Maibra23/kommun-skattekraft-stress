"""Estimate the two-way fixed-effects panel model using linearmodels.PanelOLS.

Reads data/processed/panel.parquet, sets the MultiIndex to [kommun_kod, year],
fits PanelOLS with entity_effects=True, time_effects=True, and standard errors
clustered at the municipality level.  Writes the fitted result object to
artifacts/model_results.pkl and the coefficient table to
artifacts/coefficients.parquet.

What this model is, after REMEDIATION_PLAN.md T2.4
--------------------------------------------------
This is the **within-time inference panel**, not the headline model.  It
answers "within a kommun over time, what is the association between its
structural conditions and its tax base growth?"  It does not rank kommuner and
never could: 98.2 % of the variation in relative position is *between*
kommuner, which the entity effects absorb.  Ranking and the position
decomposition come from the cross-sectional estimator in ``estimate_cross``.

Within this panel the **lagged specification is primary** (``PRIMARY_SPEC``).
Every regressor's within-kommun correlation with growth peaks at t-1 or later
— unemployment at -0.500 (t-1) against -0.180 contemporaneous — which is what
the two-year publication lag on skattekraft (METHODOLOGY §7.6) implies.  The
lagged spec is also the only one usable for forecasting, since it needs no
contemporaneous data.  The contemporaneous spec is retained as a robustness
check.

Primacy is carried by the ``role`` column, **not** by the ``spec`` names.  The
names are a published contract: the deployed dashboard filters
``spec == "main"`` (app.py:226), and artifacts are read straight from git with
no build step (METHODOLOGY §11.7).  Renaming ``main`` to ``contemporaneous``
belongs to the single UI cutover commit, not here.
"""

import logging
import pickle
from pathlib import Path

import pandas as pd
from linearmodels import PanelOLS

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"

Y_VAR = "tax_base_growth_pct"
X_VARS = ["unemployment_rate", "dependency_ratio", "population_growth_pct", "edu_share"]

# The FE panel's primary specification (REMEDIATION_PLAN.md T2.4).  Every other
# spec in coefficients.parquet is a robustness check on this one.
PRIMARY_SPEC = "lagged"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _set_panel_index(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of df with MultiIndex (kommun_kod, year)."""
    return df.set_index(["kommun_kod", "year"])


def _lag_x(panel: pd.DataFrame, x_cols: list[str]) -> pd.DataFrame:
    """Return panel with X columns replaced by their one-year within-entity lag."""
    df = panel.sort_values(["kommun_kod", "year"]).copy()
    for col in x_cols:
        df[col] = df.groupby("kommun_kod")[col].shift(1)
    return df


def _log_coefficients(label: str, results) -> None:
    """Log one line per coefficient, with significance stars."""
    logger.info(
        "%s — N=%d, R²(within)=%.4f",
        label,
        results.nobs,
        results.rsquared_within,
    )
    for var in results.params.index:
        p = results.pvalues[var]
        sig = "***" if p < 0.01 else ("**" if p < 0.05 else ("*" if p < 0.10 else ""))
        logger.info(
            "  %-30s b=%+.4f  SE=%.4f  t=%+.2f  p=%.4f %s",
            var,
            results.params[var],
            results.std_errors[var],
            results.tstats[var],
            p,
            sig,
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def estimate_main(panel: pd.DataFrame):
    """Estimate the contemporaneous two-way fixed-effects specification.

    Named ``main`` in ``coefficients.parquet`` for contract stability only; T2.4
    demoted it to a robustness check against ``PRIMARY_SPEC``.  It remains the
    spec pickled to ``model_results.pkl``, which the pre-remediation prediction
    path still reads.

    Args:
        panel: Panel DataFrame with columns including Y_VAR and all X_VARS.

    Returns:
        Fitted PanelEffectsResults object.
    """
    df = _set_panel_index(panel)[X_VARS + [Y_VAR]].dropna()
    y = df[Y_VAR]
    X = df[X_VARS]

    model = PanelOLS(y, X, entity_effects=True, time_effects=True)
    results = model.fit(cov_type="clustered", cluster_entity=True)

    _log_coefficients("Contemporaneous spec 'main' (robustness)", results)
    logger.info(
        "  T_avg=%.1f, R²(between)=%.4f",
        results.nobs / df.index.get_level_values(0).nunique(),
        results.rsquared_between,
    )
    return results


def estimate_robustness(panel: pd.DataFrame) -> dict:
    """Estimate the four remaining specifications.

    One of them — ``lagged`` — is the panel's primary specification since T2.4;
    it is estimated here rather than in ``estimate_main`` so that
    ``model_results.pkl`` and the deployed dashboard's ``spec == "main"`` filter
    keep reading what they read before the promotion.

    Args:
        panel: Panel DataFrame.

    Returns:
        Dict mapping spec name to fitted PanelEffectsResults.
        Keys: 'lagged', 'no_covid', 'large_only', 'no_education'.
    """
    results: dict = {}

    # lagged (PRIMARY): RHS variables lagged one year within each entity.
    # Primary because every regressor's within-kommun correlation with growth
    # peaks at t-1 or later, and because it needs no contemporaneous data.
    df_lag = _lag_x(panel, X_VARS)
    df_lag = _set_panel_index(df_lag)[X_VARS + [Y_VAR]].dropna()
    results["lagged"] = PanelOLS(
        df_lag[Y_VAR], df_lag[X_VARS], entity_effects=True, time_effects=True
    ).fit(cov_type="clustered", cluster_entity=True)
    _log_coefficients("Lagged spec 'lagged' (PRIMARY)", results["lagged"])

    # no_covid: exclude years 2020 and 2021
    df_nc = panel[~panel["year"].isin([2020, 2021])]
    df_nc = _set_panel_index(df_nc)[X_VARS + [Y_VAR]].dropna()
    results["no_covid"] = PanelOLS(
        df_nc[Y_VAR], df_nc[X_VARS], entity_effects=True, time_effects=True
    ).fit(cov_type="clustered", cluster_entity=True)
    logger.info(
        "Robustness 'no_covid'     — N=%d, R²(within)=%.4f",
        results["no_covid"].nobs, results["no_covid"].rsquared_within,
    )

    # large_only: kommuner with 2024 population > 10 000
    large_codes = (
        panel.loc[panel["year"] == 2024]
        .query("population > 10000")["kommun_kod"]
        .unique()
    )
    df_lo = panel[panel["kommun_kod"].isin(large_codes)]
    df_lo = _set_panel_index(df_lo)[X_VARS + [Y_VAR]].dropna()
    results["large_only"] = PanelOLS(
        df_lo[Y_VAR], df_lo[X_VARS], entity_effects=True, time_effects=True
    ).fit(cov_type="clustered", cluster_entity=True)
    logger.info(
        "Robustness 'large_only'   — N=%d, R²(within)=%.4f",
        results["large_only"].nobs, results["large_only"].rsquared_within,
    )

    # no_education: drop edu_share from RHS
    x_no_edu = [v for v in X_VARS if v != "edu_share"]
    df_ne = _set_panel_index(panel)[x_no_edu + [Y_VAR]].dropna()
    results["no_education"] = PanelOLS(
        df_ne[Y_VAR], df_ne[x_no_edu], entity_effects=True, time_effects=True
    ).fit(cov_type="clustered", cluster_entity=True)
    logger.info(
        "Robustness 'no_education' — N=%d, R²(within)=%.4f",
        results["no_education"].nobs, results["no_education"].rsquared_within,
    )

    return results


def extract_coefficients(results) -> pd.DataFrame:
    """Extract a tidy coefficient table from a linearmodels results object.

    Args:
        results: Fitted PanelEffectsResults object.

    Returns:
        DataFrame with columns: variable, coefficient, std_error, t_stat,
        p_value, lower_ci, upper_ci.
    """
    ci = results.conf_int()
    records = []
    for var in results.params.index:
        records.append(
            {
                "variable": str(var),
                "coefficient": float(results.params[var]),
                "std_error": float(results.std_errors[var]),
                "t_stat": float(results.tstats[var]),
                "p_value": float(results.pvalues[var]),
                "lower_ci": float(ci.loc[var].iloc[0]),
                "upper_ci": float(ci.loc[var].iloc[1]),
            }
        )
    return pd.DataFrame(records)


def save_model_artifacts(
    main_results,
    robustness_results: dict,
    output_dir: Path,
) -> None:
    """Persist model results to disk.

    Pickles main_results to artifacts/model_results.pkl and saves the combined
    coefficient table (all specs) to artifacts/coefficients.parquet.

    Args:
        main_results: Fitted results from estimate_main.
        robustness_results: Dict of fitted results from estimate_robustness.
        output_dir: Directory to write artifacts into.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    pkl_path = output_dir / "model_results.pkl"
    with open(pkl_path, "wb") as fh:
        pickle.dump(main_results, fh)
    logger.info("Pickled main results -> %s", pkl_path)

    # Build combined coefficient table: one row per (variable, spec).
    # Each spec carries its own role, sample size and fit, so a consumer can
    # render the primary specification without unpickling model_results.pkl.
    all_coefs: list[pd.DataFrame] = []
    for spec_name, res in [("main", main_results)] + list(robustness_results.items()):
        df = extract_coefficients(res)
        df["spec"] = spec_name
        df["role"] = "primary" if spec_name == PRIMARY_SPEC else "robustness"
        df["n_obs"] = int(res.nobs)
        df["r_squared_within"] = float(res.rsquared_within)
        all_coefs.append(df)

    coef_df = pd.concat(all_coefs, ignore_index=True)

    if set(coef_df.loc[coef_df["role"] == "primary", "spec"]) != {PRIMARY_SPEC}:
        raise ValueError(
            f"Primary spec {PRIMARY_SPEC!r} is missing from the coefficient "
            f"table; specs present: {sorted(coef_df['spec'].unique())}."
        )

    coef_path = output_dir / "coefficients.parquet"
    coef_df.to_parquet(coef_path, index=False)
    logger.info(
        "Saved coefficient table (%d rows, %d specs, primary=%r) -> %s",
        len(coef_df),
        coef_df["spec"].nunique(),
        PRIMARY_SPEC,
        coef_path,
    )


def run_estimation() -> None:
    """Orchestrate the full estimation pipeline.

    Loads the panel, estimates the main and robustness specifications, logs
    all diagnostics, and saves artifacts to the artifacts/ directory.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )

    panel_path = PROJECT_ROOT / "data" / "processed" / "panel.parquet"
    if not panel_path.exists():
        raise FileNotFoundError(
            f"Panel file not found: {panel_path}. Run build_panel first."
        )

    logger.info("Loading panel from %s", panel_path)
    panel = pd.read_parquet(panel_path)
    logger.info("Panel shape: %s  years: %s–%s", panel.shape, panel["year"].min(), panel["year"].max())

    logger.info("=== Estimating contemporaneous specification ===")
    main_results = estimate_main(panel)

    logger.info(
        "=== Estimating remaining specifications (primary: %r) ===", PRIMARY_SPEC
    )
    robustness_results = estimate_robustness(panel)

    logger.info("=== Saving model artifacts ===")
    save_model_artifacts(main_results, robustness_results, ARTIFACTS_DIR)

    logger.info("Estimation complete. Artifacts written to %s/", ARTIFACTS_DIR)


if __name__ == "__main__":
    run_estimation()
