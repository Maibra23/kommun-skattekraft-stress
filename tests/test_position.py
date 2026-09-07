"""Unit tests for the relative position and drift module.

Covers REMEDIATION_PLAN.md T1.1 — the product's new descriptive spine.

Position answers "where does this kommun stand against the national average"
and drift answers "which way is it moving", both from skattekraft alone. No
model is involved, which is the point: rank reliability is ~0.99 year over
year, against r = 0.016 for the model-derived forecast this replaces as the
headline.

Two position measures are carried deliberately and must not be conflated:
  * tax_base_index_riket - SCB's own published, population-weighted, integer
    index. The citable figure users arrive already knowing from Regionfakta.
  * relative_position    - kommun / unweighted cross-kommun mean x 100.
    Unrounded, for internal analysis, because SCB's integer rounding is too
    coarse to measure drift over short windows.

No test touches the network.
"""

import numpy as np
import pandas as pd
import pytest

from src.model import position as pos

_WINDOWS = (1, 3, 5, 10)


@pytest.fixture(scope="module")
def panel() -> pd.DataFrame:
    return pd.read_parquet(pos._PANEL_PATH)


@pytest.fixture(scope="module")
def result(panel) -> pd.DataFrame:
    return pos.build_position(panel)


def _synthetic() -> pd.DataFrame:
    """Three kommuner over four years with hand-checkable values."""
    rows = []
    for kod, base in [("0001", 100.0), ("0002", 200.0), ("0003", 300.0)]:
        for i, year in enumerate([2020, 2021, 2022, 2023]):
            rows.append(
                {
                    "kommun_kod": kod,
                    "year": year,
                    "tax_base_per_capita": base + 10 * i,
                    "tax_base_index_riket": round(base / 2),
                }
            )
    return pd.DataFrame(rows)


class TestShape:
    def test_has_the_required_columns(self, result):
        expected = ["kommun_kod", "year", "tax_base_index_riket", "relative_position"]
        expected += [f"drift_{w}y" for w in _WINDOWS]
        assert list(result.columns) == expected

    def test_one_row_per_kommun_year(self, result, panel):
        assert len(result) == len(panel)
        assert not result.duplicated(subset=["kommun_kod", "year"]).any()

    def test_covers_the_full_ragged_range_not_the_complete_case_year(self, result):
        """Position needs skattekraft only, so it must reach 2026.

        Truncating to complete_case_max_year (2024) would discard the two
        newest years for no reason - unemployment is irrelevant here.
        """
        assert result["year"].min() == 2010
        assert result["year"].max() == 2026


class TestRelativePosition:
    def test_riket_is_100_in_every_year(self, result):
        """The defining invariant: the unweighted mean is the denominator."""
        means = result.groupby("year")["relative_position"].mean()
        assert np.allclose(means, 100.0)

    def test_is_finer_than_scbs_rounded_index(self, result):
        """SCB publishes integers; drift over short windows needs more."""
        assert not np.allclose(
            result["relative_position"], result["relative_position"].round()
        )

    def test_tracks_scbs_index_closely(self, result):
        """Different denominators, so not equal - but the same phenomenon."""
        latest = result[result.year == 2024]
        assert latest["relative_position"].corr(latest["tax_base_index_riket"]) > 0.95

    def test_scb_index_is_passed_through_unchanged(self, result, panel):
        merged = result.merge(
            panel[["kommun_kod", "year", "tax_base_index_riket"]],
            on=["kommun_kod", "year"],
            suffixes=("_out", "_panel"),
        )
        pd.testing.assert_series_equal(
            merged["tax_base_index_riket_out"],
            merged["tax_base_index_riket_panel"],
            check_names=False,
        )

    def test_computed_against_the_unweighted_mean(self):
        df = pos.build_position(_synthetic())
        row = df[(df.kommun_kod == "0002") & (df.year == 2020)].iloc[0]
        # values are 100, 200, 300 -> mean 200 -> kommun 0002 sits exactly at riket
        assert row["relative_position"] == pytest.approx(100.0)


class TestDrift:
    def test_is_a_difference_in_index_points_not_a_growth_rate(self):
        df = pos.build_position(_synthetic())
        k1 = df[df.kommun_kod == "0001"].set_index("year")
        # 0001: values 100,110,120,130 against means 200,210,220,230
        # position 2020 = 50.000, position 2021 = 110/210*100 = 52.381
        expected = 110 / 210 * 100 - 100 / 200 * 100
        assert k1.loc[2021, "drift_1y"] == pytest.approx(expected)
        assert k1.loc[2021, "drift_1y"] == pytest.approx(2.381, abs=1e-3)

    def test_is_null_before_the_window_opens(self):
        df = pos.build_position(_synthetic())
        assert df[df.year == 2020]["drift_1y"].isna().all()
        assert df[df.year == 2021]["drift_1y"].notna().all()
        assert df["drift_10y"].isna().all()  # only four years of data

    def test_all_windows_are_present_on_the_real_panel(self, result):
        for w in _WINDOWS:
            col = f"drift_{w}y"
            assert result.loc[result.year == 2010 + w - 1, col].isna().all()
            assert result.loc[result.year == 2026, col].notna().all()

    def test_drift_sums_consistently_across_windows(self, result):
        """drift_3y at t must equal the sum of the three 1-year drifts."""
        piv = result.pivot_table(index="kommun_kod", columns="year", values="relative_position")
        for kod in list(piv.index[:5]):
            direct = piv.loc[kod, 2024] - piv.loc[kod, 2021]
            reported = result[(result.kommun_kod == kod) & (result.year == 2024)]["drift_3y"].iloc[0]
            assert reported == pytest.approx(direct)


class TestStability:
    """The claim that justifies making this the product's headline.

    These lock the position-derived findings in REMEDIATION_PLAN.md §1.2.
    They are deliberately *not* marked ``baseline``: unlike the model figures
    in tests/test_audit_baseline.py, these describe the descriptive spine,
    which the remediation keeps rather than retires. They should hold forever.

    Verified against the audit on 2026-09-07 — see the §13 entry for that date.
    """

    @staticmethod
    def _spearman(result, lag):
        piv = result.pivot_table(index="kommun_kod", columns="year", values="relative_position")
        pairs = [(y, y + lag) for y in piv.columns if y + lag in piv.columns]
        return np.mean([piv[a].corr(piv[b], method="spearman") for a, b in pairs])

    def test_one_year_rank_stability_above_098(self, result):
        """Audit: 0.992. Recomputed 2026-09-07: 0.9924."""
        assert self._spearman(result, 1) > 0.98

    def test_ten_year_rank_stability_above_090(self, result):
        """Audit: 0.915. Recomputed 2026-09-07: 0.9299.

        The 0.008 gap against the audit is windowing detail (which year pairs
        are averaged), not a disagreement — both say the same thing.
        """
        assert self._spearman(result, 10) > 0.90

    def test_variance_in_position_is_overwhelmingly_between_kommuner(self, result):
        """Audit: 98.3 %. Recomputed 2026-09-07: 98.0 % on the full panel.

        This is the single number that condemns the old specification: entity
        fixed effects delete this share of the variation the ranking is about.
        """
        grand = result["relative_position"].mean()
        kommun_means = result.groupby("kommun_kod")["relative_position"].mean()
        n = result.groupby("kommun_kod").size()
        between = (n * (kommun_means - grand) ** 2).sum()
        total = ((result["relative_position"] - grand) ** 2).sum()
        assert between / total > 0.95


class TestGrowthIsNotPredictable:
    """The other half of the argument: why position replaced growth as the target.

    Position is near-frozen (above); the growth rate the old model predicted is
    serially unpredictable. Both must hold for the remediation's premise.
    """

    def test_growth_persistence_is_near_zero_after_removing_year_effects(self, panel):
        """Audit: −0.06. Recomputed 2026-09-07: −0.0537.

        **The demeaning is the whole point and the audit's table omits it.**
        Raw pooled autocorrelation is +0.153, which looks like persistence but
        is national wage growth moving every kommun together. What a two-way FE
        model could actually exploit is what remains after the year effect is
        removed, and that is indistinguishable from noise.
        """
        d = panel.dropna(subset=["tax_base_growth_pct"]).sort_values(
            ["kommun_kod", "year"]
        ).copy()
        d["demeaned"] = d["tax_base_growth_pct"] - d.groupby("year")[
            "tax_base_growth_pct"
        ].transform("mean")
        d["lagged"] = d.groupby("kommun_kod")["demeaned"].shift(1)
        d = d.dropna(subset=["demeaned", "lagged"])

        persistence = d["demeaned"].corr(d["lagged"])
        assert abs(persistence) < 0.15, (
            f"Year-demeaned growth persistence is {persistence:+.4f}. The audit "
            "measured -0.06; if this has become substantial, the claim that the "
            "growth target is unpredictable no longer holds."
        )
