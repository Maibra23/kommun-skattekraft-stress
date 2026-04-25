"""Download kommun-level GeoJSON from okfse/sweden-geojson on GitHub.

Saves to data/geo/kommuner.geojson with validation that exactly 290
municipality features are present and that each feature has a property
that can be normalized to a 4-digit kommun code.

Idempotent: skips download if the file already exists and has 290 features.

Usage:
    python scripts/download_geojson.py
"""

import json
import sys
from pathlib import Path

import requests

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_OUTPUT_PATH = _PROJECT_ROOT / "data" / "geo" / "kommuner.geojson"

# Primary source: okfse/sweden-geojson on GitHub
_PRIMARY_URL = (
    "https://raw.githubusercontent.com/okfse/sweden-geojson/"
    "master/swedish_municipalities.geojson"
)

# Fallback URL (alternative repo mirror)
_FALLBACK_URL = (
    "https://raw.githubusercontent.com/okfse/sweden-geojson/"
    "main/swedish_municipalities.geojson"
)

_EXPECTED_FEATURES = 290


def _extract_kommun_kod(feature: dict) -> str | None:
    """Try to extract a 4-digit kommun code from feature properties."""
    props = feature.get("properties", {})
    for key in ("KnKod", "kommun_kod", "ref", "KOD", "id", "KNKOD", "knkod"):
        val = props.get(key)
        if val is not None:
            s = str(val).zfill(4)
            if len(s) == 4 and s.isdigit():
                return s
    # Try feature id
    fid = feature.get("id")
    if fid is not None:
        s = str(fid).zfill(4)
        if len(s) == 4 and s.isdigit():
            return s
    return None


def download() -> None:
    """Download and validate the kommun GeoJSON file."""
    # Check if already exists and valid
    if _OUTPUT_PATH.exists():
        try:
            with open(_OUTPUT_PATH, encoding="utf-8") as f:
                existing = json.load(f)
            n_features = len(existing.get("features", []))
            if n_features == _EXPECTED_FEATURES:
                print(
                    f"GeoJSON already exists with {n_features} features. "
                    "Skipping download."
                )
                return
            print(
                f"Existing file has {n_features} features "
                f"(expected {_EXPECTED_FEATURES}). Re-downloading."
            )
        except (json.JSONDecodeError, OSError):
            print("Existing file is corrupt. Re-downloading.")

    # Try primary URL, then fallback
    geojson = None
    for url in [_PRIMARY_URL, _FALLBACK_URL]:
        print(f"Downloading from {url}...")
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            geojson = resp.json()
            break
        except (requests.RequestException, json.JSONDecodeError) as e:
            print(f"  Failed: {e}")
            continue

    if geojson is None:
        print(
            "\nCould not download GeoJSON from any source.\n"
            "Manual download instructions:\n"
            "  1. Visit https://github.com/okfse/sweden-geojson\n"
            "  2. Download swedish_municipalities.geojson\n"
            "  3. Save to data/geo/kommuner.geojson\n"
            "\nAlternatively, install swemaps:\n"
            "  pip install swemaps\n"
            "  python -c \"import swemaps; print(swemaps.get_path('kommun'))\"\n"
        )
        sys.exit(1)

    # Validate feature count
    features = geojson.get("features", [])
    n_features = len(features)
    print(f"Downloaded {n_features} features.")

    if n_features != _EXPECTED_FEATURES:
        print(
            f"WARNING: Expected {_EXPECTED_FEATURES} features but got "
            f"{n_features}. The file may include non-municipality features "
            "or use outdated boundaries."
        )

    # Validate kommun codes
    valid_codes = set()
    invalid_features = 0
    for feature in features:
        kod = _extract_kommun_kod(feature)
        if kod:
            valid_codes.add(kod)
        else:
            invalid_features += 1

    print(f"Found {len(valid_codes)} unique kommun codes.")
    if invalid_features:
        print(f"WARNING: {invalid_features} features have no extractable kommun code.")

    # Save
    _OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False)

    print(f"Saved to {_OUTPUT_PATH}")


if __name__ == "__main__":
    download()
