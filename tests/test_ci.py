"""Backlog #7: CI runs the same checks as a developer runs locally."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github/workflows/ci.yml"
CHECK = ROOT / "scripts/check.sh"


def test_workflow_triggers_on_push_and_pull_request():
    text = WORKFLOW.read_text()
    assert "\n  push:" in text and "\n  pull_request:" in text


def test_workflow_installs_dev_requirements_and_runs_check_script():
    text = WORKFLOW.read_text()
    assert "pip install -r requirements-dev.txt" in text
    assert "scripts/check.sh" in text
    assert "python-version: \"3.11\"" in text


def test_check_script_runs_pytest_and_ty_and_fails_fast():
    assert os.access(CHECK, os.X_OK), "scripts/check.sh must be executable"
    text = CHECK.read_text()
    assert "set -euo pipefail" in text  # any failing step makes the whole run fail
    assert "-m pytest" in text and "ty@" in text and " check " in text


def test_data_update_runs_on_weekdays_after_the_close_and_on_demand():
    text = (ROOT / ".github/workflows/update-data.yml").read_text()
    assert 'cron: "30 11 * * 1-5"' in text  # 18:30 Bangkok
    assert "workflow_dispatch:" in text
    assert "python scripts/update_data.py" in text


# ---------- Windows: double-click start.bat / update.bat ----------

def test_bat_files_are_ascii_and_checked_out_with_windows_line_endings():
    assert "*.bat text eol=crlf" in (ROOT / ".gitattributes").read_text().splitlines()
    for name in ("start.bat", "update.bat"):
        (ROOT / name).read_bytes().decode("ascii")  # no Thai: cmd.exe would garble it


def test_start_bat_sets_up_once_then_runs_the_app_in_thai():
    text = (ROOT / "start.bat").read_text()
    assert 'cd /d "%~dp0"' in text
    assert "py -3.11 -m venv .venv" in text and "python -m venv .venv" in text
    assert "-m pip install -r requirements.txt" in text
    assert "STOCKS_LANG=th" in text
    assert r".venv\Scripts\python.exe" in text and "-m streamlit run app.py" in text
    assert "--server.showEmailPrompt false" in text  # else the first run waits for an email in the console
    assert "pause" in text


def test_update_bat_pulls_and_reinstalls():
    text = (ROOT / "update.bat").read_text()
    assert "git pull" in text and "-m pip install -r requirements.txt" in text and "pause" in text


def test_workflow_runs_tests_and_start_bat_on_windows():
    text = WORKFLOW.read_text()
    windows = text.split("\n  windows:", 1)[1]
    assert "runs-on: windows-latest" in windows and 'python-version: "3.11"' in windows
    assert "python -m pytest -q" in windows and "scripts/check.sh is bash" in windows
    assert "start.bat" in windows and "/_stcore/health" in windows and "AddSeconds(300)" in windows
