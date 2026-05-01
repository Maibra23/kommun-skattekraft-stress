"""Render an interactive Folium choropleth map of municipal vulnerability scores.

Run scripts/download_geojson.py once before first use to populate data/geo/.

render_choropleth(data, height, key) creates a polygon-based Folium map
using data/geo/kommuner.geojson (from okfse/sweden-geojson).  Colors are drawn
from DIVERGING_SCALE: green = low vulnerability, red = high vulnerability.
Map height is 480 px.  Tooltips show municipality name and key metrics.
The map is embedded in Streamlit via streamlit_folium.st_folium().

Legend caption comes from SWEDISH_LABELS['map_legend_caption'].
"""

import json
from pathlib import Path

import branca.colormap as cm
import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from src.ui.css import COLORS, DIVERGING_SCALE
from src.ui.labels import SWEDISH_LABELS, format_pct, format_sek

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_GEOJSON_PATH = _PROJECT_ROOT / "data" / "geo" / "kommuner.geojson"

# Z-score range for the color scale (vulnerability_score)
_VMIN = -2.5
_VMAX = 2.5

# Tooltip field aliases (Swedish)
_TOOLTIP_ALIASES = {
    "kommun_name": SWEDISH_LABELS["th_kommun"],
    "risk_class_label": SWEDISH_LABELS["th_risk_class"],
    "vulnerability_score_fmt": SWEDISH_LABELS["tooltip_vulnerability_score"],
    "predicted_growth_fmt": SWEDISH_LABELS["th_prognosis"],
    "vulnerability_rank": SWEDISH_LABELS["th_rank"],
    "tax_base_per_capita_fmt": SWEDISH_LABELS["th_skattekraft"],
    "unemployment_rate_fmt": SWEDISH_LABELS["th_unemployment"],
    "population_fmt": SWEDISH_LABELS["tooltip_population"],
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def render_choropleth(
    data: pd.DataFrame,
    height: int = 480,
    key: str = "kss_choropleth",
) -> None:
    """Render an interactive Folium choropleth in Streamlit.

    The map colors municipalities by vulnerability_score using a diverging
    green-to-red scale.  Tooltips show Swedish labels and formatted values.

    Args:
        data: DataFrame with required columns: kommun_kod, vulnerability_score,
            predicted_growth_2025, vulnerability_rank, risk_class, kommun_name,
            tax_base_per_capita, unemployment_rate, population.
        height: Map height in pixels.
        key: Streamlit component key for st_folium.
    """
    if not _GEOJSON_PATH.exists():
        st.warning(SWEDISH_LABELS["choropleth_missing_geojson"])
        return

    geojson = _load_geojson()

    # Build a lookup from kommun_kod to row data
    df = data.copy()
    df["kommun_kod"] = df["kommun_kod"].astype(str).str.zfill(4)

    # Format display columns for tooltips
    risk_label_map = {
        "lag": SWEDISH_LABELS["risk_low"],
        "medel": SWEDISH_LABELS["risk_medium"],
        "hog": SWEDISH_LABELS["risk_high"],
    }
    df["risk_class_label"] = df["risk_class"].map(risk_label_map).fillna("")
    df["vulnerability_score_fmt"] = df["vulnerability_score"].apply(
        lambda x: f"{x:+.2f}".replace(".", ",")
    )
    df["predicted_growth_fmt"] = df["predicted_growth_2025"].apply(
        lambda x: format_pct(x)
    )
    df["tax_base_per_capita_fmt"] = df["tax_base_per_capita"].apply(
        lambda x: format_sek(x)
    )
    df["unemployment_rate_fmt"] = df["unemployment_rate"].apply(
        lambda x: format_pct(x)
    )
    df["population_fmt"] = df["population"].apply(
        lambda x: f"{int(x):,}".replace(",", "\u202f")
    )

    lookup = df.set_index("kommun_kod").to_dict("index")

    # Build linear colormap
    colormap = cm.LinearColormap(
        colors=DIVERGING_SCALE,
        vmin=_VMIN,
        vmax=_VMAX,
        caption=SWEDISH_LABELS["map_legend_caption"],
    )

    # Create base map centered on Sweden
    m = folium.Map(
        location=[63.0, 16.5],
        zoom_start=5,
        tiles="cartodbpositron",
        control_scale=False,
    )

    # Style function
    def style_function(feature):
        kod = _extract_kommun_kod(feature)
        row = lookup.get(kod, {})
        score = row.get("vulnerability_score", 0.0)
        fill_color = colormap(max(_VMIN, min(_VMAX, score)))
        return {
            "fillColor": fill_color,
            "color": "#FFFFFF",
            "weight": 0.5,
            "fillOpacity": 0.75,
        }

    # Highlight function
    def highlight_function(feature):
        return {
            "weight": 2,
            "color": COLORS["primary"],
            "fillOpacity": 0.9,
        }

    # Add GeoJSON layer with tooltips
    tooltip_fields = list(_TOOLTIP_ALIASES.keys())
    tooltip_aliases = list(_TOOLTIP_ALIASES.values())

    # Inject data into GeoJSON properties for tooltips
    for feature in geojson["features"]:
        kod = _extract_kommun_kod(feature)
        row = lookup.get(kod, {})
        for field in tooltip_fields:
            feature["properties"][field] = row.get(field, "")

    folium.GeoJson(
        geojson,
        name="kommuner",
        style_function=style_function,
        highlight_function=highlight_function,
        tooltip=folium.GeoJsonTooltip(
            fields=tooltip_fields,
            aliases=tooltip_aliases,
            localize=False,
            sticky=True,
            style=(
                "background-color: white; "
                "border: 1px solid #ccc; "
                "border-radius: 4px; "
                "padding: 8px 12px; "
                "font-family: Source Sans 3, sans-serif; "
                "font-size: 12px; "
                "color: #1A1A2E; "
                "box-shadow: 0 2px 6px rgba(0,0,0,0.15);"
            ),
        ),
    ).add_to(m)

    colormap.add_to(m)

    # Render in Streamlit
    st_folium(m, height=height, use_container_width=True, key=key, returned_objects=[])


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


@st.cache_data
def _load_geojson() -> dict:
    """Load and cache the kommun GeoJSON file."""
    with open(_GEOJSON_PATH, encoding="utf-8") as f:
        return json.load(f)


def _extract_kommun_kod(feature: dict) -> str:
    """Extract a 4-digit kommun code from a GeoJSON feature's properties.

    Handles various property naming conventions in Swedish GeoJSON files:
    'KnKod', 'kommun_kod', 'ref', 'KOD', 'id', or the feature's id field.

    Args:
        feature: A GeoJSON feature dict.

    Returns:
        4-digit zero-padded kommun code string.
    """
    props = feature.get("properties", {})

    # Try common property names
    for key in ("KnKod", "kommun_kod", "ref", "KOD", "id", "KNKOD", "knkod"):
        val = props.get(key)
        if val is not None:
            return str(val).zfill(4)

    # Fall back to feature id
    fid = feature.get("id", "")
    if fid:
        return str(fid).zfill(4)

    return "0000"
