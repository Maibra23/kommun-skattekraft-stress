"""Fetch municipal population data from SCB table BE0101.

Downloads folkmängd by age group for all 290 kommuner for 2010–2024 using
the generic pxweb_client.  Caches raw response to data/raw/.  Returns a
tidy DataFrame with columns [kommun_kod, year, population_total,
pop_0_19, pop_20_64, pop_65_plus] needed to compute dependency_ratio and
population_growth_pct in the clean module.
"""
