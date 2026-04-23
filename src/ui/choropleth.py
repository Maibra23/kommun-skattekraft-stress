"""Render an interactive Folium choropleth map of municipal vulnerability scores.

render_choropleth(df_ranking, geojson_path) creates a polygon-based Folium map
using data/geo/kommuner.geojson (from okfse/sweden-geojson).  Colors are drawn
from DIVERGING_SCALE: green = low vulnerability, red = high vulnerability.
Map height is 480 px.  Tooltips show municipality name and key metrics.
The map is embedded in Streamlit via streamlit_folium.st_folium().

Legend caption comes from SWEDISH_LABELS['map_legend_caption'].
"""
