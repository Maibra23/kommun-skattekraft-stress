"""Unit tests for the AA0003 unemployment fetcher.

Covers the snapshot/live split introduced by REMEDIATION_PLAN.md T0.2a
(option A).  SCB withdrew the AA0003X archive, so 2010-2021 can no longer be
fetched from source and is served from a committed snapshot; 2022 onwards
still comes from the live AA0003B table.

No test touches the network.
"""

import pandas as pd
import pytest

from src.fetch import fetch_unemployment as fu

_SNAPSHOT_YEARS = list(range(2010, 2022))
_EXPECTED_ROWS = 290 * len(_SNAPSHOT_YEARS)


@pytest.fixture(scope="module")
def snapshot() -> pd.DataFrame:
    """The committed snapshot, loaded through the module's own reader."""
    return fu._load_snapshot(_SNAPSHOT_YEARS)


@pytest.fixture(scope="module")
def committed_panel() -> pd.DataFrame:
    """Historical unemployment as it stands in the committed panel."""
    panel = pd.read_parquet(fu._PROJECT_ROOT / "data/processed/panel.parquet")
    return panel.loc[
        panel["year"] <= fu._SNAPSHOT_LAST_YEAR,
        ["kommun_kod", "year", "unemployment_rate"],
    ]


class TestSnapshotFile:
    """The snapshot is now the sole surviving source for 2010-2021."""

    def test_covers_every_kommun_year(self, snapshot):
        assert len(snapshot) == _EXPECTED_ROWS
        assert sorted(snapshot["year"].unique()) == _SNAPSHOT_YEARS
        assert snapshot.groupby("year")["kommun_kod"].nunique().eq(290).all()

    def test_has_no_missing_rates(self, snapshot):
        assert snapshot["unemployment_rate"].notna().all()

    def test_matches_the_committed_panel_exactly(self, snapshot, committed_panel):
        """The snapshot is a faithful copy, not a re-derivation.

        Any divergence means the historical series changed silently — the
        one failure mode option A exists to prevent.
        """
        merged = committed_panel.merge(
            snapshot, on=["kommun_kod", "year"], suffixes=("_panel", "_snap")
        )
        assert len(merged) == _EXPECTED_ROWS
        pd.testing.assert_series_equal(
            merged["unemployment_rate_panel"],
            merged["unemployment_rate_snap"],
            check_names=False,
        )


class TestLoadSnapshot:
    """The reader filters and types the snapshot the same way the API path does."""

    def test_returns_only_requested_years(self):
        df = fu._load_snapshot([2010, 2015])
        assert sorted(df["year"].unique()) == [2010, 2015]
        assert len(df) == 580

    def test_kommun_kod_is_zero_padded_string(self, snapshot):
        assert snapshot["kommun_kod"].map(len).eq(4).all()
        assert "0114" in set(snapshot["kommun_kod"])

    def test_raises_for_a_year_the_snapshot_cannot_serve(self):
        """2009 predates the panel; failing loudly beats returning short."""
        with pytest.raises(ValueError, match="2009"):
            fu._load_snapshot([2009, 2010])


class TestFetchRouting:
    """Historical years must never reach the network; recent years must."""

    @staticmethod
    def _live_frame(year: int) -> pd.DataFrame:
        codes = sorted({f"{i:04d}" for i in range(1, 291)})
        return pd.DataFrame(
            {
                "Region": codes,
                "Tid": [str(year)] * 290,
                "000007K9": ["5.0"] * 290,
            }
        )

    def test_historical_years_do_not_touch_the_network(self, monkeypatch):
        def explode(*args, **kwargs):
            raise AssertionError("network call made for pre-2022 years")

        monkeypatch.setattr(fu, "_discover_table", explode)
        monkeypatch.setattr(fu, "query_pxweb", explode)
        monkeypatch.setattr(fu, "save_df_cache", lambda *a, **k: None)

        df = fu.fetch_unemployment(years=[2010, 2011], force_refresh=True)

        assert len(df) == 580
        assert sorted(df["year"].unique()) == [2010, 2011]

    def test_recent_years_come_from_the_live_table(self, monkeypatch):
        calls: list[list[int]] = []

        def fake_discover(subset_years, candidates):
            calls.append(sorted(subset_years))
            assert "AA0003B" in candidates[0], "must query the live table only"
            return candidates[0], "000007K9", list(subset_years), {}

        monkeypatch.setattr(fu, "_discover_table", fake_discover)
        monkeypatch.setattr(fu, "_build_query", lambda *a, **k: {})
        monkeypatch.setattr(fu, "query_pxweb", lambda url, body: self._live_frame(2022))
        monkeypatch.setattr(fu, "save_df_cache", lambda *a, **k: None)

        df = fu.fetch_unemployment(years=[2022], force_refresh=True)

        assert calls == [[2022]]
        assert len(df) == 290

    def test_spans_the_2021_2022_seam_in_one_call(self, monkeypatch):
        monkeypatch.setattr(
            fu,
            "_discover_table",
            lambda subset_years, candidates: (candidates[0], "000007K9", list(subset_years), {}),
        )
        monkeypatch.setattr(fu, "_build_query", lambda *a, **k: {})
        monkeypatch.setattr(fu, "query_pxweb", lambda url, body: self._live_frame(2022))
        monkeypatch.setattr(fu, "save_df_cache", lambda *a, **k: None)

        df = fu.fetch_unemployment(years=[2021, 2022], force_refresh=True)

        assert sorted(df["year"].unique()) == [2021, 2022]
        assert len(df) == 580
