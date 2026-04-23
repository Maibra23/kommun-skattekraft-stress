"""Merge all cleaned data sources into the balanced panel DataFrame.

Joins harmonized skattekraft, population, unemployment, and education data on
[kommun_kod, year], validates that the result is a balanced 290 × 15 panel,
drops municipalities with any missing values, and writes the final panel to
data/processed/panel.parquet using PyArrow.
"""
