"""Unit tests for collinearity and scale diagnostics.

Covers REMEDIATION_PLAN.md T2.3 as reframed on 2026-09-07.

The task was written expecting collinearity to be the threat to the
cross-sectional model. It is not: VIF there is 1.3-2.1. The audit's finding F3
is real, but it belongs to the *within* design, where three of six pairs exceed
|0.65|. So this module's job is to close F3 honestly in both directions -
showing where the problem exists and where it does not - rather than to
confirm a problem that is not there.

No test touches the network.
"""

import numpy as np
import pandas as pd
import pytest

from src.model import diagnostics as dg

_VARS = ["edu_share", "unemployment_rate", "dependency_ratio", "population_growth_pct"]


@pytest.fixture(scope="module")
def panel() -> pd.DataFrame:
    return pd.read_parquet(dg._PANEL_PATH)


@pytest.fixture(scope="module")
def table(panel) -> pd.DataFrame:
    return dg.build_diagnostics(panel)


class TestBothDesigns:
    """F3 is closed by measuring both designs, not just the new one."""

    def test_covers_the_cross_sectional_and_within_designs(self, table):
        assert set(table["design"].unique()) == {dg.CROSS_DESIGN, dg.WITHIN_DESIGN}

    def test_vif_computed_for_every_variable_in_both_designs(self, table):
        vif = table[table["metric"] == "vif"]
        for design in (dg.CROSS_DESIGN, dg.WITHIN_DESIGN):
            got = set(vif.loc[vif["design"] == design, "variable"])
            assert got == set(_VARS)

    def test_condition_number_recorded_per_design(self, table):
        vif = table[table["metric"] == "vif"]
        for design in (dg.CROSS_DESIGN, dg.WITHIN_DESIGN):
            values = vif.loc[vif["design"] == design, "condition_number"].dropna()
            assert len(values) > 0 and values.nunique() == 1


class TestCrossSectionalDesignIsClean:
    """The finding that lets T2.2 proceed: collinearity is not the problem here."""

    def test_all_vifs_below_the_warning_threshold(self, table):
        vif = table[(table["metric"] == "vif") & (table["design"] == dg.CROSS_DESIGN)]
        assert (vif["value"] < dg.VIF_WARNING).all(), (
            f"Cross-sectional VIFs: {dict(zip(vif['variable'], vif['value'].round(2)))}"
        )
        assert (vif["flag"] == "ok").all()

    def test_no_pair_is_flagged_high(self, table):
        corr = table[
            (table["metric"] == "correlation") & (table["design"] == dg.CROSS_DESIGN)
        ]
        assert (corr["flag"] == "ok").all()


class TestWithinDesignShowsF3:
    """The audit's high-correlation pairs must be flagged where they occur."""

    @pytest.mark.parametrize(
        "a,b",
        [
            ("dependency_ratio", "edu_share"),
            ("unemployment_rate", "dependency_ratio"),
            ("unemployment_rate", "edu_share"),
        ],
    )
    def test_audit_pairs_are_flagged_high_within(self, table, a, b):
        corr = table[
            (table["metric"] == "correlation") & (table["design"] == dg.WITHIN_DESIGN)
        ]
        row = corr[
            ((corr["variable"] == a) & (corr["variable_2"] == b))
            | ((corr["variable"] == b) & (corr["variable_2"] == a))
        ]
        assert len(row) == 1, f"pair {a}x{b} missing from the within correlations"
        assert abs(row["value"].iloc[0]) > 0.65
        assert row["flag"].iloc[0] == "high"


class TestScaleIsTheRealRisk:
    """dependency_ratio fails on variation, not on collinearity."""

    def test_records_each_variables_standard_deviation(self, table):
        vif = table[(table["metric"] == "vif") & (table["design"] == dg.CROSS_DESIGN)]
        assert vif["x_sd"].notna().all()

    def test_dependency_ratio_barely_varies_between_kommuner(self, table):
        vif = table[(table["metric"] == "vif") & (table["design"] == dg.CROSS_DESIGN)]
        sds = dict(zip(vif["variable"], vif["x_sd"]))
        assert sds["dependency_ratio"] < 0.2
        assert sds["dependency_ratio"] < 0.05 * sds["edu_share"]


class TestFlagging:
    def test_vif_thresholds(self):
        assert dg._vif_flag(1.5) == "ok"
        assert dg._vif_flag(dg.VIF_WARNING + 0.1) == "warning"
        assert dg._vif_flag(dg.VIF_SEVERE + 0.1) == "severe"

    def test_correlation_threshold(self):
        assert dg._corr_flag(0.5) == "ok"
        assert dg._corr_flag(-0.9) == "high"

    def test_vif_of_an_orthogonal_design_is_one(self):
        rng = np.random.default_rng(0)
        df = pd.DataFrame(rng.normal(size=(500, 3)), columns=["a", "b", "c"])
        vifs = dg._vifs(df, ["a", "b", "c"])
        assert all(v == pytest.approx(1.0, abs=0.1) for v in vifs.values())

    def test_vif_detects_a_collinear_pair(self):
        rng = np.random.default_rng(0)
        a = rng.normal(size=500)
        df = pd.DataFrame({"a": a, "b": a + rng.normal(scale=0.01, size=500)})
        vifs = dg._vifs(df, ["a", "b"])
        assert vifs["a"] > dg.VIF_SEVERE


class TestArtifact:
    def test_does_not_touch_a_deployed_artifact(self):
        assert dg._OUTPUT_PATH.name == "diagnostics.parquet"

    def test_every_row_carries_a_flag(self, table):
        assert table["flag"].notna().all()
