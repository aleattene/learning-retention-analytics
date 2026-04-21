"""Stress tests and random tests for src/stats/tests.py.

Pushes the statistical wrappers to their limits: extreme values,
degenerate distributions, massive NaN arrays, boundary conditions,
and randomized property-based testing with multiple seeds.
"""

import math

import numpy as np
import pandas as pd
import pytest

from src.stats.tests import (
    TestResult,
    apply_multiple_comparison_correction,
    bootstrap_ci,
    chi_square_test,
    independent_t_test,
)

# ===================================================================
# independent_t_test — stress & edge cases
# ===================================================================


@pytest.mark.filterwarnings(
    "ignore:Precision loss occurred in moment calculation:RuntimeWarning"
)
class TestTTestZeroVariance:
    """Zero-variance groups: the Copilot-flagged edge case.

    scipy.stats.ttest_ind emits a RuntimeWarning when both groups are
    constant (catastrophic cancellation in moment calculation). This is
    expected — our code handles the degenerate case in the pooled_std
    and se_diff guards before using scipy's result.
    """

    def test_zero_variance_different_means_returns_inf(self) -> None:
        """Constant groups with different means → Cohen's d = ±inf."""
        g1: np.ndarray = np.array([5.0, 5.0, 5.0, 5.0, 5.0])
        g2: np.ndarray = np.array([3.0, 3.0, 3.0, 3.0, 3.0])
        result: TestResult = independent_t_test(g1, g2, "zero_var_diff")

        assert math.isinf(result.effect_size)
        assert result.effect_size > 0  # g1 > g2 → positive

    def test_zero_variance_same_means_returns_zero(self) -> None:
        """Constant groups with identical means → Cohen's d = 0."""
        g: np.ndarray = np.array([7.0, 7.0, 7.0, 7.0])
        result: TestResult = independent_t_test(g, g, "zero_var_same")
        assert np.isclose(result.effect_size, 0.0)

    def test_zero_variance_ci_collapses_to_point(self) -> None:
        """With zero variance, CI should equal [mean_diff, mean_diff]."""
        g1: np.ndarray = np.array([10.0, 10.0, 10.0])
        g2: np.ndarray = np.array([4.0, 4.0, 4.0])
        result: TestResult = independent_t_test(g1, g2, "zero_var_ci")

        assert np.isclose(result.ci_lower, 6.0)
        assert np.isclose(result.ci_upper, 6.0)

    def test_zero_variance_negative_direction(self) -> None:
        """g1 < g2 with zero variance → negative inf Cohen's d."""
        g1: np.ndarray = np.array([1.0, 1.0, 1.0])
        g2: np.ndarray = np.array([9.0, 9.0, 9.0])
        result: TestResult = independent_t_test(g1, g2, "neg_inf")

        assert math.isinf(result.effect_size)
        assert result.effect_size < 0


class TestTTestExtremeValues:
    """Extreme numeric ranges and edge conditions."""

    def test_very_large_values(self) -> None:
        """Should handle large values without overflow.

        We use 1e10 rather than truly extreme magnitudes (e.g. 1e150)
        because float64 cannot distinguish adjacent integers at those
        scales (big + 1 == big).  At 1e10 the +1 spacing is still
        representable, so the two groups remain genuinely distinct.
        """
        big: float = 1e10
        g1: np.ndarray = np.array([big, big + 1, big + 2, big + 3, big + 4])
        g2: np.ndarray = np.array(
            [big + 100, big + 101, big + 102, big + 103, big + 104]
        )
        result: TestResult = independent_t_test(g1, g2, "large")
        assert np.isfinite(result.statistic)
        assert np.isfinite(result.p_value)

    def test_very_small_values(self) -> None:
        """Should handle very small but distinguishable values."""
        # 1e-15 is small but well above denormalized-float territory,
        # so variance and standard error remain numerically stable
        eps: float = 1e-15
        g1: np.ndarray = np.array([eps, eps * 2, eps * 3, eps * 4, eps * 5])
        g2: np.ndarray = np.array([eps * 10, eps * 11, eps * 12, eps * 13, eps * 14])
        result: TestResult = independent_t_test(g1, g2, "tiny")
        assert np.isfinite(result.statistic)

    def test_mixed_positive_negative(self) -> None:
        """Groups spanning positive and negative values."""
        g1: np.ndarray = np.array([-100.0, -50.0, 0.0, 50.0, 100.0])
        g2: np.ndarray = np.array([200.0, 250.0, 300.0, 350.0, 400.0])
        result: TestResult = independent_t_test(g1, g2, "mixed")
        assert result.effect_size < 0  # g1 mean < g2 mean
        assert result.ci_lower < result.ci_upper

    def test_single_outlier_group(self) -> None:
        """One group with a massive outlier — should not crash."""
        g1: np.ndarray = np.array([1.0, 2.0, 3.0, 4.0, 1e10])
        g2: np.ndarray = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        result: TestResult = independent_t_test(g1, g2, "outlier")
        assert np.isfinite(result.p_value)


class TestTTestNaNStress:
    """Aggressive NaN patterns."""

    def test_mostly_nan_still_works(self) -> None:
        """Groups where most values are NaN but enough survive."""
        g1: np.ndarray = np.array([np.nan] * 50 + [1.0, 2.0, 3.0])
        g2: np.ndarray = np.array([np.nan] * 50 + [4.0, 5.0, 6.0])
        result: TestResult = independent_t_test(g1, g2, "mostly_nan")
        assert result.n_group1 == 3
        assert result.n_group2 == 3

    def test_all_nan_one_group_raises(self) -> None:
        """All-NaN group should raise ValueError (< 2 finite values)."""
        g1: np.ndarray = np.full(10, np.nan)
        g2: np.ndarray = np.array([1.0, 2.0, 3.0])
        with pytest.raises(ValueError, match="at least 2 finite values"):
            independent_t_test(g1, g2, "all_nan")

    def test_exactly_two_values_after_nan_drop(self) -> None:
        """Minimum viable group size (exactly 2) should work."""
        g1: np.ndarray = np.array([np.nan, 1.0, 2.0, np.nan])
        g2: np.ndarray = np.array([np.nan, 5.0, 6.0, np.nan])
        result: TestResult = independent_t_test(g1, g2, "min_size")
        assert result.n_group1 == 2
        assert result.n_group2 == 2


class TestTTestAsymmetricGroups:
    """Very unbalanced group sizes."""

    def test_highly_unbalanced_groups(self) -> None:
        """One group much larger — Welch's t-test should handle this."""
        rng = np.random.default_rng(42)
        g1: np.ndarray = rng.normal(10, 2, size=5)
        g2: np.ndarray = rng.normal(10, 2, size=500)
        result: TestResult = independent_t_test(g1, g2, "unbalanced")
        assert result.n_group1 == 5
        assert result.n_group2 == 500
        assert np.isfinite(result.statistic)

    def test_two_vs_thousand(self) -> None:
        """Extreme imbalance: 2 vs 1000."""
        rng = np.random.default_rng(99)
        g1: np.ndarray = rng.normal(0, 1, size=2)
        g2: np.ndarray = rng.normal(0, 1, size=1000)
        result: TestResult = independent_t_test(g1, g2, "2v1000")
        assert np.isfinite(result.p_value)
        assert result.ci_lower < result.ci_upper


class TestTTestPandasInput:
    """Verify that pd.Series input works (not just np.ndarray)."""

    def test_pandas_series_input(self) -> None:
        """pd.Series should be accepted as group input."""
        s1: pd.Series = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        s2: pd.Series = pd.Series([6.0, 7.0, 8.0, 9.0, 10.0])
        result: TestResult = independent_t_test(s1, s2, "pandas")
        assert result.n_group1 == 5
        assert result.p_value < 0.05

    def test_pandas_series_with_nan(self) -> None:
        """pd.Series with NaN should be handled like np.ndarray."""
        s1: pd.Series = pd.Series([1.0, np.nan, 3.0, 4.0])
        s2: pd.Series = pd.Series([10.0, 11.0, np.nan, 13.0])
        result: TestResult = independent_t_test(s1, s2, "pd_nan")
        assert result.n_group1 == 3
        assert result.n_group2 == 3


class TestTTestRandomized:
    """Property-based random tests with multiple seeds.

    These tests verify statistical invariants that should hold
    regardless of the specific random data generated.
    """

    @pytest.mark.parametrize("seed", range(10))
    def test_p_value_always_between_0_and_1(self, seed: int) -> None:
        """p-value must be in [0, 1] for any random input."""
        rng = np.random.default_rng(seed)
        g1: np.ndarray = rng.normal(
            rng.uniform(-100, 100), rng.uniform(0.1, 50), size=rng.integers(5, 200)
        )
        g2: np.ndarray = rng.normal(
            rng.uniform(-100, 100), rng.uniform(0.1, 50), size=rng.integers(5, 200)
        )
        result: TestResult = independent_t_test(g1, g2, f"random_{seed}")
        assert 0 <= result.p_value <= 1

    @pytest.mark.parametrize("seed", range(10))
    def test_ci_lower_leq_upper(self, seed: int) -> None:
        """CI lower bound must always be <= upper bound."""
        rng = np.random.default_rng(seed + 100)
        g1: np.ndarray = rng.normal(0, 1, size=rng.integers(3, 100))
        g2: np.ndarray = rng.normal(0, 1, size=rng.integers(3, 100))
        result: TestResult = independent_t_test(g1, g2, f"ci_rand_{seed}")
        assert result.ci_lower <= result.ci_upper

    @pytest.mark.parametrize("seed", range(10))
    def test_identical_groups_nonsignificant(self, seed: int) -> None:
        """Passing the same array as both groups → p should be ~1."""
        rng = np.random.default_rng(seed + 200)
        data: np.ndarray = rng.normal(0, 1, size=rng.integers(10, 200))
        result: TestResult = independent_t_test(data, data, f"same_{seed}")
        assert result.p_value > 0.9
        assert abs(result.effect_size) < 0.01

    @pytest.mark.parametrize("seed", range(10))
    def test_effect_size_sign_matches_mean_diff(self, seed: int) -> None:
        """Cohen's d sign should match the sign of mean(g1) - mean(g2)."""
        rng = np.random.default_rng(seed + 300)
        g1: np.ndarray = rng.normal(rng.uniform(-50, 50), 5, size=50)
        g2: np.ndarray = rng.normal(rng.uniform(-50, 50), 5, size=50)
        result: TestResult = independent_t_test(g1, g2, f"sign_{seed}")
        mean_diff: float = float(np.mean(g1) - np.mean(g2))
        if abs(mean_diff) > 1e-10:
            assert np.sign(result.effect_size) == np.sign(mean_diff)


# ===================================================================
# chi_square_test — stress & edge cases
# ===================================================================


class TestChiSquareStress:
    """Edge cases and stress tests for chi-square wrapper."""

    def test_large_contingency_table(self) -> None:
        """Should handle large tables (10×10)."""
        rng = np.random.default_rng(42)
        observed: np.ndarray = rng.integers(10, 100, size=(10, 10))
        result: TestResult = chi_square_test(observed, "large_table")
        assert np.isfinite(result.statistic)
        assert 0 <= result.p_value <= 1
        assert 0 <= result.effect_size <= 1

    def test_very_sparse_table(self) -> None:
        """Table with small counts — should still compute.

        Fully-zero expected cells make scipy raise, so we use a table
        that is sparse (low counts, strong association) but has no
        structural zeros in the expected-frequency matrix.
        """
        observed: np.ndarray = np.array([[95, 5], [5, 95]])
        result: TestResult = chi_square_test(observed, "sparse")
        assert result.p_value < 0.01

    def test_single_row_raises(self) -> None:
        """1×N table (one variable has single category) should raise."""
        observed: np.ndarray = np.array([[10, 20, 30]])
        with pytest.raises(ValueError, match="at least 2×2"):
            chi_square_test(observed, "single_row")

    def test_single_column_raises(self) -> None:
        """N×1 table should raise."""
        observed: np.ndarray = np.array([[10], [20], [30]])
        with pytest.raises(ValueError, match="at least 2×2"):
            chi_square_test(observed, "single_col")

    def test_1d_array_raises(self) -> None:
        """1D array is not a contingency table — should raise."""
        with pytest.raises(ValueError, match="at least 2×2"):
            chi_square_test(np.array([10, 20, 30]), "1d")

    def test_minimal_2x2_table(self) -> None:
        """Smallest valid table (2×2) should work."""
        observed: np.ndarray = np.array([[5, 5], [5, 5]])
        result: TestResult = chi_square_test(observed, "minimal")
        assert result.p_value > 0.9
        assert result.effect_size < 0.05

    def test_asymmetric_table_3x5(self) -> None:
        """Non-square table should compute correctly."""
        rng = np.random.default_rng(77)
        observed: np.ndarray = rng.integers(5, 50, size=(3, 5))
        result: TestResult = chi_square_test(observed, "3x5")
        assert np.isfinite(result.statistic)

    def test_very_large_counts(self) -> None:
        """Large cell counts should not cause overflow."""
        observed: np.ndarray = np.array([[10**6, 10**6], [10**6, 10**6]])
        result: TestResult = chi_square_test(observed, "big_counts")
        assert np.isfinite(result.statistic)

    @pytest.mark.parametrize("seed", range(10))
    def test_cramers_v_between_0_and_1(self, seed: int) -> None:
        """Cramér's V must be in [0, 1] for any random input."""
        rng = np.random.default_rng(seed + 500)
        rows: int = rng.integers(2, 8)
        cols: int = rng.integers(2, 8)
        observed: np.ndarray = rng.integers(1, 100, size=(rows, cols))
        result: TestResult = chi_square_test(observed, f"rand_chi_{seed}")
        assert 0 <= result.effect_size <= 1


# ===================================================================
# apply_multiple_comparison_correction — stress
# ===================================================================


class TestMultipleComparisonStress:
    """Edge cases for p-value correction methods."""

    def test_single_p_value_bonferroni(self) -> None:
        """With one test, Bonferroni should return the same p-value."""
        assert apply_multiple_comparison_correction([0.03], "bonferroni") == [0.03]

    def test_single_p_value_bh(self) -> None:
        """With one test, BH should return the same p-value."""
        result: list[float] = apply_multiple_comparison_correction(
            [0.03], "benjamini-hochberg"
        )
        assert np.isclose(result[0], 0.03)

    def test_all_p_values_zero(self) -> None:
        """All p=0 should remain 0 after correction."""
        corrected: list[float] = apply_multiple_comparison_correction(
            [0.0, 0.0, 0.0], "bonferroni"
        )
        assert corrected == [0.0, 0.0, 0.0]

    def test_all_p_values_one(self) -> None:
        """All p=1 should remain 1 after correction (capped)."""
        corrected: list[float] = apply_multiple_comparison_correction(
            [1.0, 1.0], "bonferroni"
        )
        assert corrected == [1.0, 1.0]

    def test_many_tests_bonferroni(self) -> None:
        """100 tests: small p-values should be inflated to ≤1."""
        p_values: list[float] = [0.001 * i for i in range(1, 101)]
        corrected: list[float] = apply_multiple_comparison_correction(
            p_values, "bonferroni"
        )
        assert all(0 <= p <= 1.0 for p in corrected)

    def test_bh_monotonicity(self) -> None:
        """BH-adjusted p-values should be non-decreasing when sorted by raw p."""
        rng = np.random.default_rng(42)
        p_values: list[float] = sorted(rng.uniform(0, 0.1, size=50).tolist())
        corrected: list[float] = apply_multiple_comparison_correction(
            p_values, "benjamini-hochberg"
        )
        # Corrected should be non-decreasing (because raw input is sorted)
        for i in range(len(corrected) - 1):
            assert corrected[i] <= corrected[i + 1] + 1e-15

    def test_bh_always_leq_bonferroni(self) -> None:
        """BH should never be more conservative than Bonferroni."""
        rng = np.random.default_rng(77)
        p_values: list[float] = rng.uniform(0, 0.05, size=20).tolist()
        bonf: list[float] = apply_multiple_comparison_correction(p_values, "bonferroni")
        bh: list[float] = apply_multiple_comparison_correction(
            p_values, "benjamini-hochberg"
        )
        for b, h in zip(bonf, bh):
            assert h <= b + 1e-15

    @pytest.mark.parametrize("seed", range(10))
    def test_corrected_p_values_always_valid(self, seed: int) -> None:
        """Corrected p-values must be in [0, 1] regardless of input."""
        rng = np.random.default_rng(seed + 600)
        n: int = rng.integers(1, 50)
        p_values: list[float] = rng.uniform(0, 1, size=n).tolist()
        for method in ["bonferroni", "benjamini-hochberg"]:
            corrected: list[float] = apply_multiple_comparison_correction(
                p_values, method
            )
            assert all(0 <= p <= 1.0 for p in corrected)


# ===================================================================
# bootstrap_ci — stress & edge cases
# ===================================================================


class TestBootstrapStress:
    """Edge cases and random tests for bootstrap CI."""

    def test_single_value_array(self) -> None:
        """Array with one unique value → CI should collapse to that value."""
        data: np.ndarray = np.array([42.0])
        lower, upper = bootstrap_ci(data)
        assert np.isclose(lower, 42.0)
        assert np.isclose(upper, 42.0)

    def test_constant_array(self) -> None:
        """All identical values → CI should collapse to that value."""
        data: np.ndarray = np.full(100, 7.0)
        lower, upper = bootstrap_ci(data)
        assert np.isclose(lower, 7.0)
        assert np.isclose(upper, 7.0)

    def test_two_values(self) -> None:
        """Array with exactly 2 values should produce a valid CI."""
        data: np.ndarray = np.array([1.0, 100.0])
        lower, upper = bootstrap_ci(data)
        assert lower <= upper

    @pytest.mark.parametrize("bad_confidence", [0.0, 1.0, -0.5, 1.5])
    def test_invalid_confidence_raises(self, bad_confidence: float) -> None:
        """Confidence outside (0, 1) should raise ValueError."""
        data: np.ndarray = np.array([1.0, 2.0, 3.0])
        with pytest.raises(ValueError, match="confidence must be between"):
            bootstrap_ci(data, confidence=bad_confidence)

    @pytest.mark.parametrize("bad_n", [0, -1, -100])
    def test_invalid_n_bootstrap_raises(self, bad_n: int) -> None:
        """Non-positive n_bootstrap should raise ValueError."""
        data: np.ndarray = np.array([1.0, 2.0, 3.0])
        with pytest.raises(ValueError, match="n_bootstrap must be a positive"):
            bootstrap_ci(data, n_bootstrap=bad_n)

    def test_empty_after_nan_drop_raises(self) -> None:
        """All-NaN input should raise ValueError."""
        with pytest.raises(ValueError, match="no finite values"):
            bootstrap_ci(np.array([np.nan, np.nan, np.nan]))

    def test_empty_array_raises(self) -> None:
        """Empty array should raise ValueError."""
        with pytest.raises(ValueError, match="no finite values"):
            bootstrap_ci(np.array([]))

    def test_large_array_performance(self) -> None:
        """Should handle 10k values without issue."""
        rng = np.random.default_rng(42)
        data: np.ndarray = rng.normal(0, 1, size=10_000)
        lower, upper = bootstrap_ci(data, n_bootstrap=500)
        assert lower < 0 < upper  # True mean is 0

    def test_custom_statistic_median(self) -> None:
        """Should work with np.median as statistic function."""
        rng = np.random.default_rng(42)
        data: np.ndarray = rng.normal(5, 1, size=200)
        lower, upper = bootstrap_ci(data, statistic_fn=np.median)
        assert lower < 5.5
        assert upper > 4.5

    def test_high_confidence_wider_than_low(self) -> None:
        """99% CI should be wider than 90% CI."""
        rng = np.random.default_rng(42)
        data: np.ndarray = rng.normal(0, 1, size=100)
        l90, u90 = bootstrap_ci(data, confidence=0.90)
        l99, u99 = bootstrap_ci(data, confidence=0.99)
        assert (u99 - l99) > (u90 - l90)

    @pytest.mark.parametrize("seed", range(10))
    def test_ci_lower_leq_upper_random(self, seed: int) -> None:
        """CI lower bound must always be <= upper bound."""
        rng = np.random.default_rng(seed + 700)
        size: int = rng.integers(5, 500)
        data: np.ndarray = rng.normal(
            rng.uniform(-100, 100), rng.uniform(0.1, 50), size=size
        )
        lower, upper = bootstrap_ci(data, seed=seed)
        assert lower <= upper

    def test_different_seeds_different_results(self) -> None:
        """Different seeds should (almost always) produce different CIs."""
        data: np.ndarray = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])
        ci1 = bootstrap_ci(data, seed=1)
        ci2 = bootstrap_ci(data, seed=2)
        # Extremely unlikely to be exactly equal with different seeds
        assert ci1 != ci2

    def test_pandas_series_input(self) -> None:
        """pd.Series should be accepted."""
        s: pd.Series = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        lower, upper = bootstrap_ci(s)
        assert lower <= upper
