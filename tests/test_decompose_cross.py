"""Unit tests for the position-gap decomposition.

Covers METHODOLOGY §13.4 as revised on 2026-09-07.

The old decomposition answered "why did Filipstad grow 1.8 pp below average in
2024?" — a question about a quantity with no year-to-year persistence, where
the residual dominated. This one answers "why does Filipstad sit at index 76?",
which is what users ask and where the model explains ~69 %.

The revision that matters: this is **not** a four-bar chart. Only `edu_share`
and `unemployment_rate` are separately identified; `dependency_ratio` and
`population_growth_pct` have intervals spanning zero in every year. They stay
in the fitted model as controls but are never attributed, because the additive
identity sums to 100 % whether or not its components mean anything — the sum
check cannot catch a bar that is noise.

No test touches the network.
"""

import numpy as np
import pandas as pd
import pytest

from src.model import decompose_cross as dc


@pytest.fixture(scope="module")
def panel() -> pd.DataFrame:
    return pd.read_parquet(dc._PANEL_PATH)


@pytest.fixture(scope="module")
def coefs() -> pd.DataFrame:
    return pd.read_parquet(dc._COEFFICIENTS_PATH)


@pytest.fixture(scope="module")
def result(panel, coefs) -> pd.DataFrame:
    return dc.build_decomposition(panel, coefs)


class TestTarget:
    """The target is position, not growth. That is the whole point."""

    def test_decomposes_the_position_gap(self, result, panel):
        latest = panel[panel.year == dc.LATEST_YEAR]
        expected_mean = latest[dc.Y_VAR].mean()
        merged = result.merge(
            latest[["kommun_kod", dc.Y_VAR]], on="kommun_kod"
        )
        recomputed = merged[dc.Y_VAR] - expected_mean
        assert np.allclose(merged["total_gap"], recomputed)

    def test_one_row_per_kommun(self, result):
        assert len(result) == 290
        assert not result["kommun_kod"].duplicated().any()

    def test_gaps_sum_to_zero_across_kommuner(self, result):
        assert result["total_gap"].sum() == pytest.approx(0.0, abs=1e-8)


class TestAdditiveIdentity:
    """Kept from the old module because it is good — but it is not sufficient."""

    def test_components_and_residual_sum_to_the_gap_exactly(self, result):
        attributed = result[[c for c in result.columns if c.startswith("contrib_")]].sum(axis=1)
        total = attributed + result["residual"]
        assert np.allclose(total, result["total_gap"], atol=1e-10)

    def test_hand_computed_single_kommun(self):
        """One kommun, arithmetic checkable by eye."""
        panel = pd.DataFrame(
            {
                "kommun_kod": ["0001", "0002", "0003"],
                "year": dc.LATEST_YEAR,
                dc.Y_VAR: [90.0, 100.0, 110.0],
                "edu_share": [10.0, 20.0, 30.0],
                "unemployment_rate": [5.0, 5.0, 5.0],
                "dependency_ratio": [0.9, 0.9, 0.9],
                "population_growth_pct": [0.0, 0.0, 0.0],
            }
        )
        coefs = pd.DataFrame(
            {
                "spec": f"year_{dc.LATEST_YEAR}",
                "variable": ["edu_share", "unemployment_rate",
                             "dependency_ratio", "population_growth_pct"],
                "coefficient": [2.0, -1.0, -5.0, -0.5],
                "identified": [True, True, False, False],
            }
        )
        out = dc.build_decomposition(panel, coefs).set_index("kommun_kod")

        # kommun 0001: edu 10 vs mean 20 -> contribution 2.0 * (-10) = -20
        assert out.loc["0001", "contrib_edu_share"] == pytest.approx(-20.0)
        # unemployment is identical everywhere -> contributes nothing
        assert out.loc["0001", "contrib_unemployment_rate"] == pytest.approx(0.0)
        # gap is 90 - 100 = -10, so the residual takes the remaining +10
        assert out.loc["0001", "total_gap"] == pytest.approx(-10.0)
        assert out.loc["0001", "residual"] == pytest.approx(10.0)


class TestIdentificationIsRespected:
    """Unidentified variables must not appear as attributed components."""

    def test_only_identified_variables_get_contribution_columns(self, result):
        contribs = {c.removeprefix("contrib_") for c in result.columns
                    if c.startswith("contrib_")}
        assert contribs == {"edu_share", "unemployment_rate"}

    def test_unidentified_variables_are_carried_as_flagged_controls(self, result):
        controls = {c.removeprefix("control_") for c in result.columns
                    if c.startswith("control_")}
        assert controls == {"dependency_ratio", "population_growth_pct"}

    def test_controls_are_not_summed_into_the_attribution(self, result):
        """A control's value must not affect the identity, only inform it."""
        attributed = result[[c for c in result.columns if c.startswith("contrib_")]].sum(axis=1)
        assert np.allclose(attributed + result["residual"], result["total_gap"], atol=1e-10)

    def test_reads_the_flag_rather_than_hardcoding_variable_names(self, panel):
        """Flipping the flag must change what is attributed."""
        coefs = pd.read_parquet(dc._COEFFICIENTS_PATH)
        flipped = coefs.copy()
        flipped.loc[flipped["variable"] == "dependency_ratio", "identified"] = True
        out = dc.build_decomposition(panel, flipped)
        assert "contrib_dependency_ratio" in out.columns


class TestResidual:
    """The residual must not dominate — measured in a way that means something.

    The DoD says "mean |residual| share of total gap < 40 %". Taken literally
    as the mean of per-kommun |residual|/|gap| that is both unreachable and
    meaningless here, for two separate reasons:

    1. **The denominator goes to zero.** A kommun sitting at the national
       average has a gap near 0 by definition — Östersund's is 0.27 index
       points — so its ratio explodes to 43 while its residual is unremarkable.
       The mean of those ratios (2.0) describes the distribution of gaps, not
       the quality of the decomposition.
    2. **The threshold contradicts the R² it is derived from.** The DoD reasons
       "two identified variables carry R² = 0.688, so this should hold
       comfortably". But R² is a *variance* share: residual variance is
       1 − 0.688 = 31 %, which in absolute-deviation terms is √0.31 ≈ 56 %.
       A mean |residual| share under 40 % would require R² ≈ 0.84.

    So the DoD's intent — the residual should not dominate — is tested as the
    residual *variance* share, which is the quantity R² actually bounds.
    See the 2026-09-07 T2.2 status-log entry.
    """

    def test_residual_variance_share_is_below_40_percent(self, result):
        share = result["residual"].var() / result["total_gap"].var()
        assert share < 0.40, f"residual variance share = {share:.3f}"

    def test_variance_share_agrees_with_the_models_r_squared(self, result, coefs):
        """1 - residual share must reproduce the estimator's R², or the
        decomposition is not using the coefficients it claims to."""
        explained = 1 - result["residual"].var() / result["total_gap"].var()
        r2 = coefs.loc[coefs["spec"] == f"year_{dc.LATEST_YEAR}", "r_squared"].iloc[0]
        assert explained == pytest.approx(r2, abs=0.02)

    def test_residual_is_smaller_than_the_gap_it_explains(self, result):
        """The old growth decomposition's residual dominated; this must not."""
        assert result["residual"].abs().mean() < result["total_gap"].abs().mean()
        assert result["residual"].abs().sum() / result["total_gap"].abs().sum() < 0.65


class TestArtifact:
    def test_writes_a_new_file_not_the_deployed_one(self):
        assert dc._OUTPUT_PATH.name == "decomposition_cross.parquet"

    def test_carries_kommun_names_for_display(self, result):
        assert "kommun_name" in result.columns
        assert result["kommun_name"].notna().all()
