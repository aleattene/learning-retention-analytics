"""Statistical test wrappers — t-test, chi-square, effect sizes, confidence intervals.

These wrappers standardize the interface for all statistical tests used
in the project, ensuring consistent output format (test statistic, p-value,
effect size, confidence interval) regardless of the underlying scipy/statsmodels call.

All tests are two-sided unless explicitly noted. Effect sizes follow
standard conventions:
- Cohen's d for continuous comparisons (small=0.2, medium=0.5, large=0.8)
- Cramér's V for categorical associations (interpretation depends on df)

NO machine learning. This module is the statistical backbone of BQ2 and BQ3.
"""

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Standardized output for all statistical tests.

    Every test in this module returns a TestResult, making it easy
    to build comparison tables across multiple variables.
    """

    test_name: str
    statistic: float
    p_value: float
    effect_size: float
    effect_size_name: str
    ci_lower: float | None = None
    ci_upper: float | None = None
    n_group1: int = 0
    n_group2: int = 0


def independent_t_test(
    group1: pd.Series | np.ndarray,
    group2: pd.Series | np.ndarray,
    variable_name: str = "",
) -> TestResult:
    """Run an independent samples t-test with Cohen's d effect size.

    Used in BQ2 (early signals) to compare engagement metrics between
    students who completed vs dropped out, and in BQ3 to compare
    behavioral features across outcome groups.

    Parameters
    ----------
    group1, group2 : array-like
        The two groups to compare (e.g. completed vs not-completed).
    variable_name : str
        Label for logging and reporting.

    Returns
    -------
    TestResult
        Includes t-statistic, p-value, Cohen's d, and 95% CI for
        the difference in means.
    """
    # Drop NaN values — missing data should not influence the test
    g1: np.ndarray = np.asarray(group1, dtype=float)
    g2: np.ndarray = np.asarray(group2, dtype=float)
    g1 = g1[~np.isnan(g1)]
    g2 = g2[~np.isnan(g2)]

    # Guard: each group needs at least 2 values for a meaningful t-test.
    # With fewer than 2 values, variance (ddof=1) becomes NaN and the
    # test statistic would silently propagate NaN/inf through results.
    if len(g1) < 2 or len(g2) < 2:
        raise ValueError(
            f"Each group must have at least 2 finite values after dropping NaNs, "
            f"got group1={len(g1)}, group2={len(g2)}. "
            "Check that the input contains sufficient valid data."
        )

    # Welch's t-test (equal_var=False): does not assume equal variances,
    # which is safer for groups that may have very different sizes
    t_stat, p_val = stats.ttest_ind(g1, g2, equal_var=False)

    # Cohen's d: standardized mean difference
    # Uses pooled standard deviation as the denominator
    pooled_std: float = np.sqrt(
        ((len(g1) - 1) * np.var(g1, ddof=1) + (len(g2) - 1) * np.var(g2, ddof=1))
        / (len(g1) + len(g2) - 2)
    )
    cohens_d: float = (
        (np.mean(g1) - np.mean(g2)) / pooled_std if pooled_std > 0 else 0.0
    )

    # 95% CI for the difference in means using Welch-Satterthwaite
    # degrees of freedom — matches the Welch t-test above instead of
    # the normal approximation (z=1.96), which undercovers for small samples
    mean_diff: float = float(np.mean(g1) - np.mean(g2))
    s1_sq_n: float = np.var(g1, ddof=1) / len(g1)
    s2_sq_n: float = np.var(g2, ddof=1) / len(g2)
    se_diff: float = np.sqrt(s1_sq_n + s2_sq_n)

    # Welch-Satterthwaite approximation for effective degrees of freedom
    df_welch: float = (s1_sq_n + s2_sq_n) ** 2 / (
        s1_sq_n**2 / (len(g1) - 1) + s2_sq_n**2 / (len(g2) - 1)
    )
    t_crit: float = float(stats.t.ppf(0.975, df_welch))
    ci_lower: float = mean_diff - t_crit * se_diff
    ci_upper: float = mean_diff + t_crit * se_diff

    logger.debug(
        "t-test %s: t=%.3f, p=%.4f, d=%.3f", variable_name, t_stat, p_val, cohens_d
    )

    return TestResult(
        test_name=f"t-test: {variable_name}",
        statistic=float(t_stat),
        p_value=float(p_val),
        effect_size=float(cohens_d),
        effect_size_name="Cohen's d",
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        n_group1=len(g1),
        n_group2=len(g2),
    )


def chi_square_test(
    observed: pd.DataFrame | np.ndarray,
    variable_name: str = "",
) -> TestResult:
    """Run a chi-square test of independence with Cramér's V effect size.

    Used in BQ3 to test whether demographic categories (education level,
    age band, disability) are associated with completion outcome.

    Parameters
    ----------
    observed : DataFrame or 2D array
        Contingency table (e.g. from pd.crosstab). Rows = one variable,
        columns = the other.
    variable_name : str
        Label for logging and reporting.

    Returns
    -------
    TestResult
        Includes chi2 statistic, p-value, and Cramér's V.
    """
    if isinstance(observed, pd.DataFrame):
        observed = observed.values

    # Guard: chi-square requires at least a 2×2 contingency table.
    # A 1×N or N×1 table means one variable has a single category,
    # so there is no association to test (and scipy would raise).
    if observed.ndim != 2 or observed.shape[0] < 2 or observed.shape[1] < 2:
        raise ValueError(
            f"Contingency table must be at least 2×2, got {observed.shape}. "
            "A degenerate table means one variable has a single category — "
            "chi-square test is not applicable."
        )

    chi2, p_val, dof, _ = stats.chi2_contingency(observed)

    # Cramér's V: effect size for chi-square
    # Ranges from 0 (no association) to 1 (perfect association)
    # k = min(rows, cols) — the smaller dimension of the contingency table
    n: int = int(observed.sum())
    k: int = min(observed.shape) - 1
    cramers_v: float = np.sqrt(chi2 / (n * k)) if (n * k) > 0 else 0.0

    logger.debug(
        "chi2 %s: χ²=%.3f, p=%.4f, V=%.3f, dof=%d",
        variable_name,
        chi2,
        p_val,
        cramers_v,
        dof,
    )

    return TestResult(
        test_name=f"chi-square: {variable_name}",
        statistic=float(chi2),
        p_value=float(p_val),
        effect_size=float(cramers_v),
        effect_size_name="Cramér's V",
        n_group1=n,
        n_group2=0,
    )


def apply_multiple_comparison_correction(
    p_values: list[float],
    method: str = "bonferroni",
) -> list[float]:
    """Correct p-values for multiple comparisons.

    When testing many variables at once (e.g. 10 engagement metrics in BQ2),
    the risk of false positives increases. This function adjusts p-values
    to control the family-wise error rate (Bonferroni) or the false
    discovery rate (Benjamini-Hochberg).

    Parameters
    ----------
    p_values : list[float]
        Raw p-values from individual tests.
    method : str
        "bonferroni" (conservative, controls FWER) or
        "benjamini-hochberg" (less conservative, controls FDR).

    Returns
    -------
    list[float]
        Adjusted p-values, capped at 1.0.
    """
    n: int = len(p_values)
    if n == 0:
        return []

    if method == "bonferroni":
        # Simply multiply each p-value by the number of tests
        return [min(p * n, 1.0) for p in p_values]

    if method == "benjamini-hochberg":
        # BH procedure: rank p-values, adjust by rank position
        # This is less conservative than Bonferroni and preferred
        # when testing many variables (>10)
        sorted_indices: list[int] = sorted(range(n), key=lambda i: p_values[i])
        adjusted: list[float] = [0.0] * n

        for rank, idx in enumerate(sorted_indices, start=1):
            adjusted[idx] = min(p_values[idx] * n / rank, 1.0)

        # Enforce monotonicity: adjusted p-values must be non-decreasing
        # when sorted by original p-value ranking
        for i in range(n - 2, -1, -1):
            idx = sorted_indices[i]
            next_idx = sorted_indices[i + 1]
            adjusted[idx] = min(adjusted[idx], adjusted[next_idx])

        return adjusted

    raise ValueError(f"Unknown correction method: {method}")


def bootstrap_ci(
    data: pd.Series | np.ndarray,
    statistic_fn=np.mean,
    n_bootstrap: int = 1000,
    confidence: float = 0.95,
    seed: int = 42,
) -> tuple[float, float]:
    """Compute a bootstrap confidence interval for any statistic.

    Non-parametric approach: resamples the data with replacement and
    computes the statistic on each resample. The CI is derived from
    the percentiles of the bootstrap distribution.

    Used when the sampling distribution of a statistic is unknown
    or when sample sizes are small.

    Parameters
    ----------
    data : array-like
        Input data.
    statistic_fn : callable
        Function to compute (default: np.mean).
    n_bootstrap : int
        Number of bootstrap resamples.
    confidence : float
        Confidence level (default: 0.95 for 95% CI).
    seed : int
        Random seed for reproducibility.

    Returns
    -------
    tuple[float, float]
        (lower_bound, upper_bound) of the confidence interval.
    """
    rng = np.random.default_rng(seed)
    arr: np.ndarray = np.asarray(data, dtype=float)
    arr = arr[~np.isnan(arr)]

    # Guard: bootstrap requires at least one finite value to resample from.
    # An empty array (all NaN or empty input) would produce a (nan, nan)
    # interval silently — better to fail explicitly.
    if len(arr) == 0:
        raise ValueError(
            "Cannot compute bootstrap CI: no finite values remain after "
            "dropping NaNs. Check that the input contains valid data."
        )

    # Generate bootstrap distribution by resampling with replacement
    boot_stats: np.ndarray = np.array(
        [
            statistic_fn(rng.choice(arr, size=len(arr), replace=True))
            for _ in range(n_bootstrap)
        ]
    )

    # Percentile method: simple and robust for most use cases
    alpha: float = (1 - confidence) / 2
    lower: float = float(np.percentile(boot_stats, 100 * alpha))
    upper: float = float(np.percentile(boot_stats, 100 * (1 - alpha)))

    return lower, upper
