"""Tests for src.ui.filters — narrowing a table to chosen kommuner.

The position-band pills answer "show me kommuner *like* this one". This filter
answers the other question users arrive with: "show me *these* kommuner",
by name, so a controller can put their own kommun next to three neighbours
without scrolling 290 rows.

The empty selection is the case worth locking. Streamlit hands back an empty
list both when nothing has been chosen yet and when the user clears the box,
and in the dashboard's existing sidebar convention empty means "all" rather
than "none" -- the pages must never render an empty table by default.
"""

import pandas as pd
import pytest

from src.ui.filters import apply_kommun_filter


@pytest.fixture
def frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "kommun_kod": ["0180", "1480", "2523", "1272"],
            "kommun_name": ["Stockholm", "Göteborg", "Gällivare", "Bromölla"],
            "relative_position": [130.0, 110.0, 95.0, 88.0],
        }
    )


class TestSelection:
    def test_keeps_only_the_chosen_kommuner(self, frame):
        out = apply_kommun_filter(frame, ["Göteborg", "Bromölla"])
        assert list(out["kommun_name"]) == ["Göteborg", "Bromölla"]

    def test_keeps_a_single_choice(self, frame):
        out = apply_kommun_filter(frame, ["Gällivare"])
        assert list(out["kommun_name"]) == ["Gällivare"]

    def test_preserves_the_incoming_row_order(self, frame):
        """The caller sorts before filtering; the filter must not reshuffle."""
        out = apply_kommun_filter(frame, ["Bromölla", "Stockholm"])
        assert list(out["kommun_name"]) == ["Stockholm", "Bromölla"]


class TestEmptySelection:
    def test_empty_list_means_all_not_none(self, frame):
        assert len(apply_kommun_filter(frame, [])) == len(frame)

    def test_none_means_all(self, frame):
        assert len(apply_kommun_filter(frame, None)) == len(frame)


class TestSafety:
    def test_unknown_names_are_ignored_rather_than_raising(self, frame):
        """A stale selection must not crash the page after a data refresh."""
        out = apply_kommun_filter(frame, ["Göteborg", "Kommun som inte finns"])
        assert list(out["kommun_name"]) == ["Göteborg"]

    def test_does_not_mutate_the_input(self, frame):
        before = frame.copy()
        apply_kommun_filter(frame, ["Stockholm"])
        pd.testing.assert_frame_equal(frame, before)

    def test_returns_a_new_object(self, frame):
        assert apply_kommun_filter(frame, []) is not frame
