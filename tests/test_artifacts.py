"""Smoke tests for precomputed artifact files.

Verifies that each artifact parquet file exists, has the expected number
of rows, and contains the required columns.  These tests catch pipeline
regressions that would break the Streamlit dashboard at load time.
"""

import pickle
from pathlib import Path

import pandas as pd
import pytest

_ARTIFACTS_DIR = Path(__file__).resolve().parents[1] / "artifacts"


class TestPredictions:
    """Smoke tests for artifacts/predictions.parquet."""

    @pytest.fixture(autouse=True)
    def load(self):
        self.path = _ARTIFACTS_DIR / "predictions.parquet"

    def test_file_exists(self):
        assert self.path.exists(), "predictions.parquet missing"

    def test_row_count(self):
        df = pd.read_parquet(self.path)
        assert len(df) == 290, f"Expected 290 rows, got {len(df)}"

    def test_expected_columns(self):
        df = pd.read_parquet(self.path)
        expected = {
            "kommun_kod",
            "kommun_name",
            "lan_name",
            "predicted_growth_2025",
            "vulnerability_score",
            "vulnerability_rank",
            "risk_class",
        }
        assert expected.issubset(set(df.columns)), (
            f"Missing columns: {expected - set(df.columns)}"
        )

    def test_risk_classes_valid(self):
        df = pd.read_parquet(self.path)
        valid = {"lag", "medel", "hog"}
        actual = set(df["risk_class"].unique())
        assert actual.issubset(valid), f"Invalid risk classes: {actual - valid}"

    def test_vulnerability_rank_complete(self):
        df = pd.read_parquet(self.path)
        ranks = sorted(df["vulnerability_rank"].astype(int).tolist())
        assert ranks == list(range(1, 291)), "Ranks must be 1..290 without gaps"


class TestRanking:
    """Smoke tests for artifacts/ranking.parquet."""

    @pytest.fixture(autouse=True)
    def load(self):
        self.path = _ARTIFACTS_DIR / "ranking.parquet"

    def test_file_exists(self):
        assert self.path.exists(), "ranking.parquet missing"

    def test_row_count(self):
        df = pd.read_parquet(self.path)
        assert len(df) == 290, f"Expected 290 rows, got {len(df)}"

    def test_sorted_by_vulnerability_rank(self):
        df = pd.read_parquet(self.path)
        assert df["vulnerability_rank"].is_monotonic_increasing, (
            "ranking.parquet must be sorted by vulnerability_rank ascending"
        )


class TestDecomposition:
    """Smoke tests for artifacts/decomposition.parquet."""

    @pytest.fixture(autouse=True)
    def load(self):
        self.path = _ARTIFACTS_DIR / "decomposition.parquet"

    def test_file_exists(self):
        assert self.path.exists(), "decomposition.parquet missing"

    def test_row_count(self):
        df = pd.read_parquet(self.path)
        assert len(df) == 290, f"Expected 290 rows, got {len(df)}"

    def test_expected_columns(self):
        df = pd.read_parquet(self.path)
        expected = {
            "kommun_kod",
            "kommun_name",
            "decomp_unemployment",
            "decomp_dependency",
            "decomp_population",
            "decomp_education",
            "decomp_residual",
        }
        assert expected.issubset(set(df.columns)), (
            f"Missing columns: {expected - set(df.columns)}"
        )

    def test_no_null_decomposition_values(self):
        df = pd.read_parquet(self.path)
        decomp_cols = [c for c in df.columns if c.startswith("decomp_")]
        for col in decomp_cols:
            assert df[col].notna().all(), f"Null values found in {col}"


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


class TestModelResults:
    """Smoke tests for artifacts/model_results.pkl."""

    @pytest.fixture(autouse=True)
    def load(self):
        self.path = _ARTIFACTS_DIR / "model_results.pkl"

    def test_file_exists(self):
        assert self.path.exists(), "model_results.pkl missing"

    def test_loadable_and_has_rsquared(self):
        with open(self.path, "rb") as f:
            res = pickle.load(f)
        assert hasattr(res, "rsquared_within"), (
            "model_results.pkl must have rsquared_within attribute"
        )
        r2 = float(res.rsquared_within)
        assert 0.0 < r2 < 1.0, f"R²(within) = {r2} out of (0, 1) range"
