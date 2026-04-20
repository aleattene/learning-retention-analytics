"""Tests for statistical test wrappers.

Validates that t-test, chi-square, effect sizes, bootstrap CI,
and multiple comparison corrections produce correct results
on known inputs.
"""

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


class TestIndependentTTest:
    """Tests for the t-test wrapper."""

    def test_identical_groups_no_difference(self) -> None:
        """Two identical groups should have p ≈ 1 and Cohen's d ≈ 0."""
        data: np.ndarray = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        result: TestResult = independent_t_test(data, data, "identical")
        assert result.p_value > 0.9
        assert abs(result.effect_size) < 0.01

    def test_different_groups_significant(self) -> None:
        """Two clearly different groups should have small p-value and large d."""
        g1: np.ndarray = np.array([10.0, 11.0, 12.0, 13.0, 14.0] * 10)
        g2: np.ndarray = np.array([1.0, 2.0, 3.0, 4.0, 5.0] * 10)
        result: TestResult = independent_t_test(g1, g2, "different")
        assert result.p_value < 0.001
        assert result.effect_size > 2.0  # Very large effect

    def test_returns_test_result_dataclass(self) -> None:
        """Output should be a TestResult with all required fields."""
        g1: np.ndarray = np.array([1.0, 2.0, 3.0])
        g2: np.ndarray = np.array([4.0, 5.0, 6.0])
        result: TestResult = independent_t_test(g1, g2, "test")
        assert result.test_name == "t-test: test"
        assert result.effect_size_name == "Cohen's d"
        assert result.ci_lower is not None
        assert result.ci_upper is not None
        assert result.n_group1 == 3
        assert result.n_group2 == 3

    def test_handles_nan_values(self) -> None:
        """NaN values should be dropped before computing the test."""
        g1: np.ndarray = np.array([1.0, 2.0, np.nan, 4.0, 5.0])
        g2: np.ndarray = np.array([6.0, 7.0, 8.0, np.nan, 10.0])
        result: TestResult = independent_t_test(g1, g2, "nan_test")
        # Should use 4 values per group (NaN dropped)
        assert result.n_group1 == 4
        assert result.n_group2 == 4

    def test_raises_on_insufficient_values_after_nan_drop(self) -> None:
        """Groups with fewer than 2 finite values should raise ValueError."""
        g1: np.ndarray = np.array([1.0])
        g2: np.ndarray = np.array([2.0, 3.0, 4.0])
        with pytest.raises(ValueError, match="at least 2 finite values"):
            independent_t_test(g1, g2, "too_small")

        # All-NaN group should also trigger the guard
        g_all_nan: np.ndarray = np.array([np.nan, np.nan])
        with pytest.raises(ValueError, match="at least 2 finite values"):
            independent_t_test(g_all_nan, g2, "all_nan")

    def test_confidence_interval_contains_mean_diff(self) -> None:
        """The 95% CI should contain the observed mean difference."""
        rng = np.random.default_rng(42)
        g1: np.ndarray = rng.normal(loc=10, scale=2, size=100)
        g2: np.ndarray = rng.normal(loc=8, scale=2, size=100)
        result: TestResult = independent_t_test(g1, g2, "ci_test")
        mean_diff: float = float(np.mean(g1) - np.mean(g2))
        assert result.ci_lower <= mean_diff <= result.ci_upper


class TestChiSquare:
    """Tests for the chi-square wrapper."""

    def test_independent_variables_high_p(self) -> None:
        """Two independent variables should have high p-value."""
        # Equal distribution across all cells (no association)
        observed: np.ndarray = np.array([[25, 25], [25, 25]])
        result: TestResult = chi_square_test(observed, "independent")
        assert result.p_value > 0.9
        assert result.effect_size < 0.05  # Cramér's V near 0

    def test_associated_variables_low_p(self) -> None:
        """Strongly associated variables should have low p-value."""
        # Perfect association: all group1 in category A, all group2 in category B
        observed: np.ndarray = np.array([[50, 0], [0, 50]])
        result: TestResult = chi_square_test(observed, "associated")
        assert result.p_value < 0.001
        assert result.effect_size > 0.9  # Cramér's V near 1

    def test_accepts_dataframe(self) -> None:
        """Should accept pd.DataFrame as input (from pd.crosstab)."""
        df: pd.DataFrame = pd.DataFrame(
            {"A": [30, 10], "B": [10, 30]}, index=["X", "Y"]
        )
        result: TestResult = chi_square_test(df, "df_test")
        assert result.p_value < 0.05
        assert result.effect_size_name == "Cramér's V"


class TestMultipleComparisonCorrection:
    """Tests for p-value correction methods."""

    def test_bonferroni_multiplies_by_n(self) -> None:
        """Bonferroni should multiply each p-value by the number of tests."""
        p_values: list[float] = [0.01, 0.02, 0.05]
        corrected: list[float] = apply_multiple_comparison_correction(
            p_values, method="bonferroni"
        )
        assert np.isclose(corrected[0], 0.03)  # 0.01 * 3
        assert np.isclose(corrected[1], 0.06)  # 0.02 * 3
        assert np.isclose(corrected[2], 0.15)  # 0.05 * 3

    def test_bonferroni_caps_at_one(self) -> None:
        """Corrected p-values should never exceed 1.0."""
        p_values: list[float] = [0.5, 0.8]
        corrected: list[float] = apply_multiple_comparison_correction(
            p_values, method="bonferroni"
        )
        assert np.isclose(corrected[0], 1.0)
        assert np.isclose(corrected[1], 1.0)

    def test_bh_less_conservative(self) -> None:
        """Benjamini-Hochberg should produce smaller corrections than Bonferroni."""
        p_values: list[float] = [0.01, 0.02, 0.03, 0.05]
        bonf: list[float] = apply_multiple_comparison_correction(
            p_values, method="bonferroni"
        )
        bh: list[float] = apply_multiple_comparison_correction(
            p_values, method="benjamini-hochberg"
        )
        # BH should be less conservative (smaller adjusted p-values) for all
        for b, h in zip(bonf, bh):
            assert h <= b

    def test_empty_input(self) -> None:
        """Empty input should return empty output."""
        assert apply_multiple_comparison_correction([], "bonferroni") == []

    def test_invalid_method_raises(self) -> None:
        """Unknown correction method should raise ValueError."""
        import pytest

        with pytest.raises(ValueError, match="Unknown correction method"):
            apply_multiple_comparison_correction([0.05], method="invalid")


class TestBootstrapCI:
    """Tests for bootstrap confidence intervals."""

    def test_ci_contains_true_mean(self) -> None:
        """95% CI should usually contain the true population mean."""
        rng = np.random.default_rng(42)
        data: np.ndarray = rng.normal(loc=10, scale=2, size=200)
        lower, upper = bootstrap_ci(data)
        # The true mean is 10; the CI should contain it
        assert lower < 10 < upper

    def test_narrow_ci_for_large_sample(self) -> None:
        """Larger samples should produce narrower CIs."""
        rng = np.random.default_rng(42)
        small: np.ndarray = rng.normal(loc=5, scale=1, size=20)
        large: np.ndarray = rng.normal(loc=5, scale=1, size=500)

        l_small, u_small = bootstrap_ci(small)
        l_large, u_large = bootstrap_ci(large)

        width_small: float = u_small - l_small
        width_large: float = u_large - l_large
        assert width_large < width_small

    def test_handles_nan_values(self) -> None:
        """NaN values should be dropped before bootstrapping."""
        data: np.ndarray = np.array([1.0, 2.0, np.nan, 4.0, 5.0, np.nan])
        lower, upper = bootstrap_ci(data)
        assert lower < upper  # Should produce a valid interval

    def test_reproducible_with_seed(self) -> None:
        """Same seed should produce identical results."""
        data: np.ndarray = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        ci1 = bootstrap_ci(data, seed=123)
        ci2 = bootstrap_ci(data, seed=123)
        assert ci1 == ci2
