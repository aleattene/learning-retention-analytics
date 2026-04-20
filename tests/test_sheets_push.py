"""Tests for src/sheets/push.py — Google Sheets push via gspread + Keychain.

All external dependencies (keyring, gspread, google.oauth2) are mocked
so these tests run without credentials or network access.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.sheets.push import (
    _authorize,
    _get_credentials_from_keychain,
    push_csvs_to_sheets,
)

# ---------------------------------------------------------------------------
# Valid service account fixture (minimum required fields)
# ---------------------------------------------------------------------------
VALID_SA_JSON: dict = {
    "type": "service_account",
    "client_email": "test@project.iam.gserviceaccount.com",
    "private_key": (
        "-----BEGIN RSA PRIVATE KEY-----\n" "fake\n" "-----END RSA PRIVATE KEY-----\n"
    ),
    "token_uri": "https://oauth2.googleapis.com/token",
}


class TestGetCredentialsFromKeychain:
    """Tests for _get_credentials_from_keychain error paths."""

    @patch("src.sheets.push.keyring.get_password", return_value=None)
    def test_missing_credentials_raises(self, mock_kp: MagicMock) -> None:
        """Keychain returning None should raise RuntimeError."""
        with pytest.raises(RuntimeError, match="Credentials not found"):
            _get_credentials_from_keychain()

    @patch("src.sheets.push.keyring.get_password", return_value="not-json{{{")
    def test_malformed_json_raises(self, mock_kp: MagicMock) -> None:
        """Invalid JSON in Keychain should raise RuntimeError."""
        with pytest.raises(RuntimeError, match="not valid JSON"):
            _get_credentials_from_keychain()

    @patch("src.sheets.push.keyring.get_password", return_value='{"type": "oauth2"}')
    def test_wrong_credential_type_raises(self, mock_kp: MagicMock) -> None:
        """Non-service-account type should raise RuntimeError."""
        with pytest.raises(RuntimeError, match="not a valid service account"):
            _get_credentials_from_keychain()

    @patch(
        "src.sheets.push.keyring.get_password",
        return_value=json.dumps({"type": "service_account", "client_email": "x"}),
    )
    def test_missing_required_fields_raises(self, mock_kp: MagicMock) -> None:
        """Service account JSON missing required fields should raise RuntimeError."""
        with pytest.raises(RuntimeError, match="missing required fields"):
            _get_credentials_from_keychain()

    @patch(
        "src.sheets.push.keyring.get_password",
        return_value=json.dumps(VALID_SA_JSON),
    )
    def test_valid_credentials_returns_dict(self, mock_kp: MagicMock) -> None:
        """Valid service account JSON should be returned as a dict."""
        result: dict = _get_credentials_from_keychain()
        assert result["type"] == "service_account"
        assert "private_key" in result

    @patch("src.sheets.push.keyring.get_password", return_value="")
    def test_empty_string_treated_as_missing(self, mock_kp: MagicMock) -> None:
        """Empty string from Keychain is falsy — should raise like None."""
        with pytest.raises(RuntimeError, match="Credentials not found"):
            _get_credentials_from_keychain()


class TestAuthorize:
    """Tests for _authorize — gspread client creation."""

    @patch("src.sheets.push.gspread.authorize")
    @patch("src.sheets.push.Credentials.from_service_account_info")
    @patch(
        "src.sheets.push.keyring.get_password",
        return_value=json.dumps(VALID_SA_JSON),
    )
    def test_authorize_calls_gspread(
        self,
        mock_kp: MagicMock,
        mock_creds: MagicMock,
        mock_auth: MagicMock,
    ) -> None:
        """_authorize should chain Keychain → Credentials → gspread.authorize."""
        mock_creds.return_value = MagicMock()
        _authorize()
        mock_creds.assert_called_once()
        mock_auth.assert_called_once()

    @patch(
        "src.sheets.push.keyring.get_password",
        return_value=None,
    )
    def test_authorize_propagates_keychain_error(self, mock_kp: MagicMock) -> None:
        """If Keychain fails, _authorize should propagate the RuntimeError."""
        with pytest.raises(RuntimeError, match="Credentials not found"):
            _authorize()


class TestPushCsvsToSheets:
    """Tests for push_csvs_to_sheets — worksheet create/update logic."""

    def test_no_spreadsheet_id_skips_push(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Passing spreadsheet_id=None should log warning and return."""
        import logging

        with caplog.at_level(logging.WARNING, logger="src.sheets.push"):
            push_csvs_to_sheets(csv_paths=[], spreadsheet_id=None)
        assert "No spreadsheet_id" in caplog.text

    @patch("src.sheets.push._authorize")
    def test_push_existing_worksheet(
        self, mock_auth: MagicMock, tmp_path: Path
    ) -> None:
        """Should clear and update an existing worksheet with RAW values."""
        # Create a small CSV
        csv_path: Path = tmp_path / "test_view.csv"
        df: pd.DataFrame = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        df.to_csv(csv_path, index=False)

        # Mock gspread chain
        mock_worksheet = MagicMock()
        mock_spreadsheet = MagicMock()
        mock_spreadsheet.worksheet.return_value = mock_worksheet
        mock_client = MagicMock()
        mock_client.open_by_key.return_value = mock_spreadsheet
        mock_auth.return_value = mock_client

        push_csvs_to_sheets([csv_path], spreadsheet_id="fake-id")

        mock_worksheet.clear.assert_called_once()
        mock_worksheet.update.assert_called_once()
        # Verify RAW value_input_option to prevent formula injection
        _, kwargs = mock_worksheet.update.call_args
        assert kwargs["value_input_option"] == "RAW"

    @patch("src.sheets.push._authorize")
    def test_push_creates_missing_worksheet(
        self, mock_auth: MagicMock, tmp_path: Path
    ) -> None:
        """Should create a new worksheet when WorksheetNotFound is raised."""
        import gspread

        csv_path: Path = tmp_path / "new_view.csv"
        df: pd.DataFrame = pd.DataFrame({"x": [10]})
        df.to_csv(csv_path, index=False)

        mock_new_ws = MagicMock()
        mock_spreadsheet = MagicMock()
        mock_spreadsheet.worksheet.side_effect = gspread.exceptions.WorksheetNotFound(
            "not found"
        )
        mock_spreadsheet.add_worksheet.return_value = mock_new_ws
        mock_client = MagicMock()
        mock_client.open_by_key.return_value = mock_spreadsheet
        mock_auth.return_value = mock_client

        push_csvs_to_sheets([csv_path], spreadsheet_id="fake-id")

        mock_spreadsheet.add_worksheet.assert_called_once()
        mock_new_ws.clear.assert_called_once()
        mock_new_ws.update.assert_called_once()

    @patch("src.sheets.push._authorize")
    def test_push_multiple_csvs(self, mock_auth: MagicMock, tmp_path: Path) -> None:
        """Should push each CSV to its own worksheet (named after file stem)."""
        csv_paths: list[Path] = []
        for name in ["view_a", "view_b", "view_c"]:
            p: Path = tmp_path / f"{name}.csv"
            pd.DataFrame({"col": [1]}).to_csv(p, index=False)
            csv_paths.append(p)

        mock_spreadsheet = MagicMock()
        mock_spreadsheet.worksheet.return_value = MagicMock()
        mock_client = MagicMock()
        mock_client.open_by_key.return_value = mock_spreadsheet
        mock_auth.return_value = mock_client

        push_csvs_to_sheets(csv_paths, spreadsheet_id="fake-id")

        # One worksheet lookup per CSV
        assert mock_spreadsheet.worksheet.call_count == 3
        worksheet_names: list[str] = [
            call.args[0] for call in mock_spreadsheet.worksheet.call_args_list
        ]
        assert worksheet_names == ["view_a", "view_b", "view_c"]

    @patch("src.sheets.push._authorize")
    def test_push_data_format_header_plus_rows(
        self, mock_auth: MagicMock, tmp_path: Path
    ) -> None:
        """Data sent to Sheets should be [header_row, *data_rows]."""
        csv_path: Path = tmp_path / "fmt.csv"
        pd.DataFrame({"name": ["alice", "bob"], "score": [90, 85]}).to_csv(
            csv_path, index=False
        )

        mock_ws = MagicMock()
        mock_spreadsheet = MagicMock()
        mock_spreadsheet.worksheet.return_value = mock_ws
        mock_client = MagicMock()
        mock_client.open_by_key.return_value = mock_spreadsheet
        mock_auth.return_value = mock_client

        push_csvs_to_sheets([csv_path], spreadsheet_id="fake-id")

        data_sent = mock_ws.update.call_args[0][0]
        assert data_sent[0] == ["name", "score"]  # header
        assert len(data_sent) == 3  # header + 2 rows
