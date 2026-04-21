"""Stress tests for src/db/connection.py.

Tests edge cases: SQL injection patterns, malformed queries, read-only
enforcement, file-based connections, parameter handling, and concurrent access.
"""

from pathlib import Path

import duckdb
import pandas as pd
import pytest

from src.db.connection import execute_query, execute_sql_file, get_connection


class TestGetConnectionEdgeCases:
    """Edge cases for get_connection."""

    def test_in_memory_is_independent(self) -> None:
        """Two in-memory connections should be fully independent."""
        conn1: duckdb.DuckDBPyConnection = get_connection(db_path=None)
        conn2: duckdb.DuckDBPyConnection = get_connection(db_path=None)

        conn1.execute("CREATE TABLE t1 (id INTEGER)")
        # t1 should NOT exist in conn2
        tables: list = conn2.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_name = 't1'"
        ).fetchall()
        assert len(tables) == 0

        conn1.close()
        conn2.close()

    def test_file_connection_creates_parent_dirs(self, tmp_path: Path) -> None:
        """Should create intermediate directories if they don't exist."""
        db_path: Path = tmp_path / "nested" / "deep" / "test.duckdb"
        conn: duckdb.DuckDBPyConnection = get_connection(db_path=db_path)
        conn.execute("SELECT 1")
        conn.close()
        assert db_path.exists()

    def test_file_connection_persists_data(self, tmp_path: Path) -> None:
        """Data written to a file-based DB should survive reconnection."""
        db_path: Path = tmp_path / "persist.duckdb"

        conn: duckdb.DuckDBPyConnection = get_connection(db_path=db_path)
        conn.execute("CREATE TABLE persist_test (val INTEGER)")
        conn.execute("INSERT INTO persist_test VALUES (42)")
        conn.close()

        # Reconnect and verify
        conn2: duckdb.DuckDBPyConnection = get_connection(
            db_path=db_path, read_only=True
        )
        result: int = conn2.execute("SELECT val FROM persist_test").fetchone()[0]
        assert result == 42
        conn2.close()

    def test_read_only_prevents_writes(self, tmp_path: Path) -> None:
        """Read-only connection should reject INSERT/CREATE."""
        db_path: Path = tmp_path / "ro.duckdb"

        # Create DB first
        conn: duckdb.DuckDBPyConnection = get_connection(db_path=db_path)
        conn.execute("CREATE TABLE ro_test (id INTEGER)")
        conn.close()

        # Open read-only and try to write
        ro_conn: duckdb.DuckDBPyConnection = get_connection(
            db_path=db_path, read_only=True
        )
        with pytest.raises(duckdb.InvalidInputException):
            ro_conn.execute("INSERT INTO ro_test VALUES (1)")
        ro_conn.close()


class TestExecuteQueryEdgeCases:
    """Edge cases for execute_query."""

    def test_empty_result_returns_empty_dataframe(self) -> None:
        """Query with no results should return an empty DataFrame."""
        conn: duckdb.DuckDBPyConnection = get_connection(db_path=None)
        conn.execute("CREATE TABLE empty_tbl (id INTEGER)")
        df: pd.DataFrame = execute_query("SELECT * FROM empty_tbl", conn=conn)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0
        assert "id" in df.columns
        conn.close()

    def test_malformed_sql_raises(self) -> None:
        """Invalid SQL should raise an exception, not return silently."""
        conn: duckdb.DuckDBPyConnection = get_connection(db_path=None)
        with pytest.raises(Exception):
            execute_query("SELEC INVALID SYNTAX", conn=conn)
        conn.close()

    def test_nonexistent_table_raises(self) -> None:
        """Querying a table that doesn't exist should raise."""
        conn: duckdb.DuckDBPyConnection = get_connection(db_path=None)
        with pytest.raises(Exception):
            execute_query("SELECT * FROM table_that_does_not_exist", conn=conn)
        conn.close()

    def test_sql_injection_attempt_in_value(self) -> None:
        """SQL injection via string values should not break the query.

        Inserts a value containing typical injection characters (quotes,
        semicolons, comment markers) and retrieves it via parameterized
        query to verify that parameter binding treats it as a literal.
        """
        conn: duckdb.DuckDBPyConnection = get_connection(db_path=None)
        conn.execute("CREATE TABLE users (name VARCHAR)")

        # Payload with classic injection characters: quote, semicolon, comment
        injection_payload: str = "Robert'; DROP TABLE users;--"
        conn.execute("INSERT INTO users VALUES (?)", [injection_payload])

        # Retrieve via parameterized query — binding must treat it as literal
        df: pd.DataFrame = execute_query(
            "SELECT * FROM users WHERE name = $name",
            conn=conn,
            params={"name": injection_payload},
        )
        assert len(df) == 1
        assert df["name"].iloc[0] == injection_payload

        # Table must still exist (the injection did not execute)
        count: int = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        assert count == 1
        conn.close()

    def test_query_with_special_characters(self) -> None:
        """Column names and values with special characters."""
        conn: duckdb.DuckDBPyConnection = get_connection(db_path=None)
        conn.execute('CREATE TABLE special ("col with spaces" VARCHAR)')
        conn.execute("INSERT INTO special VALUES ('value''s quote')")
        df: pd.DataFrame = execute_query("SELECT * FROM special", conn=conn)
        assert len(df) == 1
        conn.close()

    def test_null_values_in_result(self) -> None:
        """NULL values should appear as NaN/None in the DataFrame."""
        conn: duckdb.DuckDBPyConnection = get_connection(db_path=None)
        df: pd.DataFrame = execute_query("SELECT NULL AS nullable_col", conn=conn)
        assert pd.isna(df["nullable_col"].iloc[0])
        conn.close()

    def test_large_result_set(self) -> None:
        """Should handle large result sets without error."""
        conn: duckdb.DuckDBPyConnection = get_connection(db_path=None)
        df: pd.DataFrame = execute_query(
            "SELECT i FROM generate_series(1, 10000) AS t(i)", conn=conn
        )
        assert len(df) == 10000
        conn.close()

    def test_multiple_queries_same_connection(self) -> None:
        """Multiple queries on the same connection should all work."""
        conn: duckdb.DuckDBPyConnection = get_connection(db_path=None)
        conn.execute("CREATE TABLE multi (id INTEGER)")
        conn.execute("INSERT INTO multi VALUES (1), (2), (3)")

        df1: pd.DataFrame = execute_query(
            "SELECT COUNT(*) AS cnt FROM multi", conn=conn
        )
        df2: pd.DataFrame = execute_query("SELECT MAX(id) AS mx FROM multi", conn=conn)

        assert df1["cnt"].iloc[0] == 3
        assert df2["mx"].iloc[0] == 3
        conn.close()


class TestExecuteSqlFileEdgeCases:
    """Edge cases for execute_sql_file."""

    def test_nonexistent_file_raises(self) -> None:
        """Missing SQL file should raise FileNotFoundError."""
        conn: duckdb.DuckDBPyConnection = get_connection(db_path=None)
        with pytest.raises(FileNotFoundError, match="SQL file not found"):
            execute_sql_file(Path("/nonexistent/file.sql"), conn=conn)
        conn.close()

    def test_empty_sql_file(self, tmp_path: Path) -> None:
        """Empty SQL file should execute without error (no-op)."""
        sql_file: Path = tmp_path / "empty.sql"
        sql_file.write_text("", encoding="utf-8")

        conn: duckdb.DuckDBPyConnection = get_connection(db_path=None)
        # DuckDB accepts empty input without error; verify that holds
        execute_sql_file(sql_file, conn=conn)
        conn.close()

    def test_sql_file_with_multiple_statements(self, tmp_path: Path) -> None:
        """SQL file with multiple statements should execute all of them."""
        sql_file: Path = tmp_path / "multi.sql"
        sql_file.write_text(
            "CREATE TABLE a (id INTEGER);\nCREATE TABLE b (id INTEGER);",
            encoding="utf-8",
        )

        conn: duckdb.DuckDBPyConnection = get_connection(db_path=None)
        execute_sql_file(sql_file, conn=conn)

        # Both tables should exist
        tables = conn.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_name IN ('a', 'b') ORDER BY table_name"
        ).fetchall()
        assert len(tables) == 2
        conn.close()

    def test_sql_file_with_syntax_error(self, tmp_path: Path) -> None:
        """SQL file with syntax errors should raise."""
        sql_file: Path = tmp_path / "bad.sql"
        sql_file.write_text("CRETE TABEL broken (id INTEGER);", encoding="utf-8")

        conn: duckdb.DuckDBPyConnection = get_connection(db_path=None)
        with pytest.raises(Exception):
            execute_sql_file(sql_file, conn=conn)
        conn.close()

    def test_sql_file_with_utf8_comments(self, tmp_path: Path) -> None:
        """SQL file with Unicode comments (accented chars) should work."""
        sql_file: Path = tmp_path / "unicode.sql"
        sql_file.write_text(
            "-- Créé pour les étudiants\nCREATE TABLE uni (id INTEGER);",
            encoding="utf-8",
        )
        conn: duckdb.DuckDBPyConnection = get_connection(db_path=None)
        execute_sql_file(sql_file, conn=conn)
        result = conn.execute("SELECT 1 FROM uni LIMIT 1").fetchall()
        assert result is not None  # Table exists
        conn.close()
