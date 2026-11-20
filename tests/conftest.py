"""Shared test setup.

Tests must never touch the internet: Yahoo Finance and thaifin are always mocked.
This guard makes any real network connection fail loudly, so an un-mocked call
is caught immediately instead of silently passing on a machine with Wi-Fi.
"""

import socket
from datetime import date

import pytest
from curl_cffi import AsyncCurl, Curl


class NetworkBlocked(RuntimeError):
    pass


@pytest.fixture(autouse=True)
def _block_network(monkeypatch):
    def guard(*args, **kwargs):
        raise NetworkBlocked("Tests must not use the network — mock the data source instead.")

    monkeypatch.setattr(socket.socket, "connect", guard)
    monkeypatch.setattr(socket.socket, "connect_ex", guard)
    monkeypatch.setattr(socket, "create_connection", guard)
    monkeypatch.setattr(socket, "getaddrinfo", guard)
    # yfinance downloads through curl_cffi. Its C library (libcurl) opens sockets itself,
    # bypassing everything above, so block the points where a curl request is started.
    monkeypatch.setattr(Curl, "perform", guard)
    monkeypatch.setattr(AsyncCurl, "add_handle", guard)


@pytest.fixture(autouse=True)
def _set50_list_not_expired(monkeypatch):
    """Keep page tests independent of today's date: the SET50 list counts as current.
    Tests about the expiry warning move SET50_PERIOD_END into the past themselves."""
    import src.universe

    monkeypatch.setattr(src.universe, "SET50_PERIOD_END", date.max)


@pytest.fixture
def fake_yahoo(monkeypatch):
    """Replace yfinance with offline fakes and start every test with empty Streamlit caches.

    Also makes thaifin unavailable, so financials come from the fake Yahoo statements.
    """
    import streamlit as st
    import yfinance

    import src.fundamentals as fd
    from tests.fakes import FakeTicker, fake_download

    FakeTicker.failing = set()
    FakeTicker.down = False
    monkeypatch.setattr(yfinance, "Ticker", FakeTicker)
    monkeypatch.setattr(yfinance, "download", fake_download)

    def no_thaifin(symbol):
        raise ConnectionError("thaifin disabled in tests")

    monkeypatch.setattr(fd, "_financials_thaifin", no_thaifin)
    st.cache_data.clear()
    yield FakeTicker
    st.cache_data.clear()
