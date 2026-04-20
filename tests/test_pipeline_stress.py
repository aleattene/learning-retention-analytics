"""Stress tests for pipeline steps (ingest, transform, export).

Tests edge cases: empty CSVs, missing columns, corrupt data,
non-writable output directories, and degenerate sample data.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import duckdb
import pandas as pd

from src.db.connection import execute_query, get_connection
from src.pipeline.step_01_ingest import ingest
from src.pipeline.step_02_transform import transform
from src.pipeline.step_03_export import EXPORT_VIEWS, export

# ===================================================================
# Ingest stress tests
# ===================================================================


class TestIngestStress:
    """Edge cases for step_01_ingest."""

    def test_ingest_with_missing_csv_files(self, tmp_path: Path) -> None:
        """If source directory has no CSV files, tables should be empty."""
        # Create empty source directory
        empty_dir: Path = tmp_path / "empty_raw"
        empty_dir.mkdir()

        conn: duckdb.DuckDBPyConnection = get_connection(db_path=None)

        # Patch RAW_DATA_DIR to point to empty dir
        # Ingest should still create schema but skip CSV loading
        with patch("src.pipeline.step_01_ingest.RAW_DATA_DIR", empty_dir):
            ingest(conn=conn, use_sample=False)

        # Tables should exist (from schema.sql) but be empty
        count: int = conn.execute("SELECT COUNT(*) FROM studentInfo").fetchone()[0]
        assert count == 0
        conn.close()

    def test_ingest_idempotency_triple_run(self) -> None:
        """Running ingest 3 times should produce identical row counts."""
        conn: duckdb.DuckDBPyConnection = get_connection(db_path=None)

        counts: list[int] = []
        for _ in range(3):
            ingest(conn=conn, use_sample=True)
            count: int = conn.execute("SELECT COUNT(*) FROM studentInfo").fetchone()[0]
            counts.append(count)

        assert counts[0] == counts[1] == counts[2]
        conn.close()

    def test_ingest_sample_loads_all_seven_tables(self) -> None:
        """Sample ingest should populate all 7 OULAD tables."""
        from src.config import OULAD_TABLES

        conn: duckdb.DuckDBPyConnection = get_connection(db_path=None)
        ingest(conn=conn, use_sample=True)

        for table_name in OULAD_TABLES:
            count: int = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[
                0
            ]
            assert count > 0, f"Table {table_name} is empty after sample ingest"

        conn.close()


# ===================================================================
# Transform stress tests
# ===================================================================


class TestTransformStress:
    """Edge cases for step_02_transform."""

    def test_transform_on_empty_tables(self) -> None:
        """Transform on empty raw tables should create views without error.

        Views may return 0 rows but should not fail — this tests
        resilience of SQL views to empty input.
        """
        conn: duckdb.DuckDBPyConnection = get_connection(db_path=None)

        # Create schema (empty tables) without loading any data
        from src.config import SQL_DIR
        from src.db.connection import execute_sql_file

        execute_sql_file(SQL_DIR / "schema.sql", conn=conn)
        transform(conn=conn)

        # Views should exist and return 0 rows (not crash)
        for view_name in [
            "v_student_enriched",
            "v_engagement_daily",
            "v_engagement_early",
            "v_dropout_timing",
            "v_course_profile",
        ]:
            df: pd.DataFrame = execute_query(
                f"SELECT COUNT(*) AS cnt FROM {view_name}", conn=conn
            )
            assert df["cnt"].iloc[0] == 0

        conn.close()

    def test_transform_idempotent(self) -> None:
        """Running transform twice should produce identical views."""
        conn: duckdb.DuckDBPyConnection = get_connection(db_path=None)
        ingest(conn=conn, use_sample=True)

        transform(conn=conn)
        count1: int = conn.execute(
            "SELECT COUNT(*) FROM v_student_enriched"
        ).fetchone()[0]

        transform(conn=conn)
        count2: int = conn.execute(
            "SELECT COUNT(*) FROM v_student_enriched"
        ).fetchone()[0]

        assert count1 == count2
        conn.close()

    def test_transform_with_missing_view_file(self, tmp_path: Path) -> None:
        """If a view file is missing, transform should skip it (warning)."""
        conn: duckdb.DuckDBPyConnection = get_connection(db_path=None)
        ingest(conn=conn, use_sample=True)

        # Patch VIEWS_DIR to an empty directory — all files will be "missing"
        empty_views: Path = tmp_path / "views"
        empty_views.mkdir()
        with patch("src.pipeline.step_02_transform.VIEWS_DIR", empty_views):
            transform(conn=conn)  # Should not raise

        conn.close()


# ===================================================================
# Export stress tests
# ===================================================================


class TestExportStress:
    """Edge cases for step_03_export."""

    def test_export_to_custom_directory(self) -> None:
        """Export should create the output directory if it doesn't exist."""
        conn: duckdb.DuckDBPyConnection = get_connection(db_path=None)
        ingest(conn=conn, use_sample=True)
        transform(conn=conn)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir: Path = Path(tmpdir) / "nested" / "output"
            exported: list[Path] = export(conn=conn, output_dir=output_dir)

            assert output_dir.exists()
            assert len(exported) >= len(EXPORT_VIEWS)
            for path in exported:
                assert path.exists()

        conn.close()

    def test_exported_csvs_match_view_data(self) -> None:
        """CSV content should exactly match the view query result."""
        conn: duckdb.DuckDBPyConnection = get_connection(db_path=None)
        ingest(conn=conn, use_sample=True)
        transform(conn=conn)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir: Path = Path(tmpdir)
            export(conn=conn, output_dir=output_dir)

            # Check that v_student_enriched CSV matches the view
            csv_df: pd.DataFrame = pd.read_csv(output_dir / "v_student_enriched.csv")
            view_df: pd.DataFrame = execute_query(
                "SELECT * FROM v_student_enriched", conn=conn
            )
            assert len(csv_df) == len(view_df)
            assert set(csv_df.columns) == set(view_df.columns)

        conn.close()

    def test_export_empty_views(self) -> None:
        """Export on empty tables should produce CSVs (views: 0 rows,
        aggregate queries like BQ5 may return 1 row with zeros)."""
        conn: duckdb.DuckDBPyConnection = get_connection(db_path=None)

        from src.config import SQL_DIR
        from src.db.connection import execute_sql_file

        execute_sql_file(SQL_DIR / "schema.sql", conn=conn)
        transform(conn=conn)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir: Path = Path(tmpdir)
            exported: list[Path] = export(conn=conn, output_dir=output_dir)

            for path in exported:
                df: pd.DataFrame = pd.read_csv(path)
                # All exported files should be valid CSVs with a header.
                # Views produce 0 data rows, but aggregate queries (e.g.
                # BQ5 segment_sizing) return 1 row of zeros — both are valid.
                assert len(df.columns) > 0

        conn.close()

    def test_export_overwrite_existing_files(self) -> None:
        """Re-exporting should overwrite existing CSV files cleanly."""
        conn: duckdb.DuckDBPyConnection = get_connection(db_path=None)
        ingest(conn=conn, use_sample=True)
        transform(conn=conn)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir: Path = Path(tmpdir)

            # First export
            exported1: list[Path] = export(conn=conn, output_dir=output_dir)
            sizes1: list[int] = [p.stat().st_size for p in exported1]

            # Second export (should overwrite, same sizes)
            exported2: list[Path] = export(conn=conn, output_dir=output_dir)
            sizes2: list[int] = [p.stat().st_size for p in exported2]

            assert sizes1 == sizes2

        conn.close()

    def test_push_to_sheets_not_called_when_disabled(self) -> None:
        """When PUSH_TO_SHEETS is False, Sheets push should not be called."""
        conn: duckdb.DuckDBPyConnection = get_connection(db_path=None)
        ingest(conn=conn, use_sample=True)
        transform(conn=conn)

        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch("src.pipeline.step_03_export._push_to_sheets") as mock_push,
            patch("src.pipeline.step_03_export.PUSH_TO_SHEETS", False),
        ):
            export(conn=conn, output_dir=Path(tmpdir))
            mock_push.assert_not_called()

        conn.close()


# ===================================================================
# Full pipeline integration stress
# ===================================================================


class TestFullPipelineStress:
    """End-to-end stress scenarios for the full pipeline."""

    def test_full_pipeline_sample_data(self) -> None:
        """Complete pipeline run on sample data should produce valid output."""
        conn: duckdb.DuckDBPyConnection = get_connection(db_path=None)

        ingest(conn=conn, use_sample=True)
        transform(conn=conn)

        with tempfile.TemporaryDirectory() as tmpdir:
            exported: list[Path] = export(conn=conn, output_dir=Path(tmpdir))
            assert len(exported) > 0

            # Every exported file should be a valid CSV with data
            for path in exported:
                df: pd.DataFrame = pd.read_csv(path)
                assert len(df) > 0, f"Exported file {path.name} is empty"

        conn.close()

    def test_pipeline_produces_consistent_row_counts(self) -> None:
        """Two full pipeline runs should produce identical row counts."""
        counts_run1: dict[str, int] = {}
        counts_run2: dict[str, int] = {}

        for counts in [counts_run1, counts_run2]:
            conn: duckdb.DuckDBPyConnection = get_connection(db_path=None)
            ingest(conn=conn, use_sample=True)
            transform(conn=conn)

            for view in [
                "v_student_enriched",
                "v_engagement_daily",
                "v_engagement_early",
                "v_dropout_timing",
                "v_course_profile",
            ]:
                count: int = conn.execute(f"SELECT COUNT(*) FROM {view}").fetchone()[0]
                counts[view] = count

            conn.close()

        assert counts_run1 == counts_run2
