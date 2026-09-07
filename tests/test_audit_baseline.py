"""Regression tests locking the 2026-09-04 audit baseline.

These tests recompute the audit's headline findings from the committed
artifacts and assert they still hold.  Their purpose is to make the
before/after comparison of the model-layer remediation automatic: when
REMEDIATION_PLAN.md Phase 2 replaces the specification, the claim that the
new model is *better* rather than merely *different* is checked here rather
than re-derived by hand.

The fixture stores realised 2025 skattekraft growth per municipality so the
backtest is reproducible offline; no test in this module touches the network.

Audit report: https://claude.ai/code/artifact/b3dfec90-7359-45fa-91d8-ea137080eb42
Plan: docs/REMEDIATION_PLAN.md sections 1.2 and 4 (T0.3)

Regenerate the fixture with: python scripts/freeze_audit_baseline.py

Marked ``baseline`` so the suite can be excluded once the pre-remediation
model is retired:  pytest -m "not baseline"
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

pytestmark = pytest.mark.baseline

_ROOT = Path(__file__).resolve().parents[1]
_ARTIFACTS_DIR = _ROOT / "artifacts"
_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "audit_baseline_2026-09-04.json"

X_VARS = ["unemployment_rate", "dependency_ratio", "population_growth_pct", "edu_share"]

# Tolerance for recomputed floating-point statistics.
_TOL = 1e-3


@pytest.fixture(scope="module")
def baseline() -> dict:
    """Recorded audit findings."""
    if not _FIXTURE_PATH.exists():
        pytest.fail(
            f"Baseline fixture missing: {_FIXTURE_PATH}. "
            "Regenerate with: python scripts/freeze_audit_baseline.py"
        )
    return json.loads(_FIXTURE_PATH.read_text())


@pytest.fixture(scope="module")
def predictions() -> pd.DataFrame:
    return pd.read_parquet(_ARTIFACTS_DIR / "predictions.parquet")


@pytest.fixture(scope="module")
def coefficients() -> pd.DataFrame:
    return pd.read_parquet(_ARTIFACTS_DIR / "coefficients.parquet")


@pytest.fixture(scope="module")
def actual_2025(baseline) -> pd.Series:
    """Realised 2025 growth per municipality, recorded from SCB OE0101."""
    return pd.Series(baseline["actual_growth_2025"], name="actual_growth_2025")


class TestFixtureIntegrity:
    """The fixture itself must stay well-formed and attributable."""

    def test_provenance_recorded(self, baseline):
        for key in ("audit_date", "source_commit", "audit_url", "scb_table"):
            assert baseline.get(key), f"Fixture missing provenance key: {key}"

    def test_covers_all_municipalities(self, actual_2025):
        assert len(actual_2025) == 290, f"Expected 290 kommuner, got {len(actual_2025)}"


class TestCoefficients:
    """METHODOLOGY 6.4 — the four main-specification coefficients."""

    def test_main_spec_coefficients_unchanged(self, coefficients, baseline):
        main = coefficients[coefficients["spec"] == "main"].set_index("variable")
        for var, recorded in baseline["coefficients_main"].items():
            assert var in main.index, f"Variable {var} absent from main spec"
            assert main.loc[var, "coefficient"] == pytest.approx(
                recorded["coefficient"], abs=_TOL
            ), f"{var} coefficient drifted from audit baseline"
            assert main.loc[var, "p_value"] == pytest.approx(
                recorded["p_value"], abs=_TOL
            ), f"{var} p-value drifted from audit baseline"

    def test_education_remains_insignificant(self, coefficients):
        """Audit finding F5 — edu_share drives 25% of the ranking at p = 0.52."""
        main = coefficients[coefficients["spec"] == "main"].set_index("variable")
        assert main.loc["edu_share", "p_value"] > 0.05

    def test_population_growth_sign_is_negative(self, coefficients):
        """METHODOLOGY 7.11 — sign reversal after two-way demeaning."""
        main = coefficients[coefficients["spec"] == "main"].set_index("variable")
        assert main.loc["population_growth_pct", "coefficient"] < 0


class TestVulnerabilityScore:
    """Audit section on what actually drives the published ranking."""

    def test_score_is_standardised(self, predictions):
        assert predictions["vulnerability_score"].mean() == pytest.approx(0.0, abs=_TOL)
        assert predictions["vulnerability_score"].std(ddof=0) == pytest.approx(
            1.0, abs=_TOL
        )

    def test_risk_class_counts(self, predictions, baseline):
        counts = predictions["risk_class"].value_counts()
        for cls, expected in baseline["risk_class_counts"].items():
            assert counts.get(cls, 0) == expected

    def test_variance_decomposition_unchanged(self, predictions, baseline):
        """Recorded shares must still sum to 100% and match the audit.

        Recomputing the decomposition requires unpickling the fitted model,
        which needs linearmodels.  The shares are asserted from the record;
        the sum identity is the check that the record is internally coherent.
        """
        shares = baseline["prediction_variance_shares_pct"]
        assert sum(shares.values()) == pytest.approx(100.0, abs=0.1)
        assert shares["dependency_ratio"] == pytest.approx(59.1, abs=0.5)
        assert shares["edu_share"] == pytest.approx(25.1, abs=0.5)
        assert shares["entity_fixed_effects"] == pytest.approx(8.8, abs=0.5)

    def test_entity_effects_do_not_dominate(self, baseline):
        """Entity effects contribute 8.8 % of prediction variance, not most.

        This was written to encode the audit's contradiction of METHODOLOGY
        7.10, and T4.1 expected to delete it once that claim was corrected.
        The claim is corrected now, and the test is kept rather than deleted:
        the figure it locks is still true, still surprising, and is quoted in
        the corrected 7.10. Deleting it would remove the only automatic check
        on a number the documentation now asserts.
        """
        shares = baseline["prediction_variance_shares_pct"]
        structural = sum(v for k, v in shares.items() if k != "entity_fixed_effects")
        assert shares["entity_fixed_effects"] < structural


class TestBacktest2025:
    """The audit's central finding, recomputed offline from the fixture."""

    @staticmethod
    def _merged(predictions: pd.DataFrame, actual: pd.Series) -> pd.DataFrame:
        df = predictions.set_index("kommun_kod").join(actual, how="inner")
        assert len(df) == 290, f"Join lost rows: {len(df)}"
        return df

    def test_forecast_has_no_predictive_correlation(
        self, predictions, actual_2025, baseline
    ):
        df = self._merged(predictions, actual_2025)
        r = df["predicted_growth_2025"].corr(df["actual_growth_2025"])
        assert r == pytest.approx(baseline["backtest_2025"]["pearson_r"], abs=_TOL)
        assert abs(r) < 0.10, "Baseline asserts near-zero predictive correlation"

    def test_forecast_loses_to_naive_benchmark(
        self, predictions, actual_2025, baseline
    ):
        df = self._merged(predictions, actual_2025)
        err = df["predicted_growth_2025"] - df["actual_growth_2025"]
        rmse = float(np.sqrt((err**2).mean()))
        naive_err = df["actual_growth_2025"].mean() - df["actual_growth_2025"]
        naive_rmse = float(np.sqrt((naive_err**2).mean()))

        recorded = baseline["backtest_2025"]
        assert rmse == pytest.approx(recorded["rmse"], abs=_TOL)
        assert naive_rmse == pytest.approx(recorded["naive_rmse"], abs=_TOL)
        assert rmse > naive_rmse, "Baseline asserts the model loses to a constant guess"

    def test_risk_classes_do_not_separate_outcomes(self, predictions, actual_2025):
        """'hog' should have the lowest realised growth.  It does not."""
        df = self._merged(predictions, actual_2025)
        means = df.groupby("risk_class", observed=True)["actual_growth_2025"].mean()
        assert means["hog"] > means["medel"], (
            "Baseline asserts the high-risk group did not underperform"
        )

    def test_predicted_dispersion_is_too_narrow(self, predictions, actual_2025):
        df = self._merged(predictions, actual_2025)
        assert df["predicted_growth_2025"].std() < 0.5 * df["actual_growth_2025"].std()


class TestVulnerabilityScoreIsBackwardLooking:
    """The audit's sharpest finding: the score describes the past, not the future.

    Added 2026-09-07. These two figures sat in REMEDIATION_PLAN.md §1.2
    unverified until artifacts/position.parquet made drift computable; both
    then reproduced to four decimal places (-0.6530 and -0.1652 against the
    audit's -0.653 and -0.165).

    They live here rather than in test_position.py because they depend on the
    pre-remediation vulnerability score, which Phase 2 retires.
    """

    @staticmethod
    def _scored_with_drift() -> pd.DataFrame:
        ranking = pd.read_parquet(_ARTIFACTS_DIR / "ranking.parquet")
        position = pd.read_parquet(_ARTIFACTS_DIR / "position.parquet")

        past = position.loc[position.year == 2024, ["kommun_kod", "drift_5y"]]
        pivot = position.pivot_table(
            index="kommun_kod", columns="year", values="relative_position"
        )
        future = (pivot[2026] - pivot[2024]).rename("future_drift_2y").reset_index()

        return (
            ranking[["kommun_kod", "vulnerability_score"]]
            .merge(past, on="kommun_kod")
            .merge(future, on="kommun_kod")
        )

    def test_score_tracks_past_drift_strongly(self):
        """Audit: -0.653. It is a descriptor of where a kommun has already been."""
        df = self._scored_with_drift()
        r = df["vulnerability_score"].corr(df["drift_5y"])
        assert r == pytest.approx(-0.653, abs=0.02)

    def test_score_tracks_future_drift_weakly(self):
        """Audit: -0.165. Yet it is presented to users as forward-looking."""
        df = self._scored_with_drift()
        r = df["vulnerability_score"].corr(df["future_drift_2y"])
        assert r == pytest.approx(-0.165, abs=0.02)

    def test_backward_association_dominates_forward(self):
        """The comparison is the finding, not either number alone."""
        df = self._scored_with_drift()
        past = abs(df["vulnerability_score"].corr(df["drift_5y"]))
        future = abs(df["vulnerability_score"].corr(df["future_drift_2y"]))
        assert past > 3 * future, (
            f"Baseline asserts the score is backward-looking: |past| {past:.3f} "
            f"vs |future| {future:.3f}"
        )
