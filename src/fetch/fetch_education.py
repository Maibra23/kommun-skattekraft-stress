"""Fetch municipal education attainment shares from SCB table UF0506.

Downloads the share of population aged 25–64 with post-secondary education
of 3 or more years for all 290 kommuner for 2010–2024 using the generic
pxweb_client.  Caches raw response to data/raw/.  Returns a tidy DataFrame
with columns [kommun_kod, year, edu_share].
"""
