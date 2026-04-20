"""Smoke tests — quick sanity checks that imports and connections work.

These tests run first and fast. If they fail, something fundamental
is broken (missing dependency, bad config, import error).
"""

import duckdb
import pytest


class TestImports:
    """Verify that all project modules can be imported without error."""

    def test_import_config(self) -> None:
        from src import config  # noqa: F401

    def test_import_connection(self) -> None:
        from src.db import connection  # noqa: F401

    def test_import_pipeline_steps(self) -> None:
        from src.pipeline import (
            step_01_ingest,  # noqa: F401
            step_02_transform,  # noqa: F401
            step_03_export,  # noqa: F401
        )

    def test_import_stats(self) -> None:
        from src.stats import tests  # noqa: F401

    def test_import_utils(self) -> None:
        from src.utils import (
            logging,  # noqa: F401
            runtime,  # noqa: F401
        )


class TestConnection:
    """Verify that DuckDB connections work."""

    def test_in_memory_connection(self) -> None:
        """An in-memory connection should open and execute a simple query."""
        from src.db.connection import get_connection

        conn: duckdb.DuckDBPyConnection = get_connection(db_path=None)
        result = conn.execute("SELECT 1 AS test").fetchone()
        assert result is not None
        assert result[0] == 1
        conn.close()

    def test_execute_query_returns_dataframe(self) -> None:
        """execute_query should return a pandas DataFrame."""
        import pandas as pd

        from src.db.connection import execute_query, get_connection

        conn = get_connection(db_path=None)
        df: pd.DataFrame = execute_query("SELECT 42 AS answer", conn=conn)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert df["answer"].iloc[0] == 42
        conn.close()


class TestConfig:
    """Verify that config values are reasonable."""

    def test_paths_exist_or_are_relative(self) -> None:
        """PROJECT_ROOT should exist; data dirs may not (created at runtime)."""
        from src.config import PROJECT_ROOT

        assert PROJECT_ROOT.exists()
        assert (PROJECT_ROOT / "src").exists()
        assert (PROJECT_ROOT / "sql").exists()

    def test_oulad_tables_defined(self) -> None:
        """OULAD_TABLES should have all 7 expected tables."""
        from src.config import OULAD_TABLES

        assert len(OULAD_TABLES) == 7
        assert "studentInfo" in OULAD_TABLES
        assert "studentVle" in OULAD_TABLES
        assert "courses" in OULAD_TABLES

    def test_push_to_sheets_default_false(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """PUSH_TO_SHEETS should default to False when env var is not set."""
        import importlib

        import src.config

        # Ensure the env var is absent, then reload config to pick up the default
        monkeypatch.delenv("PUSH_TO_SHEETS", raising=False)
        importlib.reload(src.config)

        assert src.config.PUSH_TO_SHEETS is False
