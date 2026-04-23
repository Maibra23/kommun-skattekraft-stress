"""Estimate the two-way fixed-effects panel model using linearmodels.PanelOLS.

Reads data/processed/panel.parquet, sets the MultiIndex to [kommun_kod, year],
fits PanelOLS with entity_effects=True, time_effects=True, and standard errors
clustered at the municipality level.  Writes the fitted result object to
artifacts/model_results.pkl and the coefficient table to
artifacts/coefficients.parquet.
"""
