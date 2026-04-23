"""Generate out-of-sample 2025 vulnerability predictions for all municipalities.

Loads the fitted model from artifacts/model_results.pkl and the most recent
observed (2024) values of the independent variables.  Computes predicted
tax_base_growth_pct for 2025 using estimated betas, municipality fixed effects,
and a year effect proxied by the mean of the last three observed year effects.
Standardizes predictions to vulnerability_score (z-score, sign-flipped so
high = more vulnerable), assigns vulnerability_rank and risk_class (quintile
labels: 'hog', 'medel', 'lag').  Writes artifacts/predictions.parquet and
artifacts/ranking.parquet.
"""
