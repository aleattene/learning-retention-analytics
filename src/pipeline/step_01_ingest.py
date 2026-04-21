"""Step 01 — Ingest OULAD CSV files into raw DuckDB tables.

Reads the 7 OULAD CSV files from data/raw/ (or data_sample/) and loads
them into DuckDB tables defined by sql/schema.sql.

This step is idempotent: running it again will DROP and re-CREATE all tables,
ensuring a clean state. This is acceptable because raw data is always
available on disk as CSVs — the DuckDB tables are a derived artifact.
"""

import logging
from pathlib import Path

import duckdb

from src.config import DATA_SAMPLE_DIR, OULAD_TABLES, RAW_DATA_DIR, SQL_DIR
from src.db.connection import execute_sql_file, get_default_connection

logger = logging.getLogger(__name__)


def ingest(
    conn: duckdb.DuckDBPyConnection | None = None,
    use_sample: bool = False,
) -> None:
    """Load OULAD CSVs into DuckDB raw tables.

    Parameters
    ----------
    conn : DuckDBPyConnection or None
        Database connection. If None, opens the default project DB.
        Tests pass an in-memory connection to avoid touching the real DB.
    use_sample : bool
        If True, load from data_sample/ instead of data/raw/.
        Used for testing and CI where the full dataset is not available.
    """
    # Determine the source directory for CSV files
    source_dir: Path = DATA_SAMPLE_DIR if use_sample else RAW_DATA_DIR

    # Track ownership so we only close connections we opened
    own_conn: bool = conn is None
    if own_conn:
        conn = get_default_connection()

    try:
        # Step 1: Create the schema (DROP + CREATE for idempotency)
        schema_path: Path = SQL_DIR / "schema.sql"
        execute_sql_file(schema_path, conn=conn)
        logger.info("Schema created from %s", schema_path.name)

        # Step 2: Load each CSV into its corresponding table
        # The table names in OULAD_TABLES match the DDL in schema.sql
        for table_name, csv_filename in OULAD_TABLES.items():
            csv_path: Path = source_dir / csv_filename
            if not csv_path.exists():
                logger.warning("CSV not found, skipping: %s", csv_path)
                continue

            # DuckDB's read_csv_auto handles type inference and quoting
            # We INSERT INTO the pre-created table (from schema.sql) rather than
            # CREATE TABLE AS to ensure schema consistency across runs
            conn.execute(
                f"INSERT INTO {table_name} SELECT * FROM read_csv_auto('{csv_path}')"
            )

            # Log row count for verification
            row_count: int = conn.execute(
                f"SELECT COUNT(*) FROM {table_name}"
            ).fetchone()[0]
            logger.info("Loaded %s: %d rows from %s", table_name, row_count, csv_path)

        logger.info("Ingest complete from %s", source_dir)

    finally:
        if own_conn:
            conn.close()
