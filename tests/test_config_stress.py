"""Stress tests for src/config.py — env var edge cases and path validation.

The config module is loaded once at import time. Since PUSH_TO_SHEETS is
computed at module level from os.environ, testing different env var values
requires reloading the module after patching the environment.
"""

import importlib
import os
from pathlib import Path

# ===================================================================
# PUSH_TO_SHEETS env var edge cases
# ===================================================================


class TestPushToSheetsEnvVar:
    """Validate PUSH_TO_SHEETS parsing for all plausible env var values."""

    def _reload_config_with_env(self, value: str | None) -> bool:
        """Set PUSH_TO_SHEETS env var to *value*, reload config, return the flag.

        If value is None, the env var is removed entirely.
        The original env var value is saved and restored in the finally
        block so that other tests are not affected by side effects.
        """
        # Save the original value to restore it after the test
        original: str | None = os.environ.get("PUSH_TO_SHEETS")

        if value is None:
            os.environ.pop("PUSH_TO_SHEETS", None)
        else:
            os.environ["PUSH_TO_SHEETS"] = value
        try:
            import src.config

            importlib.reload(src.config)
            return src.config.PUSH_TO_SHEETS
        finally:
            # Restore the original env var state (present or absent)
            if original is None:
                os.environ.pop("PUSH_TO_SHEETS", None)
            else:
                os.environ["PUSH_TO_SHEETS"] = original
            importlib.reload(importlib.import_module("src.config"))

    def test_true_lowercase(self) -> None:
        """'true' → True."""
        assert self._reload_config_with_env("true") is True

    def test_true_uppercase(self) -> None:
        """'TRUE' → True (case insensitive)."""
        assert self._reload_config_with_env("TRUE") is True

    def test_true_mixed_case(self) -> None:
        """'True' → True (case insensitive)."""
        assert self._reload_config_with_env("True") is True

    def test_false_lowercase(self) -> None:
        """'false' → False."""
        assert self._reload_config_with_env("false") is False

    def test_false_uppercase(self) -> None:
        """'FALSE' → False."""
        assert self._reload_config_with_env("FALSE") is False

    def test_empty_string(self) -> None:
        """'' → False (empty is not 'true')."""
        assert self._reload_config_with_env("") is False

    def test_unset_env_var(self) -> None:
        """Unset env var → False (default)."""
        assert self._reload_config_with_env(None) is False

    def test_yes_is_not_true(self) -> None:
        """'yes' → False (only 'true' is accepted)."""
        assert self._reload_config_with_env("yes") is False

    def test_one_is_not_true(self) -> None:
        """'1' → False (only 'true' is accepted)."""
        assert self._reload_config_with_env("1") is False

    def test_whitespace_is_not_true(self) -> None:
        """' true ' with whitespace → False (.lower() doesn't strip)."""
        assert self._reload_config_with_env(" true ") is False


# ===================================================================
# Path constants validation
# ===================================================================


class TestPathConstants:
    """Validate that path constants are structurally correct."""

    def test_project_root_exists(self) -> None:
        """PROJECT_ROOT should exist on disk."""
        from src.config import PROJECT_ROOT

        assert PROJECT_ROOT.exists()
        assert PROJECT_ROOT.is_dir()

    def test_sql_dir_exists(self) -> None:
        """SQL_DIR should exist (required for pipeline)."""
        from src.config import SQL_DIR

        assert SQL_DIR.exists()

    def test_views_dir_exists(self) -> None:
        """VIEWS_DIR should exist (required for transform step)."""
        from src.config import VIEWS_DIR

        assert VIEWS_DIR.exists()

    def test_queries_dir_exists(self) -> None:
        """QUERIES_DIR should exist (required for export step)."""
        from src.config import QUERIES_DIR

        assert QUERIES_DIR.exists()

    def test_data_sample_dir_exists(self) -> None:
        """DATA_SAMPLE_DIR should exist (required for CI tests)."""
        from src.config import DATA_SAMPLE_DIR

        assert DATA_SAMPLE_DIR.exists()

    def test_all_paths_under_project_root(self) -> None:
        """All configured paths should be under PROJECT_ROOT."""
        from src.config import (
            ANALYSIS_DIR,
            DATA_DIR,
            DATA_SAMPLE_DIR,
            DB_DIR,
            FIGURES_DIR,
            PROJECT_ROOT,
            QUERIES_DIR,
            RAW_DATA_DIR,
            REPORTS_DIR,
            SQL_DIR,
            VIEWS_DIR,
        )

        for path in [
            DATA_DIR,
            RAW_DATA_DIR,
            DB_DIR,
            ANALYSIS_DIR,
            DATA_SAMPLE_DIR,
            REPORTS_DIR,
            FIGURES_DIR,
            SQL_DIR,
            VIEWS_DIR,
            QUERIES_DIR,
        ]:
            assert str(path).startswith(
                str(PROJECT_ROOT)
            ), f"{path} not under PROJECT_ROOT"


# ===================================================================
# OULAD table constants
# ===================================================================


class TestOuladTableConstants:
    """Validate OULAD_TABLES and target variable constants."""

    def test_oulad_tables_count(self) -> None:
        """Should have exactly 7 OULAD tables."""
        from src.config import OULAD_TABLES

        assert len(OULAD_TABLES) == 7

    def test_oulad_tables_csv_extensions(self) -> None:
        """All OULAD table files should be .csv."""
        from src.config import OULAD_TABLES

        for csv_filename in OULAD_TABLES.values():
            assert csv_filename.endswith(".csv"), f"{csv_filename} not a .csv"

    def test_sample_csvs_match_oulad_tables(self) -> None:
        """Every OULAD table should have a matching CSV in data_sample/."""
        from src.config import DATA_SAMPLE_DIR, OULAD_TABLES

        for csv_filename in OULAD_TABLES.values():
            csv_path: Path = DATA_SAMPLE_DIR / csv_filename
            assert csv_path.exists(), f"Missing sample CSV: {csv_path}"

    def test_completed_values_cover_positive_outcomes(self) -> None:
        """COMPLETED_VALUES should include Pass and Distinction."""
        from src.config import COMPLETED_VALUES

        assert "Pass" in COMPLETED_VALUES
        assert "Distinction" in COMPLETED_VALUES

    def test_not_completed_values_cover_negative_outcomes(self) -> None:
        """NOT_COMPLETED_VALUES should include Fail and Withdrawn."""
        from src.config import NOT_COMPLETED_VALUES

        assert "Fail" in NOT_COMPLETED_VALUES
        assert "Withdrawn" in NOT_COMPLETED_VALUES

    def test_no_overlap_between_completed_and_not(self) -> None:
        """Completed and not-completed values should be disjoint."""
        from src.config import COMPLETED_VALUES, NOT_COMPLETED_VALUES

        overlap: set[str] = set(COMPLETED_VALUES) & set(NOT_COMPLETED_VALUES)
        assert overlap == set(), f"Overlap found: {overlap}"
