"""Collinearity and scale diagnostics for both model designs.

Closes audit finding F3, which observed that collinearity had never been
checked. It is closed in both directions, because the answer differs by design
and the difference is the point:

  * **Within design** (the two-way FE model in ``estimate.py``) — F3's concern
    is real here. Three of six pairs exceed |0.65| after entity demeaning:
    dependency × education, unemployment × dependency, unemployment × education.
  * **Cross-sectional design** (``estimate_cross.py``, now primary for the
    ranking) — VIF is 1.3–2.1, comfortably inside tolerance. Collinearity does
    **not** bite here.

That second result is what lets T2.2 attribute a kommun's position to separate
variables at all, so it is worth publishing rather than assuming. It also
corrects an expectation written into the plan: T2.3 anticipated that
collinearity would be *worse* in the cross-section. It is not.

**The real risk in the cross-section is scale, not collinearity.**
``dependency_ratio`` cannot be separated from zero between kommuner because it
barely varies — SD 0.116, against 8.5 for ``edu_share`` — so a per-unit
coefficient is read across 8.6 SDs of data that does not exist. A VIF table
alone would give that design a clean bill of health and miss the reason two of
its four variables are unusable. Each variable's SD is therefore recorded here
beside its VIF, and the identification verdict itself lives in
``coefficients_cross.parquet``.

Severity is diagnostic, not blocking (METHODOLOGY §11.6): this module writes
the numbers and flags them; it never raises.

Writes ``artifacts/diagnostics.parquet`` in tidy form, one row per
(design, metric, variable[, variable_2]).

Implements METHODOLOGY §13.4.
"""

import itertools
import logging
from pathlib import Path

import numpy as np
import pandas as pd

from src.provenance import analysis_year

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_PANEL_PATH: Path = _PROJECT_ROOT / "data" / "processed" / "panel.parquet"
_OUTPUT_PATH: Path = _PROJECT_ROOT / "artifacts" / "diagnostics.parquet"

X_VARS: list[str] = [
    "edu_share",
    "unemployment_rate",
    "dependency_ratio",
    "population_growth_pct",
]

CROSS_DESIGN = "cross_section_2024"
WITHIN_DESIGN = "within_entity_demeaned"

#: Conventional VIF thresholds.
VIF_WARNING: float = 5.0
VIF_SEVERE: float = 10.0

#: The audit reported the within-design pairs above this in absolute value.
CORR_HIGH: float = 0.65

#: Read from the provenance artifact, not hardcoded (src/provenance.py).
_LATEST_YEAR: int = analysis_year()


# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------


def _vif_flag(vif: float) -> str:
    if vif > VIF_SEVERE:
        return "severe"
    if vif > VIF_WARNING:
        return "warning"
    return "ok"


def _corr_flag(corr: float) -> str:
    return "high" if abs(corr) > CORR_HIGH else "ok"


def _vifs(df: pd.DataFrame, variables: list[str]) -> dict[str, float]:
    """Variance inflation factors via auxiliary regressions.

    VIF_k = 1 / (1 - R²_k), where R²_k regresses variable k on the others.
    Computed directly rather than via statsmodels' helper so the intercept
    handling is explicit: each auxiliary regression includes one.

    Args:
        df: Frame containing the design variables.
        variables: Column names to compute VIF for.

    Returns:
        Mapping of variable name to VIF.
    """
    out: dict[str, float] = {}
    for var in variables:
        others = [v for v in variables if v != var]
        y = df[var].to_numpy(dtype=float)
        X = np.column_stack([np.ones(len(df))] + [df[o].to_numpy(dtype=float) for o in others])
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        resid = y - X @ beta
        ss_res = float((resid**2).sum())
        ss_tot = float(((y - y.mean()) ** 2).sum())
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
        out[var] = float("inf") if r2 >= 1.0 else 1.0 / (1.0 - r2)
    return out


def _condition_number(df: pd.DataFrame, variables: list[str]) -> float:
    """Condition number of the design matrix, intercept included."""
    X = np.column_stack([np.ones(len(df))] + [df[v].to_numpy(dtype=float) for v in variables])
    return float(np.linalg.cond(X))


# ---------------------------------------------------------------------------
# Designs
# ---------------------------------------------------------------------------


def cross_section_design(panel: pd.DataFrame, year: int = _LATEST_YEAR) -> pd.DataFrame:
    """The regressors as the cross-sectional model sees them: one year, as-is."""
    return panel.loc[panel["year"] == year, X_VARS].dropna().reset_index(drop=True)


def within_design(panel: pd.DataFrame) -> pd.DataFrame:
    """The regressors as the FE model sees them: deviations from kommun means.

    Entity demeaning is what the two-way FE estimator does internally, so this
    is the design whose collinearity F3 was actually about.
    """
    df = panel[["kommun_kod"] + X_VARS].dropna()
    demeaned = df[X_VARS] - df.groupby(df["kommun_kod"])[X_VARS].transform("mean")
    return demeaned.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Table
# ---------------------------------------------------------------------------


def _rows_for_design(design: pd.DataFrame, label: str) -> list[dict]:
    vifs = _vifs(design, X_VARS)
    cond = _condition_number(design, X_VARS)
    sds = design[X_VARS].std()

    rows = [
        {
            "design": label,
            "metric": "vif",
            "variable": var,
            "variable_2": None,
            "value": vifs[var],
            "flag": _vif_flag(vifs[var]),
            "x_sd": float(sds[var]),
            "condition_number": cond,
        }
        for var in X_VARS
    ]

    corr = design[X_VARS].corr()
    rows += [
        {
            "design": label,
            "metric": "correlation",
            "variable": a,
            "variable_2": b,
            "value": float(corr.loc[a, b]),
            "flag": _corr_flag(corr.loc[a, b]),
            "x_sd": None,
            "condition_number": None,
        }
        for a, b in itertools.combinations(X_VARS, 2)
    ]
    return rows


def build_diagnostics(panel: pd.DataFrame) -> pd.DataFrame:
    """Compute VIF, condition number and pairwise correlations for both designs.

    Args:
        panel: The kommun-year panel.

    Returns:
        Tidy diagnostics table.
    """
    rows = _rows_for_design(cross_section_design(panel), CROSS_DESIGN)
    rows += _rows_for_design(within_design(panel), WITHIN_DESIGN)
    return pd.DataFrame(rows)


def run_diagnostics() -> pd.DataFrame:
    """Read the panel, compute diagnostics, write the artifact."""
    logger.info("Loading panel from %s", _PANEL_PATH)
    panel = pd.read_parquet(_PANEL_PATH)

    table = build_diagnostics(panel)

    for design in (CROSS_DESIGN, WITHIN_DESIGN):
        vif = table[(table["design"] == design) & (table["metric"] == "vif")]
        worst = vif.loc[vif["value"].idxmax()]
        flagged = table[
            (table["design"] == design)
            & (table["metric"] == "correlation")
            & (table["flag"] == "high")
        ]
        logger.info(
            "%s — max VIF %.2f (%s, %s), condition number %.0f, "
            "%d pair(s) above |%.2f|",
            design,
            worst["value"],
            worst["variable"],
            worst["flag"],
            worst["condition_number"],
            len(flagged),
            CORR_HIGH,
        )
        for _, row in flagged.iterrows():
            logger.info("    %s x %s = %+.3f", row["variable"], row["variable_2"], row["value"])

    _OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    table.to_parquet(_OUTPUT_PATH, index=False)
    logger.info("Diagnostics written to %s", _OUTPUT_PATH)
    return table


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    )
    run_diagnostics()
