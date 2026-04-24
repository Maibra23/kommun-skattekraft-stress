"""Validate and harmonize municipality codes against the 2024 SCB reference list.

Loads data/lookup/kommunkod_harmonization.csv and uses it to:
  1. Verify that every kod in a fetched DataFrame appears in the lookup.
  2. Assert no duplicate (kod, year) pairs.
  3. Enrich the DataFrame with kommun_name, lan_kod, and lan_name columns.

All 290 codes in the lookup are valid for the 2010–2024 analysis window.
No mergers, splits, or renames occurred within this window that affect the
290 municipalities used by the vs:RegionKommun07EjAggr filter on SCB pxweb.
"""

import logging
from functools import lru_cache
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).parents[2]
_LOOKUP_PATH: Path = _PROJECT_ROOT / "data" / "lookup" / "kommunkod_harmonization.csv"

_LOOKUP_DTYPES: dict[str, str] = {
    "kod": str,
    "lan_kod": str,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate_and_harmonize(
    df: pd.DataFrame,
    code_col: str = "kommun_kod",
    year_col: str = "year",
) -> pd.DataFrame:
    """Validate municipality codes and enrich with name columns from the lookup.

    Checks that every code in df[code_col] exists in the 2024 SCB reference
    list, that there are no duplicate (code, year) pairs, and then joins
    kommun_name, lan_kod, and lan_name onto the DataFrame.

    Args:
        df: Input DataFrame containing at least a municipality code column and
            optionally a year column for duplicate checking.
        code_col: Name of the column holding the 4-digit municipality code.
            Defaults to 'kommun_kod'.
        year_col: Name of the column holding the year integer.  Used for
            duplicate detection.  If the column is absent, duplicate checking
            is skipped.  Defaults to 'year'.

    Returns:
        Copy of df with additional columns:
            - kommun_name: Swedish municipality name (e.g. 'Stockholm')
            - lan_kod: 2-digit county code (e.g. '01')
            - lan_name: Swedish county name (e.g. 'Stockholms län')

    Raises:
        ValueError: If any code in df is not in the lookup (unrecognized codes
            listed in the error message), or if duplicate (code, year) pairs
            are found.
        FileNotFoundError: If the lookup CSV does not exist at the expected path.
    """
    lookup = _load_lookup()

    # --- 1. Validate codes ---
    input_codes = set(df[code_col].astype(str).str.zfill(4).unique())
    valid_codes = set(lookup["kod"])
    unknown = input_codes - valid_codes
    if unknown:
        raise ValueError(
            f"Unrecognized municipality codes in column '{code_col}': "
            f"{sorted(unknown)}. "
            "These codes are not in data/lookup/kommunkod_harmonization.csv. "
            "Check for zero-padding, transcription errors, or boundary changes."
        )

    # --- 2. Check for duplicates ---
    if year_col in df.columns:
        key_cols = [code_col, year_col]
        dup_mask = df.duplicated(subset=key_cols, keep=False)
        if dup_mask.any():
            dup_pairs = (
                df.loc[dup_mask, key_cols]
                .drop_duplicates()
                .head(10)
                .to_dict(orient="records")
            )
            raise ValueError(
                f"Duplicate ({code_col}, {year_col}) pairs found in input DataFrame. "
                f"First offenders: {dup_pairs}. "
                "Resolve duplicates before harmonizing."
            )

    # --- 3. Enrich with name columns ---
    df = df.copy()
    df[code_col] = df[code_col].astype(str).str.zfill(4)

    lookup_renamed = lookup.rename(
        columns={
            "kod": code_col,
            "namn": "kommun_name",
            "lan_kod": "lan_kod",
            "lan_namn": "lan_name",
        }
    )[[code_col, "kommun_name", "lan_kod", "lan_name"]]

    # Drop any existing name columns to avoid conflicts on re-harmonization.
    for col in ("kommun_name", "lan_kod", "lan_name"):
        if col in df.columns:
            df = df.drop(columns=[col])

    df = df.merge(lookup_renamed, on=code_col, how="left")

    logger.info(
        "validate_and_harmonize: %d rows, %d unique codes, all valid.",
        len(df),
        df[code_col].nunique(),
    )
    return df


def load_valid_codes() -> set[str]:
    """Return the set of all 290 valid 4-digit municipality codes.

    Useful for quick membership checks without loading the full lookup table.

    Returns:
        Set of zero-padded 4-digit string codes (e.g. {'0114', '0115', ...}).

    Raises:
        FileNotFoundError: If the lookup CSV does not exist.
    """
    return set(_load_lookup()["kod"])


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _load_lookup() -> pd.DataFrame:
    """Load and cache the harmonization lookup CSV.

    Caches the result so repeated calls within the same process read the file
    only once.

    Returns:
        DataFrame with columns [kod, namn, lan_kod, lan_namn, valid_from, valid_to].

    Raises:
        FileNotFoundError: If the CSV is not found at _LOOKUP_PATH.
    """
    if not _LOOKUP_PATH.exists():
        raise FileNotFoundError(
            f"Lookup file not found: {_LOOKUP_PATH}. "
            "Run 'python -m src.clean.generate_kommunkod_lookup' to generate it."
        )
    df = pd.read_csv(_LOOKUP_PATH, dtype=_LOOKUP_DTYPES, encoding="utf-8-sig")
    # Ensure zero-padding in case the CSV was edited manually.
    df["kod"] = df["kod"].str.zfill(4)
    df["lan_kod"] = df["lan_kod"].str.zfill(2)
    logger.debug("Loaded harmonization lookup: %d rows from %s", len(df), _LOOKUP_PATH)
    return df
