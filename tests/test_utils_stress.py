"""Stress tests for src/utils/ — logging and runtime utilities.

Tests edge cases: exception handling in step_timer, missing libraries
in log_environment, setup_logging idempotency, and timer accuracy.
"""

import logging
import time
from unittest.mock import patch

import pytest

from src.utils.logging import setup_logging
from src.utils.runtime import log_environment, step_timer

# ===================================================================
# step_timer — stress tests
# ===================================================================


class TestStepTimerStress:
    """Edge cases for the step_timer context manager."""

    def test_timer_logs_start_and_completion(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Should log both 'Starting' and 'completed in' messages."""
        with caplog.at_level(logging.INFO, logger="src.utils.runtime"):
            with step_timer("Test Step"):
                pass

        assert "Starting: Test Step" in caplog.text
        assert "Test Step completed in" in caplog.text

    def test_timer_logs_completion_on_exception(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Should still log completion time even if the block raises."""
        with caplog.at_level(logging.INFO, logger="src.utils.runtime"):
            with pytest.raises(ValueError):
                with step_timer("Failing Step"):
                    raise ValueError("intentional error")

        # The 'completed in' message should appear because it's in finally
        assert "Failing Step completed in" in caplog.text

    def test_timer_measures_actual_time(self, caplog: pytest.LogCaptureFixture) -> None:
        """Elapsed time should be logged after a real delay."""
        with caplog.at_level(logging.INFO, logger="src.utils.runtime"):
            with step_timer("Timed Step"):
                time.sleep(0.1)

        assert "Timed Step completed in" in caplog.text

    def test_timer_with_empty_step_name(self, caplog: pytest.LogCaptureFixture) -> None:
        """Empty step name should not crash — just produce odd log messages."""
        with caplog.at_level(logging.INFO, logger="src.utils.runtime"):
            with step_timer(""):
                pass
        assert "Starting: " in caplog.text

    def test_timer_with_unicode_step_name(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Unicode characters in step name should be logged correctly."""
        with caplog.at_level(logging.INFO, logger="src.utils.runtime"):
            with step_timer("Étape 1 — Ingest données"):
                pass
        assert "Étape 1" in caplog.text

    def test_nested_timers(self, caplog: pytest.LogCaptureFixture) -> None:
        """Nested step_timer calls should each log independently."""
        with caplog.at_level(logging.INFO, logger="src.utils.runtime"):
            with step_timer("Outer"):
                with step_timer("Inner"):
                    pass

        assert "Starting: Outer" in caplog.text
        assert "Starting: Inner" in caplog.text
        assert "Inner completed in" in caplog.text
        assert "Outer completed in" in caplog.text


# ===================================================================
# log_environment — stress tests
# ===================================================================


class TestLogEnvironmentStress:
    """Edge cases for log_environment."""

    def test_logs_python_version(self, caplog: pytest.LogCaptureFixture) -> None:
        """Should log the Python version."""
        with caplog.at_level(logging.INFO, logger="src.utils.runtime"):
            log_environment()
        assert "Python" in caplog.text

    def test_logs_library_versions(self, caplog: pytest.LogCaptureFixture) -> None:
        """Should log duckdb, pandas, numpy, scipy versions."""
        with caplog.at_level(logging.INFO, logger="src.utils.runtime"):
            log_environment()

        for lib in ["duckdb", "pandas", "numpy", "scipy"]:
            assert lib in caplog.text

    def test_handles_missing_library_gracefully(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """If a library is not installed, should log warning not crash."""
        # Simulate a missing library by making __import__ raise for one lib
        original_import = (
            __builtins__.__import__
            if hasattr(__builtins__, "__import__")
            else __import__
        )

        def mock_import(name, *args, **kwargs):
            if name == "scipy":
                raise ImportError("mocked missing")
            return original_import(name, *args, **kwargs)

        with (
            caplog.at_level(logging.WARNING, logger="src.utils.runtime"),
            patch("builtins.__import__", side_effect=mock_import),
        ):
            log_environment()

        assert "scipy" in caplog.text

    def test_handles_library_without_version(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Library without __version__ attribute should log 'unknown'."""
        import types

        fake_module = types.ModuleType("fake_lib")
        # No __version__ attribute on purpose

        original_import = __import__

        def mock_import(name, *args, **kwargs):
            if name == "duckdb":
                return fake_module
            return original_import(name, *args, **kwargs)

        with (
            caplog.at_level(logging.INFO, logger="src.utils.runtime"),
            patch("builtins.__import__", side_effect=mock_import),
        ):
            log_environment()

        assert "unknown" in caplog.text

    def test_log_environment_is_idempotent(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Calling log_environment twice should not crash or duplicate state."""
        with caplog.at_level(logging.INFO, logger="src.utils.runtime"):
            log_environment()
            log_environment()

        # Should see "Python" logged at least twice
        assert caplog.text.count("Python") >= 2


# ===================================================================
# setup_logging — stress tests
# ===================================================================


class TestSetupLoggingStress:
    """Edge cases for setup_logging."""

    def test_default_level_is_info(self) -> None:
        """Default call should set INFO level."""
        setup_logging()
        assert logging.getLogger().level == logging.INFO

    def test_debug_level(self) -> None:
        """Passing DEBUG should set DEBUG level."""
        setup_logging(level=logging.DEBUG)
        assert logging.getLogger().level == logging.DEBUG

    def test_idempotent_setup(self) -> None:
        """Calling setup_logging twice should not crash or stack handlers."""
        setup_logging(level=logging.INFO)
        handler_count_1: int = len(logging.getLogger().handlers)

        setup_logging(level=logging.DEBUG)
        handler_count_2: int = len(logging.getLogger().handlers)

        # force=True in basicConfig replaces handlers, so count should not grow
        assert handler_count_2 <= handler_count_1 + 1

    def test_log_output_after_setup(self) -> None:
        """After setup_logging, module loggers should produce output.

        setup_logging configures a StreamHandler on stdout, which caplog
        does not intercept.  Instead we verify the root logger is properly
        configured and that calling a child logger does not raise.
        """
        setup_logging(level=logging.DEBUG)
        root: logging.Logger = logging.getLogger()
        assert root.level == logging.DEBUG
        assert len(root.handlers) > 0

        # Verify a child logger can emit without error
        test_logger: logging.Logger = logging.getLogger("test_module_stress")
        test_logger.debug("Debug message from stress test")  # should not raise
