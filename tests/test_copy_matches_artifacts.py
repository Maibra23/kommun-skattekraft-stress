"""Every number the UI copy states must still be the number in the artifacts.

The prose in ``src/ui/labels.py`` quotes concrete results: effect sizes,
worked decompositions, two named forecasts, the backtest scores.  Those
numbers were correct when they were written and have no link to the data
afterwards, so a rerun of the pipeline silently turns them into claims the
dashboard cannot support.  That has already happened twice: the backtest
sentence kept a rounding from an older two decimal display, and the sentence
about the two index measures kept an average taken over all years after it
was rewritten to describe the latest year only.

Each case here rebuilds the fragment from the artifact, in the same wording
and rounding the copy uses, and asserts that fragment appears verbatim.  A
failure means the copy and the data disagree; the assertion message shows
what the data says now.

Artifacts are a published contract (METHODOLOGY.md 11.7), so these are
checked against the committed artifacts rather than recomputed from source.
"""

import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from src.provenance import analysis_year, panel_max_year
from src.ui.labels import SWEDISH_LABELS

_ROOT = Path(__file__).resolve().parents[1]
_ARTIFACTS_DIR = _ROOT / "artifacts"
_PANEL_PATH = _ROOT / "data" / "processed" / "panel.parquet"
_BASELINE_PATH = Path(__file__).parent / "fixtures" / "audit_baseline_2026-09-04.json"


# --------------------------------------------------------------------------
# Formatting helpers, matching what the copy does by hand.
# --------------------------------------------------------------------------


def _sv(value: float, decimals: int = 1) -> str:
    """A number as Swedish prose writes it: decimal comma, fixed decimals."""
    return f"{value:.{decimals}f}".replace(".", ",")


def _signed(value: float, decimals: int = 1) -> str:
    """As above, but always carrying its sign, and never a negative zero."""
    rounded = round(value, decimals)
    sign = "-" if rounded < 0 else "+"
    return f"{sign}{_sv(abs(rounded), decimals)}"


@pytest.fixture(scope="module")
def data() -> SimpleNamespace:
    """The artifacts the copy draws its numbers from."""
    panel = pd.read_parquet(_PANEL_PATH)
    names = panel[["kommun_kod", "kommun_name"]].drop_duplicates()
    position = pd.read_parquet(_ARTIFACTS_DIR / "position.parquet")
    coefficients = pd.read_parquet(_ARTIFACTS_DIR / "coefficients.parquet")
    cross = pd.read_parquet(_ARTIFACTS_DIR / "coefficients_cross.parquet")
    forecast = pd.read_parquet(_ARTIFACTS_DIR / "forecast.parquet")
    return SimpleNamespace(
        panel=panel,
        position_year=panel_max_year(),
        position_latest=position[position["year"] == panel_max_year()],
        cross=cross[cross["spec"] == f"year_{analysis_year()}"].set_index("variable"),
        primary=coefficients[coefficients["role"] == "primary"].set_index("variable"),
        decomposition=pd.read_parquet(
            _ARTIFACTS_DIR / "decomposition_cross.parquet"
        ).set_index("kommun_name"),
        forecast=forecast.merge(names, on="kommun_kod").set_index("kommun_name"),
        baseline=json.loads(_BASELINE_PATH.read_text(encoding="utf-8")),
    )


@pytest.fixture(scope="module")
def copy_text() -> str:
    """Every rendered string in the app, as one searchable body of text."""
    return " ".join(v for v in SWEDISH_LABELS.values() if isinstance(v, str))


# --------------------------------------------------------------------------
# The claims.  Each builds the fragment the copy should contain.
# --------------------------------------------------------------------------


def _cross_effect(d, variable):
    return _signed(d.cross.loc[variable, "beta_sd"])


def _cross_interval(d, variable):
    row = d.cross.loc[variable]
    return f"{_signed(row['lower_ci_sd'])} till {_signed(row['upper_ci_sd'])}"


def _attribution(d, kommun):
    """The worked decomposition, as the guides narrate it."""
    row = d.decomposition.loc[kommun]
    return (
        f"{kommun} ligger {_sv(-row['total_gap'])} indexenheter under "
        f"riksgenomsnittet",
        f"{_sv(-row['contrib_edu_share'])} av dem till utbildningsnivån och "
        f"{_sv(-row['contrib_unemployment_rate'])} till arbetslösheten",
    )


def _forecast_sentence(d, kommun):
    row = d.forecast.loc[kommun]
    return (
        f"{kommun} har prognosen {_signed(row['drift_forecast'])} med "
        f"intervallet {_signed(row['lower'])} till {_signed(row['upper'])}"
    )


def _latest_panel(d):
    """The last panel year that actually carries a tax base."""
    with_tax = d.panel[d.panel["tax_base_per_capita"].notna()]
    return with_tax[with_tax["year"] == d.position_year]


def _kronor(d, kommun: str) -> float:
    return _latest_panel(d).set_index("kommun_name").loc[kommun, "tax_base_per_capita"]


def _lowest_kommun(d) -> str:
    latest = _latest_panel(d)
    return latest.loc[latest["tax_base_per_capita"].idxmin(), "kommun_name"]


def _thousands(value: float) -> str:
    """Kronor as the concept copy rounds them: nearest thousand, space group."""
    return f"{int(round(value, -3)):,}".replace(",", " ")


CLAIMS = {
    # The four cross-sectional effects, quoted in the guide and the glossary.
    "edu_effect": lambda d: _cross_effect(d, "edu_share"),
    "edu_interval": lambda d: _cross_interval(d, "edu_share"),
    "unemployment_effect": lambda d: (
        f"{_cross_effect(d, 'unemployment_rate')} med intervallet "
        f"{_cross_interval(d, 'unemployment_rate')}"
    ),
    "dependency_effect": lambda d: (
        f"{_cross_effect(d, 'dependency_ratio')} med intervallet "
        f"{_cross_interval(d, 'dependency_ratio')}"
    ),
    # The within-kommun panel, demoted to inference only.
    "fe_unemployment": lambda d: _sv(
        d.primary.loc["unemployment_rate", "coefficient"], 3
    ),
    "fe_dependency": lambda d: _sv(d.primary.loc["dependency_ratio", "coefficient"], 2),
    "fe_r_squared_within": lambda d: (
        f"{_sv(d.primary['r_squared_within'].iloc[0] * 100)} procent"
    ),
    # Worked decompositions, one per guide.
    "goinge_gap": lambda d: _attribution(d, "Östra Göinge")[0],
    "goinge_attribution": lambda d: _attribution(d, "Östra Göinge")[1],
    "goinge_residual": lambda d: (
        f"lämnar {_sv(abs(d.decomposition.loc['Östra Göinge', 'residual']), 2)} "
        f"oförklarat"
    ),
    "filipstad_gap": lambda d: _attribution(d, "Filipstad")[0],
    "filipstad_attribution": lambda d: _attribution(d, "Filipstad")[1],
    "filipstad_residual": lambda d: (
        f"lämnar {_sv(abs(d.decomposition.loc['Filipstad', 'residual']))} oförklarat"
    ),
    "danderyd_gap": lambda d: (
        f"Danderyd ligger {_sv(d.decomposition.loc['Danderyd', 'total_gap'])}"
    ),
    # The forecast, its two named examples and its score.
    "forecast_solna": lambda d: _forecast_sentence(d, "Solna"),
    "forecast_hogsby": lambda d: _forecast_sentence(d, "Högsby"),
    "forecast_spearman": lambda d: _sv(d.forecast["backtest_spearman"].iloc[0], 2),
    "forecast_vs_mean": lambda d: (
        f"{_sv(d.forecast['backtest_rmse'].iloc[0])} mot "
        f"{_sv(d.forecast['backtest_naive_rmse'].iloc[0])} för att gissa "
        f"genomsnittet"
    ),
    "forecast_vs_persistence": lambda d: (
        f"{_sv(d.forecast['backtest_persistence_rmse'].iloc[0])} för att anta "
        f"att trenden fortsätter"
    ),
    # The two index measures.  The offset is stated for the year the chart
    # shows, which is the latest year, not the average across the panel.
    "index_offset": lambda d: (
        f"i snitt {_sv((d.position_latest['relative_position'] - d.position_latest['tax_base_index_riket']).mean(), 0)} "
        f"indexenheter"
    ),
    # The panel itself.
    "n_kommuner": lambda d: f"{d.panel['kommun_kod'].nunique()} kommuner",
    "panel_years": lambda d: (
        f"{d.panel['year'].min()} till {d.panel['year'].max()}"
    ),
    "median_position": lambda d: (
        f"mediankommunen ligger på "
        f"{_sv(d.position_latest['relative_position'].median(), 0)}"
    ),
    "max_position": lambda d: (
        f"den högsta på {_sv(d.position_latest['relative_position'].max(), 0)}"
    ),
    # The retired forecast's record, as the method section reports it.  These
    # come from the frozen audit fixture, not from a live artifact, because
    # the model that produced them has been removed.
    "retired_correlation": lambda d: (
        f"korrelationen på {_sv(d.baseline['backtest_2025']['pearson_r'], 2)}"
    ),
    "retired_rmse": lambda d: (
        f"{_sv(d.baseline['backtest_2025']['rmse'], 2)} procentenheter, mot "
        f"{_sv(d.baseline['backtest_2025']['naive_rmse'], 2)}"
    ),
    # The concept section's kronor figures. These went stale unnoticed once
    # already: they named "flera Norrlandskommuner" as the lowest when the
    # five lowest sat in Värmland, Kalmar and Skåne, and put them under
    # 180 000 kr when none was.
    "concept_top_kronor": lambda d: (
        f"{d.position_year} hade Danderyd {_thousands(_kronor(d, 'Danderyd'))} "
        f"kr per invånare"
    ),
    "concept_bottom_kronor": lambda d: (
        f"{_lowest_kommun(d)}, den lägsta kommunen, hade "
        f"{_thousands(_kronor(d, _lowest_kommun(d)))} kr"
    ),
    "concept_as_index": lambda d: (
        f"index {_sv(d.position_latest['relative_position'].max(), 0)} "
        f"respektive {_sv(d.position_latest['relative_position'].min(), 0)}"
    ),
    "retired_risk_classes": lambda d: (
        "låg {lag} %, medel {medel} %, hög {hog} %".format(
            **{
                k: _sv(v, 2)
                for k, v in d.baseline["backtest_2025"][
                    "actual_growth_by_risk_class"
                ].items()
            }
        )
    ),
}


@pytest.mark.parametrize("case", sorted(CLAIMS), ids=sorted(CLAIMS))
def test_copy_states_the_number_the_artifacts_hold(case, data, copy_text):
    fragment = CLAIMS[case](data)
    assert fragment in copy_text, (
        f"The copy no longer matches the data for {case!r}. "
        f"The artifacts say: {fragment!r}. Update src/ui/labels.py to say it, "
        f"or fix the pipeline if the artifact is wrong."
    )
