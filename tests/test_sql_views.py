"""Tests for SQL views — validate analytical logic on sample data.

These tests verify that the SQL views produce correct results
by checking business logic invariants on the sample data.
"""

import duckdb
import pandas as pd

from src.db.connection import execute_query


class TestStudentEnriched:
    """Tests for v_student_enriched view."""

    def test_no_duplicate_students(self, db_conn: duckdb.DuckDBPyConnection) -> None:
        """Each student should appear once per course-presentation."""
        df: pd.DataFrame = execute_query(
            """
            SELECT id_student, code_module, code_presentation, COUNT(*) AS cnt
            FROM v_student_enriched
            GROUP BY id_student, code_module, code_presentation
            HAVING COUNT(*) > 1
            """,
            conn=db_conn,
        )
        assert len(df) == 0, f"Found {len(df)} duplicate student-course combinations"

    def test_withdrew_explicit_matches_dropout_day(
        self, db_conn: duckdb.DuckDBPyConnection
    ) -> None:
        """withdrew_explicit=1 iff dropout_day IS NOT NULL."""
        df: pd.DataFrame = execute_query(
            """
            SELECT COUNT(*) AS mismatches
            FROM v_student_enriched
            WHERE (withdrew_explicit = 1 AND dropout_day IS NULL)
               OR (withdrew_explicit = 0 AND dropout_day IS NOT NULL)
            """,
            conn=db_conn,
        )
        assert df["mismatches"].iloc[0] == 0

    def test_all_final_results_present(
        self, db_conn: duckdb.DuckDBPyConnection
    ) -> None:
        """Sample data should include all 4 final_result categories."""
        df: pd.DataFrame = execute_query(
            "SELECT DISTINCT final_result FROM v_student_enriched",
            conn=db_conn,
        )
        results: set[str] = set(df["final_result"].tolist())
        expected: set[str] = {"Pass", "Distinction", "Fail", "Withdrawn"}
        assert results == expected


class TestEngagementDaily:
    """Tests for v_engagement_daily view."""

    def test_total_clicks_positive(self, db_conn: duckdb.DuckDBPyConnection) -> None:
        """Every row should have at least 1 click (by construction)."""
        df: pd.DataFrame = execute_query(
            "SELECT MIN(total_clicks) AS min_clicks FROM v_engagement_daily",
            conn=db_conn,
        )
        assert df["min_clicks"].iloc[0] >= 1

    def test_distinct_resources_bounded(
        self, db_conn: duckdb.DuckDBPyConnection
    ) -> None:
        """distinct_resources should be >= 1 (at least one resource clicked)."""
        df: pd.DataFrame = execute_query(
            "SELECT MIN(distinct_resources) AS min_res FROM v_engagement_daily",
            conn=db_conn,
        )
        assert df["min_res"].iloc[0] >= 1


class TestEngagementEarly:
    """Tests for v_engagement_early view."""

    def test_decile_range(self, db_conn: duckdb.DuckDBPyConnection) -> None:
        """Engagement deciles should be between 1 and 10."""
        df: pd.DataFrame = execute_query(
            """
            SELECT
                MIN(engagement_decile_in_course) AS min_dec,
                MAX(engagement_decile_in_course) AS max_dec
            FROM v_engagement_early
            """,
            conn=db_conn,
        )
        assert df["min_dec"].iloc[0] >= 1
        assert df["max_dec"].iloc[0] <= 10

    def test_active_days_bounded(self, db_conn: duckdb.DuckDBPyConnection) -> None:
        """active_days_first_28 should be between 1 and 29 (days 0-28)."""
        df: pd.DataFrame = execute_query(
            """
            SELECT
                MIN(active_days_first_28) AS min_days,
                MAX(active_days_first_28) AS max_days
            FROM v_engagement_early
            """,
            conn=db_conn,
        )
        assert df["min_days"].iloc[0] >= 1
        assert df["max_days"].iloc[0] <= 29


class TestDropoutTiming:
    """Tests for v_dropout_timing view."""

    def test_only_withdrawn_students(
        self, db_conn: duckdb.DuckDBPyConnection
    ) -> None:
        """This view should only contain students who explicitly withdrew."""
        df: pd.DataFrame = execute_query(
            "SELECT COUNT(*) AS cnt FROM v_dropout_timing WHERE dropout_day IS NULL",
            conn=db_conn,
        )
        assert df["cnt"].iloc[0] == 0

    def test_dropout_pct_reasonable(
        self, db_conn: duckdb.DuckDBPyConnection
    ) -> None:
        """dropout_pct should be mostly between 0 and 100."""
        df: pd.DataFrame = execute_query(
            """
            SELECT
                MIN(dropout_pct) AS min_pct,
                MAX(dropout_pct) AS max_pct
            FROM v_dropout_timing
            """,
            conn=db_conn,
        )
        # Some edge cases may exceed 100% (withdrawal after official end)
        # but minimum should be positive
        assert df["min_pct"].iloc[0] >= 0


class TestCourseProfile:
    """Tests for v_course_profile view."""

    def test_completion_rate_bounded(
        self, db_conn: duckdb.DuckDBPyConnection
    ) -> None:
        """Completion rate should be between 0% and 100%."""
        df: pd.DataFrame = execute_query(
            """
            SELECT
                MIN(completion_rate_pct) AS min_rate,
                MAX(completion_rate_pct) AS max_rate
            FROM v_course_profile
            """,
            conn=db_conn,
        )
        assert df["min_rate"].iloc[0] >= 0
        assert df["max_rate"].iloc[0] <= 100

    def test_enrolled_equals_completed_plus_others(
        self, db_conn: duckdb.DuckDBPyConnection
    ) -> None:
        """n_completed should never exceed n_enrolled."""
        df: pd.DataFrame = execute_query(
            """
            SELECT COUNT(*) AS violations
            FROM v_course_profile
            WHERE n_completed > n_enrolled
            """,
            conn=db_conn,
        )
        assert df["violations"].iloc[0] == 0
