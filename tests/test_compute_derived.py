"""Tests for src.clean.compute_derived.

Focused on the population total, which METHODOLOGY §12.8 moved off a
client-side sum and onto SCB's published aggregate.
"""

import pandas as pd
import pytest

from src.clean.compute_derived import (
    compute_dependency_ratio,
    compute_population_growth,
)


def _long(values_by_year: dict[int, tuple[int, int, int]]) -> pd.DataFrame:
    rows = []
    for year, (young, working, old) in values_by_year.items():
        for group, value in zip(("0-19", "20-64", "65+"), (young, working, old)):
            rows.append(
                {"kommun_kod": "2513", "year": year, "age_group": group, "population": value}
            )
    return pd.DataFrame(rows)


class TestPopulationTotalSource:
    """The total comes from the publisher when it is supplied."""

    def test_falls_back_to_summing_when_no_totals_are_given(self):
        out = compute_population_growth(_long({2024: (700, 1800, 701)}))
        assert out.loc[0, "population"] == 3201

    def test_prefers_the_published_total_over_the_sum(self):
        """Överkalix as measured: the parts sum to 3 151, SCB publishes 3 183."""
        totals = pd.DataFrame(
            {"kommun_kod": ["2513"], "year": [2025], "population": [3183]}
        )
        out = compute_population_growth(_long({2025: (700, 1800, 651)}), totals=totals)
        assert out.loc[0, "population"] == 3183

    def test_growth_is_computed_from_the_published_totals(self):
        """The defect in one number: -1.56 % summed against -0.56 % published."""
        totals = pd.DataFrame(
            {
                "kommun_kod": ["2513", "2513"],
                "year": [2024, 2025],
                "population": [3201, 3183],
            }
        )
        long = _long({2024: (700, 1800, 701), 2025: (700, 1800, 651)})

        summed = compute_population_growth(long)
        published = compute_population_growth(long, totals=totals)

        assert summed.loc[summed.year == 2025, "population_growth_pct"].iloc[0] == pytest.approx(-1.5620, abs=1e-3)
        assert published.loc[published.year == 2025, "population_growth_pct"].iloc[0] == pytest.approx(-0.5623, abs=1e-3)

    def test_raises_when_the_published_totals_do_not_cover_every_row(self):
        totals = pd.DataFrame(
            {"kommun_kod": ["2513"], "year": [2024], "population": [3201]}
        )
        with pytest.raises(ValueError, match="published total"):
            compute_population_growth(
                _long({2024: (700, 1800, 701), 2025: (700, 1800, 651)}), totals=totals
            )


class TestDependencyRatioUnaffected:
    """The ratio still comes from the age groups; only the total moved."""

    def test_ratio_is_computed_from_the_age_groups(self):
        out = compute_dependency_ratio(_long({2024: (700, 1800, 701)}))
        assert out.loc[0, "dependency_ratio"] == pytest.approx((700 + 701) / 1800)
