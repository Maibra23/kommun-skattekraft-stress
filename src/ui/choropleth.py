"""Render an interactive Folium choropleth map of municipal position and drift.

Run scripts/download_geojson.py once before first use to populate data/geo/.

render_choropleth(data, layer, height, key) creates a polygon-based Folium map
using data/geo/kommuner.geojson (from okfse/sweden-geojson).  Two layers are
offered: relative position on a sequential ramp, and five-year drift on a
diverging one centred at zero.  Map height is 480 px.  Tooltips show
municipality name and key metrics.  The map is embedded in Streamlit via
streamlit_folium.st_folium().  Basemap tiles come from Esri's light grey
canvas, which needs no API key.

Each layer carries its own legend caption; see MAP_LAYERS.
"""

import json
from dataclasses import dataclass
from pathlib import Path

import branca.colormap as cm
import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from src.ui.css import COLORS, DIVERGING_SCALE, SEQUENTIAL_SCALE
from src.ui.labels import SWEDISH_LABELS, format_pct, format_sek

#: DIVERGING_SCALE runs orange (low) to blue (high), which is the right
#: direction for drift: falling behind reads warm, gaining reads cool.
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


# ---------------------------------------------------------------------------
# Map layers (REMEDIATION_PLAN.md T1.2)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MapLayer:
    """One selectable choropleth layer.

    Attributes:
        key: Stable identifier used in code and tests.
        column: The column of the merged frame this layer colours by.
        label: Swedish radio-button label.
        colors: Colour ramp, low value first.
        vmin: Value mapped to the first colour; values below are clipped.
        vmax: Value mapped to the last colour; values above are clipped.
        diverging: Whether the scale has a meaningful midpoint. Signed
            quantities do; levels do not.
        legend_caption: Caption under the legend gradient.
        decimals: Digits shown in the tooltip.
    """

    key: str
    column: str
    label: str
    colors: list[str]
    vmin: float
    vmax: float
    diverging: bool
    legend_caption: str
    decimals: int = 1


#: The three layers the plan specifies. Position and drift must never share a
#: palette: position is a level on a sequential ramp, drift is signed and
#: centred on zero. Reusing the vulnerability palette for drift would imply
#: that a falling kommun is "high risk", which is a different claim.
MAP_LAYERS: dict[str, MapLayer] = {
    "position": MapLayer(
        key="position",
        column="relative_position",
        label=SWEDISH_LABELS["map_layer_position"],
        colors=SEQUENTIAL_SCALE,
        # Clipped to the body of the distribution: the median kommun sits at
        # 96.6 and the maximum at 208, so an unclipped ramp would render nine
        # kommuner in ten as one indistinguishable colour.
        vmin=80.0,
        vmax=130.0,
        diverging=False,
        legend_caption=SWEDISH_LABELS["map_legend_position"],
    ),
    "drift": MapLayer(
        key="drift",
        column="drift_5y",
        label=SWEDISH_LABELS["map_layer_drift"],
        colors=DIVERGING_SCALE,
        vmin=-4.0,
        vmax=4.0,
        diverging=True,
        legend_caption=SWEDISH_LABELS["map_legend_drift"],
    ),
}


def resolve_layer(selection: str) -> MapLayer:
    """Return the layer named by a key or by its Swedish label.

    The radio widget hands back the label; code and tests use the key.

    Args:
        selection: Either a MAP_LAYERS key or a layer's Swedish label.

    Returns:
        The matching MapLayer.

    Raises:
        KeyError: If nothing matches.
    """
    if selection in MAP_LAYERS:
        return MAP_LAYERS[selection]
    for layer in MAP_LAYERS.values():
        if layer.label == selection:
            return layer
    raise KeyError(
        f"Okänt kartlager: {selection!r}. Giltiga lager: "
        + ", ".join(f"{k} ({v.label})" for k, v in MAP_LAYERS.items())
    )

# Tooltip field aliases (Swedish), in display order.  Every field is optional:
# which ones exist depends on what the caller merged in, and after T1.2 the
# position layers carry no vulnerability columns at all.
_TOOLTIP_ALIASES = {
    "kommun_name": SWEDISH_LABELS["th_kommun"],
    "position_fmt": SWEDISH_LABELS["position_index"],
    "scb_index_fmt": SWEDISH_LABELS["position_scb_index"],
    "drift_5y_fmt": SWEDISH_LABELS["drift_5y"],
    "drift_10y_fmt": SWEDISH_LABELS["drift_10y"],
    "tax_base_per_capita_fmt": SWEDISH_LABELS["th_skattekraft"],
    "unemployment_rate_fmt": SWEDISH_LABELS["th_unemployment"],
    "population_fmt": SWEDISH_LABELS["tooltip_population"],
}


def _format_tooltip_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add the formatted tooltip columns the frame has the inputs for.

    Args:
        df: Frame keyed by kommun_kod, carrying any subset of the source
            columns.

    Returns:
        The same frame with formatted `*_fmt` columns added where possible.
    """

    def _signed_points(value: float) -> str:
        return f"{value:+.1f}".replace(".", ",")

    formatters = {
        "position_fmt": ("relative_position", lambda v: f"{v:.1f}".replace(".", ",")),
        "scb_index_fmt": ("tax_base_index_riket", lambda v: f"{v:.0f}"),
        "drift_5y_fmt": ("drift_5y", _signed_points),
        "drift_10y_fmt": ("drift_10y", _signed_points),
        "tax_base_per_capita_fmt": ("tax_base_per_capita", format_sek),
        "unemployment_rate_fmt": ("unemployment_rate", format_pct),
        "population_fmt": (
            "population",
            lambda v: f"{int(v):,}".replace(",", " "),
        ),
    }

    for target, (source, fmt) in formatters.items():
        if source in df.columns:
            df[target] = df[source].apply(lambda v, f=fmt: "" if pd.isna(v) else f(v))

    return df


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def render_choropleth(
    data: pd.DataFrame,
    layer: "str | MapLayer" = "position",
    height: int = 480,
    key: str = "kss_choropleth",
) -> None:
    """Render an interactive Folium choropleth in Streamlit.

    The colour scale comes from the selected layer, and the layers do not share
    one: relative position is a level on a sequential ramp, and five-year
    drift is signed and centred on zero. See MAP_LAYERS.

    Args:
        data: DataFrame keyed by kommun_kod. It must carry the selected layer's
            column; every other column named in _TOOLTIP_ALIASES is optional and
            appears in the tooltip only when present.
        layer: A MAP_LAYERS key, a layer's Swedish label, or a MapLayer.
        height: Map height in pixels.
        key: Streamlit component key for st_folium.
    """
    map_layer = layer if isinstance(layer, MapLayer) else resolve_layer(layer)
    if not _GEOJSON_PATH.exists():
        st.warning(SWEDISH_LABELS["choropleth_missing_geojson"])
        return

    geojson = _load_geojson()

    # Build a lookup from kommun_kod to row data
    df = data.copy()
    df["kommun_kod"] = df["kommun_kod"].astype(str).str.zfill(4)

    # Format display columns for tooltips.  Which columns exist depends on the
    # layer the caller is showing, so each is formatted only when present.
    df = _format_tooltip_columns(df)

    lookup = df.set_index("kommun_kod").to_dict("index")

    # Build linear colormap from the selected layer
    colormap = cm.LinearColormap(
        colors=map_layer.colors,
        vmin=map_layer.vmin,
        vmax=map_layer.vmax,
        caption=map_layer.legend_caption,
    )

    # Value used when a kommun has no data for this layer: the midpoint of a
    # diverging scale is meaningful (zero drift), the low end of a sequential
    # one is not, so an absent level is drawn at the bottom of the ramp.
    fallback = 0.0 if map_layer.diverging else map_layer.vmin

    # Create base map centered on Sweden
    m = build_base_map()

    # Style function
    def style_function(feature):
        kod = _extract_kommun_kod(feature)
        row = lookup.get(kod, {})
        value = row.get(map_layer.column, fallback)
        if value is None or pd.isna(value):
            value = fallback
        fill_color = colormap(
            max(map_layer.vmin, min(map_layer.vmax, float(value)))
        )
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
    # Only the fields this frame actually carries: after the cutover the
    # position layers have no vulnerability columns, and an alias pointing at a
    # missing field renders as a blank row in every tooltip.
    present = [f for f in _TOOLTIP_ALIASES if f in df.columns]
    tooltip_fields = present
    tooltip_aliases = [_TOOLTIP_ALIASES[f] for f in present]

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
        colors=map_layer.colors,
        vmin=map_layer.vmin,
        vmax=map_layer.vmax,
        caption=map_layer.legend_caption,
        diverging=map_layer.diverging,
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
    diverging: bool = True,
) -> str:
    """Build a responsive HTML legend that scales with map container width.

    The middle tick used to be a hardcoded "0", which was right while the only
    layer was a zero-centred z-score and wrong the moment a sequential level
    scale arrived: the position ramp runs 80–130 and was labelled 80 · 0 · 130.
    The midpoint is now computed, and signs are shown only for scales where a
    sign means something.

    Args:
        colors: List of hex color strings for the gradient.
        vmin: Minimum value for the scale.
        vmax: Maximum value for the scale.
        caption: Legend caption text.
        diverging: Whether the scale is signed and centred on its midpoint.

    Returns:
        HTML string for the legend element.
    """
    fmt = "+.0f" if diverging else ".0f"
    low_label = format(vmin, fmt)
    high_label = format(vmax, fmt)
    mid_label = format((vmin + vmax) / 2.0, fmt)
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
                <span>{low_label}</span>
                <span>{mid_label}</span>
                <span>{high_label}</span>
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
