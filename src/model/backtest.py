"""Rolling-origin backtesting: score a forecast before shipping it.

This module exists because of the single most damaging finding in the
2026-09-04 audit. The project shipped a 2025 growth forecast that had never
been tested against realised outcomes; when it finally was, it correlated with
them at **r = 0.016** and lost to guessing the national mean by 55 %. Nothing
in the codebase would have said so, because nothing scored it.

Built **before** the forecaster it exists to test (REMEDIATION_PLAN.md T3.1),
which is the ordering that makes that failure structurally hard to repeat.

How it works
------------
For every origin year *T* where an outcome at *T + h* exists:

1. the estimator is fitted on the panel truncated to ``year <= T``,
2. it predicts from features observed **at** *T*,
3. the prediction is scored against the realised outcome at *T + h*.

The truncation is the whole point, and is asserted by the tests: a harness that
lets the estimator see past its origin reports whatever the author hoped for.

Benchmarks are mandatory
------------------------
Every report carries two, because a metric alone says nothing:

* ``naive_mean`` — predict the cross-sectional mean of the training outcomes.
  This is the plan's required benchmark. Note it has no correlation with
  anything by construction, so only its error metrics are meaningful.
* ``persistence`` — predict that the last *h* years repeat. For a **drift**
  target the constant-mean benchmark is nearly vacuous, since drift averages
  near zero; persistence is the one that bites. Measured on this project's own
  data, "assume the drift continues" scores Spearman ≈ 0.15 over five years,
  which is the number a drift forecaster actually has to beat.
"""

import logging
from dataclasses import dataclass, field
from typing import Callable

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

#: Predict the mean of the training outcomes for every kommun.
BENCHMARK_MEAN = "naive_mean"
#: Predict that the previous h years' change repeats over the next h.
BENCHMARK_PERSISTENCE = "persistence"

#: Signature of a fitted estimator: features at the origin -> predictions.
PredictFn = Callable[[pd.DataFrame], pd.Series]
#: Signature of an estimator factory: training panel -> fitted estimator.
EstimatorFn = Callable[[pd.DataFrame], PredictFn]
#: Features observed at one year, indexed by kommun_kod.
FeatureFn = Callable[[pd.DataFrame, int], pd.DataFrame]
#: The realised outcome for one year, indexed by kommun_kod.
OutcomeFn = Callable[[pd.DataFrame, int], pd.Series]


@dataclass
class BacktestResult:
    """Everything a reader needs to judge a forecast, benchmarks included.

    Attributes:
        horizon: Forecast horizon in years.
        origins: Origin years actually scored.
        predictions: One row per (kommun, origin) with y_true and y_pred.
        per_origin: Metrics for each origin separately.
        pooled: Metrics over every prediction stacked together.
        benchmarks: Pooled metrics for each mandatory benchmark.
    """

    horizon: int
    origins: list[int]
    predictions: pd.DataFrame
    per_origin: pd.DataFrame
    pooled: dict
    benchmarks: dict = field(default_factory=dict)

    def beats(self, benchmark: str, metric: str = "rmse") -> bool:
        """Whether the model beats a benchmark on an error metric.

        Args:
            benchmark: One of the BENCHMARK_* names.
            metric: An error metric where lower is better.

        Returns:
            True when the model's value is lower than the benchmark's.
        """
        return float(self.pooled[metric]) < float(self.benchmarks[benchmark][metric])

    def summary(self) -> str:
        """Return a plain-text report. Benchmarks are never omitted."""
        lines = [
            f"Rolling-origin backtest, horizon {self.horizon}y, "
            f"origins {min(self.origins)}–{max(self.origins)} "
            f"({len(self.origins)} of them), N={int(self.pooled['n'])}",
            f"  model        RMSE {self.pooled['rmse']:.3f}  "
            f"bias {self.pooled['bias']:+.3f}  "
            f"r {self.pooled['pearson_r']:+.3f}  "
            f"rho {self.pooled['spearman_rho']:+.3f}",
        ]
        for name, metrics in self.benchmarks.items():
            lines.append(
                f"  {name:<12} RMSE {metrics['rmse']:.3f}  "
                f"bias {metrics['bias']:+.3f}  "
                f"r {metrics['pearson_r']:+.3f}  "
                f"rho {metrics['spearman_rho']:+.3f}"
            )
        return "\n".join(lines)


def score_predictions(y_true: pd.Series, y_pred: pd.Series) -> dict:
    """Score one set of predictions against realised outcomes.

    Pairs where either side is missing are dropped, so every metric describes
    the same sample.

    Args:
        y_true: Realised outcomes.
        y_pred: Predicted outcomes, aligned to y_true.

    Returns:
        Dict with n, pearson_r, spearman_rho, rmse and bias. The two
        correlations are NaN rather than 0.0 when either side is constant:
        a constant prediction has no correlation with anything, and reporting
        0.0 would read as "measured and found useless" rather than "not
        applicable". The naive-mean benchmark is exactly that case.
    """
    frame = pd.DataFrame({"y": pd.Series(y_true), "p": pd.Series(y_pred)}).dropna()
    n = len(frame)
    if n == 0:
        return {
            "n": 0,
            "pearson_r": float("nan"),
            "spearman_rho": float("nan"),
            "rmse": float("nan"),
            "bias": float("nan"),
        }

    error = frame["p"] - frame["y"]
    constant = frame["p"].nunique() <= 1 or frame["y"].nunique() <= 1
    return {
        "n": n,
        "pearson_r": float("nan") if constant else float(frame["y"].corr(frame["p"])),
        "spearman_rho": (
            float("nan")
            if constant
            else float(frame["y"].corr(frame["p"], method="spearman"))
        ),
        "rmse": float(np.sqrt((error**2).mean())),
        "bias": float(error.mean()),
    }


def rolling_origin_backtest(
    panel: pd.DataFrame,
    horizon: int,
    estimator: EstimatorFn,
    feature_fn: FeatureFn,
    outcome_fn: OutcomeFn,
    origins: list[int] | None = None,
    year_column: str = "year",
) -> BacktestResult:
    """Fit at every origin, predict h years ahead, and score against reality.

    Args:
        panel: Long panel carrying at least kommun_kod and the year column.
        horizon: Years ahead to forecast.
        estimator: Called with the panel truncated to ``year <= origin``;
            returns a callable that maps features to predictions.
        feature_fn: ``(panel, year) -> DataFrame`` of features observed at
            that year, indexed by kommun_kod.
        outcome_fn: ``(panel, year) -> Series`` of realised outcomes for that
            year, indexed by kommun_kod.
        origins: Origin years to use. Defaults to every year that has both a
            training window and a realised outcome at origin + horizon.
        year_column: Name of the year column.

    Returns:
        A BacktestResult, always including both mandatory benchmarks.

    Raises:
        ValueError: If no origin has a realised outcome at origin + horizon.
    """
    years = sorted(int(y) for y in panel[year_column].dropna().unique())
    if origins is None:
        # An origin needs at least one earlier year to train on and a realised
        # outcome h years later to be scored against.
        origins = [y for y in years if y > min(years) and y + horizon in set(years)]
    origins = sorted(int(o) for o in origins)

    if not origins:
        raise ValueError(
            f"No usable origin for horizon {horizon}: the panel covers "
            f"{min(years)}–{max(years)}, so no year has a realised outcome "
            f"{horizon} years later. Use a shorter horizon."
        )

    rows: list[pd.DataFrame] = []
    for origin in origins:
        train = panel[panel[year_column] <= origin]
        predict = estimator(train)

        features = feature_fn(panel, origin)
        truth = outcome_fn(panel, origin + horizon)
        prediction = pd.Series(predict(features))

        index = features.index.intersection(truth.index)
        frame = pd.DataFrame(
            {
                "kommun_kod": index,
                "origin": origin,
                "y_true": truth.reindex(index).to_numpy(),
                "y_pred": prediction.reindex(index).to_numpy(),
            }
        )
        frame[BENCHMARK_MEAN] = _naive_mean_prediction(
            panel, outcome_fn, origin, horizon, index
        )
        frame[BENCHMARK_PERSISTENCE] = _persistence_prediction(
            panel, outcome_fn, origin, horizon, index
        )
        rows.append(frame)

    predictions = pd.concat(rows, ignore_index=True)

    per_origin = pd.DataFrame(
        [
            {"origin": origin, **score_predictions(chunk["y_true"], chunk["y_pred"])}
            for origin, chunk in predictions.groupby("origin")
        ]
    )

    pooled = score_predictions(predictions["y_true"], predictions["y_pred"])

    # Benchmarks are scored on exactly the pairs the model was scored on, so
    # the comparison is like for like.
    scored = predictions.dropna(subset=["y_true", "y_pred"])
    benchmarks = {
        name: score_predictions(scored["y_true"], scored[name])
        for name in (BENCHMARK_MEAN, BENCHMARK_PERSISTENCE)
    }

    result = BacktestResult(
        horizon=horizon,
        origins=origins,
        predictions=predictions,
        per_origin=per_origin,
        pooled=pooled,
        benchmarks=benchmarks,
    )
    logger.info("%s", result.summary())
    return result


# ---------------------------------------------------------------------------
# Benchmarks
# ---------------------------------------------------------------------------


def _naive_mean_prediction(
    panel: pd.DataFrame,
    outcome_fn: OutcomeFn,
    origin: int,
    horizon: int,
    index: pd.Index,
) -> np.ndarray:
    """Predict the mean of the most recent outcome observable at the origin.

    Uses the outcome for ``origin`` itself — the latest realisation a forecaster
    standing at the origin could have seen — never the outcome being scored.
    """
    try:
        observable = outcome_fn(panel, origin)
    except Exception:  # noqa: BLE001 - a missing year is not an error here
        observable = pd.Series(dtype=float)
    mean = float(pd.Series(observable).mean()) if len(observable) else 0.0
    return np.full(len(index), mean)


def _persistence_prediction(
    panel: pd.DataFrame,
    outcome_fn: OutcomeFn,
    origin: int,
    horizon: int,
    index: pd.Index,
) -> np.ndarray:
    """Predict that each kommun's own most recent outcome repeats.

    For a drift target this is "the last h years' movement continues", which is
    the benchmark a drift forecaster has to beat. The constant-mean benchmark
    is nearly vacuous there, because drift averages near zero.
    """
    try:
        observable = pd.Series(outcome_fn(panel, origin))
    except Exception:  # noqa: BLE001
        return np.full(len(index), np.nan)
    return observable.reindex(index).to_numpy()
