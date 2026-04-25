"""Tests for run_pipeline.py — CLI orchestrator.

Validates argument parsing, step selection logic, and error propagation.
All pipeline steps are mocked to test only the orchestration layer,
not the actual ETL logic (which is tested in test_pipeline*.py).
"""

import logging
from unittest.mock import MagicMock, patch

import pytest

# ===================================================================
# Argument parsing
# ===================================================================


class TestArgumentParsing:
    """Verify CLI flags are parsed correctly and forwarded to steps."""

    @patch("run_pipeline.export")
    @patch("run_pipeline.transform")
    @patch("run_pipeline.ingest")
    @patch("run_pipeline.log_environment")
    @patch("run_pipeline.setup_logging")
    def test_no_args_runs_all_steps(
        self,
        mock_setup: MagicMock,
        mock_env: MagicMock,
        mock_ingest: MagicMock,
        mock_transform: MagicMock,
        mock_export: MagicMock,
    ) -> None:
        """No arguments → all three steps run."""
        from run_pipeline import main

        with patch("sys.argv", ["run_pipeline"]):
            main()

        mock_ingest.assert_called_once()
        mock_transform.assert_called_once()
        mock_export.assert_called_once()

    @patch("run_pipeline.export")
    @patch("run_pipeline.transform")
    @patch("run_pipeline.ingest")
    @patch("run_pipeline.log_environment")
    @patch("run_pipeline.setup_logging")
    def test_step_ingest_runs_only_ingest(
        self,
        mock_setup: MagicMock,
        mock_env: MagicMock,
        mock_ingest: MagicMock,
        mock_transform: MagicMock,
        mock_export: MagicMock,
    ) -> None:
        """--step ingest → only ingest runs."""
        from run_pipeline import main

        with patch("sys.argv", ["run_pipeline", "--step", "ingest"]):
            main()

        mock_ingest.assert_called_once()
        mock_transform.assert_not_called()
        mock_export.assert_not_called()

    @patch("run_pipeline.export")
    @patch("run_pipeline.transform")
    @patch("run_pipeline.ingest")
    @patch("run_pipeline.log_environment")
    @patch("run_pipeline.setup_logging")
    def test_step_transform_runs_only_transform(
        self,
        mock_setup: MagicMock,
        mock_env: MagicMock,
        mock_ingest: MagicMock,
        mock_transform: MagicMock,
        mock_export: MagicMock,
    ) -> None:
        """--step transform → only transform runs."""
        from run_pipeline import main

        with patch("sys.argv", ["run_pipeline", "--step", "transform"]):
            main()

        mock_ingest.assert_not_called()
        mock_transform.assert_called_once()
        mock_export.assert_not_called()

    @patch("run_pipeline.export")
    @patch("run_pipeline.transform")
    @patch("run_pipeline.ingest")
    @patch("run_pipeline.log_environment")
    @patch("run_pipeline.setup_logging")
    def test_step_export_runs_only_export(
        self,
        mock_setup: MagicMock,
        mock_env: MagicMock,
        mock_ingest: MagicMock,
        mock_transform: MagicMock,
        mock_export: MagicMock,
    ) -> None:
        """--step export → only export runs."""
        from run_pipeline import main

        with patch("sys.argv", ["run_pipeline", "--step", "export"]):
            main()

        mock_ingest.assert_not_called()
        mock_transform.assert_not_called()
        mock_export.assert_called_once()

    @patch("run_pipeline.log_environment")
    @patch("run_pipeline.setup_logging")
    def test_invalid_step_raises_system_exit(
        self,
        mock_setup: MagicMock,
        mock_env: MagicMock,
    ) -> None:
        """--step invalid → argparse raises SystemExit."""
        from run_pipeline import main

        with patch("sys.argv", ["run_pipeline", "--step", "invalid"]):
            with pytest.raises(SystemExit):
                main()


# ===================================================================
# --sample flag
# ===================================================================


class TestSampleFlag:
    """Verify --sample flag is forwarded correctly to ingest."""

    @patch("run_pipeline.export")
    @patch("run_pipeline.transform")
    @patch("run_pipeline.ingest")
    @patch("run_pipeline.log_environment")
    @patch("run_pipeline.setup_logging")
    def test_sample_flag_passed_to_ingest(
        self,
        mock_setup: MagicMock,
        mock_env: MagicMock,
        mock_ingest: MagicMock,
        mock_transform: MagicMock,
        mock_export: MagicMock,
    ) -> None:
        """--sample → ingest(use_sample=True)."""
        from run_pipeline import main

        with patch("sys.argv", ["run_pipeline", "--sample"]):
            main()

        mock_ingest.assert_called_once_with(use_sample=True)

    @patch("run_pipeline.export")
    @patch("run_pipeline.transform")
    @patch("run_pipeline.ingest")
    @patch("run_pipeline.log_environment")
    @patch("run_pipeline.setup_logging")
    def test_no_sample_flag_default_false(
        self,
        mock_setup: MagicMock,
        mock_env: MagicMock,
        mock_ingest: MagicMock,
        mock_transform: MagicMock,
        mock_export: MagicMock,
    ) -> None:
        """No --sample → ingest(use_sample=False)."""
        from run_pipeline import main

        with patch("sys.argv", ["run_pipeline"]):
            main()

        mock_ingest.assert_called_once_with(use_sample=False)


# ===================================================================
# --debug flag
# ===================================================================


class TestDebugFlag:
    """Verify --debug flag sets correct logging level."""

    @patch("run_pipeline.export")
    @patch("run_pipeline.transform")
    @patch("run_pipeline.ingest")
    @patch("run_pipeline.log_environment")
    @patch("run_pipeline.setup_logging")
    def test_debug_flag_sets_debug_level(
        self,
        mock_setup: MagicMock,
        mock_env: MagicMock,
        mock_ingest: MagicMock,
        mock_transform: MagicMock,
        mock_export: MagicMock,
    ) -> None:
        """--debug → setup_logging(level=logging.DEBUG)."""
        from run_pipeline import main

        with patch("sys.argv", ["run_pipeline", "--debug"]):
            main()

        mock_setup.assert_called_once_with(level=logging.DEBUG)

    @patch("run_pipeline.export")
    @patch("run_pipeline.transform")
    @patch("run_pipeline.ingest")
    @patch("run_pipeline.log_environment")
    @patch("run_pipeline.setup_logging")
    def test_no_debug_flag_sets_info_level(
        self,
        mock_setup: MagicMock,
        mock_env: MagicMock,
        mock_ingest: MagicMock,
        mock_transform: MagicMock,
        mock_export: MagicMock,
    ) -> None:
        """No --debug → setup_logging(level=logging.INFO)."""
        from run_pipeline import main

        with patch("sys.argv", ["run_pipeline"]):
            main()

        mock_setup.assert_called_once_with(level=logging.INFO)


# ===================================================================
# Error propagation
# ===================================================================


class TestErrorPropagation:
    """Pipeline step exceptions must propagate to the caller."""

    @patch("run_pipeline.log_environment")
    @patch("run_pipeline.setup_logging")
    @patch("run_pipeline.ingest", side_effect=RuntimeError("ingest failed"))
    def test_ingest_error_propagates(
        self,
        mock_ingest: MagicMock,
        mock_setup: MagicMock,
        mock_env: MagicMock,
    ) -> None:
        """RuntimeError in ingest should propagate out of main()."""
        from run_pipeline import main

        with patch("sys.argv", ["run_pipeline", "--step", "ingest"]):
            with pytest.raises(RuntimeError, match="ingest failed"):
                main()

    @patch("run_pipeline.log_environment")
    @patch("run_pipeline.setup_logging")
    @patch("run_pipeline.transform", side_effect=FileNotFoundError("no view"))
    def test_transform_error_propagates(
        self,
        mock_transform: MagicMock,
        mock_setup: MagicMock,
        mock_env: MagicMock,
    ) -> None:
        """FileNotFoundError in transform should propagate out of main()."""
        from run_pipeline import main

        with patch("sys.argv", ["run_pipeline", "--step", "transform"]):
            with pytest.raises(FileNotFoundError, match="no view"):
                main()

    @patch("run_pipeline.log_environment")
    @patch("run_pipeline.setup_logging")
    @patch("run_pipeline.export", side_effect=PermissionError("read-only"))
    def test_export_error_propagates(
        self,
        mock_export: MagicMock,
        mock_setup: MagicMock,
        mock_env: MagicMock,
    ) -> None:
        """PermissionError in export should propagate out of main()."""
        from run_pipeline import main

        with patch("sys.argv", ["run_pipeline", "--step", "export"]):
            with pytest.raises(PermissionError, match="read-only"):
                main()


# ===================================================================
# Combined flags
# ===================================================================


class TestCombinedFlags:
    """Verify that multiple flags work together."""

    @patch("run_pipeline.export")
    @patch("run_pipeline.transform")
    @patch("run_pipeline.ingest")
    @patch("run_pipeline.log_environment")
    @patch("run_pipeline.setup_logging")
    def test_sample_and_debug_together(
        self,
        mock_setup: MagicMock,
        mock_env: MagicMock,
        mock_ingest: MagicMock,
        mock_transform: MagicMock,
        mock_export: MagicMock,
    ) -> None:
        """--sample --debug → sample=True + level=DEBUG."""
        from run_pipeline import main

        with patch("sys.argv", ["run_pipeline", "--sample", "--debug"]):
            main()

        mock_setup.assert_called_once_with(level=logging.DEBUG)
        mock_ingest.assert_called_once_with(use_sample=True)

    @patch("run_pipeline.export")
    @patch("run_pipeline.transform")
    @patch("run_pipeline.ingest")
    @patch("run_pipeline.log_environment")
    @patch("run_pipeline.setup_logging")
    def test_step_and_sample_together(
        self,
        mock_setup: MagicMock,
        mock_env: MagicMock,
        mock_ingest: MagicMock,
        mock_transform: MagicMock,
        mock_export: MagicMock,
    ) -> None:
        """--step ingest --sample → only ingest with sample=True."""
        from run_pipeline import main

        with patch("sys.argv", ["run_pipeline", "--step", "ingest", "--sample"]):
            main()

        mock_ingest.assert_called_once_with(use_sample=True)
        mock_transform.assert_not_called()
        mock_export.assert_not_called()
