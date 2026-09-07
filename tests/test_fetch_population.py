"""Unit tests for the BE0101 population fetcher.

Covers the two-table split introduced by REMEDIATION_PLAN.md T0.2.  SCB froze
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
) -> dict:
    """A minimal BE0101 metadata dict shaped like the real API response."""
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
            {"code": "Kon", "values": ["TotSa", "1", "2"], "valueTexts": ["tot", "män", "kvinnor"]},
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
    ages=[str(a) for a in range(0, 100)] + ["100+"],
    civilstand_eliminates=True,
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
