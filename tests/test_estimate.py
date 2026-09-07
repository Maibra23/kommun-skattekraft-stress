"""Tests for src.model.estimate — uses a small synthetic panel, no API calls."""

import pickle
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.model.estimate import (
    Y_VAR,
    X_VARS,
    estimate_main,
    estimate_robustness,
    extract_coefficients,
    save_model_artifacts,
)


# ---------------------------------------------------------------------------
# Synthetic panel factory
# ---------------------------------------------------------------------------

def _make_synthetic_panel(
    n_entities: int = 40,
    n_years: int = 12,
    seed: int = 42,
) -> pd.DataFrame:
    """Create a balanced synthetic panel large enough for two-way FE estimation."""
    rng = np.random.default_rng(seed)
    entities = [f"{i:04d}" for i in range(1, n_entities + 1)]
    years = list(range(2025 - n_years, 2025))  # always end at 2024 so large_only filter finds year 2024

    entity_fe = rng.normal(0, 1, n_entities)
    year_fe = rng.normal(0, 0.5, n_years)

    records = []
    for ei, kod in enumerate(entities):
        pop = int(rng.uniform(5_000, 200_000))
        for yi, year in enumerate(years):
            u = float(rng.uniform(2.0, 12.0))
            dep = float(rng.uniform(0.5, 1.2))
            pop_g = float(rng.normal(0.5, 1.5))
            edu = float(rng.uniform(15.0, 45.0))
            growth = (
                entity_fe[ei]
                + year_fe[yi]
                - 0.3 * u
                + 1.0 * pop_g
                + rng.normal(0, 0.8)
            )
            records.append(
                {
                    "kommun_kod": kod,
                    "kommun_name": f"Testkommun {ei + 1}",
                    "lan_kod": "01",
                    "lan_name": "Testlän",
                    "year": year,
                    "tax_base_per_capita": int(200_000 + rng.normal(0, 20_000)),
                    Y_VAR: float(growth),
                    "unemployment_rate": u,
                    "dependency_ratio": dep,
                    "population": pop,
                    "population_growth_pct": pop_g,
                    "edu_share": edu,
                }
            )
    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# estimate_main
# ---------------------------------------------------------------------------

def test_estimate_main_returns_results():
    panel = _make_synthetic_panel()
    results = estimate_main(panel)
    assert results is not None
    assert results.nobs > 0


def test_estimate_main_within_r2_in_range():
    panel = _make_synthetic_panel()
    results = estimate_main(panel)
    assert 0.0 <= results.rsquared_within <= 1.0


def test_estimate_main_has_all_x_vars():
    panel = _make_synthetic_panel()
    results = estimate_main(panel)
    assert set(results.params.index) == set(X_VARS)


def test_estimate_main_unemployment_sign():
    """Unemployment coefficient should be negative (higher unemployment → lower growth)."""
    panel = _make_synthetic_panel()
    results = estimate_main(panel)
    # With synthetic DGP we built in -0.3 * unemployment, so sign should be negative
    assert results.params["unemployment_rate"] < 0


# ---------------------------------------------------------------------------
# extract_coefficients
# ---------------------------------------------------------------------------

def test_extract_coefficients_columns():
    panel = _make_synthetic_panel()
    results = estimate_main(panel)
    coef_df = extract_coefficients(results)
    expected_cols = {
        "variable", "coefficient", "std_error", "t_stat",
        "p_value", "lower_ci", "upper_ci",
    }
    assert expected_cols == set(coef_df.columns)


def test_extract_coefficients_row_count():
    panel = _make_synthetic_panel()
    results = estimate_main(panel)
    coef_df = extract_coefficients(results)
    assert len(coef_df) == len(X_VARS)


def test_extract_coefficients_ci_ordering():
    """lower_ci <= coefficient <= upper_ci for every row."""
    panel = _make_synthetic_panel()
    results = estimate_main(panel)
    coef_df = extract_coefficients(results)
    assert (coef_df["lower_ci"] <= coef_df["coefficient"]).all()
    assert (coef_df["coefficient"] <= coef_df["upper_ci"]).all()


# ---------------------------------------------------------------------------
# estimate_robustness
# ---------------------------------------------------------------------------

def test_estimate_robustness_returns_four_keys():
    panel = _make_synthetic_panel()
    robustness = estimate_robustness(panel)
    assert set(robustness.keys()) == {"lagged", "no_covid", "large_only", "no_education"}


def test_estimate_robustness_all_have_observations():
    panel = _make_synthetic_panel()
    robustness = estimate_robustness(panel)
    for name, res in robustness.items():
        assert res.nobs > 0, f"Spec '{name}' returned zero observations"


def test_estimate_robustness_no_education_has_three_vars():
    panel = _make_synthetic_panel()
    robustness = estimate_robustness(panel)
    assert "edu_share" not in set(robustness["no_education"].params.index)
    assert len(robustness["no_education"].params) == 3


def test_estimate_robustness_no_covid_fewer_obs():
    panel = _make_synthetic_panel()
    main = estimate_main(panel)
    robustness = estimate_robustness(panel)
    assert robustness["no_covid"].nobs < main.nobs


# ---------------------------------------------------------------------------
# save_model_artifacts
# ---------------------------------------------------------------------------

def test_save_model_artifacts_creates_files(tmp_path):
    panel = _make_synthetic_panel()
    main_results = estimate_main(panel)
    robustness_results = estimate_robustness(panel)
    save_model_artifacts(main_results, robustness_results, tmp_path)

    assert (tmp_path / "model_results.pkl").exists()
    assert (tmp_path / "coefficients.parquet").exists()


def test_save_model_artifacts_pickle_roundtrip(tmp_path):
    panel = _make_synthetic_panel()
    main_results = estimate_main(panel)
    robustness_results = estimate_robustness(panel)
    save_model_artifacts(main_results, robustness_results, tmp_path)

    with open(tmp_path / "model_results.pkl", "rb") as fh:
        loaded = pickle.load(fh)
    assert loaded.nobs == main_results.nobs
    assert set(loaded.params.index) == set(main_results.params.index)


def test_save_model_artifacts_coef_table_has_all_specs(tmp_path):
    panel = _make_synthetic_panel()
    main_results = estimate_main(panel)
    robustness_results = estimate_robustness(panel)
    save_model_artifacts(main_results, robustness_results, tmp_path)

    coef_df = pd.read_parquet(tmp_path / "coefficients.parquet")
    assert "spec" in coef_df.columns
    expected_specs = {"main", "lagged", "no_covid", "large_only", "no_education"}
    assert set(coef_df["spec"].unique()) == expected_specs


def test_save_model_artifacts_coef_table_row_count(tmp_path):
    panel = _make_synthetic_panel()
    main_results = estimate_main(panel)
    robustness_results = estimate_robustness(panel)
    save_model_artifacts(main_results, robustness_results, tmp_path)

    coef_df = pd.read_parquet(tmp_path / "coefficients.parquet")
    # main: 4 vars, lagged: 4, no_covid: 4, large_only: 4, no_education: 3
    assert len(coef_df) == 4 + 4 + 4 + 4 + 3


# ---------------------------------------------------------------------------
# Spec roles — REMEDIATION_PLAN.md T2.4 (the lagged spec is promoted to primary)
# ---------------------------------------------------------------------------


def _coef_table(tmp_path) -> pd.DataFrame:
    panel = _make_synthetic_panel()
    save_model_artifacts(
        estimate_main(panel), estimate_robustness(panel), tmp_path
    )
    return pd.read_parquet(tmp_path / "coefficients.parquet")


def test_lagged_spec_is_the_only_primary_spec(tmp_path):
    coef_df = _coef_table(tmp_path)
    primary = set(coef_df.loc[coef_df["role"] == "primary", "spec"])
    assert primary == {"lagged"}


def test_every_other_spec_is_labelled_robustness(tmp_path):
    coef_df = _coef_table(tmp_path)
    robustness = set(coef_df.loc[coef_df["role"] == "robustness", "spec"])
    assert robustness == {"main", "no_covid", "large_only", "no_education"}


def test_contemporaneous_spec_keeps_its_legacy_name(tmp_path):
    """The deployed dashboard filters ``spec == "main"`` (app.py:226).

    T2.4 demotes that spec but must not rename it: artifacts are a published
    contract (METHODOLOGY §11.7) and the UI cutover is a later, single commit.
    """
    coef_df = _coef_table(tmp_path)
    assert (coef_df["spec"] == "main").sum() == len(X_VARS)


def test_coef_table_carries_sample_and_fit_per_spec(tmp_path):
    """Each spec self-describes, so the within-time panel can be rendered
    without unpickling model_results.pkl."""
    coef_df = _coef_table(tmp_path)
    assert {"n_obs", "r_squared_within"}.issubset(coef_df.columns)

    lagged = coef_df[coef_df["spec"] == "lagged"]
    assert lagged["n_obs"].nunique() == 1
    assert lagged["n_obs"].iloc[0] > 0
    assert lagged["r_squared_within"].iloc[0] <= 1.0


def test_n_obs_is_recorded_per_spec_not_broadcast_from_main(tmp_path):
    """On a balanced panel the lag and the COVID exclusion each cost rows, so
    a per-spec n_obs must differ from the contemporaneous one."""
    coef_df = _coef_table(tmp_path)
    n = coef_df.groupby("spec")["n_obs"].first()
    assert n["lagged"] < n["main"]
    assert n["no_covid"] < n["main"]
