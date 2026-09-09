"""Unit tests for the cross-sectional estimator.

Covers METHODOLOGY §13.4 — the fix at the centre of the remediation.

The two-way FE model estimates within-kommun variation; the product is a
between-kommun ranking, and 98.3 % of the variation in relative position is
between kommuner. This module drops entity effects so that variation is
estimated rather than deleted.

Two things these tests must lock, beyond the fit itself:

  * **No entity effects, ever.** Reintroducing them recreates the exact
    mismatch this module exists to remove, and would do so silently — the
    artifact would still be written and the R2 would still look plausible.
  * **The identification finding.** Only edu_share and unemployment_rate are
    separately identified; dependency_ratio and population_growth_pct have
    confidence intervals spanning zero in every year and add ~0.001 each to
    R2. That is a *finding*, not a defect, so it is regression-tested in both
    directions: someone is told if it ever changes.

Per the plan's revised DoD, the suite deliberately does NOT assert the signs
of all four coefficients — doing so would lock noise into the suite for two
of them.

No test touches the network.
"""

import numpy as np
import pandas as pd
import pytest

from src.model import estimate_cross as ec

_IDENTIFIED = ["edu_share", "unemployment_rate"]
_UNIDENTIFIED = ["dependency_ratio", "population_growth_pct"]
_EXPECTED_SIGN = {"edu_share": 1.0, "unemployment_rate": -1.0}


@pytest.fixture(scope="module")
def panel() -> pd.DataFrame:
    return pd.read_parquet(ec._PANEL_PATH)


@pytest.fixture(scope="module")
def coefs(panel) -> pd.DataFrame:
    return ec.build_coefficient_table(panel)


def _synthetic() -> pd.DataFrame:
    """A cross-section with an exactly known OLS solution.

    y = 100 + 2*edu_share exactly. The other three regressors vary
    independently (seeded, so the fixture stays deterministic per the
    project's reproducibility rule) rather than on a shared linspace, which
    would make the design matrix singular. Because the relationship is exact,
    OLS recovers beta_edu = 2.0, zero on the rest, and R2 = 1.
    """
    n = 40
    rng = np.random.default_rng(20260907)
    edu = np.linspace(10.0, 50.0, n)
    return pd.DataFrame(
        {
            "kommun_kod": [f"{i:04d}" for i in range(n)],
            "year": 2024,
            "tax_base_index_riket": 100.0 + 2.0 * edu,
            "edu_share": edu,
            "unemployment_rate": rng.uniform(3.0, 9.0, n),
            "dependency_ratio": rng.uniform(0.5, 0.9, n),
            "population_growth_pct": rng.uniform(-1.0, 1.0, n),
        }
    )


class TestSpecification:
    """The design must stay cross-sectional. This is the module's whole point."""

    def test_target_is_relative_position_not_growth(self):
        assert ec.Y_VAR == "tax_base_index_riket"

    def test_pooled_spec_has_year_effects_but_no_entity_effects(self, panel):
        results = ec.fit_pooled(panel)
        params = set(results.params.index)
        n_years = len(ec.ESTIMATION_YEARS)
        # const + 4 regressors + (n_years - 1) year dummies, and nothing else.
        assert len(params) == 1 + len(ec.X_VARS) + (n_years - 1)
        assert not any("kommun" in str(p) for p in params)

    def test_single_year_spec_uses_hc3_robust_errors(self, panel):
        results = ec.fit_year(panel, ec.LATEST_YEAR)
        assert results.cov_type == "HC3"


class TestFit:
    """The Phase-2 gate: R2 > 0.60, and in every year, not just the best one."""

    def test_r_squared_exceeds_gate_in_every_year(self, coefs):
        for year in ec.ESTIMATION_YEARS:
            r2 = coefs.loc[coefs["spec"] == f"year_{year}", "r_squared"].iloc[0]
            assert r2 > 0.60, f"{year}: R2 = {r2:.3f} fails the Phase-2 gate"

    def test_latest_year_uses_the_complete_case_maximum(self):
        assert ec.LATEST_YEAR == 2024

    def test_every_year_uses_all_290_kommuner(self, coefs):
        for year in ec.ESTIMATION_YEARS:
            n = coefs.loc[coefs["spec"] == f"year_{year}", "n_obs"].iloc[0]
            assert n == 290


class TestIdentification:
    """Two variables are drivers; two are controls. Both halves are asserted."""

    @pytest.mark.parametrize("var", _IDENTIFIED)
    def test_identified_variables_exclude_zero_with_expected_sign_every_year(
        self, coefs, var
    ):
        for year in ec.ESTIMATION_YEARS:
            row = coefs[(coefs["spec"] == f"year_{year}") & (coefs["variable"] == var)]
            lo, hi = row["lower_ci"].iloc[0], row["upper_ci"].iloc[0]
            assert lo * hi > 0, f"{var} {year}: CI [{lo:.3f}, {hi:.3f}] spans zero"
            assert np.sign(row["coefficient"].iloc[0]) == _EXPECTED_SIGN[var]

    @pytest.mark.parametrize("var", _UNIDENTIFIED)
    def test_unidentified_variables_span_zero_in_the_latest_year(self, coefs, var):
        row = coefs[
            (coefs["spec"] == f"year_{ec.LATEST_YEAR}") & (coefs["variable"] == var)
        ]
        lo, hi = row["lower_ci"].iloc[0], row["upper_ci"].iloc[0]
        assert lo * hi < 0, (
            f"{var} CI [{lo:.3f}, {hi:.3f}] no longer spans zero — the "
            "identification finding has changed, see METHODOLOGY §13.4"
        )

    @pytest.mark.parametrize("var", _IDENTIFIED)
    def test_identified_flag_is_true_for_drivers(self, coefs, var):
        assert coefs.loc[coefs["variable"] == var, "identified"].all()

    @pytest.mark.parametrize("var", _UNIDENTIFIED)
    def test_identified_flag_is_false_for_controls(self, coefs, var):
        assert not coefs.loc[coefs["variable"] == var, "identified"].any()

    def test_unidentified_variables_stay_in_the_model_as_controls(self, coefs):
        """Dropping them would misstate the specification; they must be present."""
        present = set(coefs.loc[coefs["spec"] == f"year_{ec.LATEST_YEAR}", "variable"])
        assert set(ec.X_VARS) <= present


class TestStandardisation:
    """beta*SD is the primary quantity — raw betas sit on incomparable scales."""

    def test_beta_sd_equals_coefficient_times_variable_sd(self):
        table = ec.build_coefficient_table(_synthetic(), years=(2024,))
        row = table[
            (table["spec"] == "year_2024") & (table["variable"] == "edu_share")
        ].iloc[0]
        expected_sd = _synthetic()["edu_share"].std(ddof=1)
        assert row["x_sd"] == pytest.approx(expected_sd)
        assert row["beta_sd"] == pytest.approx(row["coefficient"] * expected_sd)

    def test_recovers_a_known_coefficient(self):
        table = ec.build_coefficient_table(_synthetic(), years=(2024,))
        row = table[
            (table["spec"] == "year_2024") & (table["variable"] == "edu_share")
        ].iloc[0]
        assert row["coefficient"] == pytest.approx(2.0, abs=1e-6)
        assert row["r_squared"] == pytest.approx(1.0, abs=1e-9)

    def test_education_dominates_on_the_standardised_scale(self, coefs):
        """Raw betas make dependency_ratio look largest; beta*SD corrects that."""
        latest = coefs[coefs["spec"] == f"year_{ec.LATEST_YEAR}"].set_index("variable")
        assert abs(latest.loc["edu_share", "beta_sd"]) > abs(
            latest.loc["dependency_ratio", "beta_sd"]
        )

    def test_confidence_intervals_are_carried_in_both_scales(self, coefs):
        latest = coefs[coefs["spec"] == f"year_{ec.LATEST_YEAR}"].set_index("variable")
        for var in ec.X_VARS:
            row = latest.loc[var]
            assert row["lower_ci_sd"] == pytest.approx(row["lower_ci"] * row["x_sd"])
            assert row["upper_ci_sd"] == pytest.approx(row["upper_ci"] * row["x_sd"])


class TestAcrossYearRange:
    """The honest headline is the range, not one arbitrary year's point estimate."""

    def test_range_is_recorded_for_every_variable(self, coefs):
        for var in ec.X_VARS:
            rows = coefs[coefs["variable"] == var]
            assert rows["beta_sd_range_low"].notna().all()
            assert rows["beta_sd_range_high"].notna().all()

    def test_range_brackets_every_yearly_point_estimate(self, coefs):
        for var in ec.X_VARS:
            rows = coefs[
                (coefs["variable"] == var)
                & (coefs["spec"].str.startswith("year_"))
            ]
            low = rows["beta_sd_range_low"].iloc[0]
            high = rows["beta_sd_range_high"].iloc[0]
            assert low <= rows["beta_sd"].min() + 1e-9
            assert high >= rows["beta_sd"].max() - 1e-9


class TestArtifact:
    def test_table_carries_every_required_column(self, coefs):
        required = {
            "spec", "year", "variable", "coefficient", "std_error", "p_value",
            "lower_ci", "upper_ci", "x_sd", "beta_sd", "lower_ci_sd",
            "upper_ci_sd", "r_squared", "n_obs", "identified",
            "beta_sd_range_low", "beta_sd_range_high",
        }
        assert required <= set(coefs.columns)

    def test_contains_both_yearly_and_pooled_specs(self, coefs):
        specs = set(coefs["spec"])
        assert "pooled" in specs
        for year in ec.ESTIMATION_YEARS:
            assert f"year_{year}" in specs

    def test_does_not_overwrite_the_deployed_fe_artifact(self):
        """The live dashboard reads coefficients.parquet; this writes its own."""
        assert ec._OUTPUT_PATH.name == "coefficients_cross.parquet"


class TestDocumentedConstraints:
    """The plan requires these statements to survive in the module itself."""

    def test_docstring_states_the_descriptive_not_causal_constraint(self):
        doc = ec.__doc__.lower()
        assert "descriptive" in doc and "causal" in doc

    def test_docstring_states_that_two_variables_are_not_identified(self):
        doc = ec.__doc__.lower()
        assert "identif" in doc
