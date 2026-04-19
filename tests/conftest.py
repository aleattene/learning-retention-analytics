"""Shared test fixtures — DuckDB in-memory database with sample data.

All tests use an in-memory DuckDB connection loaded with data_sample/ CSVs.
This avoids touching the real database and makes tests fast and isolated.

The db_conn fixture is session-scoped: the database is created once per
test session and shared across all tests (read-only access pattern).
"""

import pytest
import duckdb

from src.config import DATA_SAMPLE_DIR, SQL_DIR, VIEWS_DIR
from src.db.connection import get_connection, execute_sql_file
from src.pipeline.step_01_ingest import ingest
from src.pipeline.step_02_transform import transform


@pytest.fixture(scope="session")
def db_conn() -> duckdb.DuckDBPyConnection:
    """Create an in-memory DuckDB with sample data and all views.

    Session-scoped so the database is built once and reused across all tests.
    This is safe because tests should only SELECT from the database,
    never INSERT/UPDATE/DELETE.
    """
    # In-memory connection: no file on disk, fully isolated
    conn: duckdb.DuckDBPyConnection = get_connection(db_path=None)

    # Step 1: Load sample CSVs into raw tables
    ingest(conn=conn, use_sample=True)

    # Step 2: Create all analytical views on top of the raw tables
    transform(conn=conn)

    yield conn

    # Cleanup: close the connection after all tests complete
    conn.close()
