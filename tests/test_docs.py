"""Backlog #9: docs and in-app text stay consistent with the code."""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def readme_structure_files() -> set[str]:
    text = (ROOT / "README.md").read_text()
    block = text.split("## Project structure", 1)[1].split("```")[1]
    return {line.split()[0] for line in block.strip().splitlines() if line.strip()}


def repo_files(*dirs: str) -> set[str]:
    out = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", *dirs],
                         cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return {f for f in out.split() if not f.endswith((".pyc",))}


def test_readme_structure_lists_every_code_and_test_file():
    listed = readme_structure_files()
    missing = repo_files("src", "app_pages", "tests") - listed
    assert not missing, f"README project structure is missing: {sorted(missing)}"


def test_readme_structure_lists_no_deleted_files():
    stale = {f for f in readme_structure_files() if not (ROOT / f).exists()}
    assert not stale, f"README lists files that don't exist: {sorted(stale)}"


def test_fundamentals_docstring_names_both_sources():
    import src.fundamentals as fd

    doc = fd.__doc__ or ""
    assert "Yahoo" in doc and "thaifin" in doc


def test_sidebar_caption_names_both_sources():
    text = (ROOT / "app.py").read_text()
    captions = re.findall(r"st\.caption\((.*?)\)\n", text, re.S)
    assert any("Yahoo" in c and "thaifin" in c for c in captions)


def test_screener_de_help_states_yahoo_definition():
    text = (ROOT / "app_pages/screener.py").read_text()
    de = text.split('"de": nc(', 1)[1].split("),", 1)[0]
    assert "interest-bearing debt" in de


def test_spec_has_a_status_row_for_each_of_the_8_categories():
    text = (ROOT / "docs/SPEC.md").read_text()
    table = text.split("## Status of the 8 categories", 1)[1].split("\n## ", 1)[0]
    rows = [line.split("|")[1:4] for line in table.splitlines() if re.match(r"\| \d \|", line)]
    assert [int(n) for n, _, _ in rows] == list(range(1, 9))
    assert all(status.strip() in {"Done", "Partial", "Not started"} for _, _, status in rows)


def test_readme_links_to_the_spec():
    assert "docs/SPEC.md" in (ROOT / "README.md").read_text()


def test_article_has_the_results_table_and_its_figures():
    text = (ROOT / "docs/article.md").read_text()
    rows = [line for line in text.splitlines() if re.match(r"\| [A-Z]+ \| \d", line)]
    assert len(rows) >= 5  # at least 5 stocks
    for image in re.findall(r"\]\((img/[^)]+)\)", text):
        assert (ROOT / "docs" / image).exists(), image
    assert "not investment advice" in text
    assert "docs/article.md" in (ROOT / "README.md").read_text()
