"""Tests for the choropleth basemap configuration.

Regression guard: CARTO started stamping its anonymous basemap tiles with an
"API KEY REQUIRED" watermark, which silently defaced the map (tiles still
return HTTP 200, so nothing raises).  The basemap must therefore come from a
tile service that serves clean tiles without credentials.
"""

from src.ui.choropleth import (
    _TILE_ATTRIBUTION,
    _TILE_URL,
    build_base_map,
)

_KEYED_TILE_HOSTS = ("cartocdn.com", "stadiamaps.com", "thunderforest.com", "mapbox.com")


def test_tile_url_is_a_keyless_xyz_template() -> None:
    """The tile template must be complete and free of credential parameters."""
    for placeholder in ("{z}", "{x}", "{y}"):
        assert placeholder in _TILE_URL

    lowered = _TILE_URL.lower()
    assert "api_key" not in lowered
    assert "apikey" not in lowered
    assert "access_token" not in lowered


def test_tile_url_avoids_providers_that_require_credentials() -> None:
    """Hosts known to watermark or reject anonymous traffic are not allowed."""
    for host in _KEYED_TILE_HOSTS:
        assert host not in _TILE_URL


def test_base_map_renders_configured_tiles_with_attribution() -> None:
    """The rendered Leaflet map uses the configured tiles and credits them."""
    html = build_base_map().get_root().render()

    assert _TILE_URL in html
    assert "Esri" in html
    for host in _KEYED_TILE_HOSTS:
        assert host not in html


def test_tile_attribution_is_non_empty() -> None:
    """Custom tile URLs require an attribution string."""
    assert _TILE_ATTRIBUTION.strip()
