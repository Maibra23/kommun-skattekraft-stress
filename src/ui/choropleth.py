"""Render an interactive Folium choropleth map of municipal vulnerability scores.

Run scripts/download_geojson.py once before first use to populate data/geo/.

render_choropleth(data, height, key) creates a polygon-based Folium map
using data/geo/kommuner.geojson (from okfse/sweden-geojson).  Colors are drawn
from DIVERGING_SCALE: green = low vulnerability, red = high vulnerability.
Map height is 480 px.  Tooltips show municipality name and key metrics.
The map is embedded in Streamlit via streamlit_folium.st_folium().
Basemap tiles come from Esri's light grey canvas, which needs no API key.

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

# Basemap tiles.  CARTO now stamps an "API KEY REQUIRED" watermark onto tiles
# served from basemaps.cartocdn.com without credentials -- the request still
# returns HTTP 200, so the map defaces itself silently.  Esri's light grey
# canvas is served without credentials and matches the muted palette.
_TILE_URL = (
    "https://server.arcgisonline.com/ArcGIS/rest/services/"
    "Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}"
)
_TILE_ATTRIBUTION = "Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ"
_TILE_MAX_ZOOM = 16

# Map viewport centred on Sweden
_MAP_CENTER = (63.0, 16.5)
_MAP_ZOOM_START = 5

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
    df["risk_class_label"] = df["risk_class"].astype(object).map(risk_label_map).fillna("")
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

    # Build linear colormap (used for coloring polygons)
    colormap = cm.LinearColormap(
        colors=DIVERGING_SCALE,
        vmin=_VMIN,
        vmax=_VMAX,
        caption=SWEDISH_LABELS["map_legend_caption"],
    )

    # Create base map centered on Sweden
    m = build_base_map()

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

    # Add responsive legend as custom HTML element
    legend_html = _build_responsive_legend(
        colors=DIVERGING_SCALE,
        vmin=_VMIN,
        vmax=_VMAX,
        caption=SWEDISH_LABELS["map_legend_caption"],
    )
    m.get_root().html.add_child(folium.Element(legend_html))

    # Hide the selection rectangle that appears on click
    hide_selection_css = """
    <style>
        .leaflet-interactive:focus {
            outline: none !important;
        }
        .folium-map path.leaflet-interactive:focus {
            outline: none !important;
        }
    </style>
    """
    m.get_root().html.add_child(folium.Element(hide_selection_css))

    # Render in Streamlit (feature_group_to_add=[] prevents selection rectangle)
    st_folium(
        m,
        height=height,
        use_container_width=True,
        key=key,
        returned_objects=[],
        feature_group_to_add=[],
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def build_base_map() -> folium.Map:
    """Create the empty Sweden-centred base map used by the choropleth.

    The tile layer is configured from an explicit URL template rather than a
    named folium provider so that the map cannot silently switch to a service
    that requires an API key.

    Returns:
        A folium.Map with the keyless basemap already attached.
    """
    return folium.Map(
        location=list(_MAP_CENTER),
        zoom_start=_MAP_ZOOM_START,
        tiles=_TILE_URL,
        attr=_TILE_ATTRIBUTION,
        max_zoom=_TILE_MAX_ZOOM,
        control_scale=False,
    )


def _build_responsive_legend(
    colors: list[str],
    vmin: float,
    vmax: float,
    caption: str,
) -> str:
    """Build a responsive HTML legend that scales with map container width.

    Args:
        colors: List of hex color strings for the gradient.
        vmin: Minimum value for the scale.
        vmax: Maximum value for the scale.
        caption: Legend caption text.

    Returns:
        HTML string for the legend element.
    """
    # Build CSS gradient from colors
    gradient_stops = ", ".join(
        f"{c} {i * 100 / (len(colors) - 1):.1f}%"
        for i, c in enumerate(colors)
    )

    return f"""
    <style>
        .kss-legend-container {{
            position: absolute;
            top: 10px;
            left: 50px;
            right: 50px;
            z-index: 1000;
            pointer-events: none;
        }}
        .kss-legend {{
            background: rgba(255, 255, 255, 0.95);
            border-radius: 4px;
            padding: 6px 10px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.15);
            font-family: Source Sans 3, system-ui, sans-serif;
            font-size: 10px;
            max-width: 100%;
            box-sizing: border-box;
        }}
        .kss-legend-caption {{
            color: #1A1A2E;
            font-weight: 500;
            margin-bottom: 3px;
            text-align: center;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .kss-legend-bar {{
            height: 8px;
            width: 100%;
            background: linear-gradient(to right, {gradient_stops});
            border-radius: 2px;
            margin-bottom: 3px;
        }}
        .kss-legend-labels {{
            display: flex;
            justify-content: space-between;
            color: #6B7280;
            font-size: 9px;
        }}
    </style>
    <div class="kss-legend-container">
        <div class="kss-legend">
            <div class="kss-legend-caption">{caption}</div>
            <div class="kss-legend-bar"></div>
            <div class="kss-legend-labels">
                <span>{vmin:+.1f}</span>
                <span>0</span>
                <span>{vmax:+.1f}</span>
            </div>
        </div>
    </div>
    """


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
