"""Structural parity tests for Italian notebook translations.

Verify that each Italian notebook in notebooks/it/ is a faithful
structural mirror of its English counterpart in notebooks/:
  - Same number of cells
  - Same cell types in the same order
  - Code cells are byte-identical (no accidental edits)
  - Markdown cells are non-empty
  - Markdown cells actually differ from English (translation happened)

These tests do NOT require a database connection — they only read
the .ipynb JSON files on disk.
"""

import json
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths and notebook list
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EN_DIR = PROJECT_ROOT / "notebooks"
IT_DIR = PROJECT_ROOT / "notebooks" / "it"

# All 7 analysis notebooks (same filenames in both directories)
NOTEBOOK_NAMES: list[str] = [
    "01_eda_student_base.ipynb",
    "02_eda_engagement_patterns.ipynb",
    "03_bq1_dropout_timing.ipynb",
    "04_bq2_early_signals.ipynb",
    "05_bq3_demographics_vs_behavior.ipynb",
    "06_bq4_course_comparison.ipynb",
    "07_bq5_recommendations_synthesis.ipynb",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_notebook(path: Path) -> dict:
    """Load a .ipynb file and return the parsed JSON."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _cell_source(cell: dict) -> str:
    """Join cell source lines into a single string for comparison."""
    return "".join(cell.get("source", []))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestITNotebookExists:
    """Each English notebook must have an Italian counterpart."""

    @pytest.mark.parametrize("nb_name", NOTEBOOK_NAMES)
    def test_it_notebook_exists(self, nb_name: str) -> None:
        it_path = IT_DIR / nb_name
        assert (
            it_path.is_file()
        ), f"Italian notebook missing: {it_path.relative_to(PROJECT_ROOT)}"


class TestCellStructure:
    """Italian notebooks must have the same cell structure as English."""

    @pytest.mark.parametrize("nb_name", NOTEBOOK_NAMES)
    def test_same_number_of_cells(self, nb_name: str) -> None:
        """IT notebook must have exactly the same number of cells as EN."""
        en_nb = _load_notebook(EN_DIR / nb_name)
        it_nb = _load_notebook(IT_DIR / nb_name)

        n_en = len(en_nb["cells"])
        n_it = len(it_nb["cells"])
        assert n_en == n_it, f"{nb_name}: EN has {n_en} cells but IT has {n_it}"

    @pytest.mark.parametrize("nb_name", NOTEBOOK_NAMES)
    def test_same_cell_types(self, nb_name: str) -> None:
        """Cell types must match in the same order (markdown, code, ...)."""
        en_nb = _load_notebook(EN_DIR / nb_name)
        it_nb = _load_notebook(IT_DIR / nb_name)

        en_types = [c["cell_type"] for c in en_nb["cells"]]
        it_types = [c["cell_type"] for c in it_nb["cells"]]
        assert (
            en_types == it_types
        ), f"{nb_name}: cell type sequence differs between EN and IT"


class TestCodeCellsIdentical:
    """Code cells must be byte-identical — translation touches only markdown."""

    @pytest.mark.parametrize("nb_name", NOTEBOOK_NAMES)
    def test_code_cells_identical(self, nb_name: str) -> None:
        en_nb = _load_notebook(EN_DIR / nb_name)
        it_nb = _load_notebook(IT_DIR / nb_name)

        for i, (en_cell, it_cell) in enumerate(
            zip(en_nb["cells"], it_nb["cells"], strict=True)
        ):
            if en_cell["cell_type"] != "code":
                continue
            en_src = _cell_source(en_cell)
            it_src = _cell_source(it_cell)
            assert en_src == it_src, (
                f"{nb_name} cell {i}: code cell differs between EN and IT. "
                f"Code cells must remain byte-identical."
            )


class TestMarkdownCellsNotEmpty:
    """Every markdown cell in the IT notebook must have non-empty content."""

    @pytest.mark.parametrize("nb_name", NOTEBOOK_NAMES)
    def test_markdown_cells_not_empty(self, nb_name: str) -> None:
        it_nb = _load_notebook(IT_DIR / nb_name)

        empty_cells: list[int] = []
        for i, cell in enumerate(it_nb["cells"]):
            if cell["cell_type"] != "markdown":
                continue
            if not _cell_source(cell).strip():
                empty_cells.append(i)

        assert (
            len(empty_cells) == 0
        ), f"{nb_name}: empty markdown cells at indices {empty_cells}"


class TestMarkdownCellsTranslated:
    """At least 80% of markdown cells must differ from the English version.

    Some short cells (e.g. '### 5a. Gender') may remain identical after
    translation because they contain only a section header with no
    translatable text. We allow up to 20% identical cells.
    """

    # Minimum fraction of markdown cells that must differ from English
    MIN_TRANSLATED_FRACTION: float = 0.80

    @pytest.mark.parametrize("nb_name", NOTEBOOK_NAMES)
    def test_markdown_cells_differ_from_english(self, nb_name: str) -> None:
        en_nb = _load_notebook(EN_DIR / nb_name)
        it_nb = _load_notebook(IT_DIR / nb_name)

        n_markdown = 0
        n_different = 0

        for en_cell, it_cell in zip(en_nb["cells"], it_nb["cells"], strict=True):
            if en_cell["cell_type"] != "markdown":
                continue
            n_markdown += 1
            # strip() so whitespace-only diffs don't count as translated
            if _cell_source(en_cell).strip() != _cell_source(it_cell).strip():
                n_different += 1

        # Guard: there must be at least one markdown cell
        assert n_markdown > 0, f"{nb_name}: no markdown cells found"

        fraction = n_different / n_markdown
        assert fraction >= self.MIN_TRANSLATED_FRACTION, (
            f"{nb_name}: only {n_different}/{n_markdown} "
            f"({fraction:.0%}) markdown cells differ from English. "
            f"Expected at least {self.MIN_TRANSLATED_FRACTION:.0%}."
        )
