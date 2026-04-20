"""Tests for pipeline steps — ingest, transform, export.

All tests use the session-scoped db_conn fixture from conftest.py,
which provides an in-memory DuckDB pre-loaded with sample data.
"""

import tempfile
from pathlib import Path

import duckdb
import pandas as pd

from src.db.connection import execute_query, get_connection
from src.pipeline.step_01_ingest import ingest
from src.pipeline.step_03_export import EXPORT_VIEWS, export


class TestIngest:
    """Test step 01 — CSV to DuckDB raw tables."""

    def test_ingest_creates_all_tables(
        self, db_conn: duckdb.DuckDBPyConnection
    ) -> None:
        """All 7 OULAD tables should exist after ingest."""
        from src.config import OULAD_TABLES

        for table_name in OULAD_TABLES:
            # This query would fail if the table doesn't exist
            df: pd.DataFrame = execute_query(
                f"SELECT COUNT(*) AS cnt FROM {table_name}", conn=db_conn
            )
            assert df["cnt"].iloc[0] > 0, f"Table {table_name} is empty"

    def test_student_info_has_expected_columns(
        self, db_conn: duckdb.DuckDBPyConnection
    ) -> None:
        """studentInfo should have the standard OULAD columns."""
        df: pd.DataFrame = execute_query(
            "SELECT * FROM studentInfo LIMIT 1", conn=db_conn
        )
        expected_cols: set[str] = {
            "id_student",
            "code_module",
            "code_presentation",
            "gender",
            "region",
            "highest_education",
            "imd_band",
            "age_band",
            "num_of_prev_attempts",
            "studied_credits",
            "disability",
            "final_result",
        }
        assert expected_cols.issubset(set(df.columns))

    def test_ingest_is_idempotent(self) -> None:
        """Running ingest twice should produce the same result (no duplicates)."""
        conn: duckdb.DuckDBPyConnection = get_connection(db_path=None)

        # Run ingest twice on the same connection
        ingest(conn=conn, use_sample=True)
        count_first: int = conn.execute("SELECT COUNT(*) FROM studentInfo").fetchone()[
            0
        ]

        ingest(conn=conn, use_sample=True)
        count_second: int = conn.execute("SELECT COUNT(*) FROM studentInfo").fetchone()[
            0
        ]

        # Counts should be identical (DROP + CREATE ensures no duplicates)
        assert count_first == count_second
        conn.close()


class TestTransform:
    """Test step 02 — raw tables to analytical views."""

    def test_views_exist(self, db_conn: duckdb.DuckDBPyConnection) -> None:
        """All 5 analytical views should be queryable."""
        view_names: list[str] = [
            "v_student_enriched",
            "v_engagement_daily",
            "v_engagement_early",
            "v_dropout_timing",
            "v_course_profile",
        ]
        for view_name in view_names:
            df: pd.DataFrame = execute_query(
                f"SELECT COUNT(*) AS cnt FROM {view_name}", conn=db_conn
            )
            assert df["cnt"].iloc[0] >= 0, f"View {view_name} failed to query"

    def test_student_enriched_has_completed_column(
        self, db_conn: duckdb.DuckDBPyConnection
    ) -> None:
        """v_student_enriched should have the binarized 'completed' column."""
        df: pd.DataFrame = execute_query(
            "SELECT DISTINCT completed FROM v_student_enriched", conn=db_conn
        )
        # completed should only contain 0 and 1
        values: set[int] = set(df["completed"].tolist())
        assert values.issubset({0, 1})

    def test_student_enriched_completed_logic(
        self, db_conn: duckdb.DuckDBPyConnection
    ) -> None:
        """Pass and Distinction should map to completed=1, others to 0."""
        df: pd.DataFrame = execute_query(
            "SELECT final_result, completed FROM v_student_enriched", conn=db_conn
        )
        for _, row in df.iterrows():
            if row["final_result"] in ("Pass", "Distinction"):
                assert row["completed"] == 1
            else:
                assert row["completed"] == 0

    def test_engagement_early_within_28_days(
        self, db_conn: duckdb.DuckDBPyConnection
    ) -> None:
        """v_engagement_early should only contain data from days 0-28."""
        df: pd.DataFrame = execute_query(
            "SELECT MAX(last_active_day_in_window) AS max_day FROM v_engagement_early",
            conn=db_conn,
        )
        # The last active day should be at most 28
        assert df["max_day"].iloc[0] <= 28

    def test_course_profile_has_all_courses(
        self, db_conn: duckdb.DuckDBPyConnection
    ) -> None:
        """v_course_profile should have one row per course-presentation."""
        n_courses: int = execute_query(
            "SELECT COUNT(*) AS cnt FROM courses", conn=db_conn
        )["cnt"].iloc[0]

        n_profiles: int = execute_query(
            "SELECT COUNT(*) AS cnt FROM v_course_profile", conn=db_conn
        )["cnt"].iloc[0]

        assert n_profiles == n_courses


class TestExport:
    """Test step 03 — views to CSV files."""

    def test_export_creates_csv_files(self, db_conn: duckdb.DuckDBPyConnection) -> None:
        """Export should create CSV files in the output directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir: Path = Path(tmpdir)
            exported: list[Path] = export(conn=db_conn, output_dir=output_dir)

            # At minimum, the 5 view CSVs should be created
            # (query CSVs depend on query files existing)
            assert len(exported) >= len(EXPORT_VIEWS)

            # Each exported file should be a non-empty CSV
            for path in exported:
                assert path.exists()
                assert path.stat().st_size > 0
                # Verify it's valid CSV by reading it
                df: pd.DataFrame = pd.read_csv(path)
                assert len(df) > 0
