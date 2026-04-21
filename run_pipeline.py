"""Pipeline orchestrator — runs all ETL steps in sequence.

Entry point for the entire analytical pipeline:
  python -m run_pipeline           # full dataset (data/raw/)
  python -m run_pipeline --sample  # sample data (data_sample/)

Each step is idempotent, so re-running the pipeline always produces
a consistent result. The --sample flag is essential for CI and testing,
where the full OULAD dataset (~450 MB) is not available.
"""

import argparse
import logging

from src.pipeline.step_01_ingest import ingest
from src.pipeline.step_02_transform import transform
from src.pipeline.step_03_export import export
from src.utils.logging import setup_logging
from src.utils.runtime import log_environment, step_timer

logger = logging.getLogger(__name__)


def main() -> None:
    """Parse arguments and run the full pipeline."""
    parser = argparse.ArgumentParser(
        description="Learning Retention Analytics — ETL Pipeline"
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Use data_sample/ instead of data/raw/ (for testing and CI)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug-level logging for troubleshooting",
    )
    args = parser.parse_args()

    # Configure logging before anything else
    setup_logging(level=logging.DEBUG if args.debug else logging.INFO)
    log_environment()

    logger.info(
        "Pipeline starting — source: %s",
        "data_sample" if args.sample else "data/raw",
    )

    # Step 1: Load CSV files into DuckDB raw tables
    with step_timer("Step 01 — Ingest"):
        ingest(use_sample=args.sample)

    # Step 2: Create analytical views from raw tables
    with step_timer("Step 02 — Transform"):
        transform()

    # Step 3: Export views to CSV (+ optional Sheets push)
    with step_timer("Step 03 — Export"):
        export()

    logger.info("Pipeline complete")


if __name__ == "__main__":
    main()
