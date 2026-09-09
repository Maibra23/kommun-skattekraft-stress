"""Reusable Streamlit UI components for the dashboard.

Implements: page_title(eyebrow, title, subtitle, year), kpi_card(label,
value, unit, delta, delta_direction, variant, tooltip), render_kpi_row(cards),
card_header(title, subtitle, tag), and footer_note(source, version).

Delta direction semantics for skattekraft growth are inverted from the SHAI
reference: 'up' = growth = GREEN (good), 'down' = decline = RED (bad),
'flat' = stable = GRAY.  This is intentional and documented here.

All user-facing strings come from SWEDISH_LABELS in src/ui/labels.py.
"""

import streamlit as st

from src.ui.labels import GLOSSARY, SWEDISH_LABELS


# ---------------------------------------------------------------------------
# Public API — all functions return raw HTML strings unless noted
# ---------------------------------------------------------------------------


def page_title(
    eyebrow: str,
    title: str,
    subtitle: str = "",
    year: int | str | None = None,
) -> str:
    """Render the page title block with eyebrow, title, subtitle, and year.

    Args:
        eyebrow: Uppercase label above title (e.g. 'NATIONELL VY').
        title: Main page title.
        subtitle: Optional description below title.
        year: Optional year badge displayed on the right.

    Returns:
        HTML string for the page title block.
    """
    year_html = ""
    if year is not None:
        year_html = f'<span class="shai-year">{year}</span>'

    subtitle_html = ""
    if subtitle:
        subtitle_html = f'<div class="shai-subtitle">{subtitle}</div>'

    return f"""
    <div class="shai-page-title">
        <div class="shai-eyebrow">{eyebrow}</div>
        <h1>{title}</h1>
        {subtitle_html}
        {year_html}
    </div>
    """


def kpi_card(
    label: str,
    value: str,
    unit: str = "",
    delta: str | None = None,
    delta_direction: str = "flat",
    variant: str = "default",
    tooltip: str | None = None,
) -> str:
    """Render a KPI metric card with optional delta indicator.

    Args:
        label: Uppercase card label (Swedish).
        value: Formatted value string.
        unit: Optional unit suffix.
        delta: Optional delta string (e.g. '+2,3 %').
        delta_direction: One of 'up' (green), 'down' (red), 'flat' (gray).
            For skattekraft: up=good, down=bad (inverted from SHAI).
        variant: CSS variant class — 'default', 'danger', or 'success'.
        tooltip: Optional tooltip text.

    Returns:
        HTML string for the KPI card.
    """
    variant_class = f" variant-{variant}" if variant != "default" else ""
    tooltip_attr = f' title="{tooltip}"' if tooltip else ""

    value_html = f"{value}"
    if unit:
        value_html += f' <span style="font-size:14px;font-weight:400;color:#6B7280;">{unit}</span>'

    delta_html = ""
    if delta is not None:
        delta_html = (
            f'<div class="shai-kpi-delta delta-{delta_direction}">'
            f"{delta}</div>"
        )

    return f"""
    <div class="shai-kpi{variant_class}"{tooltip_attr}>
        <div class="shai-kpi-label">{label}</div>
        <div class="shai-kpi-value">{value_html}</div>
        {delta_html}
    </div>
    """


def render_kpi_row(cards: list[str]) -> None:
    """Render a row of KPI cards in equal-width columns.

    Args:
        cards: List of HTML strings from kpi_card().
    """
    cols = st.columns(len(cards))
    for col, card_html in zip(cols, cards):
        with col:
            st.html(card_html)


def help_badge(*terms: str) -> str:
    """Render a '?' that reveals the glossary entries a section relies on.

    Replaces the single glossary expander: a reader who meets
    "försörjningskvot" under a chart should find out what it means there,
    not on another page.  Pure CSS, revealed on hover and on keyboard focus,
    so it costs no rerun and works without JavaScript.

    Args:
        *terms: Keys into labels.GLOSSARY, shown in the order given.

    Returns:
        HTML string for the badge, or "" when no term is named.

    Raises:
        KeyError: If a term is not in the glossary.
    """
    if not terms:
        return ""
    entries = "".join(
        f'<span class="shai-help-item">'
        f"<strong>{GLOSSARY[term].title}</strong> {GLOSSARY[term].text}"
        f"</span>"
        for term in terms
    )
    return (
        '<span class="shai-help" tabindex="0" role="note" '
        f'aria-label="{SWEDISH_LABELS["help_aria"]}">'
        '<span class="shai-help-mark">?</span>'
        f'<span class="shai-help-pop">{entries}</span>'
        "</span>"
    )


def card_header(
    title: str,
    subtitle: str = "",
    tag: str = "",
    help_terms: tuple[str, ...] = (),
) -> str:
    """Render a card header with title, optional subtitle, and tag.

    Args:
        title: Card title.
        subtitle: Optional description.
        tag: Optional metadata tag (e.g. '2024').
        help_terms: Glossary keys to offer behind a '?' beside the title.

    Returns:
        HTML string for the card header.
    """
    tag_html = f'<span class="shai-tag">{tag}</span>' if tag else ""

    subtitle_html = ""
    if subtitle:
        subtitle_html = f'<div class="shai-subtitle">{subtitle}</div>'

    return f"""
    <div class="shai-card-header">
        <div>
            <div class="shai-card-title-row">
                <h3>{title}</h3>
                {help_badge(*help_terms)}
            </div>
            {subtitle_html}
        </div>
        {tag_html}
    </div>
    """


def footer_note(source: str, version: str, updated: str = "") -> str:
    """Render the page footer with source attribution, version, and date.

    Args:
        source: Data source string (Swedish).
        version: Version code (e.g. 'v1.0').
        updated: Optional last-updated date string (e.g. '2026-04-24').

    Returns:
        HTML string for the footer.
    """
    updated_html = ""
    if updated:
        updated_html = (
            f'<span class="shai-footer-source" style="margin-left:12px;">'
            f'{SWEDISH_LABELS["footer_updated"]}: {updated}</span>'
        )
    return f"""
    <div class="shai-footer">
        <span class="shai-footer-source">{SWEDISH_LABELS["footer_source_label"]}: {source}</span>
        {updated_html}
        <span class="shai-footer-version">{version}</span>
    </div>
    """
