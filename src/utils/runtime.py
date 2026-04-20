"""Runtime utilities — step timing and environment info.

Provides a context manager for timing pipeline steps and a function
to log the current runtime environment (Python version, key library versions).
Useful for reproducibility: when a pipeline run produces unexpected results,
the environment snapshot helps identify version-related issues.
"""

import logging
import platform
import time
from contextlib import contextmanager
from typing import Generator

logger = logging.getLogger(__name__)


@contextmanager
def step_timer(step_name: str) -> Generator[None, None, None]:
    """Context manager that logs the elapsed time for a pipeline step.

    Usage
    -----
    >>> with step_timer("Step 01 — Ingest"):
    ...     ingest()
    # logs: "Step 01 — Ingest completed in 3.42s"
    """
    start: float = time.perf_counter()
    logger.info("Starting: %s", step_name)
    try:
        yield
    finally:
        elapsed: float = time.perf_counter() - start
        logger.info("%s completed in %.2fs", step_name, elapsed)


def log_environment() -> None:
    """Log key environment details for reproducibility.

    Called once at pipeline startup to record which versions
    of Python and critical libraries were used for the run.
    """
    logger.info("Python %s on %s", platform.python_version(), platform.system())

    # Log versions of key analytical libraries
    # Each import is wrapped individually so a missing library
    # doesn't prevent logging the others
    for lib_name in ["duckdb", "pandas", "numpy", "scipy"]:
        try:
            lib = __import__(lib_name)
            # Not all modules expose __version__ — guard to avoid
            # AttributeError breaking the entire startup log
            version: str = getattr(lib, "__version__", "unknown")
            logger.info("%s %s", lib_name, version)
        except ImportError:
            logger.warning("%s not installed", lib_name)
