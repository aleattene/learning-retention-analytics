"""Tests for BQ SQL queries — validate business logic invariants on sample data.

These tests verify that the BQ1–BQ5 queries produce structurally correct
results.  The queries are loaded from sql/queries/ and executed against the
in-memory DuckDB fixture populated with data_sample/ CSVs.
"""

import duckdb
import pandas as pd

from src.config import QUERIES_DIR
from src.db.connection import execute_query

# ---------------------------------------------------------------------------
# Helper — load a query file and execute it against the test DB
# ---------------------------------------------------------------------------


def _run_query_file(filename: str, conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Read a .sql file from QUERIES_DIR and execute it."""
    sql: str = (QUERIES_DIR / filename).read_text(encoding="utf-8")
    return execute_query(sql, conn=conn)


# ===================================================================
# BQ1 — q_bq1_dropout_curves
# ===================================================================


class TestBQ1DropoutCurves:
    """Invariants for q_bq1_dropout_curves.sql."""

    def test_cumulative_dropouts_monotonic(
        self, db_conn: duckdb.DuckDBPyConnection
    ) -> None:
        """cumulative_dropouts must never decrease within a course-presentation."""
        df: pd.DataFrame = _run_query_file("q_bq1_dropout_curves.sql", db_conn)

        for (module, pres), group in df.groupby(["code_module", "code_presentation"]):
            values: list[int] = group.sort_values("dropout_day")[
                "cumulative_dropouts"
            ].tolist()
            # Each value must be >= the previous one
            for i in range(1, len(values)):
                assert values[i] >= values[i - 1], (
                    f"{module}-{pres}: cumulative_dropouts decreased "
                    f"from {values[i - 1]} to {values[i]}"
                )

    def test_cumulative_dropout_rate_bounded(
        self, db_conn: duckdb.DuckDBPyConnection
    ) -> None:
        """cumulative_dropout_rate_pct must be between 0 and 100."""
        df: pd.DataFrame = _run_query_file("q_bq1_dropout_curves.sql", db_conn)

        assert (
            df["cumulative_dropout_rate_pct"].min() >= 0
        ), "cumulative_dropout_rate_pct went below 0"
        assert (
            df["cumulative_dropout_rate_pct"].max() <= 100
        ), "cumulative_dropout_rate_pct exceeded 100"

    def test_dropout_day_not_null(self, db_conn: duckdb.DuckDBPyConnection) -> None:
        """Every row must have a non-null dropout_day (by construction)."""
        df: pd.DataFrame = _run_query_file("q_bq1_dropout_curves.sql", db_conn)

        n_nulls: int = df["dropout_day"].isna().sum()
        assert n_nulls == 0, f"Found {n_nulls} rows with NULL dropout_day"

    def test_n_enrolled_consistent_with_student_enriched(
        self, db_conn: duckdb.DuckDBPyConnection
    ) -> None:
        """n_enrolled in BQ1 should match total students in v_student_enriched."""
        # Ground truth from the view
        df_se: pd.DataFrame = execute_query(
            """
            SELECT code_module, code_presentation, COUNT(*) AS n_enrolled
            FROM v_student_enriched
            GROUP BY code_module, code_presentation
            """,
            conn=db_conn,
        )

        # n_enrolled from the BQ1 query (must be constant within each
        # course-presentation — verify before comparing)
        df_bq1: pd.DataFrame = _run_query_file("q_bq1_dropout_curves.sql", db_conn)
        n_unique_per_group: pd.Series = df_bq1.groupby(
            ["code_module", "code_presentation"]
        )["n_enrolled"].nunique()
        assert (
            n_unique_per_group == 1
        ).all(), "n_enrolled varies within some course-presentations in BQ1"
        df_bq1_enrolled: pd.DataFrame = (
            df_bq1.groupby(["code_module", "code_presentation"])["n_enrolled"]
            .first()
            .reset_index()
        )

        # Merge and compare — only for courses that appear in the dropout query
        # (courses with zero dropouts won't have rows in BQ1)
        merged: pd.DataFrame = df_bq1_enrolled.merge(
            df_se,
            on=["code_module", "code_presentation"],
            suffixes=("_bq1", "_se"),
        )
        mismatches: pd.DataFrame = merged[
            merged["n_enrolled_bq1"] != merged["n_enrolled_se"]
        ]
        assert (
            len(mismatches) == 0
        ), f"n_enrolled mismatch in {len(mismatches)} course-presentations"


# ===================================================================
# BQ2 — q_bq2_early_signals
# ===================================================================


class TestBQ2EarlySignals:
    """Invariants for q_bq2_early_signals.sql."""

    def test_composite_key_unique(self, db_conn: duckdb.DuckDBPyConnection) -> None:
        """(id_student, code_module, code_presentation) must be unique."""
        df: pd.DataFrame = _run_query_file("q_bq2_early_signals.sql", db_conn)

        dupes: pd.DataFrame = df[
            df.duplicated(
                subset=["id_student", "code_module", "code_presentation"],
                keep=False,
            )
        ]
        assert len(dupes) == 0, f"Found {len(dupes)} rows with duplicate composite keys"

    def test_completed_binary(self, db_conn: duckdb.DuckDBPyConnection) -> None:
        """completed column must contain only 0 or 1."""
        df: pd.DataFrame = _run_query_file("q_bq2_early_signals.sql", db_conn)

        unique_values: set[int] = set(df["completed"].unique())
        assert unique_values.issubset(
            {0, 1}
        ), f"completed has unexpected values: {unique_values - {0, 1}}"

    def test_active_days_bounded(self, db_conn: duckdb.DuckDBPyConnection) -> None:
        """active_days_first_28 must be between 0 and 29.

        0 is valid because COALESCE fills ghost students (no VLE activity)
        with 0.  29 is the maximum because days 0 through 28 = 29 days.
        """
        df: pd.DataFrame = _run_query_file("q_bq2_early_signals.sql", db_conn)

        min_days: int = df["active_days_first_28"].min()
        max_days: int = df["active_days_first_28"].max()
        assert min_days >= 0, f"active_days_first_28 went below 0: {min_days}"
        assert max_days <= 29, f"active_days_first_28 exceeded 29: {max_days}"

    def test_engagement_decile_bounded(
        self, db_conn: duckdb.DuckDBPyConnection
    ) -> None:
        """engagement_decile_in_course must be between 1 and 10.

        The BQ2 query COALESCEs NULL deciles to 1 (ghost students
        get the lowest decile), so no NULLs should appear.
        """
        df: pd.DataFrame = _run_query_file("q_bq2_early_signals.sql", db_conn)

        deciles: pd.Series = df["engagement_decile_in_course"]
        assert deciles.notna().all(), "engagement_decile_in_course contains NULL values"
        min_dec: int = deciles.min()
        max_dec: int = deciles.max()
        assert min_dec >= 1, f"engagement_decile_in_course went below 1: {min_dec}"
        assert max_dec <= 10, f"engagement_decile_in_course exceeded 10: {max_dec}"


# ===================================================================
# BQ3 — q_bq3_demographics_vs_behavior
# ===================================================================


class TestBQ3DemographicsVsBehavior:
    """Invariants for q_bq3_demographics_vs_behavior.sql."""

    def test_composite_key_unique(self, db_conn: duckdb.DuckDBPyConnection) -> None:
        """(id_student, code_module, code_presentation) must be unique."""
        df: pd.DataFrame = _run_query_file(
            "q_bq3_demographics_vs_behavior.sql", db_conn
        )

        dupes: pd.DataFrame = df[
            df.duplicated(
                subset=["id_student", "code_module", "code_presentation"],
                keep=False,
            )
        ]
        assert len(dupes) == 0, f"Found {len(dupes)} rows with duplicate composite keys"

    def test_completed_binary(self, db_conn: duckdb.DuckDBPyConnection) -> None:
        """completed column must contain only 0 or 1."""
        df: pd.DataFrame = _run_query_file(
            "q_bq3_demographics_vs_behavior.sql", db_conn
        )

        unique_values: set[int] = set(df["completed"].unique())
        assert unique_values.issubset(
            {0, 1}
        ), f"completed has unexpected values: {unique_values - {0, 1}}"

    def test_behavioral_coalesce_non_negative(
        self, db_conn: duckdb.DuckDBPyConnection
    ) -> None:
        """Behavioral columns COALESCEd to 0 must be >= 0.

        Ghost students (no VLE activity) get 0 via COALESCE in the query,
        so negative values would indicate a logic error.
        """
        df: pd.DataFrame = _run_query_file(
            "q_bq3_demographics_vs_behavior.sql", db_conn
        )

        for col in [
            "active_days_first_28",
            "total_clicks_first_28",
            "avg_clicks_per_active_day",
        ]:
            min_val: float = df[col].min()
            assert min_val >= 0, f"{col} went below 0: {min_val}"

    def test_submitted_first_assessment_binary(
        self, db_conn: duckdb.DuckDBPyConnection
    ) -> None:
        """submitted_first_assessment must contain only 0 or 1."""
        df: pd.DataFrame = _run_query_file(
            "q_bq3_demographics_vs_behavior.sql", db_conn
        )

        unique_values: set[int] = set(df["submitted_first_assessment"].unique())
        assert unique_values.issubset(
            {0, 1}
        ), f"submitted_first_assessment has unexpected values: {unique_values - {0, 1}}"

    def test_engagement_decile_bounded(
        self, db_conn: duckdb.DuckDBPyConnection
    ) -> None:
        """When not NULL, engagement_decile_in_course must be between 1 and 10.

        Unlike BQ2 (which COALESCEs NULL to 1), BQ3 preserves NULL for
        ghost students — so we filter NULLs before checking the range.
        """
        df: pd.DataFrame = _run_query_file(
            "q_bq3_demographics_vs_behavior.sql", db_conn
        )

        non_null: pd.Series = df["engagement_decile_in_course"].dropna()
        if len(non_null) > 0:
            min_dec: float = non_null.min()
            max_dec: float = non_null.max()
            assert min_dec >= 1, f"engagement_decile_in_course went below 1: {min_dec}"
            assert max_dec <= 10, f"engagement_decile_in_course exceeded 10: {max_dec}"

    def test_decile_null_iff_zero_active_days(
        self, db_conn: duckdb.DuckDBPyConnection
    ) -> None:
        """engagement_decile_in_course IS NULL iff active_days_first_28 = 0.

        Students with zero VLE activity have no row in v_engagement_early,
        so the LEFT JOIN produces NULL for the decile. Conversely, any
        student with at least one active day must have a decile rank.
        """
        df: pd.DataFrame = _run_query_file(
            "q_bq3_demographics_vs_behavior.sql", db_conn
        )

        # NULL decile but positive active_days — should never happen
        null_decile_positive_days: pd.DataFrame = df[
            df["engagement_decile_in_course"].isna() & (df["active_days_first_28"] > 0)
        ]
        assert len(null_decile_positive_days) == 0, (
            f"Found {len(null_decile_positive_days)} rows with NULL decile "
            f"but active_days_first_28 > 0"
        )

        # Non-NULL decile but zero active_days — should never happen
        has_decile_zero_days: pd.DataFrame = df[
            df["engagement_decile_in_course"].notna()
            & (df["active_days_first_28"] == 0)
        ]
        assert len(has_decile_zero_days) == 0, (
            f"Found {len(has_decile_zero_days)} rows with a decile rank "
            f"but active_days_first_28 = 0"
        )

    def test_row_count_matches_student_enriched(
        self, db_conn: duckdb.DuckDBPyConnection
    ) -> None:
        """BQ3 must return exactly one row per student in v_student_enriched."""
        df: pd.DataFrame = _run_query_file(
            "q_bq3_demographics_vs_behavior.sql", db_conn
        )

        df_se: pd.DataFrame = execute_query(
            "SELECT COUNT(*) AS n FROM v_student_enriched",
            conn=db_conn,
        )
        expected: int = df_se["n"].iloc[0]
        assert (
            len(df) == expected
        ), f"BQ3 returned {len(df)} rows but v_student_enriched has {expected}"


# ===================================================================
# BQ4 — q_bq4_course_comparison
# ===================================================================


class TestBQ4CourseComparison:
    """Invariants for q_bq4_course_comparison.sql."""

    def test_code_module_unique(self, db_conn: duckdb.DuckDBPyConnection) -> None:
        """Each code_module must appear exactly once (one row per module)."""
        df: pd.DataFrame = _run_query_file("q_bq4_course_comparison.sql", db_conn)

        dupes: pd.DataFrame = df[df.duplicated(subset=["code_module"], keep=False)]
        assert (
            len(dupes) == 0
        ), f"Found {len(dupes)} rows with duplicate code_module values"

    def test_completion_rate_bounded(self, db_conn: duckdb.DuckDBPyConnection) -> None:
        """avg_completion_rate_pct must be between 0 and 100."""
        df: pd.DataFrame = _run_query_file("q_bq4_course_comparison.sql", db_conn)

        min_rate: float = df["avg_completion_rate_pct"].min()
        max_rate: float = df["avg_completion_rate_pct"].max()
        assert min_rate >= 0, f"avg_completion_rate_pct went below 0: {min_rate}"
        assert max_rate <= 100, f"avg_completion_rate_pct exceeded 100: {max_rate}"

    def test_withdrawal_rate_bounded(self, db_conn: duckdb.DuckDBPyConnection) -> None:
        """avg_withdrawal_rate_pct must be between 0 and 100."""
        df: pd.DataFrame = _run_query_file("q_bq4_course_comparison.sql", db_conn)

        min_rate: float = df["avg_withdrawal_rate_pct"].min()
        max_rate: float = df["avg_withdrawal_rate_pct"].max()
        assert min_rate >= 0, f"avg_withdrawal_rate_pct went below 0: {min_rate}"
        assert max_rate <= 100, f"avg_withdrawal_rate_pct exceeded 100: {max_rate}"

    def test_total_completed_le_enrolled(
        self, db_conn: duckdb.DuckDBPyConnection
    ) -> None:
        """total_completed must not exceed total_enrolled for any module."""
        df: pd.DataFrame = _run_query_file("q_bq4_course_comparison.sql", db_conn)

        violations: pd.DataFrame = df[df["total_completed"] > df["total_enrolled"]]
        assert len(violations) == 0, (
            f"Found {len(violations)} modules where total_completed > total_enrolled: "
            f"{violations['code_module'].tolist()}"
        )

    def test_design_features_positive(self, db_conn: duckdb.DuckDBPyConnection) -> None:
        """Course design metrics must be strictly positive.

        Every course has a duration, at least one assessment, and at
        least one VLE resource — zero would indicate missing data.
        """
        df: pd.DataFrame = _run_query_file("q_bq4_course_comparison.sql", db_conn)

        for col in [
            "avg_course_length_days",
            "avg_n_assessments",
            "avg_n_vle_resources",
        ]:
            min_val: float = df[col].min()
            assert min_val > 0, f"{col} has non-positive value: {min_val}"


# ===================================================================
# BQ5 — q_bq5_segment_sizing
# ===================================================================


class TestBQ5SegmentSizing:
    """Invariants for q_bq5_segment_sizing.sql."""

    def test_single_row_output(self, db_conn: duckdb.DuckDBPyConnection) -> None:
        """Query must return exactly one aggregate row (no GROUP BY)."""
        df: pd.DataFrame = _run_query_file("q_bq5_segment_sizing.sql", db_conn)

        assert len(df) == 1, f"Expected 1 row, got {len(df)}"

    def test_total_students_matches_student_enriched(
        self, db_conn: duckdb.DuckDBPyConnection
    ) -> None:
        """total_students must equal the count from v_student_enriched."""
        df: pd.DataFrame = _run_query_file("q_bq5_segment_sizing.sql", db_conn)

        df_se: pd.DataFrame = execute_query(
            "SELECT COUNT(*) AS n FROM v_student_enriched",
            conn=db_conn,
        )
        expected: int = df_se["n"].iloc[0]
        actual: int = df["total_students"].iloc[0]
        assert (
            actual == expected
        ), f"total_students = {actual} but v_student_enriched has {expected}"

    def test_segment_counts_non_negative(
        self, db_conn: duckdb.DuckDBPyConnection
    ) -> None:
        """All segment counts must be >= 0."""
        df: pd.DataFrame = _run_query_file("q_bq5_segment_sizing.sql", db_conn)

        for col in ["n_ghost", "n_non_submitter", "n_early_disengager"]:
            val: int = df[col].iloc[0]
            assert val >= 0, f"{col} is negative: {val}"

    def test_segment_percentages_bounded(
        self, db_conn: duckdb.DuckDBPyConnection
    ) -> None:
        """Segment percentage columns must be between 0 and 100."""
        df: pd.DataFrame = _run_query_file("q_bq5_segment_sizing.sql", db_conn)

        for col in ["pct_ghost", "pct_non_submitter", "pct_early_disengager"]:
            val: float = df[col].iloc[0]
            assert 0 <= val <= 100, f"{col} out of range [0, 100]: {val}"

    def test_non_completion_rates_bounded(
        self, db_conn: duckdb.DuckDBPyConnection
    ) -> None:
        """Non-completion rate columns must be between 0 and 100, or NULL.

        NULL is valid when a segment is empty (the NULLIF guard in the
        query prevents division by zero and returns NULL instead).
        """
        df: pd.DataFrame = _run_query_file("q_bq5_segment_sizing.sql", db_conn)

        for col in [
            "ghost_non_completion_rate_pct",
            "non_submitter_non_completion_rate_pct",
            "disengager_non_completion_rate_pct",
        ]:
            val = df[col].iloc[0]
            if pd.notna(val):
                assert 0 <= val <= 100, f"{col} out of range [0, 100]: {val}"
