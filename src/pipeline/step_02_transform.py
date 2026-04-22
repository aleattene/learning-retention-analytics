"""Step 02 — Transform raw tables into analytical views.

Executes all SQL view definitions from sql/views/ against the DuckDB database.
Views are the analytical backbone of the project: they encapsulate the business
logic (outcome binarization, engagement aggregation, dropout timing) in pure SQL,
keeping Python code focused on orchestration and statistics.

Views are idempotent by design (CREATE OR REPLACE VIEW), so re-running
this step always produces a consistent state without needing to drop anything.
"""

import logging
from pathlib import Path

import duckdb

from src.config import VIEWS_DIR
from src.db.connection import execute_sql_file, get_default_connection

logger = logging.getLogger(__name__)

# Views must be created in this specific order because later views
# depend on earlier ones (e.g. v_engagement_early needs raw studentVle,
# while queries will reference v_student_enriched)
VIEW_ORDER: list[str] = [
    "v_student_enriched.sql",
    "v_engagement_daily.sql",
    "v_engagement_early.sql",
    "v_dropout_timing.sql",
    "v_course_profile.sql",
]


def transform(
    conn: duckdb.DuckDBPyConnection | None = None,
) -> None:
    """Create all analytical views in the database.

    Parameters
    ----------
    conn : DuckDBPyConnection or None
        Database connection. If None, opens the default project DB.
        Tests pass an in-memory connection with sample data already loaded.
    """
    own_conn: bool = conn is None
    if own_conn:
        conn = get_default_connection()

    try:
        created: int = 0
        for view_file in VIEW_ORDER:
            view_path: Path = VIEWS_DIR / view_file
            if not view_path.exists():
                logger.warning("View file not found, skipping: %s", view_path)
                continue

            execute_sql_file(view_path, conn=conn)
            created += 1

            # Validate view by querying its row count immediately after creation.
            # This catches silent failures (e.g. empty results due to broken joins)
            # and gives operators a quick sanity check in the logs.
            view_name: str = view_file.removesuffix(".sql")
            row_count: int = conn.execute(
                f"SELECT COUNT(*) FROM {view_name}"
            ).fetchone()[0]
            logger.info("Created %s: %d rows", view_name, row_count)

        logger.info(
            "Transform complete: %d/%d views created from %s",
            created,
            len(VIEW_ORDER),
            VIEWS_DIR,
        )

    finally:
        if own_conn:
            conn.close()
