"""Static checks on the analysis notebooks.

The test suite never executes the notebooks: they require the full DuckDB
pipeline and would regenerate figures. These tests parse the .ipynb JSON
instead, locking two things that would otherwise only fail at notebook
runtime:

- repository hygiene: stripped outputs, pure-Python code cells, no local
  absolute paths leaking into public artifacts;
- the NB07 display-label contract: segment, overlap-category and
  recommendation names are constants used as dictionary keys shared across
  cells (palette, DataFrames, L10N maps). A typo in one of those keys would
  surface as a KeyError (or a silently gray bar) only when the notebook
  runs; here it fails fast in CI.
"""

import ast
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from src.config import PROJECT_ROOT

NOTEBOOKS_DIR: Path = PROJECT_ROOT / "notebooks"
NOTEBOOK_PATHS: list[Path] = sorted(NOTEBOOKS_DIR.glob("*.ipynb"))
NB07_PATH: Path = NOTEBOOKS_DIR / "07_bq5_recommendations_synthesis.ipynb"


def _load_notebook(path: Path) -> dict[str, Any]:
    """Parse a notebook as plain JSON: no nbformat dependency needed."""
    return json.loads(path.read_text(encoding="utf-8"))


def _code_cells(notebook: dict[str, Any]) -> list[dict[str, Any]]:
    return [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]


def _source(cell: dict[str, Any]) -> str:
    # .ipynb stores each cell source as a list of lines with trailing newlines
    return "".join(cell["source"])


def _find_code_cell(notebook: dict[str, Any], marker: str) -> str:
    """Return the source of the single code cell containing marker.

    Uniqueness is asserted so a copy-pasted definition in a second cell
    (which would shadow the first at runtime) fails the lookup loudly.
    """
    matches: list[str] = [
        _source(cell) for cell in _code_cells(notebook) if marker in _source(cell)
    ]
    assert len(matches) == 1, (
        f"Expected exactly one code cell containing {marker!r}, "
        f"found {len(matches)}"
    )
    return matches[0]


def test_notebooks_are_discovered() -> None:
    """Guard for the parametrized tests below: an empty glob would make
    them all pass vacuously (e.g. after a directory rename)."""
    assert len(NOTEBOOK_PATHS) >= 7


@pytest.mark.parametrize("path", NOTEBOOK_PATHS, ids=lambda p: p.name)
class TestNotebookHygiene:
    """Hygiene rules every committed notebook must satisfy."""

    def test_outputs_are_stripped(self, path: Path) -> None:
        """nbstripout must have removed outputs and execution counts."""
        for index, cell in enumerate(_code_cells(_load_notebook(path))):
            assert cell["outputs"] == [], f"code cell {index} has outputs"
            assert (
                cell["execution_count"] is None
            ), f"code cell {index} has an execution count"

    def test_code_cells_are_pure_python(self, path: Path) -> None:
        """Every code cell must parse with ast (no IPython magics or shell
        escapes): the notebooks are read as plain Python by tooling
        (ruff, static analysis) and by these very tests."""
        for index, cell in enumerate(_code_cells(_load_notebook(path))):
            try:
                ast.parse(_source(cell))
            except SyntaxError as exc:
                pytest.fail(f"{path.name} code cell {index} is not pure Python: {exc}")

    def test_no_absolute_local_paths(self, path: Path) -> None:
        """Public artifacts must not leak absolute paths from a local machine."""
        for index, cell in enumerate(_load_notebook(path)["cells"]):
            assert "/Users/" not in _source(
                cell
            ), f"cell {index} contains a local absolute path"


class TestNb07DisplayLabelContract:
    """Cross-check NB07's display-label constants against its L10N maps.

    The two cells are executed in isolation: the labels cell is pure by
    design, and the localization cell only needs three names from the
    setup cell (FIGURES_DIR, FIG_DPI, plt), stubbed here so no matplotlib
    import or real figures directory is involved.
    """

    @pytest.fixture(scope="class")
    def nb07_namespace(
        self, tmp_path_factory: pytest.TempPathFactory
    ) -> dict[str, Any]:
        notebook = _load_notebook(NB07_PATH)
        namespace: dict[str, Any] = {
            "FIGURES_DIR": tmp_path_factory.mktemp("figures"),
            "FIG_DPI": 150,
            "plt": SimpleNamespace(show=lambda: None, close=lambda fig: None),
        }
        # exec() is deliberate: it is the only way to run notebook cells
        # without a kernel, and the source is our own repository content.
        exec(_find_code_cell(notebook, "PALETTE_SEGMENT = {"), namespace)
        exec(_find_code_cell(notebook, "L10N = {"), namespace)
        return namespace

    @pytest.mark.parametrize("lang", ["en", "it"])
    def test_l10n_covers_all_segments(
        self, nb07_namespace: dict[str, Any], lang: str
    ) -> None:
        display = nb07_namespace["L10N"][lang]["segment_display"]
        assert set(display) == set(nb07_namespace["SEGMENT_ORDER"])

    @pytest.mark.parametrize("lang", ["en", "it"])
    def test_l10n_covers_all_overlap_categories(
        self, nb07_namespace: dict[str, Any], lang: str
    ) -> None:
        display = nb07_namespace["L10N"][lang]["category_display"]
        assert set(display) == set(nb07_namespace["OVERLAP_CATEGORIES"])

    @pytest.mark.parametrize("lang", ["en", "it"])
    def test_l10n_covers_all_recommendations(
        self, nb07_namespace: dict[str, Any], lang: str
    ) -> None:
        display = nb07_namespace["L10N"][lang]["rec_display"]
        assert set(display) == set(nb07_namespace["RECOMMENDATIONS"])

    def test_palette_matches_segment_order(
        self, nb07_namespace: dict[str, Any]
    ) -> None:
        """SEGMENT_ORDER is derived from the palette keys; if that ever
        changes, the per-segment colors would silently shuffle."""
        assert list(nb07_namespace["PALETTE_SEGMENT"]) == list(
            nb07_namespace["SEGMENT_ORDER"]
        )

    def test_one_recommendation_per_segment(
        self, nb07_namespace: dict[str, Any]
    ) -> None:
        """The priority matrix zips RECOMMENDATIONS with SEGMENT_ORDER
        positionally, so their lengths must match."""
        assert len(nb07_namespace["RECOMMENDATIONS"]) == len(
            nb07_namespace["SEGMENT_ORDER"]
        )

    def test_l10n_languages_are_structurally_identical(
        self, nb07_namespace: dict[str, Any]
    ) -> None:
        """EN and IT must expose the same furniture keys and the same
        number of cost ticks: a key present in one language only would
        crash the figure loop for the other."""
        l10n = nb07_namespace["L10N"]
        assert set(l10n["en"]) == set(l10n["it"])
        assert len(l10n["en"]["cost_ticks"]) == len(l10n["it"]["cost_ticks"])
