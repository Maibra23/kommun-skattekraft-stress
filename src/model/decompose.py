"""Decompose each municipality's predicted growth gap vs the national mean.

For each municipality and each independent variable, computes
(municipality value − national mean) × beta_coefficient.  The residual term
captures the municipality fixed effect plus the idiosyncratic error.  Writes
the 290 × 5 contribution matrix to artifacts/decomposition.parquet with
columns [kommun_kod, decomp_unemployment, decomp_dependency,
decomp_population, decomp_education, decomp_residual].
"""
