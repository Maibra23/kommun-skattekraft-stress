"""Plotly chart theme and layout factory for the dashboard.

Defines CHART_PALETTE (8-color sequence) and get_chart_layout(title, height,
xaxis_title, yaxis_title, showlegend) which returns a Plotly Layout dict
conforming to the design system: Source Sans 3 12 px base font, white plot
background, navy (#0B1F3F) hover background, gridlines #E5E7EB, and no
Plotly branding.  All axis label strings should be passed in from
SWEDISH_LABELS by the calling page.
"""
