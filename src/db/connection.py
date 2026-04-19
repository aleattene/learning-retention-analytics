"""Database abstraction layer — DuckDB now, BigQuery later.

All database access in the project MUST go through this module.
No direct duckdb.connect() calls elsewhere in the codebase.

This abstraction exists to make the cloud migration (BigQuery) a matter
of swapping this single module, without touching any pipeline or analysis code.
"""

import logging
from pathlib import Path

import duckdb
import pandas as pd

from src.config import DB_PATH

logger = logging.getLogger(__name__)


def get_connection(
    db_path: Path | None = None, read_only: bool = False
) -> duckdb.DuckDBPyConnection:
    """Return a DuckDB connection.

    Parameters
    ----------
    db_path : Path or None
        Path to the DuckDB file. None = in-memory database.
        In-memory is used by tests to avoid polluting the real DB.
    read_only : bool
        If True, open the database in read-only mode.
        Use read_only=True for queries that only read data (exports, analysis)
        to prevent accidental writes and allow concurrent access.

    Returns
    -------
    duckdb.DuckDBPyConnection
    """
    if db_path is None:
        logger.debug("Opening in-memory DuckDB connection")
        return duckdb.connect(":memory:")

    # Ensure the parent directory exists (e.g. data/db/ on first run)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    logger.debug("Opening DuckDB connection at %s", db_path)
    return duckdb.connect(str(db_path), read_only=read_only)


def get_default_connection(
    read_only: bool = False,
) -> duckdb.DuckDBPyConnection:
    """Return a connection to the project's default DuckDB database.

    This is the standard entry point for all pipeline steps.
    The DB path is defined in src/config.py (data/db/oulad.duckdb).
    """
    return get_connection(db_path=DB_PATH, read_only=read_only)


def execute_query(
    sql: str,
    conn: duckdb.DuckDBPyConnection | None = None,
    params: dict | None = None,
) -> pd.DataFrame:
    """Execute a SQL query and return results as a DataFrame.

    This is the single point of entry for all SELECT queries in the project.
    Returning a DataFrame keeps the interface consistent regardless of
    whether the backend is DuckDB or BigQuery.

    Parameters
    ----------
    sql : str
        SQL query string. Must be ANSI-compliant (no DuckDB-specific syntax).
    conn : DuckDBPyConnection or None
        Database connection. If None, opens a default read-only connection.
        Pass an explicit connection when running inside a pipeline step
        that already holds an open connection.
    params : dict or None
        Named parameters for the query (DuckDB $name syntax).

    Returns
    -------
    pd.DataFrame
    """
    # Track whether we own the connection (and must close it when done)
    own_conn: bool = conn is None
    if own_conn:
        # Default to read-only: SELECT queries should never modify data
        conn = get_default_connection(read_only=True)

    try:
        if params:
            result = conn.execute(sql, params)
        else:
            result = conn.execute(sql)
        return result.fetchdf()
    finally:
        # Only close connections we opened ourselves;
        # caller-provided connections are the caller's responsibility
        if own_conn:
            conn.close()


def execute_sql_file(
    sql_path: Path,
    conn: duckdb.DuckDBPyConnection | None = None,
) -> None:
    """Execute a SQL file (DDL, view creation, etc.).

    Used by pipeline steps to run schema.sql and view definitions.
    The SQL file is read entirely and executed as a single statement block.

    Parameters
    ----------
    sql_path : Path
        Path to the .sql file.
    conn : DuckDBPyConnection or None
        Database connection. If None, opens a default read-write connection.
    """
    if not sql_path.exists():
        raise FileNotFoundError(f"SQL file not found: {sql_path}")

    sql: str = sql_path.read_text(encoding="utf-8")

    # Track ownership to avoid closing a caller-provided connection
    own_conn: bool = conn is None
    if own_conn:
        conn = get_default_connection()

    try:
        conn.execute(sql)
        logger.info("Executed SQL file: %s", sql_path.name)
    finally:
        if own_conn:
            conn.close()
