"""Authoritative Swedish user-facing label dictionary and number formatters.

SWEDISH_LABELS is the single source of truth for every string visible to
dashboard users.  Code that hardcodes Swedish text in component logic is
rejected in code review — always import from here.

Also provides three number formatting helpers:
  format_sek(value)              — integer SEK with narrow no-break space thousands separator
  format_pct(value, decimals)    — percentage with comma decimal and % suffix
  format_signed_pct(value, decimals) — signed percentage with explicit + or - sign
"""
