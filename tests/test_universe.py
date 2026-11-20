"""Backlog #3 / #19: data/set100.csv is a well-formed SET100 list."""

from datetime import date

import pandas as pd

from src.universe import (
    OUTSIDE_SET100,
    SET100_CSV,
    SET100_PERIOD,
    SET100_PERIOD_END,
    SET_SECTORS,
    describe,
    load_set100,
    set100_expiry_warning,
    yahoo_symbol,
)

# Copied by hand from SET's "SET100 / SET100FF Index Constituents", July 1 - December 31, 2026,
# update on August 3, 2026 (SET50_SET100_H2_2026_revise.pdf, pages 3-5), in the document's order.
PDF_SET100 = """
AAV ADVANC AEONTS AMATA AOT AP AURA AWC BA BAM BANPU BBL BCH BCP BCPG BDMS BEM BGRIM BH BJC
BLA BTG BTS CBG CCET CENTEL CHG CK COM7 CPALL CPF CPN CRC DELTA DOHOME EA EGCO ERW GFPT GLOBAL
GPSC GST GULF GUNKUL HANA HMPRO ICHI IRPC IVL JMART JMT KBANK KCE KKP KTB KTC LH M MEGA MINT
MOSHI MRDIYT MTC OR OSP PLANB PR9 PRM PTG PTT PTTEP PTTGC QH RATCH RCL SAWAD SCB SCC SCGP SIRI
SPALI SPRC STA STECON STGT TASCO TCAP TFG THAI TIDLOR TISCO TLI TOA TOP TRUE TTB TU VGI WHA WHAUP
""".split()

# The SET50 list for the same period (the former data/set50.csv, checked against pages 1-2 of the same PDF).
SET50 = """
ADVANC AOT AWC BANPU BBL BCP BDMS BEM BH BJC CCET COM7 CPALL CPF CPN CRC DELTA EGCO GPSC GULF
HMPRO IVL KBANK KKP KTB KTC LH MINT MRDIYT MTC OR OSP PTT PTTEP PTTGC RATCH SCB SCC SCGP TCAP
TFG THAI TIDLOR TISCO TLI TOP TRUE TTB TU WHA
""".split()


def test_symbols_match_the_official_document():
    assert load_set100()["symbol"].tolist() == PDF_SET100
    assert len(PDF_SET100) == 100 and len(set(PDF_SET100)) == 100


def test_in_set50_marks_exactly_the_set50_stocks():
    df = load_set100()
    assert df["in_set50"].dtype == bool
    assert sorted(df.loc[df["in_set50"], "symbol"]) == sorted(SET50)
    assert set(SET50) <= set(df["symbol"])  # SET100 is a superset of SET50


def test_no_blank_fields():
    df = pd.read_csv(SET100_CSV, dtype=str, keep_default_na=False)
    assert list(df.columns) == ["symbol", "name", "sector", "in_set50"]
    for col in df.columns:
        assert (df[col].str.strip() != "").all(), f"blank value in column {col!r}"


def test_symbols_look_like_set_symbols():
    for sym in load_set100()["symbol"]:
        assert sym == sym.strip().upper() and " " not in sym and not sym.endswith(".BK"), sym


def test_sectors_are_official_set_sector_names():
    unknown = set(load_set100()["sector"]) - SET_SECTORS
    assert not unknown, (
        f"sector not in SET_SECTORS: {unknown}. Fix the typo in data/set100.csv, or, if a stock from a "
        "new sector joined SET100, add SET's exact spelling to SET_SECTORS in src/universe.py."
    )


def test_describe_a_listed_and_an_unlisted_symbol():
    df = load_set100()
    assert describe(df, "PTT") == ("PTT", "Energy & Utilities")
    assert describe(df, "MAJOR") == ("MAJOR", OUTSIDE_SET100)


def test_yahoo_symbol():
    assert yahoo_symbol("PTT") == "PTT.BK"


def test_period_text_ends_on_the_period_end_date():
    # The caption text and the date the expiry warning uses must not drift apart.
    assert SET100_PERIOD.endswith(f"{SET100_PERIOD_END.day} {SET100_PERIOD_END:%b %Y}")


def test_no_expiry_warning_on_the_last_day_of_the_period():
    assert set100_expiry_warning(date(2026, 12, 31), period_end=date(2026, 12, 31)) is None


def test_expiry_warning_from_the_day_after_the_period():
    msg = set100_expiry_warning(date(2027, 1, 1), period_end=date(2026, 12, 31))
    assert msg and "data/set100.csv" in msg
