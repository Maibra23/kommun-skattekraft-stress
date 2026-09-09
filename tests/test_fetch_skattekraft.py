"""Unit tests for the OE0101 skattekraft fetcher.

Covers query construction, response cleaning and verification for the
two-metric fetch introduced by METHODOLOGY §13.2: skattekraft per
inhabitant (OE0101A0) alongside SCB's own published index, andel av
riksmedelvärdet (OE0101B0).

All tests operate on in-memory frames; none touch the network.
"""

import pandas as pd
import pytest

from src.fetch import fetch_skattekraft as fs


@pytest.fixture
def raw_response() -> pd.DataFrame:
    """A PxWeb response frame carrying both metrics, as query_pxweb returns it.

    Value columns are named by their ContentsCode; every value is a string.
    """
    return pd.DataFrame(
        {
            "Region": ["0162", "0162", "1782", "1782"],
            "Tid": ["2024", "2026", "2024", "2026"],
            "OE0101A0": ["481069", "516807", "189587", "206455"],
            "OE0101B0": ["191", "191", "75", "76"],
        }
    )


class TestBuildQuery:
    """The POST body must request both metrics in one call."""

    def test_requests_both_contents_codes(self):
        query = fs._build_query(
            ["OE0101A0", "OE0101B0"], [2024, 2025], ["0162", "1782"]
        )
        contents = next(
            dim for dim in query["query"] if dim["code"] == "ContentsCode"
        )
        assert contents["selection"]["values"] == ["OE0101A0", "OE0101B0"]

    def test_uses_explicit_region_items_not_value_set(self):
        """METHODOLOGY 12.1 — the vs: filter returns HTTP 400."""
        query = fs._build_query(["OE0101A0"], [2024], ["0162", "1782"])
        region = next(dim for dim in query["query"] if dim["code"] == "Region")
        assert region["selection"]["filter"] == "item"
        assert region["selection"]["values"] == ["0162", "1782"]

    def test_years_are_sorted_strings(self):
        query = fs._build_query(["OE0101A0"], [2026, 2009, 2024], ["0162"])
        tid = next(dim for dim in query["query"] if dim["code"] == "Tid")
        assert tid["selection"]["values"] == ["2009", "2024", "2026"]


class TestCleanResponse:
    """Value columns must be mapped by ContentsCode, never by position."""

    def test_maps_both_metrics_to_named_columns(self, raw_response):
        df = fs._clean_response(raw_response, "OE0101A0", "OE0101B0")
        assert list(df.columns) == [
            "kommun_kod",
            "year",
            "tax_base_per_capita",
            "tax_base_index_riket",
        ]

    def test_casts_types(self, raw_response):
        df = fs._clean_response(raw_response, "OE0101A0", "OE0101B0")
        assert df["year"].dtype.kind == "i"
        assert df["tax_base_per_capita"].dtype.kind == "f"
        assert df["tax_base_index_riket"].dtype.kind == "f"

    def test_preserves_values(self, raw_response):
        df = fs._clean_response(raw_response, "OE0101A0", "OE0101B0")
        danderyd_2026 = df[(df.kommun_kod == "0162") & (df.year == 2026)].iloc[0]
        assert danderyd_2026["tax_base_per_capita"] == pytest.approx(516807)
        assert danderyd_2026["tax_base_index_riket"] == pytest.approx(191)

    def test_zero_pads_kommun_kod(self):
        raw = pd.DataFrame(
            {
                "Region": ["114"],
                "Tid": ["2024"],
                "OE0101A0": ["250000"],
                "OE0101B0": ["99"],
            }
        )
        df = fs._clean_response(raw, "OE0101A0", "OE0101B0")
        assert df["kommun_kod"].iloc[0] == "0114"

    def test_index_column_optional(self, raw_response):
        """A response without the index metric still yields the per-capita frame."""
        single = raw_response.drop(columns=["OE0101B0"])
        df = fs._clean_response(single, "OE0101A0", "OE0101B0")
        assert df["tax_base_index_riket"].isna().all()
        assert df["tax_base_per_capita"].notna().all()

    def test_raises_when_per_capita_column_absent(self, raw_response):
        """Never silently substitute another metric for skattekraft."""
        broken = raw_response.drop(columns=["OE0101A0"])
        with pytest.raises(ValueError, match="OE0101A0"):
            fs._clean_response(broken, "OE0101A0", "OE0101B0")


class TestVerify:
    """Sanity checks must catch a wrong-metric or wrong-scale fetch."""

    @staticmethod
    def _frame(per_capita: float, index: float) -> pd.DataFrame:
        """A minimal 290-kommun 2024 frame with Danderyd on top."""
        codes = [f"{i:04d}" for i in range(1, 291)]
        rows = pd.DataFrame(
            {
                "kommun_kod": codes,
                "year": 2024,
                "tax_base_per_capita": 231_000.0,
                "tax_base_index_riket": 92.0,
            }
        )
        rows.loc[rows.kommun_kod == "0162", "tax_base_per_capita"] = per_capita
        rows.loc[rows.kommun_kod == "0162", "tax_base_index_riket"] = index
        return rows

    def test_accepts_plausible_data(self):
        fs._verify(self._frame(481_069, 191), [2024])

    def test_rejects_wrong_top_municipality(self):
        df = self._frame(481_069, 191)
        df.loc[df.kommun_kod == "0180", "tax_base_per_capita"] = 900_000
        with pytest.raises(ValueError, match="0162"):
            fs._verify(df, [2024])

    def test_rejects_implausible_index_scale(self):
        """A ratio fetched as a fraction rather than a percent must fail."""
        df = self._frame(481_069, 191)
        df["tax_base_index_riket"] = df["tax_base_index_riket"] / 100.0
        with pytest.raises(ValueError, match="index"):
            fs._verify(df, [2024])

    def test_skips_index_checks_when_column_absent(self):
        df = self._frame(481_069, 191).drop(columns=["tax_base_index_riket"])
        fs._verify(df, [2024])


class TestCoverage:
    """T0.1 extends the fetch window past the closed 2025 forecast horizon."""

    def test_default_years_reach_2026(self):
        assert max(fs._DEFAULT_YEARS) >= 2026

    def test_cache_schema_includes_index(self):
        assert "tax_base_index_riket" in fs._CACHE_DTYPES


# ---------------------------------------------------------------------------
# The publisher cross-check (METHODOLOGY §13.4, 2026-09-07 review).
# SCB's index and its per-capita values come from the same table as two
# separate ContentsCodes.  They must agree: index = 100 x kommun / riket,
# to within SCB's own integer rounding of the index.  Needs no extra query —
# riket is implied by the 290 kommuner already fetched.
# ---------------------------------------------------------------------------


def _consistent_frame(riket: float = 250_000.0) -> pd.DataFrame:
    per_capita = [riket * f for f in (0.75, 1.0, 1.25, 1.9)]
    return pd.DataFrame(
        {
            "kommun_kod": ["0001", "0002", "0003", "0004"],
            "year": [2024] * 4,
            "tax_base_per_capita": per_capita,
            "tax_base_index_riket": [round(100 * v / riket) for v in per_capita],
        }
    )


class TestIndexMatchesPerCapita:
    def test_passes_on_a_consistent_pair(self):
        fs._verify_index_matches_per_capita(_consistent_frame())

    def test_passes_when_only_rounding_separates_them(self):
        df = _consistent_frame(riket=251_437.0)
        fs._verify_index_matches_per_capita(df)

    def test_raises_when_the_index_is_a_fraction_not_a_percent(self):
        df = _consistent_frame()
        df["tax_base_index_riket"] = df["tax_base_index_riket"] / 100.0
        with pytest.raises(ValueError, match="index"):
            fs._verify_index_matches_per_capita(df)

    def test_raises_when_one_kommun_is_paired_with_the_wrong_value(self):
        """The failure mode the ContentsCode mapping exists to prevent."""
        df = _consistent_frame()
        df.loc[0, "tax_base_index_riket"] = df.loc[3, "tax_base_index_riket"]
        with pytest.raises(ValueError, match="index"):
            fs._verify_index_matches_per_capita(df)

    def test_skips_silently_when_the_index_is_absent(self):
        df = _consistent_frame().drop(columns="tax_base_index_riket")
        fs._verify_index_matches_per_capita(df)

    def test_skips_silently_when_the_index_is_entirely_null(self):
        df = _consistent_frame()
        df["tax_base_index_riket"] = None
        fs._verify_index_matches_per_capita(df)
