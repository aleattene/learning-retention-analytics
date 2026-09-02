"""Step 04: statistical inference export, BQ2/BQ3 test results to CSV.

Materializes the statistical evidence behind BQ2 and BQ3 as CSV files
under data/analysis/. Notebook outputs are stripped by nbstripout, so
without this step the published p-values and effect sizes would have no
committed, reproducible artifact to be checked against. Every inferential
number quoted in reports/REPORT.md for BQ2/BQ3 is traceable to these files.

The computations mirror notebooks 04 and 05 exactly: same SQL queries,
same test wrappers from src/stats/tests.py, same correction families.
This guarantees the exported values match the published figures by
construction, not by transcription.
"""

import logging
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from src.config import ANALYSIS_DIR, QUERIES_DIR
from src.db.connection import execute_query, get_default_connection

# Reuse step 03's CSV writer so every exported artifact shares the same
# conventions (UTF-8, no index). Private by naming, but the pipeline
# steps form one cohesive package with a single export style.
from src.pipeline.step_03_export import _export_dataframe
from src.stats.tests import (
    TestResult,
    apply_multiple_comparison_correction,
    bootstrap_ci,
    chi_square_test,
    independent_t_test,
)

logger = logging.getLogger(__name__)

# Significance threshold for the significant_* flags in the exported CSVs.
# 0.05 matches the notebooks; the flags are a convenience for dashboard
# consumers; effect size remains the primary ranking criterion.
ALPHA: float = 0.05

# Bootstrap resamples for the ghost/active completion-rate CIs.
# 2000 matches notebook 04, and bootstrap_ci uses a fixed seed, so the
# exported intervals reproduce the published figure exactly.
N_BOOTSTRAP: int = 2000

# The 8 early behavioral signals tested in BQ2 (mirrors notebook 04).
SIGNAL_COLUMNS: list[str] = [
    "active_days_first_28",
    "total_clicks_first_28",
    "avg_clicks_per_active_day",
    "last_active_day_in_window",
    "engagement_decile_in_course",
    "first_score",
    "first_submit_day",
    "date_registration",
]

# BQ3 feature groups (mirrors notebook 05). Multiple-comparison
# corrections are applied WITHIN each family, never across families:
# merging families would change every adjusted p-value.
DEMO_CATEGORICAL: list[str] = [
    "gender",
    "age_band",
    "highest_education",
    "imd_band",
    "disability",
    "region",
]
DEMO_NUMERIC: list[str] = ["num_of_prev_attempts", "studied_credits"]
BEHAV_COLUMNS: list[str] = [
    "active_days_first_28",
    "total_clicks_first_28",
    "avg_clicks_per_active_day",
    "engagement_decile_in_course",
    "submitted_first_assessment",
    "first_score",
]

# Features measured on a reduced population: their NULLs mark a meaningful
# segment (no VLE activity, no early submission), not random missingness.
# Flagged in the export so downstream consumers do not compare them
# head-to-head with full-population features.
CONDITIONAL_FEATURES: set[str] = {"engagement_decile_in_course", "first_score"}


def _load_query(filename: str, conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Read a BQ query from sql/queries/ and return its result set.

    Rows are pinned to a canonical order because DuckDB's parallel
    execution does not guarantee it. Order matters here in two ways:
    bootstrap resampling draws by index, and floating-point summation
    is not associative: without a fixed order, repeated runs would
    produce slightly different (non-reproducible) exported numbers.
    """
    sql: str = (QUERIES_DIR / filename).read_text(encoding="utf-8")
    df: pd.DataFrame = execute_query(sql, conn=conn)
    return df.sort_values(
        ["id_student", "code_module", "code_presentation"]
    ).reset_index(drop=True)


def _t_test_or_none(
    group1: pd.Series,
    group2: pd.Series,
    name: str,
) -> TestResult | None:
    """Run a t-test, returning None instead of raising on degenerate input.

    The wrapper raises when a group has fewer than 2 finite values, which
    can happen on the synthetic sample (few submitters). The pipeline must
    not crash on the sample: the variable is skipped with a warning, and
    the correction family then covers only the tests actually run.
    """
    try:
        return independent_t_test(group1, group2, variable_name=name)
    except ValueError as exc:
        logger.warning("Skipping t-test %s: %s", name, exc)
        return None


def _bq2_signal_tests(df: pd.DataFrame) -> pd.DataFrame:
    """Welch t-tests on the 8 BQ2 signals, with Bonferroni and BH.

    Mirrors notebook 04 sections 4-5: group1 = completed, group2 = not
    completed, so a positive Cohen's d means completers score higher.
    """
    completed: pd.DataFrame = df[df["completed"] == 1]
    not_completed: pd.DataFrame = df[df["completed"] == 0]

    rows: list[dict] = []
    for col in SIGNAL_COLUMNS:
        g1: pd.Series = completed[col].dropna()
        g2: pd.Series = not_completed[col].dropna()
        result: TestResult | None = _t_test_or_none(g1, g2, col)
        if result is None:
            continue
        rows.append(
            {
                "signal": col,
                "n_completed": result.n_group1,
                "n_not_completed": result.n_group2,
                "mean_completed": float(g1.mean()),
                "mean_not_completed": float(g2.mean()),
                "t_statistic": result.statistic,
                "p_value": result.p_value,
                "cohens_d": result.effect_size,
                "ci_lower": result.ci_lower,
                "ci_upper": result.ci_upper,
            }
        )

    out: pd.DataFrame = pd.DataFrame(rows)
    if out.empty:
        return out

    raw_p: list[float] = out["p_value"].tolist()
    out["p_bonferroni"] = apply_multiple_comparison_correction(raw_p, "bonferroni")
    out["p_bh"] = apply_multiple_comparison_correction(raw_p, "benjamini-hochberg")
    out["significant_bonferroni"] = out["p_bonferroni"] < ALPHA
    out["significant_bh"] = out["p_bh"] < ALPHA

    # Rank by |d|: with ~32K enrollments nearly everything is significant,
    # so effect size, not p-value, is the ordering that matters downstream.
    out = out.sort_values(
        "cohens_d", key=lambda s: s.abs(), ascending=False
    ).reset_index(drop=True)
    return out[
        [
            "signal",
            "n_completed",
            "n_not_completed",
            "mean_completed",
            "mean_not_completed",
            "t_statistic",
            "p_value",
            "p_bonferroni",
            "p_bh",
            "significant_bonferroni",
            "significant_bh",
            "cohens_d",
            "ci_lower",
            "ci_upper",
        ]
    ]


def _bq2_ghost_segments(df: pd.DataFrame) -> pd.DataFrame:
    """Ghost vs active completion rates with 95% bootstrap CIs.

    Mirrors notebook 04 section 9. Ghost = zero VLE activity in the first
    28 days (the BQ2 query COALESCEs missing activity to 0). Bootstrap is
    used because the ghost completion rate sits near the [0, 1] boundary,
    where parametric CI assumptions are weakest.
    """
    is_ghost: pd.Series = df["active_days_first_28"] == 0

    rows: list[dict] = []
    for segment, mask in (("ghost", is_ghost), ("active", ~is_ghost)):
        outcomes: pd.Series = df.loc[mask, "completed"]
        if len(outcomes) == 0:
            logger.warning("Skipping segment '%s': no enrollments", segment)
            continue
        ci_low, ci_up = bootstrap_ci(
            outcomes, statistic_fn=np.mean, n_bootstrap=N_BOOTSTRAP
        )
        rows.append(
            {
                "segment": segment,
                "n_enrollments": int(len(outcomes)),
                "completion_rate": float(outcomes.mean()),
                "ci_lower_95": ci_low,
                "ci_upper_95": ci_up,
            }
        )
    return pd.DataFrame(rows)


def _bq3_demographic_tests(df: pd.DataFrame) -> pd.DataFrame:
    """Chi-square (categorical) and t-tests (numeric) on demographics.

    Mirrors notebook 05 Part A: one BH family across all 8 demographic
    tests, chi-square and t-test together. NULLs are dropped per variable
    (imd_band has missing values in the source data).
    """
    rows: list[dict] = []
    for col in DEMO_CATEGORICAL:
        valid: pd.DataFrame = df[[col, "completed"]].dropna()
        contingency: pd.DataFrame = pd.crosstab(valid[col], valid["completed"])
        try:
            result: TestResult = chi_square_test(contingency, variable_name=col)
        except ValueError as exc:
            logger.warning("Skipping chi-square %s: %s", col, exc)
            continue
        rows.append(
            {
                "feature": col,
                "test": "chi-square",
                "n": result.n_group1,
                "n_categories": contingency.shape[0],
                "statistic": result.statistic,
                "p_value": result.p_value,
                # Cramér's V is non-negative by construction, so the
                # signed and absolute columns coincide for chi-square rows.
                "effect_size": result.effect_size,
                "abs_effect_size": result.effect_size,
                "effect_size_name": result.effect_size_name,
            }
        )

    completed: pd.DataFrame = df[df["completed"] == 1]
    not_completed: pd.DataFrame = df[df["completed"] == 0]
    for col in DEMO_NUMERIC:
        t_result: TestResult | None = _t_test_or_none(
            completed[col].dropna(), not_completed[col].dropna(), col
        )
        if t_result is None:
            continue
        rows.append(
            {
                "feature": col,
                "test": "t-test",
                "n": t_result.n_group1 + t_result.n_group2,
                "n_categories": np.nan,
                "statistic": t_result.statistic,
                "p_value": t_result.p_value,
                "effect_size": t_result.effect_size,
                "abs_effect_size": abs(t_result.effect_size),
                "effect_size_name": t_result.effect_size_name,
            }
        )

    out: pd.DataFrame = pd.DataFrame(rows)
    if out.empty:
        return out

    out["p_bh"] = apply_multiple_comparison_correction(
        out["p_value"].tolist(), "benjamini-hochberg"
    )
    out["significant_bh"] = out["p_bh"] < ALPHA
    return out.sort_values("abs_effect_size", ascending=False).reset_index(drop=True)


def _bq3_behavioral_tests(df: pd.DataFrame) -> pd.DataFrame:
    """Welch t-tests on the 6 BQ3 behavioral features, with BH.

    Mirrors notebook 05 Part B. Conditional features (engagement decile,
    first score) are tested on reduced populations and flagged as such.
    """
    completed: pd.DataFrame = df[df["completed"] == 1]
    not_completed: pd.DataFrame = df[df["completed"] == 0]

    rows: list[dict] = []
    for col in BEHAV_COLUMNS:
        result: TestResult | None = _t_test_or_none(
            completed[col].dropna(), not_completed[col].dropna(), col
        )
        if result is None:
            continue
        rows.append(
            {
                "feature": col,
                "conditional_population": col in CONDITIONAL_FEATURES,
                "n_completed": result.n_group1,
                "n_not_completed": result.n_group2,
                "t_statistic": result.statistic,
                "p_value": result.p_value,
                "cohens_d": result.effect_size,
                "abs_cohens_d": abs(result.effect_size),
                "ci_lower": result.ci_lower,
                "ci_upper": result.ci_upper,
            }
        )

    out: pd.DataFrame = pd.DataFrame(rows)
    if out.empty:
        return out

    out["p_bh"] = apply_multiple_comparison_correction(
        out["p_value"].tolist(), "benjamini-hochberg"
    )
    out["significant_bh"] = out["p_bh"] < ALPHA
    return out.sort_values("abs_cohens_d", ascending=False).reset_index(drop=True)


def compute_stats(
    conn: duckdb.DuckDBPyConnection | None = None,
    output_dir: Path | None = None,
) -> list[Path]:
    """Compute all BQ2/BQ3 statistical tests and export them to CSV.

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
        df_bq2: pd.DataFrame = _load_query("q_bq2_early_signals.sql", conn)
        df_bq3: pd.DataFrame = _load_query("q_bq3_demographics_vs_behavior.sql", conn)

        outputs: dict[str, pd.DataFrame] = {
            "stats_bq2_early_signals": _bq2_signal_tests(df_bq2),
            "stats_bq2_ghost_segments": _bq2_ghost_segments(df_bq2),
            "stats_bq3_demographics": _bq3_demographic_tests(df_bq3),
            "stats_bq3_behavior": _bq3_behavioral_tests(df_bq3),
        }

        for name, df in outputs.items():
            # An empty frame means every test in the family was skipped;
            # writing a header-only CSV would look like a valid artifact.
            if df.empty:
                logger.warning("No results for %s: file not written", name)
                continue
            exported.append(_export_dataframe(df, name, output_dir))

        logger.info("Stats export complete: %d files → %s", len(exported), output_dir)

    finally:
        if own_conn:
            conn.close()

    return exported
