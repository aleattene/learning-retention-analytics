"""Tests for step 04: statistical export invariants.

The stats step runs against the in-memory sample database. These tests
do not check specific statistical values (the synthetic sample has no
"correct" answer): they verify structural invariants that must hold on
ANY dataset, such as p-value ranges, correction monotonicity, CI
ordering, family membership, and bootstrap determinism (fixed seed).
"""

from pathlib import Path

import duckdb
import pandas as pd
import pytest

from src.pipeline.step_04_stats import (
    BEHAV_COLUMNS,
    CONDITIONAL_FEATURES,
    DEMO_CATEGORICAL,
    DEMO_NUMERIC,
    SIGNAL_COLUMNS,
    compute_stats,
)

# The synthetic sample makes some signals nearly constant within a group,
# so scipy warns about precision loss in the t-test moment calculation.
# Expected on sample data and absent on the real dataset: silenced here
# only, never in production code, where the same warning would be a
# genuine data-quality signal worth surfacing.
pytestmark = pytest.mark.filterwarnings(
    "ignore:Precision loss occurred in moment calculation:RuntimeWarning"
)

EXPECTED_FILES: list[str] = [
    "stats_bq2_early_signals.csv",
    "stats_bq2_ghost_segments.csv",
    "stats_bq3_demographics.csv",
    "stats_bq3_behavior.csv",
]


@pytest.fixture(scope="module")
def stats_dir(
    db_conn: duckdb.DuckDBPyConnection,
    tmp_path_factory: pytest.TempPathFactory,
) -> Path:
    """Run the stats export once for the whole module.

    Module-scoped because compute_stats() bootstraps 2000 resamples:
    running it once and sharing the output keeps the suite fast while
    every test still reads its own CSV independently.
    """
    out: Path = tmp_path_factory.mktemp("stats_export")
    compute_stats(conn=db_conn, output_dir=out)
    return out


def test_all_expected_files_created(stats_dir: Path) -> None:
    """All four stats artifacts must exist and be non-empty."""
    for filename in EXPECTED_FILES:
        path: Path = stats_dir / filename
        assert path.exists(), f"Missing stats export: {filename}"
        assert path.stat().st_size > 0, f"Empty stats export: {filename}"


def test_bq2_signals_families_and_ranges(stats_dir: Path) -> None:
    """BQ2 export covers the 8 signals with valid p-values and CIs."""
    df: pd.DataFrame = pd.read_csv(stats_dir / "stats_bq2_early_signals.csv")

    # The sample data must support all 8 tests: a silent skip here would
    # mean the published correction family (n=8) no longer matches.
    assert set(df["signal"]) == set(SIGNAL_COLUMNS)

    for col in ["p_value", "p_bonferroni", "p_bh"]:
        assert df[col].between(0, 1).all(), f"{col} out of [0, 1]"

    # Corrected p-values can never be smaller than the raw ones, and
    # Bonferroni is at least as conservative as Benjamini-Hochberg.
    assert (df["p_bonferroni"] >= df["p_value"]).all()
    assert (df["p_bh"] >= df["p_value"]).all()
    assert (df["p_bonferroni"] >= df["p_bh"]).all()

    # The CI is for the mean difference: it must bracket it.
    mean_diff: pd.Series = df["mean_completed"] - df["mean_not_completed"]
    assert (df["ci_lower"] <= mean_diff + 1e-9).all()
    assert (df["ci_upper"] >= mean_diff - 1e-9).all()

    # Export is ranked by |d| descending, the ordering the report uses.
    abs_d: pd.Series = df["cohens_d"].abs()
    assert abs_d.is_monotonic_decreasing


def test_bq2_ghost_segments_invariants(stats_dir: Path) -> None:
    """Ghost/active rates are valid proportions inside their own CIs."""
    df: pd.DataFrame = pd.read_csv(stats_dir / "stats_bq2_ghost_segments.csv")

    assert set(df["segment"]) == {"ghost", "active"}
    assert df["completion_rate"].between(0, 1).all()
    assert (df["ci_lower_95"] <= df["completion_rate"]).all()
    assert (df["ci_upper_95"] >= df["completion_rate"]).all()
    assert (df["n_enrollments"] > 0).all()


def test_bq3_demographics_families_and_tests(stats_dir: Path) -> None:
    """Demographic export pairs each feature with the right test type."""
    df: pd.DataFrame = pd.read_csv(stats_dir / "stats_bq3_demographics.csv")

    assert set(df["feature"]) == set(DEMO_CATEGORICAL + DEMO_NUMERIC)

    chi_rows: pd.DataFrame = df[df["test"] == "chi-square"]
    t_rows: pd.DataFrame = df[df["test"] == "t-test"]
    assert set(chi_rows["feature"]) == set(DEMO_CATEGORICAL)
    assert set(t_rows["feature"]) == set(DEMO_NUMERIC)

    # Cramér's V lives in [0, 1] by construction; a value outside means
    # the contingency table or the formula went wrong upstream.
    assert chi_rows["effect_size"].between(0, 1).all()
    assert (chi_rows["n_categories"] >= 2).all()

    assert df["p_value"].between(0, 1).all()
    assert (df["p_bh"] >= df["p_value"]).all()


def test_bq3_behavior_conditional_flags(stats_dir: Path) -> None:
    """Conditional-population features are flagged, and only those."""
    df: pd.DataFrame = pd.read_csv(stats_dir / "stats_bq3_behavior.csv")

    assert set(df["feature"]) == set(BEHAV_COLUMNS)

    flagged: set[str] = set(df[df["conditional_population"]]["feature"])
    assert flagged == CONDITIONAL_FEATURES

    assert df["p_value"].between(0, 1).all()
    assert (df["p_bh"] >= df["p_value"]).all()
    assert (df["abs_cohens_d"] == df["cohens_d"].abs()).all()


def test_stats_export_is_deterministic(
    db_conn: duckdb.DuckDBPyConnection,
    stats_dir: Path,
    tmp_path: Path,
) -> None:
    """Two runs produce byte-identical files.

    The bootstrap uses a fixed seed and the queries are deterministic,
    so any difference between runs would signal hidden nondeterminism,
    which would make the published numbers non-reproducible.
    """
    compute_stats(conn=db_conn, output_dir=tmp_path)

    for filename in EXPECTED_FILES:
        first: bytes = (stats_dir / filename).read_bytes()
        second: bytes = (tmp_path / filename).read_bytes()
        assert first == second, f"Non-deterministic export: {filename}"
