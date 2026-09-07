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
raw JSON responses in data/raw/ are reused unless --force-refresh is passed.
"""

import argparse
import logging
import sys
import time
import traceback
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
PANEL_PATH = PROJECT_ROOT / "data" / "processed" / "panel.parquet"
LOG_PATH = PROJECT_ROOT / "data" / "raw" / "pipeline.log"

# Artifact files that must exist for steps 6-8 to be skippable
_MODEL_ARTIFACTS = [
    ARTIFACTS_DIR / "model_results.pkl",
    ARTIFACTS_DIR / "coefficients.parquet",
    ARTIFACTS_DIR / "coefficients_cross.parquet",
]
_PREDICTION_ARTIFACTS = [
    ARTIFACTS_DIR / "predictions.parquet",
    ARTIFACTS_DIR / "ranking.parquet",
]
_DECOMPOSITION_ARTIFACTS = [
    ARTIFACTS_DIR / "decomposition.parquet",
    ARTIFACTS_DIR / "decomposition_cross.parquet",
    ARTIFACTS_DIR / "diagnostics.parquet",
]
# Descriptive spine (REMEDIATION_PLAN.md T1.1). Depends on the panel only, not
# on the model, so it is regenerated with the panel rather than with steps 5-7.
_POSITION_ARTIFACTS = [
    ARTIFACTS_DIR / "position.parquet",
]
_ALL_ARTIFACTS = (
    _MODEL_ARTIFACTS
    + _PREDICTION_ARTIFACTS
    + _DECOMPOSITION_ARTIFACTS
    + _POSITION_ARTIFACTS
)

logger = logging.getLogger("pipeline")


def _configure_logging() -> None:
    """Configure logging to both stdout and data/raw/pipeline.log."""
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s  %(levelname)-8s  %(name)s — %(message)s"
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler
    file_handler = logging.FileHandler(LOG_PATH, mode="a", encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)


def _artifacts_are_fresh() -> bool:
    """Check if all artifacts exist and are newer than panel.parquet.

    Returns:
        True if all artifact files exist and have modification times
        newer than panel.parquet (i.e., steps 6-8 can be skipped).
    """
    if not PANEL_PATH.exists():
        return False

    panel_mtime = PANEL_PATH.stat().st_mtime

    for artifact_path in _ALL_ARTIFACTS:
        if not artifact_path.exists():
            return False
        if artifact_path.stat().st_mtime < panel_mtime:
            return False

    return True


def _run_step(step_num: int, description: str, func, *args, **kwargs):
    """Run a pipeline step with timing and logging.

    Args:
        step_num: Step number for logging.
        description: Human-readable description.
        func: Callable to execute.
        *args, **kwargs: Passed to func.

    Returns:
        The return value of func.
    """
    logger.info("Step %d: %s", step_num, description)
    t0 = time.perf_counter()
    result = func(*args, **kwargs)
    elapsed = time.perf_counter() - t0
    logger.info("Step %d completed in %.1f seconds", step_num, elapsed)
    return result


def main() -> None:
    """Run the full pipeline: fetch → clean → estimate → predict → decompose."""
    parser = argparse.ArgumentParser(
        description="Kommunal Skattekraft Stress Monitor — data pipeline"
    )
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        default=False,
        help="Re-fetch all data from SCB API and regenerate all artifacts, "
        "ignoring caches.",
    )
    args = parser.parse_args()

    _configure_logging()
    logger.info("=" * 70)
    logger.info("Pipeline started (force_refresh=%s)", args.force_refresh)
    logger.info("=" * 70)

    pipeline_t0 = time.perf_counter()

    try:
        # ---------------------------------------------------------------
        # Steps 1-4: Fetch + build panel (handled by build_panel)
        # ---------------------------------------------------------------
        from src.clean.build_panel import build_panel

        _run_step(
            1,
            "Fetch all data sources and build panel",
            build_panel,
            force_refresh=args.force_refresh,
        )

        # ---------------------------------------------------------------
        # Step 4b: Position and drift (descriptive spine, no model)
        # ---------------------------------------------------------------
        # Runs unconditionally with the panel: it depends on skattekraft alone,
        # is cheap, and must stay in step with the panel's full 2010-2026 range
        # rather than with the model artifacts.
        from src.model.position import run_position

        _run_step(4, "Compute relative position and drift", run_position)

        # ---------------------------------------------------------------
        # Steps 5-7: Estimate, predict, decompose
        # ---------------------------------------------------------------
        # Idempotency: skip if all artifacts are fresh
        if not args.force_refresh and _artifacts_are_fresh():
            logger.info(
                "All artifacts are newer than panel.parquet — skipping "
                "steps 5-7. Use --force-refresh to regenerate."
            )
        else:
            # Step 5: Estimate
            from src.model.estimate import run_estimation

            _run_step(5, "Estimate panel regression model", run_estimation)

            # Step 5b: Cross-sectional estimate (REMEDIATION_PLAN.md T2.1).
            # Writes its own artifact; the FE coefficients.parquet the deployed
            # dashboard reads is left untouched until the T1.2 cutover.
            from src.model.estimate_cross import run_estimation_cross

            _run_step(
                5,
                "Estimate cross-sectional model (position on structural variables)",
                run_estimation_cross,
            )

            # Step 6: Predict
            from src.model.predict import run_prediction

            _run_step(
                6,
                "Generate 2025 predictions and vulnerability ranking",
                run_prediction,
            )

            # Step 7: Decompose
            from src.model.decompose import run_decomposition

            _run_step(
                7,
                "Compute structural decomposition",
                run_decomposition,
            )

            # Step 7b: Diagnostics, then the cross-sectional decomposition.
            # Order matters: the diagnostics say how far the variables can be
            # separated at all, and the decomposition then draws only what the
            # identification flag permits (REMEDIATION_PLAN.md T2.3, T2.2).
            from src.model.diagnostics import run_diagnostics

            _run_step(7, "Compute collinearity and scale diagnostics", run_diagnostics)

            from src.model.decompose_cross import run_decomposition_cross

            _run_step(
                7,
                "Decompose the position gap (identified components only)",
                run_decomposition_cross,
            )

        # ---------------------------------------------------------------
        # Summary
        # ---------------------------------------------------------------
        total_elapsed = time.perf_counter() - pipeline_t0
        logger.info("=" * 70)
        logger.info(
            "Pipeline completed. Total time: %.1f seconds. "
            "Artifacts written to %s/",
            total_elapsed,
            ARTIFACTS_DIR,
        )
        logger.info("=" * 70)

    except Exception:
        total_elapsed = time.perf_counter() - pipeline_t0
        logger.error(
            "Pipeline FAILED after %.1f seconds. Traceback:\n%s",
            total_elapsed,
            traceback.format_exc(),
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
