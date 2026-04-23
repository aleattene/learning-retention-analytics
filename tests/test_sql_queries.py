"""Tests for BQ SQL queries — validate business logic invariants on sample data.

These tests verify that the BQ1 (dropout curves) and BQ2 (early signals)
queries produce structurally correct results.  The queries are loaded from
sql/queries/ and executed against the in-memory DuckDB fixture populated
with data_sample/ CSVs.
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
