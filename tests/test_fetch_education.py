"""Tests for the UF0506 education fetcher.

This module had no test file before 2026-09-07; it was added with the
disclosure-protection tripwire below.  No test touches the network.
"""

import pandas as pd
import pytest

from src.fetch import fetch_education as fe


# ---------------------------------------------------------------------------
# Tripwire for the METHODOLOGY §12.8 failure mode in this table.
# edu_share sums roughly 640 cells per kommun (40 ages x 8 levels x 2 sexes),
# so it is the most exposed of the four fetchers if SCB ever starts protecting
# UF0506 cells the way it protects BefolkningCKM.  Verified live 2026-09-07:
# the sum of single ages 16-74 equals the published 'tot16-74' exactly, for
# all 290 kommuner in both 2024 and 2025.  This check keeps that true.
# ---------------------------------------------------------------------------


class TestUnprotectedTableProbe:
    def _counts(self, values):
        return pd.DataFrame(
            {
                "kommun_kod": ["0114", "0180"],
                "summed": values,
                "published": [5000.0, 400_000.0],
            }
        )

    def test_passes_when_the_parts_equal_the_published_total(self):
        fe._verify_probe_totals(self._counts([5000.0, 400_000.0]), 2025)

    def test_raises_when_the_table_has_become_protected(self):
        with pytest.raises(ValueError, match="disclosure"):
            fe._verify_probe_totals(self._counts([4993.0, 400_000.0]), 2025)

    def test_names_the_offending_kommun(self):
        with pytest.raises(ValueError, match="0114"):
            fe._verify_probe_totals(self._counts([4993.0, 400_000.0]), 2025)
