"""Generate data/lookup/kommunkod_harmonization.csv from SCB pxweb metadata.

Fetches the Region dimension from the OE0101/SkatteKraft table using the
vs:RegionKommun07EjAggr value set, which returns exactly the 290 kommuner valid
for 2024 boundaries.  Produces the static CSV consumed by harmonize_kommunkod.py.

Run this script once to (re)generate the lookup file:
    python -m src.clean.generate_kommunkod_lookup

The generated CSV has columns:
    kod        — 4-digit zero-padded SCB municipality code (string)
    namn       — Swedish municipality name
    lan_kod    — 2-digit zero-padded county code (string, first two digits of kod)
    lan_namn   — Swedish county name (looked up from the embedded mapping)
    valid_from — First year the code is valid (integer; 2010 for all 2024 codes)
    valid_to   — Last year the code is valid (integer; 9999 = currently valid)
"""

import logging
import sys
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).parents[2]
_OUTPUT_PATH = _PROJECT_ROOT / "data" / "lookup" / "kommunkod_harmonization.csv"

# Add project root to sys.path so the import below works when run as a script.
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.fetch.pxweb_client import fetch_metadata  # noqa: E402

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# County (län) code → name mapping (all 21 counties in Sweden, 2024)
# ---------------------------------------------------------------------------

_LAN_NAMES: dict[str, str] = {
    "01": "Stockholms län",
    "03": "Uppsala län",
    "04": "Södermanlands län",
    "05": "Östergötlands län",
    "06": "Jönköpings län",
    "07": "Kronobergs län",
    "08": "Kalmar län",
    "09": "Gotlands län",
    "10": "Blekinge län",
    "12": "Skåne län",
    "13": "Hallands län",
    "14": "Västra Götalands län",
    "17": "Värmlands län",
    "18": "Örebro län",
    "19": "Västmanlands län",
    "20": "Dalarnas län",
    "21": "Gävleborgs län",
    "22": "Västernorrlands län",
    "23": "Jämtlands län",
    "24": "Västerbottens län",
    "25": "Norrbottens län",
}

# SCB table to query for the region dimension
_METADATA_URL = (
    "https://api.scb.se/OV0104/v1/doris/sv/ssd/START/OE/OE0101/SkatteKraft"
)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def generate_lookup() -> pd.DataFrame:
    """Fetch municipality codes and names from SCB and write the lookup CSV.

    Returns:
        DataFrame with columns [kod, namn, lan_kod, lan_namn, valid_from, valid_to].

    Raises:
        ValueError: If the API call fails or the result does not have exactly 290 rows.
    """
    logger.info("Fetching OE0101 metadata to extract Region dimension …")
    meta = fetch_metadata(_METADATA_URL)

    # Extract the Region variable from metadata
    region_var = next(
        (v for v in meta.get("variables", []) if v.get("code") == "Region"),
        None,
    )
    if region_var is None:
        raise ValueError(
            "Region variable not found in OE0101 metadata. "
            "SCB API may have changed its response structure."
        )

    codes: list[str] = region_var.get("values", [])
    names: list[str] = region_var.get("valueTexts", [])

    if len(codes) != len(names):
        raise ValueError(
            f"Mismatch: {len(codes)} codes but {len(names)} names in Region metadata."
        )

    # Filter to 4-digit municipality codes only (exclude län and national totals).
    rows = []
    for code, name in zip(codes, names):
        code_z = code.zfill(4)
        if len(code_z) != 4 or not code_z.isdigit():
            continue
        lan_kod = code_z[:2]
        if lan_kod not in _LAN_NAMES:
            continue  # skip non-municipality codes (e.g. aggregation groups)
        rows.append(
            {
                "kod": code_z,
                "namn": name,
                "lan_kod": lan_kod,
                "lan_namn": _LAN_NAMES[lan_kod],
                "valid_from": 2010,
                "valid_to": 9999,
            }
        )

    df = pd.DataFrame(rows).sort_values("kod").reset_index(drop=True)

    n = len(df)
    logger.info("Extracted %d municipality entries from SCB metadata.", n)
    if n != 290:
        raise ValueError(
            f"Expected exactly 290 municipalities, got {n}. "
            "Check the Region dimension filter and _LAN_NAMES mapping."
        )

    _OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(_OUTPUT_PATH, index=False, encoding="utf-8-sig")
    logger.info("Written lookup CSV to %s", _OUTPUT_PATH)
    return df


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    )
    df = generate_lookup()
    print(f"\nGenerated {len(df)}-row lookup CSV at {_OUTPUT_PATH}")
    print(f"\nFirst 5 rows:\n{df.head().to_string(index=False)}")
    print(f"\nLast 5 rows:\n{df.tail().to_string(index=False)}")
    print(f"\nCounties covered: {df['lan_kod'].nunique()}")
