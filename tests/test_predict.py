"""Tests for src.model.predict — uses a small synthetic panel, no API calls."""

import numpy as np
import pandas as pd
import pytest

from src.model.estimate import X_VARS, Y_VAR, estimate_main
from src.model.predict import compute_vulnerability, predict_2025


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
    years = list(range(2025 - n_years, 2025))

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
# predict_2025
# ---------------------------------------------------------------------------


def test_predict_2025_returns_correct_columns():
    panel = _make_synthetic_panel()
    results = estimate_main(panel)
    predictions = predict_2025(results, panel)
    expected_cols = {"kommun_kod", "kommun_name", "lan_name", "predicted_growth_2025"}
    assert expected_cols == set(predictions.columns)


def test_predict_2025_row_count():
    panel = _make_synthetic_panel()
    results = estimate_main(panel)
    predictions = predict_2025(results, panel)
    n_entities = panel["kommun_kod"].nunique()
    assert len(predictions) == n_entities


def test_predict_2025_no_nan():
    panel = _make_synthetic_panel()
    results = estimate_main(panel)
    predictions = predict_2025(results, panel)
    assert predictions["predicted_growth_2025"].isna().sum() == 0


def test_predict_2025_mean_near_historical():
    """Predicted mean should be in the same ballpark as historical mean."""
    panel = _make_synthetic_panel()
    results = estimate_main(panel)
    predictions = predict_2025(results, panel)
    hist_mean = panel[Y_VAR].mean()
    pred_mean = predictions["predicted_growth_2025"].mean()
    # Allow generous tolerance for synthetic data
    assert abs(pred_mean - hist_mean) < 5.0


# ---------------------------------------------------------------------------
# compute_vulnerability
# ---------------------------------------------------------------------------


def test_compute_vulnerability_columns():
    panel = _make_synthetic_panel()
    results = estimate_main(panel)
    predictions = predict_2025(results, panel)
    vuln = compute_vulnerability(predictions)
    expected_cols = {
        "kommun_kod",
        "kommun_name",
        "lan_name",
        "predicted_growth_2025",
        "vulnerability_score",
        "vulnerability_rank",
        "risk_class",
    }
    assert expected_cols == set(vuln.columns)


def test_compute_vulnerability_row_count():
    panel = _make_synthetic_panel()
    results = estimate_main(panel)
    predictions = predict_2025(results, panel)
    vuln = compute_vulnerability(predictions)
    assert len(vuln) == len(predictions)


def test_compute_vulnerability_score_sign_flip():
    """Lower predicted growth should map to higher vulnerability score."""
    panel = _make_synthetic_panel()
    results = estimate_main(panel)
    predictions = predict_2025(results, panel)
    vuln = compute_vulnerability(predictions)
    lowest_growth_idx = vuln["predicted_growth_2025"].idxmin()
    highest_growth_idx = vuln["predicted_growth_2025"].idxmax()
    assert (
        vuln.loc[lowest_growth_idx, "vulnerability_score"]
        > vuln.loc[highest_growth_idx, "vulnerability_score"]
    )


def test_compute_vulnerability_rank_one_is_most_vulnerable():
    """Rank 1 should correspond to the lowest predicted growth."""
    panel = _make_synthetic_panel()
    results = estimate_main(panel)
    predictions = predict_2025(results, panel)
    vuln = compute_vulnerability(predictions)
    rank_1 = vuln.loc[vuln["vulnerability_rank"] == 1]
    assert rank_1["predicted_growth_2025"].values[0] == vuln["predicted_growth_2025"].min()


def test_compute_vulnerability_risk_class_categories():
    """Risk classes should be exactly 'lag', 'medel', 'hog'."""
    panel = _make_synthetic_panel()
    results = estimate_main(panel)
    predictions = predict_2025(results, panel)
    vuln = compute_vulnerability(predictions)
    assert set(vuln["risk_class"].unique()) == {"lag", "medel", "hog"}


def test_compute_vulnerability_risk_class_ordered():
    """Risk class should be an ordered Categorical."""
    panel = _make_synthetic_panel()
    results = estimate_main(panel)
    predictions = predict_2025(results, panel)
    vuln = compute_vulnerability(predictions)
    assert vuln["risk_class"].cat.ordered


def test_compute_vulnerability_all_ranks_unique_or_tied():
    """Every rank should be a positive integer <= n_entities."""
    panel = _make_synthetic_panel()
    results = estimate_main(panel)
    predictions = predict_2025(results, panel)
    vuln = compute_vulnerability(predictions)
    n = len(vuln)
    assert vuln["vulnerability_rank"].min() >= 1
    assert vuln["vulnerability_rank"].max() <= n


def test_compute_vulnerability_z_score_mean_near_zero():
    """Mean of vulnerability_score (z-score) should be approximately 0."""
    panel = _make_synthetic_panel()
    results = estimate_main(panel)
    predictions = predict_2025(results, panel)
    vuln = compute_vulnerability(predictions)
    assert abs(vuln["vulnerability_score"].mean()) < 1e-10
