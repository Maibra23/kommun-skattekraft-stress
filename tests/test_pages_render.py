"""Every page must actually execute against the committed artifacts.

The dashboard is deployed on Streamlit Cloud reading artifacts straight from
git, with no build step (METHODOLOGY 11.7).  A page that raises renders as a
stack trace for users, and an HTTP 200 on the page shell does not catch it --
the script runs over the websocket, after the shell is served.

These tests run each page's script for real, against the real artifacts, and
fail on any uncaught exception.  They are the check that the T1.2 cutover kept
the site working at the commit that changed it.

Pages are reached through `switch_page` rather than `AppTest.from_file`,
because the shared sidebar calls `st.page_link`, which needs a multipage
context to resolve.
"""

import pytest
from streamlit.testing.v1 import AppTest

_PAGES = ["pages/01_Riksoversikt.py", "pages/02_Kommunjamforelse.py"]


def _landing() -> AppTest:
    app = AppTest.from_file("app.py", default_timeout=120)
    app.run()
    return app


def _page(path: str) -> AppTest:
    app = _landing()
    app.switch_page(path)
    app.run()
    return app


@pytest.fixture(scope="module")
def landing() -> AppTest:
    return _landing()


@pytest.fixture(scope="module")
def riks() -> AppTest:
    return _page(_PAGES[0])


@pytest.fixture(scope="module")
def kommun() -> AppTest:
    return _page(_PAGES[1])


def test_landing_runs_without_exception(landing):
    assert not landing.exception, [str(e.value) for e in landing.exception]


def test_riksoversikt_runs_without_exception(riks):
    assert not riks.exception, [str(e.value) for e in riks.exception]


def test_kommun_page_runs_without_exception(kommun):
    assert not kommun.exception, [str(e.value) for e in kommun.exception]


@pytest.mark.parametrize("name", ["landing", "riks", "kommun"])
def test_no_page_renders_an_error_element(name, request):
    app = request.getfixturevalue(name)
    assert not app.error, [e.value for e in app.error]


def _rendered_text(app: AppTest) -> str:
    """Everything the page emitted, including st.html blocks.

    st.html lands in the tree as an UnknownElement with no `.value`, so the
    proto is read directly.  Widget elements are skipped rather than read
    through `.value`, which resolves against session state and raises for
    widgets this helper never needs.
    """
    parts = []
    for element in app.main:
        proto = getattr(element, "proto", None)
        for attr in ("body", "html"):
            text = getattr(proto, attr, None)
            if isinstance(text, str):
                parts.append(text)
    return " ".join(parts)


class TestLandingLeadsWithTheIdentifiedModel:
    def test_shows_the_within_time_panel_under_its_own_heading(self, landing):
        from src.ui.labels import SWEDISH_LABELS

        assert SWEDISH_LABELS["within_section_title"] in _rendered_text(landing)

    def test_states_that_the_panel_cannot_rank_kommuner(self, landing):
        assert "rangordna" in _rendered_text(landing).lower()

    def test_does_not_advertise_a_growth_forecast(self, landing):
        """The 2025 forecast scored r = +0.016 and no longer appears."""
        rendered = _rendered_text(landing).lower()
        assert "tillväxtprognos" not in rendered
        assert "prognos för 2025" not in rendered


class TestRiksoversiktContent:
    def test_offers_all_three_map_layers(self, riks):
        from src.ui.choropleth import MAP_LAYERS

        options = [opt for radio in riks.radio for opt in radio.options]
        for layer in MAP_LAYERS.values():
            assert layer.label in options

    def test_position_is_the_default_layer(self, riks):
        from src.ui.choropleth import MAP_LAYERS

        assert riks.radio[0].value == MAP_LAYERS["position"].label

    def test_renders_a_row_for_every_kommun(self, riks):
        assert riks.dataframe, "the kommun table is missing"
        assert len(riks.dataframe[0].value) == 290

    def test_table_carries_both_index_measures_and_their_difference(self, riks):
        from src.ui.labels import SWEDISH_LABELS

        columns = list(riks.dataframe[0].value.columns)
        joined = " ".join(columns)
        assert SWEDISH_LABELS["index_compare_ours"] in joined
        assert SWEDISH_LABELS["index_compare_scb"] in joined
        assert SWEDISH_LABELS["index_diff"] in columns

    def test_every_column_mixing_vintages_names_its_year(self, riks):
        """Position runs to a later year than the structural variables, so a
        bare column header would silently mix two vintages."""
        from src.provenance import panel_max_year
        from src.ui.labels import SWEDISH_LABELS

        columns = list(riks.dataframe[0].value.columns)
        indexed = [c for c in columns if SWEDISH_LABELS["index_compare_ours"] in c]
        assert indexed and str(panel_max_year()) in indexed[0]


class TestKommunPageContent:
    def test_selector_lists_every_kommun(self, kommun):
        assert len(kommun.selectbox[0].options) == 290

    def test_selector_is_ordered_by_position_not_by_forecast_rank(self, kommun):
        """Lowest position first; 'Rang' ordering came from the retired score."""
        first = kommun.selectbox[0].options[0]
        assert "index" in first.lower()
        assert "rang" not in first.lower()

    def test_decomposition_draws_only_identified_components(self, kommun):
        """Two attributed variables plus the residual -- never four bars."""
        import pandas as pd

        decomp = pd.read_parquet("artifacts/decomposition_cross.parquet")
        attributed = [c for c in decomp.columns if c.startswith("contrib_")]
        controls = [c for c in decomp.columns if c.startswith("control_")]
        assert len(attributed) == 2
        assert len(controls) == 2

    def test_controls_are_listed_with_their_intervals(self, kommun):
        from src.ui.labels import SWEDISH_LABELS

        tables = [df.value for df in kommun.dataframe]
        control_tables = [
            t for t in tables if SWEDISH_LABELS["vars_table_ci"] in t.columns
        ]
        assert control_tables, "controls must be shown with confidence intervals"
        assert len(control_tables[0]) == 2


class TestRetiredLayerExplainsItself:
    """Selecting the retired score must say why it is retired, where it is used."""

    def test_callout_appears_only_for_the_vulnerability_layer(self):
        from src.ui.choropleth import MAP_LAYERS

        app = _page(_PAGES[0])
        assert not app.warning, "no callout on the default position layer"

        app.radio[0].set_value(MAP_LAYERS["vulnerability"].label).run()
        assert app.warning, "the retired layer must carry its scored record"
        text = " ".join(str(w.value) for w in app.warning)
        assert "0,02" in text, "the callout must state what the score actually scored"
