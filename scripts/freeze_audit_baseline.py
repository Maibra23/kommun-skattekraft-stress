"""Freeze the 2026-09-04 audit findings as a test fixture.

Recomputes every headline number in the Skattekraft Model Audit from the
committed artifacts plus a single live SCB query for realised 2025 outcomes,
and writes them to tests/fixtures/audit_baseline_2026-09-04.json.

This is the only place the network is touched: the realised 2025 growth vector
is stored in the fixture so tests/test_audit_baseline.py runs fully offline.

Run from the project root:
    python scripts/freeze_audit_baseline.py

Implements REMEDIATION_PLAN.md T0.3.
Audit: https://claude.ai/code/artifact/b3dfec90-7359-45fa-91d8-ea137080eb42
"""

import json
import logging
import pickle
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Allow `python scripts/freeze_audit_baseline.py` without an editable install.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.fetch.pxweb_client import (  # noqa: E402  (path bootstrap must precede)
    fetch_metadata,
    get_dimension_codes,
    query_pxweb,
)

logger = logging.getLogger(__name__)
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
PANEL_PATH = PROJECT_ROOT / "data" / "processed" / "panel.parquet"
FIXTURE_PATH = PROJECT_ROOT / "tests" / "fixtures" / "audit_baseline_2026-09-04.json"

SKATTEKRAFT_URL = (
    "https://api.scb.se/OV0104/v1/doris/sv/ssd/START/OE/OE0101/SkatteKraft"
)
_CONTENTS_PER_CAPITA = "OE0101A0"
_BACKTEST_YEARS = ["2024", "2025"]

AUDIT_DATE = "2026-09-04"
AUDIT_URL = "https://claude.ai/code/artifact/b3dfec90-7359-45fa-91d8-ea137080eb42"

X_VARS = ["unemployment_rate", "dependency_ratio", "population_growth_pct", "edu_share"]


# ---------------------------------------------------------------------------
# Data acquisition
# ---------------------------------------------------------------------------


def fetch_actual_2025_growth() -> pd.Series:
    """Fetch realised 2024 and 2025 skattekraft and return percent growth.

    Returns:
        Series indexed by kommun_kod with realised 2025 growth in percent.

    Raises:
        ValueError: If the response does not cover all 290 municipalities.
    """
    metadata = fetch_metadata(SKATTEKRAFT_URL)
    region_codes = sorted(
        c for c in get_dimension_codes(metadata, "Region") if len(c) == 4 and c.isdigit()
    )
    query = {
        "query": [
            {
                "code": "Region",
                "selection": {"filter": "item", "values": region_codes},
            },
            {
                "code": "ContentsCode",
                "selection": {"filter": "item", "values": [_CONTENTS_PER_CAPITA]},
            },
            {"code": "Tid", "selection": {"filter": "item", "values": _BACKTEST_YEARS}},
        ],
        "response": {"format": "json"},
    }
    # query_pxweb returns a tidy frame: dimension columns named by their PxWeb
    # code, then one column per ContentsCode.  All values arrive as strings.
    raw = query_pxweb(SKATTEKRAFT_URL, query)
    tidy = pd.DataFrame(
        {
            "kommun_kod": raw["Region"].astype(str).str.zfill(4),
            "year": raw["Tid"].astype(int),
            "tax_base_per_capita": raw[_CONTENTS_PER_CAPITA].astype(float),
        }
    )
    wide = tidy.pivot(
        index="kommun_kod", columns="year", values="tax_base_per_capita"
    )
    if len(wide) != 290:
        raise ValueError(f"Expected 290 municipalities from SCB, got {len(wide)}.")

    growth = (wide[2025] / wide[2024] - 1) * 100
    logger.info(
        "Realised 2025 growth: mean %.2f%%, sd %.2f, range [%.2f, %.2f]",
        growth.mean(),
        growth.std(),
        growth.min(),
        growth.max(),
    )
    return growth


# ---------------------------------------------------------------------------
# Metric computation
# ---------------------------------------------------------------------------


def compute_variance_shares(main_results, panel: pd.DataFrame) -> dict:
    """Decompose the variance of predicted growth into exact covariance shares.

    Each component's share is cov(component, total) / var(total); these sum to
    exactly 100 percent by construction.

    Args:
        main_results: Fitted PanelEffectsResults from estimate_main.
        panel: Full panel DataFrame.

    Returns:
        Dict mapping component name to percent share of prediction variance.
    """
    effects = main_results.estimated_effects
    if isinstance(effects, pd.DataFrame):
        effects = effects.iloc[:, 0]
    entity_means = effects.groupby(level=0).mean()

    latest = panel[panel["year"] == panel["year"].max()].set_index("kommun_kod")
    betas = main_results.params

    components = pd.DataFrame(index=latest.index)
    components["entity_fixed_effects"] = entity_means.reindex(latest.index)
    for var in X_VARS:
        components[var] = latest[var] * float(betas[var])

    total = components.sum(axis=1)
    total_var = float(total.var())
    return {
        name: float(np.cov(components[name], total)[0, 1] / total_var * 100.0)
        for name in components.columns
    }


def compute_standardised_importance(main_results, panel: pd.DataFrame) -> dict:
    """Compute beta x within-kommun SD, the comparable effect-size measure.

    Raw betas are not comparable across variables with different units; scaling
    by the within-entity standard deviation is what the fixed-effects model
    actually exploits.

    Args:
        main_results: Fitted PanelEffectsResults.
        panel: Full panel DataFrame.

    Returns:
        Dict mapping variable to its beta, within SD, product, and the share of
        its own variance that survives entity demeaning.
    """
    indexed = panel.set_index(["kommun_kod", "year"])[X_VARS].dropna()
    within = indexed - indexed.groupby(level=0).transform("mean")
    betas = main_results.params

    return {
        var: {
            "beta": float(betas[var]),
            "sd_within": float(within[var].std()),
            "beta_x_sd_within": float(betas[var] * within[var].std()),
            "within_share_of_variance": float(within[var].var() / indexed[var].var()),
        }
        for var in X_VARS
    }


def compute_backtest(predictions: pd.DataFrame, actual: pd.Series) -> dict:
    """Score the committed 2025 predictions against realised outcomes.

    Args:
        predictions: artifacts/predictions.parquet.
        actual: Realised 2025 growth indexed by kommun_kod.

    Returns:
        Dict of scoring metrics including the naive constant-mean benchmark.
    """
    df = predictions.set_index("kommun_kod").join(
        actual.rename("actual_growth_2025"), how="inner"
    )
    predicted = df["predicted_growth_2025"]
    realised = df["actual_growth_2025"]

    error = predicted - realised
    naive_error = realised.mean() - realised

    return {
        "n": int(len(df)),
        "pearson_r": float(predicted.corr(realised)),
        "spearman_rho": float(predicted.corr(realised, method="spearman")),
        "rmse": float(np.sqrt((error**2).mean())),
        "naive_rmse": float(np.sqrt((naive_error**2).mean())),
        "bias": float(error.mean()),
        "predicted_mean": float(predicted.mean()),
        "predicted_sd": float(predicted.std()),
        "actual_mean": float(realised.mean()),
        "actual_sd": float(realised.std()),
        "actual_growth_by_risk_class": {
            str(cls): float(value)
            for cls, value in df.groupby("risk_class", observed=True)[
                "actual_growth_2025"
            ]
            .mean()
            .items()
        },
    }


def _source_commit() -> str:
    """Return the current HEAD commit, or 'unknown' outside a git checkout."""
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.warning("Could not determine source commit.")
        return "unknown"


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def build_baseline() -> dict:
    """Assemble the complete baseline record from artifacts and SCB."""
    # model_results.pkl is generated by this project's own pipeline
    # (src/model/estimate.py) and committed to the repository; it is not
    # third-party input.  linearmodels results objects have no JSON form,
    # which is why the pipeline pickles them.
    with open(ARTIFACTS_DIR / "model_results.pkl", "rb") as handle:
        main_results = pickle.load(handle)
    panel = pd.read_parquet(PANEL_PATH)
    predictions = pd.read_parquet(ARTIFACTS_DIR / "predictions.parquet")
    coefficients = pd.read_parquet(ARTIFACTS_DIR / "coefficients.parquet")

    actual = fetch_actual_2025_growth()
    main_coefs = coefficients[coefficients["spec"] == "main"].set_index("variable")

    return {
        "audit_date": AUDIT_DATE,
        "audit_url": AUDIT_URL,
        "source_commit": _source_commit(),
        "scb_table": "OE0101/SkatteKraft, ContentsCode OE0101A0",
        "note": (
            "Pre-remediation baseline. Recorded so that REMEDIATION_PLAN.md "
            "Phase 2 can demonstrate improvement rather than mere change. "
            "See tests/test_audit_baseline.py."
        ),
        "panel": {
            "n_municipalities": int(panel["kommun_kod"].nunique()),
            "year_min": int(panel["year"].min()),
            "year_max": int(panel["year"].max()),
            "n_observations": int(len(panel)),
        },
        "model_fit": {
            "rsquared_within": float(main_results.rsquared_within),
            "rsquared_between": float(main_results.rsquared_between),
            "nobs": int(main_results.nobs),
        },
        "coefficients_main": {
            var: {
                "coefficient": float(main_coefs.loc[var, "coefficient"]),
                "std_error": float(main_coefs.loc[var, "std_error"]),
                "p_value": float(main_coefs.loc[var, "p_value"]),
            }
            for var in X_VARS
        },
        "standardised_importance": compute_standardised_importance(main_results, panel),
        "prediction_variance_shares_pct": compute_variance_shares(main_results, panel),
        "risk_class_counts": {
            str(cls): int(count)
            for cls, count in predictions["risk_class"].value_counts().items()
        },
        "backtest_2025": compute_backtest(predictions, actual),
        "actual_growth_2025": {
            str(kod): float(value) for kod, value in actual.sort_index().items()
        },
    }


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s"
    )
    logger.info("Building audit baseline fixture")
    baseline = build_baseline()

    FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE_PATH.write_text(json.dumps(baseline, indent=2, sort_keys=False) + "\n")

    logger.info("Wrote %s", FIXTURE_PATH)
    logger.info(
        "  R2(within)=%.4f  backtest r=%.3f  RMSE=%.3f vs naive %.3f",
        baseline["model_fit"]["rsquared_within"],
        baseline["backtest_2025"]["pearson_r"],
        baseline["backtest_2025"]["rmse"],
        baseline["backtest_2025"]["naive_rmse"],
    )


if __name__ == "__main__":
    main()
