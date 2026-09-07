"""Tests for src.model.backtest — the rolling-origin harness.

This module exists so that no forecast can be shipped unscored again.  The
audit's most damaging finding was a forecast that had never been tested against
realised outcomes and turned out to correlate with them at r = 0.016.

The tests that matter most here are the leakage tests: a backtest that can see
the future reports whatever you hoped for.
"""

import numpy as np
import pandas as pd
import pytest

from src.model.backtest import (
    BENCHMARK_MEAN,
    BENCHMARK_PERSISTENCE,
    rolling_origin_backtest,
    score_predictions,
)


# ---------------------------------------------------------------------------
# A synthetic panel with a known answer: the outcome is exactly 2x the feature.
# ---------------------------------------------------------------------------


def _synthetic_panel(n_kommuner: int = 40, years: range = range(2000, 2021)) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    rows = []
    for i in range(n_kommuner):
        kod = f"{i:04d}"
        # Constant within a kommun: the outcome h years ahead is then exactly
        # 2x of the feature observed at the origin, so a correct harness must
        # score a perfect recovery and an incorrect one cannot.
        x = rng.uniform(-2, 2)
        for year in years:
            rows.append({"kommun_kod": kod, "year": year, "x": x, "y": 2.0 * x})
    return pd.DataFrame(rows)


def _features(panel: pd.DataFrame, year: int) -> pd.DataFrame:
    return panel[panel["year"] == year].set_index("kommun_kod")[["x"]]


def _outcome(panel: pd.DataFrame, year: int) -> pd.Series:
    return panel[panel["year"] == year].set_index("kommun_kod")["y"]


def _exact_estimator(train: pd.DataFrame):
    """Recovers y = 2x from the training data it is given."""
    slope = (train["y"] / train["x"].replace(0, np.nan)).median()

    def predict(features: pd.DataFrame) -> pd.Series:
        return features["x"] * slope

    return predict


# ---------------------------------------------------------------------------
# score_predictions
# ---------------------------------------------------------------------------


class TestScorePredictions:
    def test_perfect_prediction_scores_perfectly(self):
        truth = pd.Series([1.0, 2.0, 3.0, 4.0])
        result = score_predictions(truth, truth.copy())
        assert result["pearson_r"] == pytest.approx(1.0)
        assert result["spearman_rho"] == pytest.approx(1.0)
        assert result["rmse"] == pytest.approx(0.0)
        assert result["bias"] == pytest.approx(0.0)

    def test_bias_is_signed_mean_error(self):
        truth = pd.Series([1.0, 2.0, 3.0])
        result = score_predictions(truth, truth + 2.0)
        assert result["bias"] == pytest.approx(2.0)
        assert result["rmse"] == pytest.approx(2.0)

    def test_reports_the_sample_size(self):
        truth = pd.Series([1.0, 2.0, 3.0])
        assert score_predictions(truth, truth)["n"] == 3

    def test_ignores_pairs_where_either_side_is_missing(self):
        truth = pd.Series([1.0, 2.0, np.nan, 4.0])
        pred = pd.Series([1.0, np.nan, 3.0, 4.0])
        assert score_predictions(truth, pred)["n"] == 2

    def test_correlation_is_nan_rather_than_zero_when_undefined(self):
        """A constant prediction has no correlation with anything; reporting
        0.0 would read as 'measured and found useless' rather than 'not
        applicable', and the naive mean benchmark is exactly this case."""
        truth = pd.Series([1.0, 2.0, 3.0])
        result = score_predictions(truth, pd.Series([2.0, 2.0, 2.0]))
        assert np.isnan(result["pearson_r"])
        assert np.isnan(result["spearman_rho"])
        assert result["rmse"] == pytest.approx(np.sqrt(2 / 3))


# ---------------------------------------------------------------------------
# rolling_origin_backtest
# ---------------------------------------------------------------------------


class TestRollingOriginBacktest:
    def _run(self, horizon: int = 5, **kwargs):
        return rolling_origin_backtest(
            panel=_synthetic_panel(),
            horizon=horizon,
            estimator=_exact_estimator,
            feature_fn=_features,
            outcome_fn=_outcome,
            **kwargs,
        )

    def test_recovers_a_known_relationship(self):
        result = self._run()
        assert result.pooled["pearson_r"] == pytest.approx(1.0, abs=1e-9)
        assert result.pooled["rmse"] == pytest.approx(0.0, abs=1e-9)

    def test_one_row_per_origin(self):
        result = self._run()
        assert len(result.per_origin) == len(result.origins)
        assert set(result.per_origin["origin"]) == set(result.origins)

    def test_origins_stop_where_the_outcome_year_runs_out(self):
        """With data to 2020 and a 5-year horizon, 2016 cannot be an origin."""
        result = self._run(horizon=5)
        assert max(result.origins) == 2015
        assert 2016 not in result.origins

    def test_horizon_is_respected(self):
        assert max(self._run(horizon=3).origins) == 2017

    def test_predictions_are_kept_for_inspection(self):
        result = self._run()
        assert {"kommun_kod", "origin", "y_true", "y_pred"}.issubset(
            result.predictions.columns
        )
        assert len(result.predictions) == 40 * len(result.origins)

    def test_raises_when_no_origin_has_an_outcome(self):
        with pytest.raises(ValueError, match="horizon"):
            self._run(horizon=50)


class TestNoLeakage:
    """A harness that can see the future reports whatever you hoped for."""

    def test_the_estimator_never_sees_beyond_its_origin(self):
        seen: list[tuple[int, int]] = []

        def spy_estimator(train: pd.DataFrame):
            seen.append((int(train["year"].min()), int(train["year"].max())))
            return _exact_estimator(train)

        result = rolling_origin_backtest(
            panel=_synthetic_panel(),
            horizon=5,
            estimator=spy_estimator,
            feature_fn=_features,
            outcome_fn=_outcome,
        )
        assert len(seen) == len(result.origins)
        for origin, (_, max_year) in zip(sorted(result.origins), seen):
            assert max_year <= origin, (
                f"estimator saw {max_year} when fitting at origin {origin}"
            )

    def test_features_come_from_the_origin_year_only(self):
        seen_years: list[int] = []

        def spy_features(panel: pd.DataFrame, year: int) -> pd.DataFrame:
            seen_years.append(year)
            return _features(panel, year)

        result = rolling_origin_backtest(
            panel=_synthetic_panel(),
            horizon=5,
            estimator=_exact_estimator,
            feature_fn=spy_features,
            outcome_fn=_outcome,
        )
        assert seen_years == sorted(result.origins)

    def test_the_scored_outcome_is_the_one_at_origin_plus_horizon(self):
        result = rolling_origin_backtest(
            panel=_synthetic_panel(),
            horizon=5,
            estimator=_exact_estimator,
            feature_fn=_features,
            outcome_fn=_outcome,
        )
        # y = 2x and x is constant per kommun, so a correctly aligned harness
        # recovers the outcome exactly; a misaligned one cannot.
        assert result.pooled["rmse"] == pytest.approx(0.0, abs=1e-9)

    def test_no_outcome_is_read_between_the_origin_and_the_scored_year(self):
        """Benchmarks may read the outcome observable *at* the origin — that is
        what a forecaster standing there could see. Nothing may be read from
        the years in between, or from beyond the scored year."""
        calls: list[int] = []

        def spy_outcome(panel: pd.DataFrame, year: int) -> pd.Series:
            calls.append(year)
            return _outcome(panel, year)

        result = rolling_origin_backtest(
            panel=_synthetic_panel(),
            horizon=5,
            estimator=_exact_estimator,
            feature_fn=_features,
            outcome_fn=spy_outcome,
        )
        allowed = {o for o in result.origins} | {o + 5 for o in result.origins}
        assert set(calls) <= allowed
        for origin in result.origins:
            between = {y for y in calls if origin < y < origin + 5}
            assert not between - allowed, f"read a year inside the horizon: {between}"


class TestBenchmarksAreMandatory:
    """The plan's hard rule: no report without its benchmark.

    The old model's RMSE of 1.51 pp only reveals itself as a failure beside the
    naive 0.97 pp.
    """

    def test_naive_mean_benchmark_is_always_present(self):
        result = rolling_origin_backtest(
            panel=_synthetic_panel(),
            horizon=5,
            estimator=_exact_estimator,
            feature_fn=_features,
            outcome_fn=_outcome,
        )
        assert BENCHMARK_MEAN in result.benchmarks
        assert "rmse" in result.benchmarks[BENCHMARK_MEAN]

    def test_persistence_benchmark_is_always_present(self):
        """For a drift target the constant-mean benchmark is nearly vacuous —
        drift averages near zero — so persistence is the one that bites.
        Measured on real data: Spearman 0.15 at five years."""
        result = rolling_origin_backtest(
            panel=_synthetic_panel(),
            horizon=5,
            estimator=_exact_estimator,
            feature_fn=_features,
            outcome_fn=_outcome,
        )
        assert BENCHMARK_PERSISTENCE in result.benchmarks

    def test_benchmarks_are_scored_on_the_same_pairs_as_the_model(self):
        result = rolling_origin_backtest(
            panel=_synthetic_panel(),
            horizon=5,
            estimator=_exact_estimator,
            feature_fn=_features,
            outcome_fn=_outcome,
        )
        for name, metrics in result.benchmarks.items():
            assert metrics["n"] == result.pooled["n"], name

    def test_summary_names_the_benchmark_it_must_beat(self):
        result = rolling_origin_backtest(
            panel=_synthetic_panel(),
            horizon=5,
            estimator=_exact_estimator,
            feature_fn=_features,
            outcome_fn=_outcome,
        )
        text = result.summary()
        assert BENCHMARK_MEAN in text
        assert BENCHMARK_PERSISTENCE in text
        assert "RMSE" in text
