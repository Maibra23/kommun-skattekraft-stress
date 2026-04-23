"""Data pipeline orchestrator: fetch → clean → estimate → predict → decompose.

Run this script locally (not on Streamlit Cloud) to regenerate all artifacts.
Steps executed in order:
  1. Fetch raw data from SCB PxWeb API (skattekraft, population, unemployment, education)
  2. Harmonize municipality codes to 2024 boundaries
  3. Compute derived variables (dependency_ratio, growth rates)
  4. Build and validate the balanced 290 × 15 panel, write panel.parquet
  5. Estimate the two-way fixed-effects PanelOLS model, write model_results.pkl
  6. Generate 2025 vulnerability predictions and ranking, write predictions.parquet
  7. Compute structural decomposition, write decomposition.parquet

All steps are logged to data/raw/pipeline.log.  Re-run is idempotent: cached
raw JSON responses in data/raw/ are reused unless --force-fetch is passed.
"""
