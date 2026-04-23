"""Unit tests for src/model/decompose.py.

Tests cover: decomposition columns sum to approximately the total predicted
gap for each municipality, national-mean municipality has all contribution
columns near zero, residual absorbs the correct amount, output DataFrame has
exactly 290 rows and the required columns [kommun_kod, decomp_unemployment,
decomp_dependency, decomp_population, decomp_education, decomp_residual],
and no NaN values appear in the output.
"""
