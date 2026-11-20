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
