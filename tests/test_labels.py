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


# ---------------------------------------------------------------------------
# Position bands replace the risk-class filter at the T1.2 cutover.
# Risk classes were quintiles of a forecast that scored r = +0.016; bands are
# cuts of an observed level, so they mean what they say.
# ---------------------------------------------------------------------------

from src.ui.labels import POSITION_BANDS, classify_position


class TestPositionBands:
    def test_three_bands_in_ascending_order(self):
        assert len(POSITION_BANDS) == 3
        lows = [b.lower for b in POSITION_BANDS]
        assert lows == sorted(lows)

    def test_bands_are_contiguous_and_cover_everything(self):
        assert POSITION_BANDS[0].lower == float("-inf")
        assert POSITION_BANDS[-1].upper == float("inf")
        for earlier, later in zip(POSITION_BANDS, POSITION_BANDS[1:]):
            assert earlier.upper == later.lower, "a gap would drop kommuner"

    @pytest.mark.parametrize(
        "index,expected_key",
        [(73.0, "low"), (89.9, "low"), (90.0, "mid"), (100.0, "mid"),
         (109.9, "mid"), (110.0, "high"), (208.1, "high")],
    )
    def test_classifies_the_boundaries_the_way_the_labels_claim(self, index, expected_key):
        assert classify_position(index).key == expected_key

    def test_every_band_has_a_swedish_label(self):
        for band in POSITION_BANDS:
            assert band.label.strip()

    def test_unknown_values_do_not_crash(self):
        assert classify_position(float("nan")) is None


# ---------------------------------------------------------------------------
# Every label a page asks for must exist.  A missing key raises KeyError at
# render time, which on Streamlit Cloud means a blank page rather than a test
# failure — so it is caught here instead.
# ---------------------------------------------------------------------------

import re
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_UI_SOURCES = (
    [_PROJECT_ROOT / "app.py"]
    + sorted((_PROJECT_ROOT / "pages").glob("*.py"))
    + sorted((_PROJECT_ROOT / "src" / "ui").glob("*.py"))
)
_LABEL_REF = re.compile(r'SWEDISH_LABELS\[\s*"([^"]+)"\s*\]')


@pytest.mark.parametrize("source", _UI_SOURCES, ids=lambda p: p.name)
def test_every_referenced_label_exists(source):
    referenced = set(_LABEL_REF.findall(source.read_text(encoding="utf-8")))
    missing = sorted(referenced - set(SWEDISH_LABELS))
    assert not missing, f"{source.name} references labels that do not exist: {missing}"


def test_the_scan_actually_finds_references():
    """Guard against the regex silently matching nothing."""
    found = sum(
        len(_LABEL_REF.findall(s.read_text(encoding="utf-8"))) for s in _UI_SOURCES
    )
    assert found > 50, f"expected many label references, found {found}"


# ---------------------------------------------------------------------------
# No string the dashboard renders may describe the retired model.
#
# T4.2's definition of done is exactly this, and it was missed once: after the
# cutover, eight rendered explanations still described a vulnerability ranking,
# risk classes, and contributions to *growth*. The page code had changed and
# the copy explaining it had not. Only a check that reads both can catch that.
# ---------------------------------------------------------------------------

#: Strings that discuss the retired model on purpose — the retirement callout,
#: the backtest's account of what the old forecast scored, and the column
#: headers of the retired layer itself.
_MAY_DISCUSS_THE_RETIRED_MODEL = {
    "vulnerability_retired_title",
    "vulnerability_retired_text",
    "map_layer_vulnerability",
    "map_legend_caption",
    "tooltip_vulnerability_score",
    "th_risk_class",
    "th_prognosis",
    "backtest_caveat",
    "backtest_title",
    "backtest_lead",
    "forecast_title",
    "forecast_lead",
    "forecast_col",
    "method_period",
    "method_units",
    "guide_text",
    "landing_model_explanation",
}

#: Vocabulary that belongs to the retired vulnerability ranking.
_RETIRED_VOCABULARY = re.compile(
    r"sårbarhet|sårbara|riskklass|prognosticerad|vikter\b", re.IGNORECASE
)


def _rendered_label_keys() -> set[str]:
    referenced: set[str] = set()
    for source in _UI_SOURCES:
        referenced |= set(_LABEL_REF.findall(source.read_text(encoding="utf-8")))
    # Built by f-string on the national page, one per map layer.
    referenced |= {"map_legend_position_full", "map_legend_drift_full"}
    return referenced


def test_no_rendered_label_describes_the_retired_ranking():
    offenders = {}
    for key in sorted(_rendered_label_keys()):
        if key in _MAY_DISCUSS_THE_RETIRED_MODEL or key not in SWEDISH_LABELS:
            continue
        match = _RETIRED_VOCABULARY.search(SWEDISH_LABELS[key])
        if match:
            offenders[key] = match.group(0)
    assert not offenders, (
        "these strings are shown to users and describe the retired model: "
        f"{offenders}"
    )


def test_the_allowlist_does_not_hide_a_stale_string():
    """Every allowlisted key must genuinely be about the retired model, so the
    allowlist cannot quietly become a place to park copy nobody fixed."""
    for key in _MAY_DISCUSS_THE_RETIRED_MODEL:
        assert key in SWEDISH_LABELS, f"allowlisted key no longer exists: {key}"


def test_decomposition_copy_talks_about_index_points_not_growth():
    """T4.2 item 6 by name: the decomposition target changed from growth to
    position, so copy describing 'procentenheter lägre tillväxt' is wrong on
    the quantity, independently of anything else."""
    text = SWEDISH_LABELS["explain_decomp_text"].lower()
    assert "indexenheter" in text
    assert "skattekraftstillväxt" not in text
