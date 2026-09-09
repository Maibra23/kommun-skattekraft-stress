"""Freeze 2010-2021 municipal unemployment as a committed snapshot.

SCB withdrew the AA0003X archive (HTTP 400 on the whole group, not just one
table), so "andel oppet arbetslosa" for 2010-2021 can no longer be fetched
from source.  Those 3 480 observations survive only in the committed panel.
This script copies them into data/lookup/ so they are a first-class, reviewed
input rather than a by-product of a cache that predates the withdrawal.

Before writing, the overlap years (2022-2024) are re-fetched live and compared
against the panel.  Equality there is the evidence that the snapshot is the
same series SCB still publishes, and not a stale or divergent vintage.

Run from the project root:
    python scripts/freeze_unemployment_snapshot.py

Implements REMEDIATION_PLAN.md T0.2a, option A.
"""

import logging
import sys
from datetime import date
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Allow `python scripts/freeze_unemployment_snapshot.py` without an editable install.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.fetch.fetch_unemployment import (  # noqa: E402  (path bootstrap must precede)
    _CONTINUATION_TABLE_URL,
    _SNAPSHOT_FILE,
    _SNAPSHOT_LAST_YEAR,
    _build_query,
    _clean_response,
    _discover_table,
)
from src.fetch.pxweb_client import query_pxweb  # noqa: E402

logger = logging.getLogger(__name__)

PANEL_FILE = PROJECT_ROOT / "data" / "processed" / "panel.parquet"
OVERLAP_YEARS = [2022, 2023, 2024]
EXPECTED_ROWS = 290 * 12


def load_historical(panel_file: Path) -> pd.DataFrame:
    """Read 2010-2021 unemployment out of the committed panel."""
    panel = pd.read_parquet(panel_file)
    hist = panel.loc[
        panel["year"] <= _SNAPSHOT_LAST_YEAR,
        ["kommun_kod", "year", "unemployment_rate"],
    ].sort_values(["kommun_kod", "year"], ignore_index=True)

    if len(hist) != EXPECTED_ROWS:
        raise ValueError(f"Expected {EXPECTED_ROWS} historical rows, got {len(hist)}.")
    if hist["unemployment_rate"].isna().any():
        raise ValueError("Historical unemployment contains nulls; refusing to freeze.")
    return hist


def verify_against_live(panel_file: Path) -> float:
    """Compare the panel's overlap years to a live fetch; return max abs diff.

    The snapshot years themselves cannot be verified — the archive is gone.
    The overlap is the closest available proxy: if the panel still matches SCB
    where SCB can still be asked, the withdrawn years are the same series.
    """
    url, contents_code, _, meta = _discover_table(
        OVERLAP_YEARS, [_CONTINUATION_TABLE_URL]
    )
    live = _clean_response(query_pxweb(url, _build_query(contents_code, OVERLAP_YEARS, meta)))

    panel = pd.read_parquet(panel_file)
    merged = panel.merge(live, on=["kommun_kod", "year"], suffixes=("_panel", "_live"))
    if merged.empty:
        raise ValueError("No overlap rows to compare; cannot validate the snapshot.")

    diff = (merged["unemployment_rate_panel"] - merged["unemployment_rate_live"]).abs()
    logger.info(
        "Overlap check: %d rows, max abs diff %.6f pp.", len(merged), diff.max()
    )
    return float(diff.max())


def write_snapshot(hist: pd.DataFrame, max_diff: float, out_file: Path) -> None:
    """Write the snapshot CSV with a provenance header."""
    header = (
        "# Municipal open unemployment (andel oppet arbetslosa), 2010-2021.\n"
        "#\n"
        "# SOURCE OF RECORD. SCB withdrew the AA0003X archive that served these\n"
        "# years; they cannot be re-fetched from SCB. Do not regenerate this file\n"
        "# from a fetch — it can only be copied forward.\n"
        "#\n"
        f"# Origin:    SCB STATIV AA0003X/IntGr1KomKonUtb, fetched 2026-04-24,\n"
        f"#            preserved via data/processed/panel.parquet.\n"
        f"# Frozen:    {date.today().isoformat()} by scripts/freeze_unemployment_snapshot.py\n"
        f"# Validated: overlap years {OVERLAP_YEARS[0]}-{OVERLAP_YEARS[-1]} re-fetched live from\n"
        f"#            AA0003B/IntGr1KomUtbBAS, max abs diff {max_diff:.6f} pp.\n"
        "# Rationale: docs/REMEDIATION_PLAN.md T0.2a (option A), METHODOLOGY 13.1.\n"
    )
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with out_file.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(header)
        hist.to_csv(fh, index=False, lineterminator="\n")
    logger.info("Wrote %d rows to %s", len(hist), out_file)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    )

    hist = load_historical(PANEL_FILE)
    max_diff = verify_against_live(PANEL_FILE)
    if max_diff > 0.05:
        raise ValueError(
            f"Overlap years diverge from live SCB by {max_diff:.4f} pp. "
            "The committed panel is not the series SCB now publishes — "
            "investigate before freezing (REMEDIATION_PLAN.md T0.2a)."
        )

    write_snapshot(hist, max_diff, _SNAPSHOT_FILE)
    print(f"\nFroze {len(hist)} rows, {hist.year.min()}-{hist.year.max()}.")
    print(f"Overlap validation: max abs diff {max_diff:.6f} pp.")
    print(f"Written to {_SNAPSHOT_FILE.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
