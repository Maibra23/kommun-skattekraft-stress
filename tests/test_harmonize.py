"""Unit tests for src/clean/harmonize_kommunkod.py.

Tests cover: correct mapping of historically merged municipalities to their
2024 successor codes, identity mapping for unchanged codes, rejection of
unrecognized codes with ValueError, zero-padding of 3-digit codes to
4-digit strings, and idempotency (applying harmonization twice yields the
same result as applying it once).
"""
