"""Relative position and drift — the dashboard's descriptive spine.

Answers the two questions users actually arrive with — *where does my kommun
stand against the national average, and which way is it moving?* — from
skattekraft alone. No model, no estimation, no forecast.

That matters because of what the 2026-09-04 audit measured: relative position
has a year-over-year rank correlation of ~0.99, while the model-derived growth
forecast it replaces as the headline scored r = 0.016 out of sample. The most
reliable thing this project can say requires no model at all; the model's job
is to explain the position, not to produce the ranking.

Two position measures are carried deliberately and must never be mixed in one
chart or averaged together (METHODOLOGY §7.13):

  * ``tax_base_index_riket`` — SCB's own published index, riket = 100. It is
    **population-weighted** and rounded to whole percent. This is the citable
    figure, the one Regionfakta republishes and users already know.
  * ``relative_position`` — kommun ÷ the **unweighted** cross-kommun mean × 100.
    Unrounded, for internal analysis. SCB's integer rounding is too coarse to
    measure drift over short windows: a kommun can move a full index point on
    rounding alone, or sit still through a real change.

Drift is a **difference in index points**, not a growth rate. "Filipstad fell
1.2 index points since 2019" is a statement about position relative to the
country; it is not a statement about its tax base shrinking, and the two are
routinely confused.

Position needs skattekraft only, so this module covers the panel's full range
(2010–2026) rather than stopping at ``complete_case_max_year``. The
unemployment gap that caps the model at 2024 is irrelevant here.

Writes ``artifacts/position.parquet``.

Implements METHODOLOGY §13.4.
"""

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).parents[2]
_PANEL_PATH: Path = _PROJECT_ROOT / "data" / "processed" / "panel.parquet"
_OUTPUT_PATH: Path = _PROJECT_ROOT / "artifacts" / "position.parquet"

#: Drift windows in years. 1 and 3 are what a controller watches; 5 and 10
#: are where the signal is — one-year moves are mostly rounding and noise.
DRIFT_WINDOWS: tuple[int, ...] = (1, 3, 5, 10)

_OUTPUT_COLUMNS: list[str] = (
    ["kommun_kod", "year", "tax_base_index_riket", "relative_position"]
    + [f"drift_{w}y" for w in DRIFT_WINDOWS]
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_relative_position(panel: pd.DataFrame) -> pd.DataFrame:
    """Add ``relative_position`` — kommun ÷ unweighted yearly mean × 100.

    The unweighted mean is the denominator by choice, not by accident. It
    makes every kommun count once, which is the right frame for a ranking of
    kommuner; SCB's population-weighted index answers a different question and
    is carried alongside rather than instead.

    Args:
        panel: Frame with kommun_kod, year, tax_base_per_capita.

    Returns:
        A new frame with the ``relative_position`` column added.
    """
    df = panel.copy()
    yearly_mean = df.groupby("year")["tax_base_per_capita"].transform("mean")
    df["relative_position"] = df["tax_base_per_capita"] / yearly_mean * 100
    return df


def compute_drift(
    df: pd.DataFrame, windows: tuple[int, ...] = DRIFT_WINDOWS
) -> pd.DataFrame:
    """Add ``drift_{n}y`` columns: change in relative position, in index points.

    Computed by joining each kommun-year to the same kommun *n* years earlier,
    rather than by a positional shift, so a gap in a kommun's year coverage
    yields a null instead of a silently wrong comparison against the wrong year.

    Args:
        df: Frame carrying kommun_kod, year, relative_position.
        windows: Look-back lengths in years.

    Returns:
        A new frame with one drift column per window. Rows earlier than the
        window are null.
    """
    out = df.copy()
    for window in windows:
        past = df[["kommun_kod", "year", "relative_position"]].copy()
        past["year"] = past["year"] + window
        past = past.rename(columns={"relative_position": "_past_position"})
        out = out.merge(past, on=["kommun_kod", "year"], how="left")
        out[f"drift_{window}y"] = out["relative_position"] - out["_past_position"]
        out = out.drop(columns="_past_position")
    return out


def build_position(panel: pd.DataFrame) -> pd.DataFrame:
    """Build the full position and drift table from the panel.

    Args:
        panel: The kommun-year panel; needs kommun_kod, year,
            tax_base_per_capita and tax_base_index_riket.

    Returns:
        One row per kommun-year in _OUTPUT_COLUMNS order, sorted by
        (kommun_kod, year).
    """
    df = compute_relative_position(panel)
    df = compute_drift(df)
    return (
        df[_OUTPUT_COLUMNS]
        .sort_values(["kommun_kod", "year"])
        .reset_index(drop=True)
    )


def run_position() -> pd.DataFrame:
    """Read the panel, build the table, write the artifact.

    Returns:
        The written DataFrame.
    """
    logger.info("Loading panel from %s", _PANEL_PATH)
    panel = pd.read_parquet(_PANEL_PATH)

    result = build_position(panel)

    _OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    result.to_parquet(_OUTPUT_PATH, index=False)
    logger.info(
        "Position written to %s (%d rows, years %d–%d)",
        _OUTPUT_PATH,
        len(result),
        result["year"].min(),
        result["year"].max(),
    )
    return result


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    )
    df = run_position()
    latest = df[df["year"] == df["year"].max()]
    print(f"\nRows: {len(df)}   years {df['year'].min()}–{df['year'].max()}")
    print(f"\nLowest relative position in {int(latest['year'].iloc[0])}:")
    print(
        latest.nsmallest(5, "relative_position")[
            ["kommun_kod", "tax_base_index_riket", "relative_position", "drift_5y"]
        ].to_string(index=False)
    )
    print(f"\nLargest 10-year falls:")
    print(
        latest.nsmallest(5, "drift_10y")[
            ["kommun_kod", "relative_position", "drift_10y"]
        ].to_string(index=False)
    )
