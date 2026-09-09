"""Why a kommun sits where it sits — decomposition of the position gap.

Replaces the growth-gap decomposition in ``decompose.py``. That module answered
*"why did Filipstad grow 1.8 pp below average in 2024?"* — a question about a
quantity with no year-to-year persistence, where the residual dominated because
there was little else to find. This one answers *"why does Filipstad sit at
index 76?"*, which is what users actually ask, is stable year to year, and is
where the four variables explain ~69 % rather than ~1 %.

**This is deliberately not a four-bar chart.** Only ``edu_share`` and
``unemployment_rate`` are separately identified in the cross-section; the
intervals for ``dependency_ratio`` and ``population_growth_pct`` span zero in
every year 2021–2024 and each adds ~0.001 to R². They remain in the fitted
model as controls — dropping them would misstate the specification — but they
are never attributed, and this module reads the ``identified`` flag from
``coefficients_cross.parquet`` rather than hardcoding which those are.

The reason to enforce that here, rather than trusting the chart layer, is that
the additive identity is no defence: contributions plus residual sum to the gap
exactly whether or not the individual components mean anything. A bar drawn
from an interval spanning zero looks exactly as confident as one drawn from
``edu_share``. The old dashboard showed ``dependency_ratio`` as the largest
contributor on precisely that basis, inherited from the within/FE variance
decomposition where the audit measured it at 59.1 %; between kommuner it
explains essentially nothing.

Contributions are ``β_k × (X_ki − X̄_k)`` in index points. The residual absorbs
what the attributed variables do not explain — including the controls'
contributions, which is honest rather than hidden: they are reported alongside
as ``control_*`` columns so a reader can see their size without being invited
to read them as findings.

**Descriptive, not causal** (METHODOLOGY §7.2). A contribution says a kommun
differs from the national average on this variable, and that variable covaries
with the tax base. It does not say that changing the variable would move the
tax base.

Writes ``artifacts/decomposition_cross.parquet``, which superseded the growth
decomposition at the T1.2 cutover; ``decompose.py`` and its artifact were
removed on 2026-09-09.

Implements REMEDIATION_PLAN.md T2.2.
"""

import logging
from pathlib import Path

import pandas as pd

from src.provenance import analysis_year

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_PANEL_PATH: Path = _PROJECT_ROOT / "data" / "processed" / "panel.parquet"
_COEFFICIENTS_PATH: Path = _PROJECT_ROOT / "artifacts" / "coefficients_cross.parquet"
_OUTPUT_PATH: Path = _PROJECT_ROOT / "artifacts" / "decomposition_cross.parquet"

Y_VAR = "tax_base_index_riket"

#: The complete-case year, read from the pipeline's provenance artifact rather
#: than hardcoded: it is 2024 today and moves when SCB publishes 2025
#: unemployment. See src/provenance.py.
LATEST_YEAR: int = analysis_year()


def _coefficients_for(coefs: pd.DataFrame, year: int) -> pd.DataFrame:
    """Return the single-year spec's coefficients with their identification flag."""
    spec = f"year_{year}"
    rows = coefs[coefs["spec"] == spec]
    if rows.empty:
        raise ValueError(
            f"No coefficients for spec {spec!r} in {_COEFFICIENTS_PATH.name}. "
            "Run src.model.estimate_cross first."
        )
    return rows.set_index("variable")


def build_decomposition(panel: pd.DataFrame, coefs: pd.DataFrame) -> pd.DataFrame:
    """Decompose each kommun's position gap into identified contributions.

    Args:
        panel: The kommun-year panel.
        coefs: The cross-sectional coefficient table, carrying ``identified``.

    Returns:
        One row per kommun: total_gap, one ``contrib_*`` column per identified
        variable, one ``control_*`` column per unidentified variable, and the
        residual. Contributions plus residual equal total_gap exactly.
    """
    beta = _coefficients_for(coefs, LATEST_YEAR)
    identified = [v for v in beta.index if bool(beta.loc[v, "identified"])]
    controls = [v for v in beta.index if not bool(beta.loc[v, "identified"])]

    cross = panel.loc[panel["year"] == LATEST_YEAR].dropna(
        subset=[Y_VAR] + list(beta.index)
    )

    out = pd.DataFrame({"kommun_kod": cross["kommun_kod"].to_numpy()})
    if "kommun_name" in cross.columns:
        out["kommun_name"] = cross["kommun_name"].to_numpy()

    out["total_gap"] = (cross[Y_VAR] - cross[Y_VAR].mean()).to_numpy()

    for var in identified:
        centred = cross[var] - cross[var].mean()
        out[f"contrib_{var}"] = (float(beta.loc[var, "coefficient"]) * centred).to_numpy()

    # Controls are reported, never attributed: they inform the reader about
    # size without entering the identity the chart draws.
    for var in controls:
        centred = cross[var] - cross[var].mean()
        out[f"control_{var}"] = (float(beta.loc[var, "coefficient"]) * centred).to_numpy()

    attributed = out[[f"contrib_{v}" for v in identified]].sum(axis=1)
    out["residual"] = out["total_gap"] - attributed

    return out.sort_values("kommun_kod").reset_index(drop=True)


def run_decomposition_cross() -> pd.DataFrame:
    """Read inputs, decompose, write the artifact."""
    logger.info("Loading panel from %s", _PANEL_PATH)
    panel = pd.read_parquet(_PANEL_PATH)
    coefs = pd.read_parquet(_COEFFICIENTS_PATH)

    result = build_decomposition(panel, coefs)

    contrib_cols = [c for c in result.columns if c.startswith("contrib_")]
    control_cols = [c for c in result.columns if c.startswith("control_")]

    # Reported as a variance share, not as the mean of per-kommun ratios. A
    # kommun sitting at the national average has a gap near zero, so that ratio
    # explodes on an unremarkable residual and describes the spread of gaps
    # rather than the fit. See the T2.2 status-log entry for 2026-09-07.
    variance_share = float(result["residual"].var() / result["total_gap"].var())

    logger.info(
        "Decomposed %d kommuner. Attributed: %s. Controls (not attributed): %s.",
        len(result),
        ", ".join(c.removeprefix("contrib_") for c in contrib_cols),
        ", ".join(c.removeprefix("control_") for c in control_cols) or "none",
    )
    logger.info(
        "Residual variance share: %.1f %% (threshold 40 %%); "
        "explained %.3f, which should match the estimator's R2",
        100 * variance_share,
        1 - variance_share,
    )
    for col in contrib_cols:
        logger.info(
            "  %-28s mean |contribution| %.2f index points",
            col.removeprefix("contrib_"),
            result[col].abs().mean(),
        )

    _OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    result.to_parquet(_OUTPUT_PATH, index=False)
    logger.info("Decomposition written to %s", _OUTPUT_PATH)
    return result


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    )
    run_decomposition_cross()
