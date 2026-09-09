"""Smoke tests for precomputed artifact files.

Verifies that each artifact parquet file exists, has the expected number
of rows, and contains the required columns.  These tests catch pipeline
regressions that would break the Streamlit dashboard at load time.
"""

from pathlib import Path

import pandas as pd
import pytest

_ARTIFACTS_DIR = Path(__file__).resolve().parents[1] / "artifacts"


class TestCoefficients:
    """Smoke tests for artifacts/coefficients.parquet."""

    @pytest.fixture(autouse=True)
    def load(self):
        self.path = _ARTIFACTS_DIR / "coefficients.parquet"

    def test_file_exists(self):
        assert self.path.exists(), "coefficients.parquet missing"

    def test_has_spec_column(self):
        df = pd.read_parquet(self.path)
        assert "spec" in df.columns, "Missing 'spec' column"

    def test_five_unique_specs(self):
        df = pd.read_parquet(self.path)
        expected_specs = {"main", "no_covid", "no_education", "lagged", "large_only"}
        actual_specs = set(df["spec"].unique())
        assert actual_specs == expected_specs, (
            f"Expected specs {expected_specs}, got {actual_specs}"
        )

    def test_main_spec_has_four_variables(self):
        df = pd.read_parquet(self.path)
        main = df[df["spec"] == "main"]
        assert len(main) == 4, f"Main spec should have 4 variables, got {len(main)}"

    def test_coefficient_columns(self):
        df = pd.read_parquet(self.path)
        expected = {"variable", "coefficient", "std_error", "t_stat", "p_value", "spec"}
        assert expected.issubset(set(df.columns)), (
            f"Missing columns: {expected - set(df.columns)}"
        )

    def test_lagged_spec_is_primary(self):
        """T2.4: the lagged spec is the FE panel's primary specification."""
        df = pd.read_parquet(self.path)
        assert "role" in df.columns, "Missing 'role' column"
        assert set(df.loc[df["role"] == "primary", "spec"]) == {"lagged"}

    def test_contemporaneous_spec_still_named_main(self):
        """The deployed dashboard filters spec == 'main' (app.py:226).

        T2.4 demotes that spec without renaming it; the rename belongs to the
        single UI cutover commit (METHODOLOGY §11.7).
        """
        df = pd.read_parquet(self.path)
        assert (df["spec"] == "main").sum() == 4

    def test_lagged_spec_identifies_unemployment_more_sharply(self):
        """Locks audit finding F4, the reason for the promotion.

        Every regressor's within-kommun correlation with growth peaks at t-1
        or later; unemployment is the sharpest case.
        """
        df = pd.read_parquet(self.path)
        t = df.set_index(["spec", "variable"])["t_stat"]
        assert abs(t[("lagged", "unemployment_rate")]) > abs(
            t[("main", "unemployment_rate")]
        )

    def test_every_spec_reports_its_sample_and_fit(self):
        df = pd.read_parquet(self.path)
        assert {"n_obs", "r_squared_within"}.issubset(df.columns)
        assert df["n_obs"].gt(0).all()
        # R2(within) is bounded above by 1 but not below by 0: linearmodels
        # measures it against the within-transformed model, so a spec that
        # drops a regressor can score below zero (no_education does).
        assert df["r_squared_within"].le(1.0).all()

    def test_primary_spec_fits_better_within_kommuner_than_the_demoted_one(self):
        """The second half of F4: lagging does not merely sharpen one t-stat,
        it explains more of the within-kommun variation."""
        df = pd.read_parquet(self.path)
        r2 = df.groupby("spec")["r_squared_within"].first()
        assert r2["lagged"] > r2["main"]
