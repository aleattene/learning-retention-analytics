"""Step 03 — Export analytical views to CSV and optionally to Google Sheets.

Materializes each analytical view into a CSV file under data/analysis/.
When PUSH_TO_SHEETS is enabled, the same data is also pushed to Google Sheets
for consumption by the Looker Studio dashboard.

CSV export always runs (zero dependencies, works offline).
Sheets push is opt-in via environment variable to avoid requiring
Google Cloud credentials for basic usage.
"""

import logging
from pathlib import Path

import duckdb
import pandas as pd

from src.config import ANALYSIS_DIR, PUSH_TO_SHEETS, QUERIES_DIR, VIEWS_DIR
from src.db.connection import execute_query, get_default_connection

logger = logging.getLogger(__name__)

# Views and queries to export as CSV files.
# Each entry maps an output filename to the SQL source (view or query file).
# Views are queried with SELECT *; query files are read and executed directly.
EXPORT_VIEWS: list[str] = [
    "v_student_enriched",
    "v_engagement_daily",
    "v_engagement_early",
    "v_dropout_timing",
    "v_course_profile",
]

EXPORT_QUERIES: dict[str, str] = {
    "bq1_dropout_curves": "q_bq1_dropout_curves.sql",
    "bq2_early_signals": "q_bq2_early_signals.sql",
    "bq3_demographics_vs_behavior": "q_bq3_demographics_vs_behavior.sql",
    "bq4_course_comparison": "q_bq4_course_comparison.sql",
    "bq5_segment_sizing": "q_bq5_segment_sizing.sql",
}


def _export_dataframe(df: pd.DataFrame, name: str, output_dir: Path) -> Path:
    """Write a DataFrame to CSV and return the output path.

    Uses UTF-8 encoding and includes the index=False to keep CSVs clean
    for downstream consumers (notebooks, Looker Studio).
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path: Path = output_dir / f"{name}.csv"
    df.to_csv(output_path, index=False, encoding="utf-8")
    logger.info("Exported %s: %d rows → %s", name, len(df), output_path)
    return output_path


def export(
    conn: duckdb.DuckDBPyConnection | None = None,
    output_dir: Path | None = None,
) -> list[Path]:
    """Export all analytical views and queries to CSV files.

    Parameters
    ----------
    conn : DuckDBPyConnection or None
        Database connection. If None, opens the default project DB read-only.
    output_dir : Path or None
        Output directory for CSVs. Defaults to data/analysis/.

    Returns
    -------
    list[Path]
        Paths to all exported CSV files.
    """
    if output_dir is None:
        output_dir = ANALYSIS_DIR

    own_conn: bool = conn is None
    if own_conn:
        conn = get_default_connection(read_only=True)

    exported: list[Path] = []

    try:
        # Export analytical views (simple SELECT * from each view)
        for view_name in EXPORT_VIEWS:
            df: pd.DataFrame = execute_query(
                f"SELECT * FROM {view_name}", conn=conn
            )
            path: Path = _export_dataframe(df, view_name, output_dir)
            exported.append(path)

        # Export business question queries (read SQL from file)
        for output_name, query_file in EXPORT_QUERIES.items():
            query_path: Path = QUERIES_DIR / query_file
            if not query_path.exists():
                logger.warning("Query file not found, skipping: %s", query_path)
                continue

            sql: str = query_path.read_text(encoding="utf-8")
            df = execute_query(sql, conn=conn)
            path = _export_dataframe(df, output_name, output_dir)
            exported.append(path)

        logger.info("Export complete: %d files → %s", len(exported), output_dir)

        # Optional: push to Google Sheets for Looker Studio dashboard
        if PUSH_TO_SHEETS:
            _push_to_sheets(exported)

    finally:
        if own_conn:
            conn.close()

    return exported


def _push_to_sheets(csv_paths: list[Path]) -> None:
    """Push exported CSVs to Google Sheets via gspread.

    Imported lazily to avoid requiring gspread/keyring when
    PUSH_TO_SHEETS is disabled (the common case during development).
    """
    try:
        from src.sheets.push import push_csvs_to_sheets

        push_csvs_to_sheets(csv_paths)
    except ImportError:
        logger.error(
            "gspread or keyring not installed. "
            "Install with: pip install gspread keyring"
        )
    except Exception:
        logger.exception("Failed to push to Google Sheets")
