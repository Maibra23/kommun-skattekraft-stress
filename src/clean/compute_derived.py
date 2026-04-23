"""Compute derived variables: dependency_ratio and year-over-year growth rates.

Calculates dependency_ratio as (pop_0_19 + pop_65_plus) / pop_20_64,
population_growth_pct as year-over-year percent change in total population,
and tax_base_growth_pct as year-over-year percent change in tax_base_per_capita.
All computations are performed within each municipality group to avoid
cross-municipality contamination.
"""
