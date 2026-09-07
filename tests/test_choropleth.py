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


# ---------------------------------------------------------------------------
# Map layers (REMEDIATION_PLAN.md T1.2).
# The plan's explicit caution: position is a *level* and drift is *signed*.
# Sharing one palette between them would mislead — a diverging scale implies a
# meaningful midpoint, which an index level does not have.
# ---------------------------------------------------------------------------

import pytest

from src.ui.choropleth import MAP_LAYERS, resolve_layer
from src.ui.css import DIVERGING_SCALE


class TestMapLayers:
    def test_the_three_planned_layers_exist(self):
        assert set(MAP_LAYERS) == {"position", "drift", "vulnerability"}

    def test_each_layer_reads_a_different_column(self):
        columns = [layer.column for layer in MAP_LAYERS.values()]
        assert len(set(columns)) == len(columns)

    def test_position_is_sequential_not_diverging(self):
        layer = MAP_LAYERS["position"]
        assert not layer.diverging
        assert layer.colors != DIVERGING_SCALE

    def test_position_scale_is_clipped_to_the_body_of_the_distribution(self):
        """Median 96.6, p95 127, max 208 — an unclipped scale renders 90 %
        of kommuner as one indistinguishable colour."""
        layer = MAP_LAYERS["position"]
        assert layer.vmin >= 70
        assert layer.vmax <= 150

    def test_drift_is_diverging_and_symmetric_about_zero(self):
        layer = MAP_LAYERS["drift"]
        assert layer.diverging
        assert layer.vmin == -layer.vmax, "a signed scale must centre on zero"

    def test_vulnerability_layer_is_unchanged(self):
        layer = MAP_LAYERS["vulnerability"]
        assert layer.column == "vulnerability_score"
        assert layer.colors == DIVERGING_SCALE
        assert layer.vmin == -2.5 and layer.vmax == 2.5

    def test_every_layer_carries_a_swedish_label_and_caption(self):
        for layer in MAP_LAYERS.values():
            assert layer.label.strip()
            assert layer.legend_caption.strip()


class TestResolveLayer:
    def test_resolves_by_key(self):
        assert resolve_layer("drift").column == "drift_5y"

    def test_resolves_by_swedish_label(self):
        """The radio widget hands back the label, not the key."""
        label = MAP_LAYERS["position"].label
        assert resolve_layer(label).key == "position"

    def test_raises_on_an_unknown_layer(self):
        with pytest.raises(KeyError, match="[Oo]känt kartlager"):
            resolve_layer("nonsense")
