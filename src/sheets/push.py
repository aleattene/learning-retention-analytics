"""Google Sheets push via gspread + macOS Keychain.

Pushes analytical CSV files to Google Sheets for consumption by
the Looker Studio dashboard. Credentials are stored exclusively
in the macOS Keychain (AES-256 encrypted, Touch ID protected).

This module is only imported when PUSH_TO_SHEETS=true. All imports
of gspread and keyring are at module level because this file is
never loaded unless the user has explicitly opted in.

Security rules (from bp-secure-pipeline-to-sheets-via-keychain.md):
- NEVER store credentials in .env, env vars, or code
- NEVER log paths, tokens, or keys
- ALWAYS use explicit minimal scopes (spreadsheets only, not drive)
- ALWAYS use open_by_key() for unambiguous sheet access
- ALWAYS use value_input_option="RAW" to prevent formula injection
"""

import json
import logging
from pathlib import Path

import gspread
import keyring
import pandas as pd
from google.oauth2.service_account import Credentials

from src.config import SHEETS_KEYCHAIN_ACCOUNT, SHEETS_KEYCHAIN_SERVICE

logger = logging.getLogger(__name__)

# Minimal scope: only Sheets API, not Drive API
# This limits what the service account can access even if compromised
_SCOPES: list[str] = ["https://www.googleapis.com/auth/spreadsheets"]


def _get_credentials_from_keychain() -> dict:
    """Retrieve and validate service account JSON from macOS Keychain.

    The entire service account JSON is stored as a single Keychain entry,
    not as a file path. This means zero sensitive files on disk at runtime.

    Raises
    ------
    RuntimeError
        If credentials are missing, malformed, or not a service account.
    """
    raw: str | None = keyring.get_password(
        SHEETS_KEYCHAIN_SERVICE, SHEETS_KEYCHAIN_ACCOUNT
    )
    if not raw:
        # Generic error message — never reveal what we expected to find
        raise RuntimeError("Credentials not found in macOS Keychain.")

    try:
        info: dict = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Credentials in Keychain are not valid JSON.") from exc

    # Validate that this is actually a service account (not an OAuth token or other)
    if info.get("type") != "service_account":
        raise RuntimeError("Keychain credentials are not a valid service account.")

    # Check minimum required fields for authentication
    required: set[str] = {"type", "client_email", "private_key", "token_uri"}
    if required - info.keys():
        raise RuntimeError("Service account JSON is missing required fields.")

    return info


def _authorize() -> gspread.Client:
    """Create an authenticated gspread client with minimal scopes."""
    info: dict = _get_credentials_from_keychain()
    credentials = Credentials.from_service_account_info(info, scopes=_SCOPES)
    return gspread.authorize(credentials)


def push_csvs_to_sheets(
    csv_paths: list[Path],
    spreadsheet_id: str | None = None,
) -> None:
    """Push a list of CSV files to Google Sheets.

    Each CSV becomes a separate worksheet in the target spreadsheet.
    Existing data is fully overwritten (clear + update) on each run
    to ensure the dashboard always reflects the latest pipeline output.

    Parameters
    ----------
    csv_paths : list[Path]
        Paths to CSV files to push. Each file becomes a worksheet
        named after the file stem (e.g. "v_student_enriched").
    spreadsheet_id : str or None
        Google Sheets spreadsheet ID. If None, must be configured
        elsewhere (future: add to config).
    """
    if spreadsheet_id is None:
        logger.warning("No spreadsheet_id configured. Skipping Sheets push.")
        return

    client: gspread.Client = _authorize()
    # open_by_key is preferred over open_by_url or open() by name
    # because the key is unambiguous (no name collisions possible)
    spreadsheet = client.open_by_key(spreadsheet_id)

    for csv_path in csv_paths:
        sheet_name: str = csv_path.stem
        df: pd.DataFrame = pd.read_csv(csv_path)

        # Get or create the worksheet for this CSV
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(
                title=sheet_name, rows=len(df) + 1, cols=len(df.columns)
            )

        # Full overwrite: clear existing data, then write header + rows
        # This is safer than append (no stale rows left behind)
        worksheet.clear()

        # Convert DataFrame to list of lists (header + data)
        # value_input_option="RAW" prevents Sheets from interpreting
        # cell values as formulas (defense against formula injection)
        data: list[list] = [df.columns.tolist()] + df.to_numpy().tolist()
        worksheet.update(data, value_input_option="RAW")

        logger.info("Pushed %s: %d rows to sheet '%s'", csv_path.name, len(df), sheet_name)

    logger.info("Sheets push complete: %d worksheets updated", len(csv_paths))
