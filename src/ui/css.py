"""Color tokens, global CSS string, and inject_css() helper for Streamlit pages.

Defines the COLORS dict (primary navy, accent gold, risk-level colors, and
neutral palette), DIVERGING_SCALE and CHART_PALETTE lists, and GLOBAL_CSS
which imports Source Sans 3 and IBM Plex Mono from Google Fonts and applies
the design system layout rules.  The inject_css() function injects GLOBAL_CSS
via st.markdown(unsafe_allow_html=True).

Note: CSS class names use the 'shai-' prefix for visual fidelity to the SHAI
reference design; only the brand mark is replaced with 'KSS'.
"""
