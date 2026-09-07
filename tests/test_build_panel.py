"""Unit tests for the ragged panel builder.

Covers REMEDIATION_PLAN.md T0.2.  The four SCB sources refresh on different
cadences and no longer end in the same year (skattekraft 2026, population and
education 2025, unemployment 2024).  The panel must keep the newest skattekraft
rather than truncate every source to the shortest one, so it is deliberately
unbalanced at the top end.

No test touches the network.
"""

import pandas as pd
import pytest

from src.clean import build_panel as bp

# Sweden has exactly 290 kommuner and the builder asserts it, so the fixture
# carries a full set rather than a token few.
_KOMMUNER = [f"{i:04d}" for i in range(114, 404)]


def _frame(years: list[int], **columns) -> pd.DataFrame:
    """A tidy kommun-year frame carrying the given columns."""
    rows = [{"kommun_kod": k, "year": y} for k in _KOMMUNER for y in years]
    df = pd.DataFrame(rows)
    for name, value in columns.items():
        df[name] = value
    return df


@pytest.fixture
def sources() -> dict[str, pd.DataFrame]:
    """Four sources ending in three different years, as SCB now serves them."""
    skattekraft = _frame(list(range(2010, 2027)), tax_base_growth_pct=3.0,
                         tax_base_per_capita=250_000.0, tax_base_index_riket=100.0)
    # METHODOLOGY 6.1 asserts Danderyd tops the 2024 skattekraft; honour it so
    # the fixture exercises the real validator rather than a weakened one.
    skattekraft.loc[skattekraft.kommun_kod == "0162", "tax_base_per_capita"] = 480_000.0

    return {
        "skattekraft": skattekraft,
        "population": _frame(list(range(2010, 2026)), dependency_ratio=0.75,
                             population=10_000, population_growth_pct=0.5),
        "education": _frame(list(range(2010, 2026)), edu_share=0.28),
        "unemployment": _frame(list(range(2010, 2025)), unemployment_rate=6.0),
    }


@pytest.fixture
def names() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "kommun_kod": _KOMMUNER,
            "kommun_name": [f"Kommun {k}" for k in _KOMMUNER],
            "lan_kod": [k[:2] for k in _KOMMUNER],
            "lan_name": [f"Län {k[:2]}" for k in _KOMMUNER],
        }
    )


class TestMergeKeepsRaggedYears:
    """The newest skattekraft must survive the merge."""

    def test_panel_extends_to_the_widest_source(self, sources, names):
        panel = bp._merge_panel(sources, names)
        assert panel["year"].max() == 2026, "2026 skattekraft was truncated away"
        assert panel["year"].min() == 2010

    def test_every_year_has_every_kommun(self, sources, names):
        panel = bp._merge_panel(sources, names)
        assert panel.groupby("year")["kommun_kod"].nunique().eq(len(_KOMMUNER)).all()

    def test_short_sources_are_null_not_missing_rows(self, sources, names):
        """2025 and 2026 exist; unemployment is simply unknown there."""
        panel = bp._merge_panel(sources, names)
        assert panel.loc[panel.year == 2026, "unemployment_rate"].isna().all()
        assert panel.loc[panel.year == 2025, "unemployment_rate"].isna().all()
        assert panel.loc[panel.year == 2024, "unemployment_rate"].notna().all()
        assert panel.loc[panel.year == 2026, "edu_share"].isna().all()
        assert panel.loc[panel.year == 2025, "edu_share"].notna().all()

    def test_rows_without_the_spine_variable_are_dropped(self, sources, names):
        """A row with no skattekraft growth carries no information."""
        sources["skattekraft"].loc[
            sources["skattekraft"].year == 2026, "tax_base_growth_pct"
        ] = None
        panel = bp._merge_panel(sources, names)
        assert 2026 not in set(panel["year"])


class TestProvenance:
    """Downstream consumers must be able to state which year they used."""

    def test_records_each_source_max_year(self, sources):
        prov = bp._build_provenance(sources)
        assert prov["sources"]["skattekraft"]["max_year"] == 2026
        assert prov["sources"]["population"]["max_year"] == 2025
        assert prov["sources"]["unemployment"]["max_year"] == 2024

    def test_records_the_complete_case_year(self, sources, names):
        """The latest year where all four variables exist — what T2.1 must use."""
        prov = bp._build_provenance(sources)
        assert prov["complete_case_max_year"] == 2024

    def test_flags_the_panel_as_unbalanced(self, sources):
        prov = bp._build_provenance(sources)
        assert prov["balanced"] is False


class TestValidation:
    """Ragged tails are expected; holes inside a source's coverage are not."""

    def test_accepts_a_ragged_tail(self, sources, names):
        panel = bp._merge_panel(sources, names)
        bp._validate_panel(panel, bp._build_provenance(sources))  # must not raise

    def test_rejects_a_hole_inside_coverage(self, sources, names):
        panel = bp._merge_panel(sources, names)
        panel.loc[
            (panel.year == 2015) & (panel.kommun_kod == "0180"), "unemployment_rate"
        ] = None
        with pytest.raises(ValueError, match="unemployment_rate"):
            bp._validate_panel(panel, bp._build_provenance(sources))

    def test_rejects_a_missing_kommun(self, sources, names):
        panel = bp._merge_panel(sources, names)
        panel = panel[~((panel.year == 2024) & (panel.kommun_kod == "0180"))]
        with pytest.raises(ValueError, match="2024"):
            bp._validate_panel(panel, bp._build_provenance(sources))
