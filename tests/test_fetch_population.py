"""Unit tests for the BE0101 population fetcher.

Covers the two-table split introduced by METHODOLOGY §13.2.  SCB froze
BefolkningNy at 2024 and published 2025 in a new parallel table, BefolkningCKM,
which differs in three ways that would each corrupt the panel silently:

  * a different ContentsCode for Folkmangd (000007ME, not BE0101N1),
  * Civilstand and Alder no longer eliminate, so both must be selected
    explicitly and the extra Civilstand column must not be read as the value,
  * the open-ended age code is '100+1', not '100+'.

No test touches the network.
"""

import pandas as pd
import pytest

from src.fetch import fetch_population as fp


def _meta(
    tid: list[str],
    contents: list[tuple[str, str]],
    ages: list[str],
    civilstand_eliminates: bool,
    sexes: list[str] | None = None,
) -> dict:
    """A minimal BE0101 metadata dict shaped like the real API response."""
    if sexes is None:
        sexes = ["TotSa", "1", "2"]
    return {
        "variables": [
            {"code": "Region", "values": ["0114", "0180", "00"], "valueTexts": ["a", "b", "riket"]},
            {
                "code": "Civilstand",
                "values": ["SC", "OG", "G"],
                "valueTexts": ["totalt, samtliga civilstånd", "ogifta", "gifta"],
                "elimination": civilstand_eliminates,
            },
            {"code": "Alder", "values": ages, "valueTexts": ages},
            {"code": "Kon", "values": sexes, "valueTexts": ["tot", "män", "kvinnor"][: len(sexes)]},
            {
                "code": "ContentsCode",
                "values": [c for c, _ in contents],
                "valueTexts": [t for _, t in contents],
            },
            {"code": "Tid", "values": tid, "valueTexts": tid},
        ]
    }


_OLD_META = _meta(
    tid=[str(y) for y in range(1968, 2025)],
    contents=[("BE0101N1", "Folkmängd"), ("BE0101N2", "Folkökning")],
    ages=[str(a) for a in range(0, 100)] + ["100+", "tot"],
    civilstand_eliminates=True,
    # BefolkningNy really does offer no sex total — verified live 2026-09-07.
    sexes=["1", "2"],
)
_NEW_META = _meta(
    tid=["2025"],
    contents=[("000007ME", "Folkmängd"), ("000007MG", "Folkökning")],
    ages=[str(a) for a in range(0, 100)] + ["100+1", "TOT1", "5-9"],
    civilstand_eliminates=False,
)


class TestAgeCodeMapping:
    """Both tables' open-ended age codes must land in 65+."""

    @pytest.mark.parametrize("code", ["100+", "100+1"])
    def test_open_ended_codes_map_to_65_plus(self, code):
        assert fp._age_code_to_group(code) == "65+"

    @pytest.mark.parametrize(
        "code,expected", [("0", "0-19"), ("19", "0-19"), ("20", "20-64"), ("64", "20-64"), ("65", "65+")]
    )
    def test_single_year_codes_unchanged(self, code, expected):
        assert fp._age_code_to_group(code) == expected


class TestContentsCode:
    """The population metric is resolved from metadata, never hardcoded."""

    def test_resolves_folkmangd_in_each_table(self):
        assert fp._contents_code(_OLD_META) == "BE0101N1"
        assert fp._contents_code(_NEW_META) == "000007ME"

    def test_never_selects_folkokning(self):
        """Folkokning is population *change* — using it would be silent nonsense."""
        assert fp._contents_code(_NEW_META) != "000007MG"


class TestAgeCodeSelection:
    """Each table is queried with the age codes it actually offers."""

    def test_old_table_uses_plain_open_ended_code(self):
        codes = fp._age_codes(_OLD_META)
        assert "100+" in codes and "100+1" not in codes
        assert len(codes) == 101

    def test_new_table_uses_suffixed_open_ended_code(self):
        codes = fp._age_codes(_NEW_META)
        assert "100+1" in codes and "100+" not in codes
        assert len(codes) == 101

    def test_excludes_aggregate_age_bands(self):
        """'TOT1' and '5-9' would double-count if requested alongside single years."""
        codes = fp._age_codes(_NEW_META)
        assert "TOT1" not in codes
        assert "5-9" not in codes


class TestBuildYearQuery:
    """Civilstand must be pinned to its total when the dimension does not eliminate."""

    def test_selects_civilstand_total_for_the_new_table(self):
        query = fp._build_year_query(_NEW_META, ["0114"], 2025)
        civil = next(d for d in query["query"] if d["code"] == "Civilstand")
        assert civil["selection"]["values"] == ["SC"]

    def test_omits_civilstand_when_it_eliminates(self):
        query = fp._build_year_query(_OLD_META, ["0114"], 2024)
        assert not [d for d in query["query"] if d["code"] == "Civilstand"]

    def test_requests_the_requested_year(self):
        query = fp._build_year_query(_NEW_META, ["0114"], 2025)
        tid = next(d for d in query["query"] if d["code"] == "Tid")
        assert tid["selection"]["values"] == ["2025"]


class TestYearRouting:
    """Each year goes to whichever table actually carries it."""

    def test_routes_across_the_2024_2025_boundary(self, monkeypatch):
        served = {fp._PRIMARY_TABLE_URL: _OLD_META, fp._RECENT_TABLE_URL: _NEW_META}

        def fake_metadata(url):
            if url not in served:  # any other candidate behaves as unreachable
                raise ValueError(f"HTTP 400 for {url}")
            return served[url]

        monkeypatch.setattr(fp, "fetch_metadata", fake_metadata)

        routing = fp._resolve_tables([2023, 2024, 2025])

        assert routing[2023][0] == fp._PRIMARY_TABLE_URL
        assert routing[2024][0] == fp._PRIMARY_TABLE_URL
        assert routing[2025][0] == fp._RECENT_TABLE_URL

    def test_raises_for_a_year_no_table_carries(self, monkeypatch):
        served = {fp._PRIMARY_TABLE_URL: _OLD_META, fp._RECENT_TABLE_URL: _NEW_META}

        def fake_metadata(url):
            if url not in served:  # any other candidate behaves as unreachable
                raise ValueError(f"HTTP 400 for {url}")
            return served[url]

        monkeypatch.setattr(fp, "fetch_metadata", fake_metadata)

        with pytest.raises(ValueError, match="2026"):
            fp._resolve_tables([2024, 2026])


class TestAggregation:
    """The extra Civilstand column must not be mistaken for the value column."""

    def test_ignores_civilstand_column(self):
        raw = pd.DataFrame(
            {
                "Region": ["0114", "0114"],
                "Civilstand": ["SC", "SC"],
                "Alder": ["10", "70"],
                "Kon": ["1", "1"],
                "Tid": ["2025", "2025"],
                "000007ME": ["100", "50"],
            }
        )
        out = fp._aggregate_to_age_groups(raw)
        assert set(out["age_group"]) == {"0-19", "65+"}
        assert out.loc[out.age_group == "0-19", "population"].iloc[0] == 100
        assert out.loc[out.age_group == "65+", "population"].iloc[0] == 50

    def test_sums_across_sexes(self):
        raw = pd.DataFrame(
            {
                "Region": ["0114", "0114"],
                "Alder": ["30", "30"],
                "Kon": ["1", "2"],
                "Tid": ["2024", "2024"],
                "BE0101N1": ["7", "5"],
            }
        )
        out = fp._aggregate_to_age_groups(raw)
        assert out.loc[out.age_group == "20-64", "population"].iloc[0] == 12


# ---------------------------------------------------------------------------
# METHODOLOGY §12.8 — BefolkningCKM is disclosure-protected, so its parts do
# not sum to its totals.  Read the total from the publisher; read the age
# groups from the coarsest aligned bands the table offers.
# ---------------------------------------------------------------------------

_FIVE_YEAR_BANDS = ["-4"] + [f"{lo}-{lo + 4}" for lo in range(5, 100, 5)] + ["100+5"]

_BANDED_META = _meta(
    tid=["2025"],
    contents=[("000007ME", "Folkmängd"), ("000007MG", "Folkökning")],
    ages=[str(a) for a in range(0, 100)]
    + ["100+1", "100+5", "100+10", "TotSA", "TOT1", "20-29", "60-69"]
    + _FIVE_YEAR_BANDS[:-1],
    civilstand_eliminates=False,
)


class TestAgeBandSelection:
    """Prefer 5-year bands: fewer summed cells means less accumulated
    disclosure noise.  Fall back to single years when the table has no bands."""

    def test_prefers_five_year_bands_when_the_table_offers_them(self):
        codes = fp._age_codes(_BANDED_META)
        assert "-4" in codes and "95-99" in codes
        assert "30" not in codes, "single years must not be mixed with bands"

    def test_falls_back_to_single_years_when_no_bands_exist(self):
        codes = fp._age_codes(_OLD_META)
        assert "30" in codes and codes[-1] == "100+"

    def test_selected_codes_cover_every_age_exactly_once(self):
        for meta in (_OLD_META, _NEW_META, _BANDED_META):
            covered: list[int] = []
            for code in fp._age_codes(meta):
                lo, hi = fp._age_bounds(code)
                covered.extend(range(lo, min(hi, 100) + 1))
            assert sorted(covered) == list(range(0, 101)), (
                f"codes for this table do not partition 0–100: {fp._age_codes(meta)}"
            )

    def test_never_selects_a_band_that_straddles_a_group_boundary(self):
        """'60-69' would put 65–69 year-olds in the working-age denominator."""
        for code in fp._age_codes(_BANDED_META):
            assert code not in ("60-69", "20-29", "TOT1", "TotSA")


class TestAgeBounds:
    """Group assignment must reject any band spanning 20 or 65."""

    @pytest.mark.parametrize(
        "code,group",
        [("-4", "0-19"), ("15-19", "0-19"), ("20-24", "20-64"),
         ("60-64", "20-64"), ("65-69", "65+"), ("100+5", "65+"), ("7", "0-19")],
    )
    def test_bands_map_to_the_group_they_lie_inside(self, code, group):
        assert fp._age_code_to_group(code) == group

    @pytest.mark.parametrize("code", ["60-69", "15-24", "0-24"])
    def test_straddling_bands_raise_rather_than_silently_mis_assign(self, code):
        with pytest.raises(ValueError, match="straddles"):
            fp._age_code_to_group(code)


class TestPublishedTotalQuery:
    """The total comes from the publisher's own aggregate, never from a sum."""

    def test_uses_the_tables_own_total_codes(self):
        q = fp._build_total_query(_BANDED_META, ["0114"], 2025)
        dims = {d["code"]: d["selection"]["values"] for d in q["query"]}
        assert dims["Alder"] == ["TotSA"]
        assert dims["Kon"] == ["TotSa"]
        assert dims["Civilstand"] == ["SC"]
        assert dims["ContentsCode"] == ["000007ME"]

    def test_sums_sexes_when_the_old_table_offers_no_sex_total(self):
        q = fp._build_total_query(_OLD_META, ["0114"], 2024)
        dims = {d["code"]: d["selection"]["values"] for d in q["query"]}
        assert dims["Alder"] == ["tot"]
        assert dims["Kon"] == ["1", "2"]
        assert "Civilstand" not in dims, "eliminating dimensions stay out"

    def test_raises_when_no_total_age_code_exists(self):
        meta = _meta(
            tid=["2025"], contents=[("X", "Folkmängd")],
            ages=[str(a) for a in range(0, 100)] + ["100+1"],
            civilstand_eliminates=False,
        )
        with pytest.raises(ValueError, match="total"):
            fp._build_total_query(meta, ["0114"], 2025)


class TestTotalFromRaw:
    def test_sums_the_sex_rows_of_the_old_table(self):
        raw = pd.DataFrame(
            {"Region": ["0114", "0114"], "Alder": ["tot", "tot"],
             "Kon": ["1", "2"], "Tid": ["2024", "2024"], "BE0101N1": ["7", "5"]}
        )
        out = fp._total_from_raw(raw)
        assert out.loc[0, "population"] == 12
        assert list(out.columns) == ["kommun_kod", "year", "population"]

    def test_reads_a_single_aggregate_row_of_the_new_table(self):
        raw = pd.DataFrame(
            {"Region": ["0114"], "Civilstand": ["SC"], "Alder": ["TotSA"],
             "Kon": ["TotSa"], "Tid": ["2025"], "000007ME": ["3183"]}
        )
        out = fp._total_from_raw(raw)
        assert out.loc[0, "population"] == 3183


class TestAggregateConsistency:
    """The check that would have caught §12.8 on the day it landed."""

    # One small kommun plus a large one, so the national deviation behaves the
    # way it does on the real 290: per-kommun noise cancels out. Measured
    # 2026-09-07 — 1.005 % in the worst kommun, 0.0012 % nationally.
    def _frames(self, small_summed: int, large_summed: int = 999_239):
        groups = pd.DataFrame(
            {
                "kommun_kod": ["2513"] * 3 + ["0180"] * 3,
                "year": [2025] * 6,
                "age_group": ["0-19", "20-64", "65+"] * 2,
                "population": [700, 1800, small_summed - 2500,
                               200_000, 600_000, large_summed - 800_000],
            }
        )
        totals = pd.DataFrame(
            {"kommun_kod": ["2513", "0180"], "year": [2025, 2025],
             "population": [3183, 999_239]}
        )
        return groups, totals

    def test_passes_when_the_sum_matches_the_published_total(self):
        fp._verify_against_published_totals(*self._frames(3183))

    def test_passes_on_disclosure_noise_within_tolerance(self):
        """Överkalix as measured: 32 people short on 3 183, 1.005 %."""
        fp._verify_against_published_totals(*self._frames(3151))

    def test_raises_when_a_kommun_deviates_beyond_tolerance(self):
        with pytest.raises(ValueError, match="published total"):
            fp._verify_against_published_totals(*self._frames(3100))

    def test_raises_on_the_civilstand_quadrupling_failure_mode(self):
        with pytest.raises(ValueError, match="published total"):
            fp._verify_against_published_totals(*self._frames(12_732, 3_996_956))


class TestFetchPopulationTotal:
    """The public total fetcher routes years the same way the group fetcher does."""

    def _patch(self, monkeypatch, captured):
        def fake_metadata(url):
            return _NEW_META if "CKM" in url else _OLD_META

        def fake_query(url, query):
            captured.append((url, query))
            year = query["query"][-1]["selection"]["values"][0]
            sexes = [
                d for d in query["query"] if d["code"] == "Kon"
            ][0]["selection"]["values"]
            return pd.DataFrame(
                {
                    "Region": ["0114"] * len(sexes),
                    "Alder": ["tot"] * len(sexes),
                    "Kon": sexes,
                    "Tid": [year] * len(sexes),
                    "value": ["10"] * len(sexes),
                }
            )

        monkeypatch.setattr(fp, "fetch_metadata", fake_metadata)
        monkeypatch.setattr(fp, "query_pxweb", fake_query)
        monkeypatch.setattr(fp, "is_cache_fresh", lambda *a, **k: False)
        monkeypatch.setattr(fp, "save_df_cache", lambda *a, **k: None)

    def test_returns_one_row_per_kommun_year(self, monkeypatch):
        captured: list = []
        self._patch(monkeypatch, captured)
        out = fp.fetch_population_total([2024, 2025])
        assert list(out.columns) == ["kommun_kod", "year", "population"]
        assert len(out) == 2

    def test_sums_the_sex_rows_of_the_old_table(self, monkeypatch):
        captured: list = []
        self._patch(monkeypatch, captured)
        out = fp.fetch_population_total([2024])
        assert out.loc[0, "population"] == 20, "män + kvinnor must be summed"

    def test_routes_each_year_to_the_table_that_carries_it(self, monkeypatch):
        captured: list = []
        self._patch(monkeypatch, captured)
        fp.fetch_population_total([2024, 2025])
        urls = {q["query"][-1]["selection"]["values"][0]: u for u, q in captured}
        assert "CKM" not in urls["2024"]
        assert "CKM" in urls["2025"]


class TestCacheShapeGuard:
    """A cached response fetched under a different query shape must not be reused.

    Changing the age codes from single years to 5-year bands changes what the
    cached JSON contains while leaving it 'fresh' by age.  Reusing it would
    silently keep the old, noisier aggregation — the same class of bug as the
    stale skattekraft cache that T0.1 guarded against.
    """

    def _cached(self, ages):
        return pd.DataFrame(
            {
                "Region": ["0114"] * len(ages),
                "Alder": ages,
                "Kon": ["1"] * len(ages),
                "Tid": ["2025"] * len(ages),
                "000007ME": ["1"] * len(ages),
            }
        )

    def test_accepts_a_cache_matching_the_current_age_codes(self):
        assert fp._cache_matches_query(self._cached(["-4", "5-9"]), ["-4", "5-9"])

    def test_rejects_a_cache_built_from_single_years(self):
        assert not fp._cache_matches_query(
            self._cached(["0", "1", "2"]), ["-4", "5-9"]
        )

    def test_rejects_a_cache_missing_an_age_code(self):
        assert not fp._cache_matches_query(self._cached(["-4"]), ["-4", "5-9"])

    def test_rejects_a_cache_without_an_age_column(self):
        assert not fp._cache_matches_query(
            pd.DataFrame({"Region": ["0114"]}), ["-4"]
        )
