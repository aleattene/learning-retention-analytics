"""Logging configuration for the project.

Provides a single setup_logging() function to be called once at startup
(in run_pipeline.py). All modules use logging.getLogger(__name__) and
inherit this configuration automatically.
"""

import logging
import sys


def setup_logging(level: int = logging.INFO) -> None:
    """Configure root logger with a consistent format.

    Format includes timestamp, module name, and level to make log output
    useful for debugging pipeline runs and tracking step durations.

    Parameters
    ----------
    level : int
        Logging level. INFO for normal runs, DEBUG for troubleshooting.
    """
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(name)-30s | %(levelname)-7s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
        # force=True ensures this config takes effect even if logging
        # was already configured by an imported library
        force=True,
    )
