"""Render the shared sidebar used on all dashboard pages.

render_sidebar(page_key) builds a 260 px navy sidebar containing: a brand
block (gold accent bar, 'KSS' mark, title, sub), navigation links to the three
pages, a year selector (st.pills, single, default 2024), a risk-class filter
(st.pills, multi, options from SWEDISH_LABELS), a color-coded risk legend, and
a footer with data source, last-updated date, and version string.

All label strings come from SWEDISH_LABELS in src/ui/labels.py.
"""
