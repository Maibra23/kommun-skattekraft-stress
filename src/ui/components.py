"""Reusable Streamlit UI components for the dashboard.

Implements: page_title(eyebrow, title, subtitle, year), kpi_card(label,
value, unit, delta, delta_direction, variant, tooltip), render_kpi_row(cards),
card_header(title, subtitle, tag), card(title, subtitle, tag, content),
risk_pill(level), and footer_note(source, version).

Delta direction semantics for skattekraft growth are inverted from the SHAI
reference: 'up' = growth = GREEN (good), 'down' = decline = RED (bad),
'flat' = stable = GRAY.  This is intentional and documented here.

All user-facing strings come from SWEDISH_LABELS in src/ui/labels.py.
"""
