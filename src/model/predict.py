"""Generate out-of-sample 2025 vulnerability predictions for all municipalities.

Loads the fitted model from artifacts/model_results.pkl and the most recent
observed (2024) values of the independent variables.  Computes predicted
tax_base_growth_pct for 2025 using estimated betas, municipality fixed effects,
and a year effect proxied by the mean of the last three observed year effects.
Standardizes predictions to vulnerability_score (z-score, sign-flipped so
high = more vulnerable), assigns vulnerability_rank and risk_class (quintile
labels: 'hog', 'medel', 'lag').  Writes artifacts/predictions.parquet and
artifacts/ranking.parquet.

DEPRECATED as the headline ranking (REMEDIATION_PLAN.md T2.4)
-------------------------------------------------------------
The 2025 horizon has closed and this forecast has been scored against it:
Pearson r = +0.016, Spearman = +0.033, RMSE 1.512 pp against a naive
constant-mean benchmark of 0.974 pp — the forecast loses to guessing the
national mean by 55 %.  Its risk classes do not separate and are not monotone:
realised 2025 growth averaged 4.74 % (låg), 4.52 % (medel), 4.68 % (hög), a
0.22 pp spread against a cross-kommun SD of 0.98 pp.  The FE model is a
within-time inference panel, not a ranking engine; 98.2 % of the variation in
relative position is between kommuner, which the entity effects absorb.

Both artifacts are still written, unchanged, because the deployed dashboard
reads them straight from git (METHODOLOGY §11.7) and the UI cutover is a later
single commit.  ``compute_vulnerability`` raises a ``DeprecationWarning`` so no
new caller adopts it silently.  Its replacement is the position and drift
measures in ``src/model/position.py``; its final removal is T3.x's call.
"""

import logging
import pickle
import warnings
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
PANEL_PATH = PROJECT_ROOT / "data" / "processed" / "panel.parquet"

X_VARS = ["unemployment_rate", "dependency_ratio", "population_growth_pct", "edu_share"]
RECENT_YEARS = [2022, 2023, 2024]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def predict_2025(main_results, panel: pd.DataFrame) -> pd.DataFrame:
    """Generate predicted tax base growth for 2025 for all 290 municipalities.

    Applies the formula from METHODOLOGY §3.1:
        predicted_i = alpha_i + gamma_recent + X_{i,2024} @ beta

    Where:
        alpha_i      = estimated kommun fixed effect
        gamma_recent = mean of estimated year FE for 2022, 2023, 2024
        beta         = estimated coefficients from the main specification
        X_{i,2024}   = most recent observed values of independent variables

    The entity and time effects are separated from the combined
    estimated_effects using the standard two-way decomposition:
        entity_means[i] = mean_t(effects_{i,t})  = alpha_i + gamma_bar
        time_means[t]   = mean_i(effects_{i,t})   = alpha_bar + gamma_t
        grand_mean       = mean_{i,t}(effects)     = alpha_bar + gamma_bar

    So alpha_i + gamma_recent = entity_means[i] + time_means_recent - grand_mean.

    Args:
        main_results: Fitted PanelEffectsResults from estimate_main.
        panel: Full panel DataFrame with columns including X_VARS,
            kommun_kod, kommun_name, lan_name, and year.

    Returns:
        DataFrame with columns: kommun_kod, kommun_name, lan_name,
        predicted_growth_2025.  One row per municipality (290 rows).
    """
    # Extract combined estimated effects (alpha_i + gamma_t)
    effects = main_results.estimated_effects
    if isinstance(effects, pd.DataFrame):
        effects = effects.iloc[:, 0]

    # Decompose into entity and time components
    entity_means = effects.groupby(level=0).mean()
    time_means = effects.groupby(level=1).mean()
    grand_mean = float(effects.mean())

    # Proxy for gamma_recent: mean of time effects for 2022-2024
    recent_mask = time_means.index.isin(RECENT_YEARS)
    if recent_mask.sum() == 0:
        raise ValueError(
            f"No year effects found for recent years {RECENT_YEARS}. "
            "Check that the panel covers these years."
        )
    recent_time_mean = float(time_means.loc[recent_mask].mean())

    logger.info(
        "Effect decomposition: grand_mean=%.4f, recent_time_mean=%.4f, "
        "gamma_recent_proxy=%.4f",
        grand_mean,
        recent_time_mean,
        recent_time_mean - grand_mean,
    )

    # Get 2024 values of independent variables for each kommun
    df_2024 = panel.loc[
        panel["year"] == 2024,
        ["kommun_kod", "kommun_name", "lan_name"] + X_VARS,
    ].copy()

    if df_2024.empty:
        raise ValueError("No 2024 observations found in panel.")

    betas = main_results.params[X_VARS]

    # Vectorized prediction
    x_contribution = df_2024[X_VARS].values @ betas.values
    entity_component = df_2024["kommun_kod"].map(entity_means).values
    gamma_adjustment = recent_time_mean - grand_mean

    df_2024["predicted_growth_2025"] = (
        entity_component + gamma_adjustment + x_contribution
    )

    result = df_2024[
        ["kommun_kod", "kommun_name", "lan_name", "predicted_growth_2025"]
    ].reset_index(drop=True)

    logger.info(
        "predict_2025: %d municipalities, predicted growth range "
        "[%.2f%%, %.2f%%], mean %.2f%%",
        len(result),
        result["predicted_growth_2025"].min(),
        result["predicted_growth_2025"].max(),
        result["predicted_growth_2025"].mean(),
    )

    return result


def compute_vulnerability(predictions: pd.DataFrame) -> pd.DataFrame:
    """Compute vulnerability score, rank, and risk class from predictions.

    Applies METHODOLOGY §3.2 (z-score, sign-flipped) and §3.3 (quintile
    risk classes).

    .. deprecated::
        This ranking is not supported by the model that produces it — see the
        module docstring for the scored result.  It is retained only until the
        dashboard is cut over to the position and drift measures.  Emits a
        ``DeprecationWarning`` on every call.

    Args:
        predictions: DataFrame with columns kommun_kod, kommun_name,
            lan_name, predicted_growth_2025.

    Returns:
        DataFrame with columns: kommun_kod, kommun_name, lan_name,
        predicted_growth_2025, vulnerability_score, vulnerability_rank,
        risk_class.  Exactly 290 rows.
    """
    warnings.warn(
        "compute_vulnerability is deprecated: the two-way FE model is a "
        "within-time inference panel, not a ranking engine, and this ranking "
        "scored r=+0.016 against realised 2025 growth (naive benchmark wins by "
        "55 %). Retained only until the dashboard reads position and drift "
        "instead. See REMEDIATION_PLAN.md T2.4.",
        DeprecationWarning,
        stacklevel=2,
    )

    df = predictions.copy()

    # §3.2: vulnerability_score = -1 * z-score of predicted growth
    mu = df["predicted_growth_2025"].mean()
    sigma = df["predicted_growth_2025"].std(ddof=0)
    if sigma == 0:
        logger.warning(
            "Zero standard deviation in predictions; all vulnerability "
            "scores will be 0."
        )
        df["vulnerability_score"] = 0.0
    else:
        df["vulnerability_score"] = -1.0 * (df["predicted_growth_2025"] - mu) / sigma

    # §3.3: Risk class via quintiles on predicted_growth_2025
    # Bottom 20% → "hog" (high risk), middle 60% → "medel", top 20% → "lag"
    df["risk_class"] = pd.qcut(
        df["predicted_growth_2025"],
        q=[0, 0.2, 0.8, 1.0],
        labels=["hog", "medel", "lag"],
    )
    df["risk_class"] = pd.Categorical(
        df["risk_class"],
        categories=["lag", "medel", "hog"],
        ordered=True,
    )

    # Vulnerability rank: 1 = most vulnerable (lowest predicted growth)
    df["vulnerability_rank"] = (
        df["predicted_growth_2025"]
        .rank(ascending=True, method="min")
        .astype(int)
    )

    # Log risk class distribution
    counts = df["risk_class"].value_counts()
    logger.info(
        "Risk class distribution: hog=%d, medel=%d, lag=%d",
        counts.get("hog", 0),
        counts.get("medel", 0),
        counts.get("lag", 0),
    )

    return df[
        [
            "kommun_kod",
            "kommun_name",
            "lan_name",
            "predicted_growth_2025",
            "vulnerability_score",
            "vulnerability_rank",
            "risk_class",
        ]
    ].reset_index(drop=True)


def run_prediction() -> None:
    """Orchestrate the full prediction pipeline.

    Loads model artifacts and panel, generates 2025 predictions, computes
    vulnerability scores and rankings, validates output, and saves to
    artifacts/predictions.parquet and artifacts/ranking.parquet.
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

    # Predict
    logger.info("=== Generating 2025 predictions ===")
    predictions = predict_2025(main_results, panel)

    # Compute vulnerability
    logger.info("=== Computing vulnerability scores ===")
    vuln = compute_vulnerability(predictions)

    # Validate
    _validate_output(vuln, panel)

    # Save predictions
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    pred_path = ARTIFACTS_DIR / "predictions.parquet"
    vuln.to_parquet(pred_path, index=False)
    logger.info("Saved predictions -> %s (%d rows)", pred_path, len(vuln))

    # Save ranking (sorted by vulnerability_rank ascending)
    ranking = vuln.sort_values("vulnerability_rank").reset_index(drop=True)
    rank_path = ARTIFACTS_DIR / "ranking.parquet"
    ranking.to_parquet(rank_path, index=False)
    logger.info("Saved ranking -> %s (%d rows)", rank_path, len(ranking))

    logger.info("Prediction complete.")


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _validate_output(vuln: pd.DataFrame, panel: pd.DataFrame) -> None:
    """Validate prediction output against TASKS.md acceptance criteria.

    Args:
        vuln: Vulnerability DataFrame from compute_vulnerability.
        panel: Full panel DataFrame (for mean growth comparison).

    Raises:
        ValueError: If any hard validation fails.
    """
    # Exactly 290 rows
    if len(vuln) != 290:
        raise ValueError(
            f"Expected 290 rows in predictions, got {len(vuln)}."
        )

    # Risk class counts: 58 hog, 174 medel, 58 lag (allow ±2 for ties)
    counts = vuln["risk_class"].value_counts()
    for cls, expected in [("hog", 58), ("medel", 174), ("lag", 58)]:
        actual = counts.get(cls, 0)
        if abs(actual - expected) > 2:
            raise ValueError(
                f"Risk class '{cls}' has {actual} kommuner; "
                f"expected {expected} (±2)."
            )

    # Mean predicted growth within 1 pp of historical mean
    historical_mean = panel["tax_base_growth_pct"].mean()
    predicted_mean = vuln["predicted_growth_2025"].mean()
    diff = abs(predicted_mean - historical_mean)
    logger.info(
        "Validation: predicted mean=%.2f%%, historical mean=%.2f%%, "
        "diff=%.2f pp",
        predicted_mean,
        historical_mean,
        diff,
    )
    if diff > 1.0:
        logger.warning(
            "Predicted mean (%.2f%%) differs from historical mean (%.2f%%) "
            "by %.2f pp (>1.0 pp threshold). This is a diagnostic warning, "
            "not a blocking error.",
            predicted_mean,
            historical_mean,
            diff,
        )

    logger.info("All prediction validations passed.")


if __name__ == "__main__":
    run_prediction()
