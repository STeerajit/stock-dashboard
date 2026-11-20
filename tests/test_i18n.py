"""Backlog #18: every user-facing string is in src/i18n.py, in both languages."""

import ast
import re
import string
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from src.fundamentals import FIN_COLUMNS, SCORE_COLUMNS
from src.i18n import LANGS, TEXT, text
from src.scoring import piotroski

ROOT = Path(__file__).resolve().parent.parent
# Where keys are used (src/i18n.py itself is left out: its docstring shows t("key") as an example).
CODE = [ROOT / "app.py", *sorted((ROOT / "app_pages").glob("*.py")),
        *[p for p in sorted((ROOT / "src").glob("*.py")) if p.name != "i18n.py"]]


def placeholders(s: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(s) if name}


@pytest.mark.parametrize("key", sorted(TEXT))
def test_every_key_has_both_languages_with_the_same_placeholders(key):
    entry = TEXT[key]
    assert set(entry) == set(LANGS), f"{key}: missing {set(LANGS) - set(entry)}"
    assert all(entry[lang].strip() for lang in LANGS), f"{key}: empty text"
    assert placeholders(entry["en"]) == placeholders(entry["th"]), key


def test_every_key_used_in_the_code_exists():
    used = set()
    for path in CODE:
        used |= set(re.findall(r"""\b(?:t|text)\(\s*["']([a-z0-9_.]+(?: [A-Za-z/ ]+)?)["']""", path.read_text()))
    assert used, "no keys found: the regex is broken"
    missing = used - set(TEXT)
    assert not missing, f"keys used but not defined: {sorted(missing)}"


def test_keys_built_at_run_time_exist():
    shown = [c for c in FIN_COLUMNS if c not in ("P/E", "P/BV", *SCORE_COLUMNS)]
    assert {f"fin.{c}" for c in shown} <= set(TEXT)
    assert {f"check.{c}" for c in _check_names()} <= set(TEXT)
    assert {f"pred.col_{k}" for k in ["period", "model", "baseline", "edge"]} <= set(TEXT)


def _check_names() -> list[str]:
    import numpy as np
    import pandas as pd

    df = pd.DataFrame(np.ones((2, len(FIN_COLUMNS))), columns=FIN_COLUMNS, index=[2024, 2025])
    return list(piotroski(df).checks)


UI_KEYWORDS = {"label", "help", "title", "placeholder", "alt", "x_label", "y_label", "body", "caption"}
UI_FUNCTIONS = {"title", "header", "subheader", "caption", "markdown", "write", "info", "warning", "error", "success",
                "metric", "button", "page_link", "expander", "popover", "toast", "spinner", "segmented_control",
                "selectbox", "multiselect", "slider", "form_submit_button", "TextColumn", "NumberColumn",
                "CheckboxColumn", "ProgressColumn"}


def literal_text(node: ast.AST) -> str | None:
    """A string literal with words in it (not a format code, icon or single token)."""
    parts = []
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        parts = [node.value]
    elif isinstance(node, ast.JoinedStr):
        parts = [v.value for v in node.values if isinstance(v, ast.Constant) and isinstance(v.value, str)]
    joined = "".join(parts)
    return joined if re.search(r"[A-Za-z]{3,}\W+[A-Za-z]{2,}", joined) else None


@pytest.mark.parametrize("path", [ROOT / "app.py", *sorted((ROOT / "app_pages").glob("*.py"))], ids=lambda p: p.name)
def test_no_hard_coded_text_in_pages(path):
    found = []
    for node in ast.walk(ast.parse(path.read_text())):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr in UI_FUNCTIONS):
            continue
        first = [] if node.func.attr == "page_link" else node.args[:1]  # page_link's first argument is a file path
        candidates = first + [k.value for k in node.keywords if k.arg in UI_KEYWORDS]
        found += [f"line {node.lineno}: {s!r}" for c in candidates if (s := literal_text(c))]
    assert not found, f"move these strings to src/i18n.py: {found}"


def test_thai_text_is_returned_for_thai():
    assert text("today.title", "th") == "วันนี้"
    assert text("today.title", "en") == "Today"
    assert text("today.title", "xx") == "Today"  # unknown language: English


def test_app_starts_in_thai_from_the_url():
    at = AppTest.from_file(ROOT / "app.py", default_timeout=30)
    at.query_params["lang"] = "th"
    at.run()
    assert not at.exception
    assert at.title[0].value == "วันนี้"
    assert at.session_state["lang_choice"] == "th"


def test_switching_language_updates_the_page_and_the_url():
    at = AppTest.from_file(ROOT / "app.py", default_timeout=30).run()
    assert at.title[0].value == "Today"
    at.sidebar.segmented_control[0].set_value("th").run()
    assert at.title[0].value == "วันนี้"
    assert at.query_params["lang"] == ["th"] or at.query_params["lang"] == "th"
