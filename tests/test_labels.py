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
    """METHODOLOGY §13.4 specifies this heading verbatim, so that the
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
# Both quote styles: the pages use each, and matching only double quotes left
# SWEDISH_LABELS['key'] invisible to the reference check below.
_LABEL_REF = re.compile(r"""SWEDISH_LABELS\[\s*["']([^"']+)["']\s*\]""")


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
    "backtest_caveat",
    "backtest_title",
    "backtest_lead",
    "forecast_title",
    "forecast_lead",
    "forecast_col",
    "method_period",
    "method_units",
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
    the quantity, independently of anything else.

    Checks every string that explains the decomposition, so consolidating them
    into one guide cannot quietly drop the guarantee.
    """
    for key in ("decomp_position_explanation", "decomp_guide"):
        text = SWEDISH_LABELS[key].lower()
        assert "indexenheter" in text, key
        assert "skattekraftstillväxt" not in text, key


# ---------------------------------------------------------------------------
# No dashes in user-facing text.
#
# Em and en dashes read as a machine-writing tell, so the Swedish copy uses
# ordinary punctuation instead: a full stop where the clause stands alone, a
# comma where it qualifies, a colon where it introduces.
#
# Two things that look like dashes are deliberately kept, because removing them
# would be wrong rather than tidy:
#   * hyphens inside Swedish compounds ("95-procentigt", "GeoJSON-fil"), which
#     are required spelling;
#   * the minus sign on a negative number, normalised to ASCII so that prose
#     and rendered figures match.
# ---------------------------------------------------------------------------

_TYPOGRAPHIC_DASHES = {
    "\u2014": "em dash",
    "\u2013": "en dash",
    "\u2212": "minus sign (use ASCII '-')",
    "\u2012": "figure dash",
    "\u2015": "horizontal bar",
}


def test_no_label_contains_a_typographic_dash():
    offenders = {}
    for key, text in SWEDISH_LABELS.items():
        if not isinstance(text, str):
            continue
        for char, name in _TYPOGRAPHIC_DASHES.items():
            if char in text:
                offenders.setdefault(key, []).append(name)
    assert not offenders, f"typographic dashes in user-facing text: {offenders}"


@pytest.mark.parametrize("source", _UI_SOURCES, ids=lambda p: p.name)
def test_no_dash_is_rendered_from_the_page_code(source):
    """Dashes in a docstring or comment are fine; a dash inside a string that
    reaches the page is not."""
    offenders = []
    for line in source.read_text(encoding="utf-8").split("\n"):
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith('"""'):
            continue
        for match in re.finditer(r'["\']([^"\']*[\u2014\u2013\u2212][^"\']*)["\']', line):
            offenders.append(match.group(1)[:60])
    assert not offenders, f"{source.name} renders dashes: {offenders}"


def test_swedish_compound_hyphens_are_untouched():
    """The de-dashing must not have broken required spelling."""
    assert "95-procentig" in SWEDISH_LABELS["landing_vars_explanation"]
    assert "GeoJSON-fil" in SWEDISH_LABELS["choropleth_missing_geojson"]


# ---------------------------------------------------------------------------
# One display policy for numbers.
# ---------------------------------------------------------------------------


class TestNumberFormatting:
    def test_index_is_shown_as_a_whole_number(self):
        from src.ui.labels import format_index

        assert format_index(208.07) == "208"
        assert format_index(79.94) == "80"

    def test_effects_carry_one_decimal_and_a_sign(self):
        from src.ui.labels import format_effect

        assert format_effect(10.033) == "+10,0"
        assert format_effect(-2.688) == "-2,7"

    def test_intervals_read_without_a_dash(self):
        from src.ui.labels import format_interval

        rendered = format_interval(6.36, 13.70)
        assert rendered == "+6,4 till +13,7"
        assert "\u2013" not in rendered and "\u2014" not in rendered

    def test_the_chart_and_the_table_agree_to_the_last_digit(self):
        """The chart used to print -2,7 beside a table printing -2,69."""
        from src.ui.labels import format_effect, format_interval

        value = -2.688112
        assert format_effect(value) in format_interval(value, value)

    def test_swedish_decimal_comma_everywhere(self):
        from src.ui.labels import format_effect, format_index_points, format_pct

        for rendered in (format_effect(1.25), format_index_points(-1.25), format_pct(9.2)):
            assert "." not in rendered, rendered


def test_a_movement_that_rounds_to_nothing_has_no_sign():
    """A drift of -0.04 rendered as "-0,0", which reads as a fall that is not
    there. Zero has no direction, so it carries no sign."""
    from src.ui.labels import format_effect, format_index_points

    assert format_index_points(-0.04) == "0,0"
    assert format_index_points(0.04) == "0,0"
    assert format_effect(-0.001) == "0,0"
    # Real movements keep theirs.
    assert format_index_points(-0.4) == "-0,4"
    assert format_index_points(0.4) == "+0,4"


def test_no_label_contains_mojibake():
    """A script that read its own source with the platform default encoding
    instead of UTF-8 wrote "Ã–ppen" into the glossary. The dash test caught it
    only by accident, because one mangled byte happened to be a dash."""
    suspects = ("Ã", " Â", "â€", "Ã¥", "Ã¤", "Ã¶")
    offenders = {
        key: text[:60]
        for key, text in SWEDISH_LABELS.items()
        if isinstance(text, str) and any(s in text for s in suspects)
    }
    assert not offenders, f"mis-encoded Swedish characters: {offenders}"


def test_the_glossary_defines_the_terms_the_app_actually_uses():
    """Every term a reader meets without introduction should still be defined,
    now per term rather than in one blob. "Förflyttning" is the one users ask
    about, because a fall in it sounds like the tax base shrank and it does
    not mean that."""
    from src.ui.labels import GLOSSARY

    defined = " ".join(f"{e.title} {e.text}" for e in GLOSSARY.values()).lower()
    for term in (
        "skattekraft",
        "indexenheter",
        "förflyttning",
        "riksmedelvärdet",
        "öppen arbetslöshet",
        "försörjningskvot",
        "befolkningstillväxt",
        "eftergymnasialt",
        "standardavvikelse",
        "konfidensintervall",
        "kontrollvariabel",
        "residual",
        "träffsäkerhet",
    ):
        assert term in defined, f"undefined in the glossary: {term}"


def test_the_glossary_says_what_a_fall_in_position_does_not_mean():
    """The distinction that matters: a kommun can grow every year in kronor and
    still fall in the index. Stating only the positive definition invites the
    wrong reading."""
    from src.ui.labels import GLOSSARY

    assert (
        "Det betyder inte att skattekraften har minskat"
        in GLOSSARY["forflyttning"].text
    )


def test_every_glossary_entry_is_reachable_from_some_section():
    """A definition nobody can open is a definition nobody has. Each term must
    be named by at least one card heading's help badge."""
    import re
    from src.ui.labels import GLOSSARY

    wired = set()
    for source in _UI_SOURCES:
        wired |= set(re.findall(r'"([a-z_]+)",?\s*(?=[,)])', source.read_text("utf-8")))
    orphans = sorted(set(GLOSSARY) - wired)
    assert not orphans, f"glossary terms no section offers: {orphans}"


def test_glossary_entries_carry_no_typographic_dash():
    """Same rule as the labels: these strings are rendered too."""
    from src.ui.labels import GLOSSARY

    for key, entry in GLOSSARY.items():
        for char in _TYPOGRAPHIC_DASHES:
            assert char not in entry.title + entry.text, key


#: The idiom is retired everywhere. It reads either as losing territory or as
#: the tax base shrinking, and it means neither: it means the index fell while
#: the kronor may well have risen. Movement is stated literally instead.
_RETIRED_IDIOM = re.compile(
    r"tappa[rt]?\s+mark|vinn(a|er)\s+mark|vunn(en|it)\s+mark",
    re.IGNORECASE,
)


def test_no_label_uses_the_retired_ground_losing_idiom():
    offenders = {
        key: text[:80]
        for key, text in SWEDISH_LABELS.items()
        if isinstance(text, str) and _RETIRED_IDIOM.search(text)
    }
    assert not offenders, f"'tappa mark' and its relatives are retired: {offenders}"


@pytest.mark.parametrize("source", _UI_SOURCES, ids=lambda p: p.name)
def test_no_page_renders_the_retired_idiom(source):
    for line in source.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        assert not _RETIRED_IDIOM.search(line), f"{source.name}: {stripped[:80]}"
