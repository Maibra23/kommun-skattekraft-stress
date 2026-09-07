"""Tests for src.model.forecast — the five-year drift forecaster.

The forecaster this replaces predicted one-year growth and scored r = 0.016.
The tests here are mostly about the things that let that happen: shipping a
forecast nobody scored, and quoting intervals narrower than the errors.
"""

import numpy as np
import pandas as pd
import pytest

from src.model.forecast import (
    HORIZON,
    MIN_SPEARMAN,
    NOMINAL_COVERAGE,
    ForecastRejected,
    build_forecast,
    empirical_interval,
    fit_drift_model,
)


def _panel(n: int = 120, years: range = range(2005, 2027), noise: float = 0.6) -> pd.DataFrame:
    """A panel where drift genuinely depends on education five years earlier."""
    rng = np.random.default_rng(7)
    edu = {f"{i:04d}": rng.uniform(10, 45) for i in range(n)}
    rows = []
    for kod, e in edu.items():
        for year in years:
            rows.append(
                {
                    "kommun_kod": kod,
                    "year": year,
                    "edu_share": e + rng.normal(0, 0.2),
                    "unemployment_rate": rng.uniform(3, 14),
                    "dependency_ratio": rng.uniform(0.6, 1.2),
                    "population_growth_pct": rng.normal(0, 1),
                    # Drift over the previous five years responds to the
                    # education level five years back, plus noise.
                    "drift_5y": 0.12 * (e - 27) + rng.normal(0, noise),
                    "relative_position": 100 + 0.5 * (e - 27),
                }
            )
    return pd.DataFrame(rows)


class TestFitDriftModel:
    def test_recovers_a_positive_education_coefficient(self):
        model = fit_drift_model(_panel(), origin=2020)
        assert model.coefficients["edu_share"] > 0

    def test_pairs_features_with_drift_five_years_later(self):
        """The plan's specification: fit drift over [T-5, T] on the structural
        variables as they stood at T-5."""
        model = fit_drift_model(_panel(), origin=2020)
        assert model.horizon == HORIZON
        assert model.n_obs > 0

    def test_never_trains_on_years_after_its_origin(self):
        model = fit_drift_model(_panel(), origin=2015)
        assert model.max_training_year <= 2015

    def test_raises_when_there_is_not_enough_history(self):
        with pytest.raises(ValueError, match="history"):
            fit_drift_model(_panel(years=range(2020, 2024)), origin=2021)


class TestEmpiricalInterval:
    def test_interval_comes_from_the_error_quantiles(self):
        errors = pd.Series(np.linspace(-4, 4, 1001))
        low, high = empirical_interval(errors, coverage=0.80)
        assert low == pytest.approx(-3.2, abs=0.1)
        assert high == pytest.approx(3.2, abs=0.1)

    def test_wider_coverage_gives_a_wider_interval(self):
        errors = pd.Series(np.random.default_rng(1).normal(0, 2, 5000))
        narrow = empirical_interval(errors, coverage=0.50)
        wide = empirical_interval(errors, coverage=0.95)
        assert (wide[1] - wide[0]) > (narrow[1] - narrow[0])

    def test_is_not_the_nominal_standard_error(self):
        """Skewed errors produce an asymmetric interval. A nominal standard
        error cannot express that at all, which is why the old forecast's
        intervals were three times narrower than its own errors."""
        errors = pd.Series(np.random.default_rng(3).exponential(1.0, 8000) - 0.5)
        low, high = empirical_interval(errors, coverage=0.80)
        wide, narrow = max(abs(low), abs(high)), min(abs(low), abs(high))
        assert wide > narrow * 2, "an empirical interval must be able to skew"


class TestBuildForecast:
    def test_produces_one_row_per_kommun_with_an_interval(self):
        result = build_forecast(_panel())
        assert len(result.forecast) == 120
        assert {"kommun_kod", "drift_forecast", "lower", "upper", "horizon"}.issubset(
            result.forecast.columns
        )
        assert (result.forecast["lower"] <= result.forecast["drift_forecast"]).all()
        assert (result.forecast["drift_forecast"] <= result.forecast["upper"]).all()

    def test_the_horizon_is_stated_on_every_row(self):
        result = build_forecast(_panel())
        assert (result.forecast["horizon"] == HORIZON).all()

    def test_the_backtest_travels_with_the_forecast(self):
        """A forecast that can be read without its score is how r = 0.016
        shipped in the first place."""
        result = build_forecast(_panel())
        assert result.backtest.pooled["n"] > 0
        assert result.backtest.benchmarks
        for column in ("backtest_spearman", "backtest_rmse", "backtest_naive_rmse"):
            assert column in result.forecast.columns
            assert result.forecast[column].notna().all()

    def test_intervals_are_calibrated_out_of_sample(self):
        """A nominal 80 % interval must contain about 80 % of realised
        outcomes at an origin whose errors did not set the quantiles."""
        result = build_forecast(_panel())
        assert result.coverage == pytest.approx(NOMINAL_COVERAGE, abs=0.12)


class TestTheGateIsEnforcedInCode:
    """The plan says a forecast that fails the gate is not shipped. That has to
    be enforced by the code, not by the author remembering."""

    def test_refuses_to_build_when_skill_is_below_the_bar(self):
        # Pure noise: nothing to forecast, so Spearman collapses.
        noise_panel = _panel(noise=40.0)
        with pytest.raises(ForecastRejected, match="Spearman"):
            build_forecast(noise_panel)

    def test_the_rejection_names_the_measured_value_and_the_bar(self):
        try:
            build_forecast(_panel(noise=40.0))
        except ForecastRejected as exc:
            assert str(MIN_SPEARMAN) in str(exc)
        else:
            pytest.fail("expected ForecastRejected")

    def test_a_skilful_model_is_allowed_through(self):
        result = build_forecast(_panel())
        assert result.backtest.pooled["spearman_rho"] > MIN_SPEARMAN
