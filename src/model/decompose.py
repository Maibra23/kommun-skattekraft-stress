"""Structural decomposition of each municipality's 2024 growth gap.

For each municipality, decomposes the gap between its actual 2024 tax base
growth and the national mean into contributions from each structural variable
plus a residual term.  Implements METHODOLOGY §4.1.

Formula for each municipality i in 2024:
    total_gap_i = actual_growth_i - national_mean_growth

    decomp_k_i = beta_k * (X_{ki,2024} - national_mean_X_k)  for k in {1..4}

    decomp_residual_i = total_gap_i - sum(decomp_k_i)

The residual absorbs the municipality fixed effect contribution and the
idiosyncratic 2024 shock (METHODOLOGY §4.2).

Writes artifacts/decomposition.parquet with columns:
    kommun_kod, kommun_name, total_gap, decomp_unemployment,
    decomp_dependency, decomp_population, decomp_education, decomp_residual
"""

import logging
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
PANEL_PATH = PROJECT_ROOT / "data" / "processed" / "panel.parquet"

X_VARS = ["unemployment_rate", "dependency_ratio", "population_growth_pct", "edu_share"]
DECOMP_COLUMNS = [
    "decomp_unemployment",
    "decomp_dependency",
    "decomp_population",
    "decomp_education",
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def decompose_2024_gaps(main_results, panel: pd.DataFrame) -> pd.DataFrame:
    """Decompose each municipality's 2024 growth gap vs the national mean.

    For each independent variable k:
        decomp_k = beta_k * (kommun_value_k - national_mean_k)

    The residual captures all remaining gap (entity FE + idiosyncratic shock):
        decomp_residual = total_gap - sum of four structural contributions

    Args:
        main_results: Fitted PanelEffectsResults from estimate_main.
        panel: Full panel DataFrame with all X_VARS, tax_base_growth_pct,
            kommun_kod, kommun_name, and year columns.

    Returns:
        DataFrame with columns: kommun_kod, kommun_name, total_gap,
        decomp_unemployment, decomp_dependency, decomp_population,
        decomp_education, decomp_residual.  One row per municipality
        (290 rows).

    Raises:
        ValueError: If year 2024 is not in the panel, or if the
            decomposition sum-check fails.
    """
    # Filter to 2024
    df_2024 = panel[panel["year"] == 2024].copy()
    if df_2024.empty:
        raise ValueError("No 2024 observations found in panel.")

    betas = main_results.params

    # National means for 2024
    national_mean_growth = df_2024["tax_base_growth_pct"].mean()
    national_means = {var: df_2024[var].mean() for var in X_VARS}

    logger.info(
        "National 2024 means — growth=%.2f%%, unemployment=%.2f%%, "
        "dependency=%.3f, pop_growth=%.2f%%, edu_share=%.2f%%",
        national_mean_growth,
        national_means["unemployment_rate"],
        national_means["dependency_ratio"],
        national_means["population_growth_pct"],
        national_means["edu_share"],
    )

    # Vectorized decomposition
    result = df_2024[["kommun_kod", "kommun_name"]].copy()

    result["total_gap"] = df_2024["tax_base_growth_pct"].values - national_mean_growth

    result["decomp_unemployment"] = (
        float(betas["unemployment_rate"])
        * (df_2024["unemployment_rate"].values - national_means["unemployment_rate"])
    )
    result["decomp_dependency"] = (
        float(betas["dependency_ratio"])
        * (df_2024["dependency_ratio"].values - national_means["dependency_ratio"])
    )
    result["decomp_population"] = (
        float(betas["population_growth_pct"])
        * (
            df_2024["population_growth_pct"].values
            - national_means["population_growth_pct"]
        )
    )
    result["decomp_education"] = (
        float(betas["edu_share"])
        * (df_2024["edu_share"].values - national_means["edu_share"])
    )

    # Residual = total_gap - sum of structural contributions
    structural_sum = (
        result["decomp_unemployment"]
        + result["decomp_dependency"]
        + result["decomp_population"]
        + result["decomp_education"]
    )
    result["decomp_residual"] = result["total_gap"] - structural_sum

    result = result.reset_index(drop=True)

    # Validation: sum of all components equals total_gap within float precision
    component_sum = (
        result[DECOMP_COLUMNS].sum(axis=1) + result["decomp_residual"]
    )
    if not np.allclose(component_sum, result["total_gap"], atol=1e-10):
        max_err = (component_sum - result["total_gap"]).abs().max()
        raise ValueError(
            f"Decomposition sum check failed: max error = {max_err:.2e}. "
            "Components do not sum to total_gap."
        )

    logger.info(
        "Decomposition complete: %d municipalities, "
        "total_gap range [%.3f, %.3f], "
        "mean residual magnitude %.4f",
        len(result),
        result["total_gap"].min(),
        result["total_gap"].max(),
        result["decomp_residual"].abs().mean(),
    )

    return result[
        [
            "kommun_kod",
            "kommun_name",
            "total_gap",
            "decomp_unemployment",
            "decomp_dependency",
            "decomp_population",
            "decomp_education",
            "decomp_residual",
        ]
    ]


def run_decomposition() -> None:
    """Orchestrate the full decomposition pipeline.

    Loads model artifacts and panel, computes structural decomposition
    for all 290 municipalities, validates output, and saves to
    artifacts/decomposition.parquet.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )

    # Load model results
    pkl_path = ARTIFACTS_DIR / "model_results.pkl"
    if not pkl_path.exists():
        raise FileNotFoundError(
            f"Model results not found: {pkl_path}. Run estimate first."
        )
    with open(pkl_path, "rb") as fh:
        main_results = pickle.load(fh)
    logger.info("Loaded model results from %s", pkl_path)

    # Load panel
    if not PANEL_PATH.exists():
        raise FileNotFoundError(
            f"Panel file not found: {PANEL_PATH}. Run build_panel first."
        )
    panel = pd.read_parquet(PANEL_PATH)
    logger.info("Loaded panel: %s", panel.shape)

    # Decompose
    logger.info("=== Computing structural decomposition ===")
    decomp = decompose_2024_gaps(main_results, panel)

    # Validate row count
    if len(decomp) != 290:
        raise ValueError(
            f"Expected 290 rows in decomposition, got {len(decomp)}."
        )

    # Save
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    decomp_path = ARTIFACTS_DIR / "decomposition.parquet"
    decomp.to_parquet(decomp_path, index=False)
    logger.info(
        "Saved decomposition -> %s (%d rows)", decomp_path, len(decomp)
    )

    logger.info("Decomposition complete.")


if __name__ == "__main__":
    run_decomposition()
