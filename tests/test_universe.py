"""Backlog #3: data/set50.csv is a well-formed SET50 list."""

from datetime import date

import pandas as pd

from src.universe import (
    SET50_CSV,
    SET50_PERIOD,
    SET50_PERIOD_END,
    SET_SECTORS,
    load_set50,
    set50_expiry_warning,
    yahoo_symbol,
)


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
    assert not unknown, (
        f"sector not in SET_SECTORS: {unknown}. Fix the typo in data/set50.csv, or, if a stock from a "
        "new sector joined SET50, add SET's exact spelling to SET_SECTORS in src/universe.py."
    )


def test_yahoo_symbol():
    assert yahoo_symbol("PTT") == "PTT.BK"


def test_period_text_ends_on_the_period_end_date():
    # The caption text and the date the expiry warning uses must not drift apart.
    assert SET50_PERIOD.endswith(f"{SET50_PERIOD_END.day} {SET50_PERIOD_END:%b %Y}")


def test_no_expiry_warning_on_the_last_day_of_the_period():
    assert set50_expiry_warning(date(2026, 12, 31), period_end=date(2026, 12, 31)) is None


def test_expiry_warning_from_the_day_after_the_period():
    msg = set50_expiry_warning(date(2027, 1, 1), period_end=date(2026, 12, 31))
    assert msg and "data/set50.csv" in msg
