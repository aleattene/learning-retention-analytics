"""Centralized configuration — paths, constants, and env vars.

All paths are relative to PROJECT_ROOT.
Single env var: PUSH_TO_SHEETS (default false).
"""

import os
from pathlib import Path

# --- Paths ---
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
DATA_DIR: Path = PROJECT_ROOT / "data"
RAW_DATA_DIR: Path = DATA_DIR / "raw"
DB_DIR: Path = DATA_DIR / "db"
ANALYSIS_DIR: Path = DATA_DIR / "analysis"
DATA_SAMPLE_DIR: Path = PROJECT_ROOT / "data_sample"
REPORTS_DIR: Path = PROJECT_ROOT / "reports"
FIGURES_DIR: Path = REPORTS_DIR / "figures"

# --- SQL paths ---
SQL_DIR: Path = PROJECT_ROOT / "sql"
VIEWS_DIR: Path = SQL_DIR / "views"
QUERIES_DIR: Path = SQL_DIR / "queries"

# --- DuckDB ---
DB_PATH: Path = DB_DIR / "oulad.duckdb"

# --- OULAD CSV file names ---
OULAD_TABLES: dict[str, str] = {
    "courses": "courses.csv",
    "assessments": "assessments.csv",
    "vle": "vle.csv",
    "studentInfo": "studentInfo.csv",
    "studentRegistration": "studentRegistration.csv",
    "studentAssessment": "studentAssessment.csv",
    "studentVle": "studentVle.csv",
}

# --- Target variable ---
FINAL_RESULT_COL: str = "final_result"
COMPLETED_VALUES: list[str] = ["Pass", "Distinction"]
NOT_COMPLETED_VALUES: list[str] = ["Fail", "Withdrawn"]

# --- Environment variables ---
PUSH_TO_SHEETS: bool = os.environ.get("PUSH_TO_SHEETS", "false").lower() == "true"

# --- Google Sheets (used only when PUSH_TO_SHEETS is True) ---
SHEETS_KEYCHAIN_SERVICE: str = "learning-retention-analytics"
SHEETS_KEYCHAIN_ACCOUNT: str = "google-sheets-service-account"
