"""Fetch municipal tax base (skattekraft) per capita from SCB table OE0101.

Downloads beskattningsbar förvärvsinkomst per invånare for all 290 kommuner
for the years 2010–2024 using the generic pxweb_client and caches the raw
JSON response to data/raw/.  Returns a tidy DataFrame with columns
[kommun_kod, year, tax_base_per_capita].
"""
