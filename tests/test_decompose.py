"""Tests for src.model.decompose — uses a small synthetic panel, no API calls.

Tests cover: decomposition columns sum to approximately the total predicted
gap for each municipality, national-mean municipality has all contribution
columns near zero, residual absorbs the correct amount, output DataFrame has
exactly the required columns, and no NaN values appear in the output.
"""

import numpy as np
import pandas as pd
import pytest

from src.model.estimate import X_VARS, Y_VAR, estimate_main
from src.model.decompose import decompose_2024_gaps


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
# decompose_2024_gaps
# ---------------------------------------------------------------------------


def test_decompose_returns_correct_columns():
    panel = _make_synthetic_panel()
    results = estimate_main(panel)
    decomp = decompose_2024_gaps(results, panel)
    expected_cols = {
        "kommun_kod",
        "kommun_name",
        "total_gap",
        "decomp_unemployment",
        "decomp_dependency",
        "decomp_population",
        "decomp_education",
        "decomp_residual",
    }
    assert expected_cols == set(decomp.columns)


def test_decompose_row_count():
    panel = _make_synthetic_panel()
    results = estimate_main(panel)
    decomp = decompose_2024_gaps(results, panel)
    n_entities = panel["kommun_kod"].nunique()
    assert len(decomp) == n_entities


def test_decompose_no_nan():
    panel = _make_synthetic_panel()
    results = estimate_main(panel)
    decomp = decompose_2024_gaps(results, panel)
    assert decomp.isna().sum().sum() == 0


def test_decompose_components_sum_to_total_gap():
    """Sum of all five decomposition components must equal total_gap exactly."""
    panel = _make_synthetic_panel()
    results = estimate_main(panel)
    decomp = decompose_2024_gaps(results, panel)
    component_sum = (
        decomp["decomp_unemployment"]
        + decomp["decomp_dependency"]
        + decomp["decomp_population"]
        + decomp["decomp_education"]
        + decomp["decomp_residual"]
    )
    assert np.allclose(component_sum, decomp["total_gap"], atol=1e-10)


def test_decompose_total_gap_sums_to_zero():
    """Mean of total_gap across all kommuner should be approximately 0.

    Since total_gap = actual - national_mean, the mean across all kommuner
    should be zero by construction.
    """
    panel = _make_synthetic_panel()
    results = estimate_main(panel)
    decomp = decompose_2024_gaps(results, panel)
    assert abs(decomp["total_gap"].mean()) < 1e-10


def test_decompose_structural_contributions_sum_to_zero():
    """Each structural decomposition column should sum to approximately 0.

    Because each contribution is beta * (X_i - mean(X)), the mean across
    all municipalities is beta * 0 = 0.
    """
    panel = _make_synthetic_panel()
    results = estimate_main(panel)
    decomp = decompose_2024_gaps(results, panel)
    for col in [
        "decomp_unemployment",
        "decomp_dependency",
        "decomp_population",
        "decomp_education",
    ]:
        assert abs(decomp[col].mean()) < 1e-10, (
            f"Mean of {col} is {decomp[col].mean():.2e}, expected ~0"
        )


def test_decompose_residual_mean_near_zero():
    """Residual contributions should also average to approximately 0.

    Since total_gap averages to 0 and all structural contributions average
    to 0, the residual must also average to 0.
    """
    panel = _make_synthetic_panel()
    results = estimate_main(panel)
    decomp = decompose_2024_gaps(results, panel)
    assert abs(decomp["decomp_residual"].mean()) < 1e-10


def test_decompose_raises_on_missing_2024():
    """Should raise ValueError if 2024 is not in the panel."""
    panel = _make_synthetic_panel()
    # Remove 2024 data
    panel_no_2024 = panel[panel["year"] != 2024]
    results = estimate_main(panel)
    with pytest.raises(ValueError, match="No 2024 observations"):
        decompose_2024_gaps(results, panel_no_2024)
