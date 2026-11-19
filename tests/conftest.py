"""Shared test setup.

Tests must never touch the internet: Yahoo Finance and thaifin are always mocked.
This guard makes any real network connection fail loudly, so an un-mocked call
is caught immediately instead of silently passing on a machine with Wi-Fi.
"""

import socket

import pytest


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
