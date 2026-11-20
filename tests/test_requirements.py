"""Backlog #1: dependencies are pinned, and dev tools are kept out of the runtime file."""

import re
import socket
from importlib.metadata import version
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PIN = re.compile(r"^([A-Za-z0-9_.\-]+)==([0-9][A-Za-z0-9.\-+]*)$")
DEV_ONLY = {"pytest"}


def _lines(name: str) -> list[str]:
    text = (ROOT / name).read_text().splitlines()
    return [ln.strip() for ln in text if ln.strip() and not ln.strip().startswith("#")]


def test_runtime_requirements_are_all_pinned():
    for line in _lines("requirements.txt"):
        assert PIN.match(line), f"not pinned with ==: {line!r}"


def test_runtime_requirements_exclude_dev_tools():
    names = {PIN.match(ln).group(1).lower() for ln in _lines("requirements.txt")}
    assert not names & DEV_ONLY


def test_dev_requirements_include_runtime_and_pinned_pytest():
    lines = _lines("requirements-dev.txt")
    assert lines[0] == "-r requirements.txt"
    pins = [PIN.match(ln) for ln in lines[1:]]
    assert all(pins), f"unpinned dev requirement in {lines[1:]}"
    assert "pytest" in {m.group(1).lower() for m in pins if m}


@pytest.mark.parametrize("req_file", ["requirements.txt", "requirements-dev.txt"])
def test_installed_versions_match_pins(req_file):
    for line in _lines(req_file):
        m = PIN.match(line)
        if m:
            assert version(m.group(1)) == m.group(2), f"{m.group(1)} installed != pinned"


def test_network_is_blocked_during_tests():
    with pytest.raises(Exception, match="must not use the network"):
        socket.create_connection(("example.com", 80), timeout=1)


def test_curl_cffi_is_blocked_during_tests():
    # yfinance downloads through curl_cffi, whose C library opens sockets itself and never
    # calls Python's socket module. Port 9 on localhost: even if the guard broke, nothing
    # would leave this machine.
    from curl_cffi import requests as curl_requests

    with pytest.raises(Exception, match="must not use the network"):
        curl_requests.get("http://127.0.0.1:9", timeout=1)
