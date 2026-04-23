"""Harmonize historical municipality codes to 2024 boundaries.

Loads the static lookup table data/lookup/kommunkod_harmonization.csv and
applies a mapping that resolves mergers, splits, and renames so that all
years in the panel reference current 2024 municipality codes.  Raises a
ValueError if any unmapped code is encountered.
"""
