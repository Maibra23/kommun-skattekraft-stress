"""Five-year drift forecast, with intervals earned from its own backtest.

Replaces the one-year growth forecast that scored **r = 0.016** against
realised 2025 outcomes and lost to guessing the national mean by 55 %.

Three things changed, and each of them addresses a specific way the old
forecast failed (METHODOLOGY §13.4):

1. **The target.** One-year growth is not recoverable — year-demeaned
   persistence is about −0.05, which is a property of the data and not of the
   estimator. Five-year drift in relative position is forecastable at
   out-of-sample Spearman ≈ 0.33.
2. **The intervals.** They come from the empirical distribution of the
   backtest's own errors, never from the regression's nominal standard error.
   The old model's predicted SD was 0.33 pp against a realised 0.98 pp — three
   times too narrow — because nominal intervals describe uncertainty about the
   fitted line, not about an unseen kommun five years out.
3. **The gate is code, not a good intention.** ``build_forecast`` refuses to
   return anything when out-of-sample skill falls below ``MIN_SPEARMAN``. The
   plan says a forecast that fails the gate is not shipped; leaving that to a
   reader's discipline is exactly how the last one shipped.

Written after ``src/model/backtest.py``, which it uses, so no forecast here can
exist without a score attached to it.

Writes ``artifacts/forecast.parquet``. This replaced the vulnerability score
outright: ``predictions.parquet`` and its producer were removed on 2026-09-09
once nothing read them (METHODOLOGY §13.4).
"""

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from src.model.backtest import (
    BENCHMARK_MEAN,
    BENCHMARK_PERSISTENCE,
    BacktestResult,
    rolling_origin_backtest,
)
from src.provenance import analysis_year

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_PANEL_PATH: Path = _PROJECT_ROOT / "data" / "processed" / "panel.parquet"
_POSITION_PATH: Path = _PROJECT_ROOT / "artifacts" / "position.parquet"
_OUTPUT_PATH: Path = _PROJECT_ROOT / "artifacts" / "forecast.parquet"

#: Forecast horizon in years. Five, because one is not recoverable and ten
#: leaves too few origins to score against.
HORIZON: int = 5

#: The structural variables, in the same order the cross-section uses.
FEATURES: list[str] = [
    "edu_share",
    "unemployment_rate",
    "dependency_ratio",
    "population_growth_pct",
]

#: The target: movement in relative position over the horizon, in index points.
TARGET: str = f"drift_{HORIZON}y"

#: The plan's gate. Below this the forecast is not shipped at all.
MIN_SPEARMAN: float = 0.25

#: Nominal coverage of the published interval.
NOMINAL_COVERAGE: float = 0.80


class ForecastRejected(RuntimeError):
    """Raised when out-of-sample skill is below the gate.

    Deliberately an exception rather than a warning: the plan's instruction is
    that a forecast failing the gate is not shipped, and an exception is the
    only version of that a caller cannot ignore by accident.
    """


@dataclass
class DriftModel:
    """A fitted linear model of drift on lagged structural variables."""

    intercept: float
    coefficients: dict[str, float]
    horizon: int
    n_obs: int
    max_training_year: int

    def predict(self, features: pd.DataFrame) -> pd.Series:
        """Predict drift for each row of a feature frame."""
        values = np.full(len(features), self.intercept, dtype=float)
        for name, beta in self.coefficients.items():
            values = values + beta * features[name].to_numpy(dtype=float)
        return pd.Series(values, index=features.index)


@dataclass
class ForecastResult:
    """The forecast, the backtest that justifies it, and its calibration."""

    forecast: pd.DataFrame
    backtest: BacktestResult
    coverage: float


def fit_drift_model(
    panel: pd.DataFrame, origin: int, horizon: int = HORIZON
) -> DriftModel:
    """Fit drift over [t-h, t] on the structural variables as they stood at t-h.

    Only years up to and including ``origin`` are used, so a model fitted at an
    origin cannot see past it.

    Args:
        panel: Panel carrying FEATURES and TARGET per kommun-year.
        origin: Latest year the model may learn from.
        horizon: Drift window in years.

    Returns:
        The fitted model.

    Raises:
        ValueError: If no (features at t-h, drift at t) pair exists in range.
    """
    train = panel[panel["year"] <= origin]
    available = set(train["year"].unique())

    pairs: list[pd.DataFrame] = []
    for year in sorted(available):
        if year - horizon not in available:
            continue
        features = train[train["year"] == year - horizon].set_index("kommun_kod")[
            FEATURES
        ]
        target = train[train["year"] == year].set_index("kommun_kod")[TARGET]
        pairs.append(features.join(target.rename("_y"), how="inner").dropna())

    stacked = pd.concat(pairs) if pairs else pd.DataFrame()
    if stacked.empty:
        raise ValueError(
            f"Not enough history to fit at origin {origin}: no year has both "
            f"structural variables at t-{horizon} and {TARGET} at t. The panel "
            f"covers {min(available)}–{max(available)}."
        )

    design = np.column_stack(
        [np.ones(len(stacked))] + [stacked[c].to_numpy(dtype=float) for c in FEATURES]
    )
    beta, *_ = np.linalg.lstsq(design, stacked["_y"].to_numpy(dtype=float), rcond=None)

    return DriftModel(
        intercept=float(beta[0]),
        coefficients={name: float(b) for name, b in zip(FEATURES, beta[1:])},
        horizon=horizon,
        n_obs=len(stacked),
        max_training_year=int(train["year"].max()),
    )


def empirical_interval(
    errors: pd.Series, coverage: float = NOMINAL_COVERAGE
) -> tuple[float, float]:
    """Return the (low, high) error offsets covering the central share.

    Taken from the realised error distribution, so the interval inherits its
    skew and its fat tails. A nominal standard error would describe uncertainty
    about the fitted line instead — which is why the old forecast's intervals
    were three times narrower than its errors.

    Args:
        errors: Realised prediction errors (prediction minus outcome).
        coverage: Central share to cover, e.g. 0.80.

    Returns:
        (low, high) offsets to add to a point forecast.
    """
    clean = pd.Series(errors).dropna()
    tail = (1.0 - coverage) / 2.0
    # Errors are prediction - outcome, so the interval around a prediction is
    # the prediction minus the upper error quantile, up to minus the lower one.
    return (
        float(-clean.quantile(1.0 - tail)),
        float(-clean.quantile(tail)),
    )


def _features_at(panel: pd.DataFrame, year: int) -> pd.DataFrame:
    return panel[panel["year"] == year].set_index("kommun_kod")[FEATURES].dropna()


def _drift_at(panel: pd.DataFrame, year: int) -> pd.Series:
    return panel[panel["year"] == year].set_index("kommun_kod")[TARGET]


def build_forecast(
    panel: pd.DataFrame,
    horizon: int = HORIZON,
    coverage: float = NOMINAL_COVERAGE,
) -> ForecastResult:
    """Backtest the drift model, then forecast forward only if it earned it.

    Args:
        panel: Panel carrying FEATURES and TARGET per kommun-year.
        horizon: Forecast horizon in years.
        coverage: Nominal coverage of the published interval.

    Returns:
        The forecast, its backtest, and the interval's out-of-sample coverage.

    Raises:
        ForecastRejected: If pooled out-of-sample Spearman is at or below
            MIN_SPEARMAN. The forecast is then not produced at all.
    """
    # This estimator needs `horizon` years of history before it can form its
    # first (features at t-h, drift at t) training pair, and another `horizon`
    # years after the origin to be scored. The harness cannot know that, so the
    # usable origins are named here rather than left to its default.
    years = sorted(int(y) for y in panel["year"].dropna().unique())
    origins = [
        y
        for y in years
        if y >= min(years) + horizon and y + horizon in set(years)
    ]

    backtest = rolling_origin_backtest(
        panel=panel,
        horizon=horizon,
        estimator=lambda train: fit_drift_model(
            train, origin=int(train["year"].max()), horizon=horizon
        ).predict,
        feature_fn=_features_at,
        outcome_fn=_drift_at,
        origins=origins,
    )

    rho = backtest.pooled["spearman_rho"]
    if not (rho > MIN_SPEARMAN):
        raise ForecastRejected(
            f"Out-of-sample Spearman is {rho:.4f}, which does not clear the "
            f"{MIN_SPEARMAN} gate, so no forecast is produced. This is an "
            "acceptable outcome, not a failure: the dashboard is complete "
            "without a forward-looking number. See METHODOLOGY §13.4.\n"
            + backtest.summary()
        )

    scored = backtest.predictions.dropna(subset=["y_true", "y_pred"])
    errors = scored["y_pred"] - scored["y_true"]
    low_offset, high_offset = empirical_interval(errors, coverage)

    coverage_measured = _out_of_sample_coverage(scored, coverage)

    origin = int(panel["year"].max())
    model = fit_drift_model(panel, origin=origin, horizon=horizon)
    features = _features_at(panel, origin)
    if features.empty:
        # The newest year often has no structural variables; fall back to the
        # latest year that does, and say so on every row.
        origin = int(analysis_year())
        features = _features_at(panel, origin)
    point = model.predict(features)

    forecast = pd.DataFrame(
        {
            "kommun_kod": features.index,
            "origin_year": origin,
            "horizon": horizon,
            "target_year": origin + horizon,
            "drift_forecast": point.to_numpy(),
            "lower": (point + low_offset).to_numpy(),
            "upper": (point + high_offset).to_numpy(),
            "interval_coverage": coverage,
            # The score travels with the forecast so it cannot be read without
            # it.  A forecast nobody scored is how r = 0.016 shipped.
            "backtest_spearman": backtest.pooled["spearman_rho"],
            "backtest_pearson": backtest.pooled["pearson_r"],
            "backtest_rmse": backtest.pooled["rmse"],
            "backtest_naive_rmse": backtest.benchmarks[BENCHMARK_MEAN]["rmse"],
            "backtest_persistence_rmse": backtest.benchmarks[BENCHMARK_PERSISTENCE][
                "rmse"
            ],
            "backtest_origins": len(backtest.origins),
            "backtest_n": int(backtest.pooled["n"]),
            "interval_coverage_measured": coverage_measured,
        }
    ).reset_index(drop=True)

    return ForecastResult(
        forecast=forecast, backtest=backtest, coverage=coverage_measured
    )


def _out_of_sample_coverage(scored: pd.DataFrame, coverage: float) -> float:
    """Coverage of the last origin, using intervals set by earlier origins only.

    Calibrating and testing on the same errors would report the nominal figure
    by construction and prove nothing.

    Args:
        scored: Backtest predictions with y_true and y_pred.
        coverage: Nominal coverage.

    Returns:
        The realised share of outcomes inside the interval, or NaN when there
        is only one origin to work with.
    """
    origins = sorted(scored["origin"].unique())
    if len(origins) < 2:
        return float("nan")

    held_out = origins[-1]
    calibration = scored[scored["origin"] < held_out]
    low_offset, high_offset = empirical_interval(
        calibration["y_pred"] - calibration["y_true"], coverage
    )

    test = scored[scored["origin"] == held_out]
    inside = (test["y_true"] >= test["y_pred"] + low_offset) & (
        test["y_true"] <= test["y_pred"] + high_offset
    )
    return float(inside.mean())


def run_forecast() -> pd.DataFrame:
    """Build the forecast from committed data and write the artifact.

    Returns:
        The written forecast frame.

    Raises:
        ForecastRejected: If the gate fails; nothing is written.
    """
    panel = pd.read_parquet(_PANEL_PATH)
    position = pd.read_parquet(_POSITION_PATH)[
        ["kommun_kod", "year", "relative_position", TARGET]
    ]
    merged = panel.merge(position, on=["kommun_kod", "year"], how="left")

    result = build_forecast(merged)

    _OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    result.forecast.to_parquet(_OUTPUT_PATH, index=False)
    logger.info(
        "Forecast written to %s (%d kommuner, %d-year horizon, origin %d)",
        _OUTPUT_PATH,
        len(result.forecast),
        HORIZON,
        int(result.forecast["origin_year"].iloc[0]),
    )
    logger.info("%s", result.backtest.summary())
    logger.info(
        "Interval: nominal %.0f %%, measured out-of-sample %.0f %%",
        NOMINAL_COVERAGE * 100,
        result.coverage * 100,
    )
    return result.forecast


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s"
    )
    run_forecast()
