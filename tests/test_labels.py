"""Tests for src.ui.labels — the single source of truth for user-facing strings.

These cover only the contract other modules and later tasks depend on, not the
wording of every string.
"""

import pytest

from src.ui.labels import SWEDISH_LABELS


_WITHIN_KEYS = [
    "within_section_title",
    "within_section_lead",
    "within_section_spec",
    "within_section_caveat",
]


def test_within_section_keys_exist_and_are_non_empty():
    for key in _WITHIN_KEYS:
        assert key in SWEDISH_LABELS, f"Missing label: {key}"
        assert SWEDISH_LABELS[key].strip(), f"Empty label: {key}"


def test_within_section_heading_matches_the_agreed_wording():
    """REMEDIATION_PLAN.md T2.4 specifies this heading verbatim, so that the
    within-time finding is visibly separated from the ranking."""
    assert SWEDISH_LABELS["within_section_title"] == "Samband inom kommuner över tid"


def test_within_section_caveat_denies_that_it_ranks_kommuner():
    """The whole point of the separation: these coefficients compare a kommun
    with itself over time and cannot order kommuner against each other."""
    caveat = SWEDISH_LABELS["within_section_caveat"].lower()
    assert "rangordna" in caveat


@pytest.mark.parametrize("key", _WITHIN_KEYS)
def test_within_section_labels_do_not_promise_a_forecast(key):
    """The 2025 forecast scored r = +0.016; no new string may advertise one."""
    text = SWEDISH_LABELS[key].lower()
    assert "prognos" not in text
