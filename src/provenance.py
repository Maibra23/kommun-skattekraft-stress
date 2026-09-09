"""The analysis year, read from the pipeline's provenance artifact.

Every consumer that needs all four structural variables must ask which year
actually has them, rather than assuming the panel's own maximum. The panel is
ragged at the top end: skattekraft reaches 2026, population and education
2025, unemployment 2024 (METHODOLOGY §2.3.1).

Before this module, six call sites hardcoded ``year == 2024`` — three in the
model layer and three in the pages. That was *correct*, which is why nothing
broke, and it becomes silently wrong the moment SCB publishes 2025
unemployment: the complete-case year moves and every hardcoded site keeps
reporting 2024 without error. Expected around February 2027.

Two different years are needed and they are not interchangeable:

  * ``analysis_year`` — the latest year with every structural variable. The
    cross-section, the decomposition and the diagnostics all key off this.
  * ``panel_max_year`` — the latest year with skattekraft. Relative position
    and drift use this, because they need skattekraft alone and stopping them
    at the analysis year would throw away two published years.

See METHODOLOGY §13.2.
"""

import json
from functools import lru_cache
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_PROVENANCE_PATH: Path = _PROJECT_ROOT / "artifacts" / "data_provenance.json"


@lru_cache(maxsize=8)
def load_provenance(path: Path | None = None) -> dict:
    """Read the provenance artifact.

    Args:
        path: Override for the artifact location; defaults to
            artifacts/data_provenance.json.

    Returns:
        The parsed artifact.

    Raises:
        FileNotFoundError: If the artifact does not exist. It is written by
            `build_panel`, so its absence means the pipeline has not run.
    """
    target = Path(path) if path is not None else _PROVENANCE_PATH
    if not target.exists():
        raise FileNotFoundError(
            f"Data provenance artifact not found: {target}. It is written by "
            "src/clean/build_panel.py; run `python pipeline.py` first."
        )
    return json.loads(target.read_text(encoding="utf-8"))


def _require_int(payload: dict, key: str, source: Path | None) -> int:
    if key not in payload:
        raise KeyError(
            f"{key!r} is missing from the provenance artifact "
            f"({source or _PROVENANCE_PATH}). Re-run the pipeline to "
            "regenerate it."
        )
    return int(payload[key])


def analysis_year(path: Path | None = None) -> int:
    """Return the latest year carrying every structural variable.

    Args:
        path: Override for the artifact location.

    Returns:
        The complete-case year, e.g. 2024.

    Raises:
        FileNotFoundError: If the artifact is missing.
        KeyError: If the artifact does not record the year.
    """
    return _require_int(load_provenance(path), "complete_case_max_year", path)


def panel_max_year(path: Path | None = None) -> int:
    """Return the latest year in the panel at all — skattekraft's last year.

    Args:
        path: Override for the artifact location.

    Returns:
        The panel's maximum year, e.g. 2026.

    Raises:
        FileNotFoundError: If the artifact is missing.
        KeyError: If the artifact does not record the year.
    """
    return _require_int(load_provenance(path), "panel_max_year", path)
