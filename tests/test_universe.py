"""Backlog #3: data/set50.csv is a well-formed SET50 list."""

import pandas as pd

from src.universe import SET50_CSV, SET_SECTORS, load_set50, yahoo_symbol


def test_exactly_50_unique_symbols():
    df = load_set50()
    assert len(df) == 50
    assert df["symbol"].is_unique


def test_no_blank_fields():
    df = pd.read_csv(SET50_CSV, dtype=str, keep_default_na=False)
    assert list(df.columns) == ["symbol", "name", "sector"]
    for col in df.columns:
        assert (df[col].str.strip() != "").all(), f"blank value in column {col!r}"


def test_symbols_look_like_set_symbols():
    for sym in load_set50()["symbol"]:
        assert sym == sym.strip().upper() and " " not in sym and not sym.endswith(".BK"), sym


def test_sectors_are_official_set_sector_names():
    unknown = set(load_set50()["sector"]) - SET_SECTORS
    assert not unknown, f"not an SET sector name: {unknown}"


def test_yahoo_symbol():
    assert yahoo_symbol("PTT") == "PTT.BK"
