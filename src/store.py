"""The daily data store: one DuckDB file (data/market.duckdb) with prices, dividends, snapshots and financials.

`update_store` fetches everything first, checks it, and only then writes it in one transaction, so a bad or
partial download never damages what is already stored. Prices are stored as traded; the dividend
adjustment is applied when reading (`adjust_for_dividends`), so fetching only the new days stays correct
even after a new dividend changes every older adjusted price.
"""

from collections.abc import Callable, Generator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import NamedTuple

import duckdb
import numpy as np
import pandas as pd

from src.fundamentals import FIN_COLUMNS, SNAPSHOT_COLUMNS

STORE_PATH = Path(__file__).resolve().parent.parent / "data" / "market.duckdb"
MAX_FAILED = 0.2
RETRIES = 1
PRICE_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]
DATE_SNAPSHOT_COLUMNS = ("ex_div_date", "earnings_date")
DE_DEFINITION = {"thaifin": "Total liabilities / shareholders' equity",
                 "Yahoo Finance": "Interest-bearing debt / shareholders' equity"}


class Fetchers(NamedTuple):
    prices: Callable[[str, date | None], pd.DataFrame]  # raw OHLCV as traded; start=None: full history
    dividends: Callable[[str], pd.Series]  # cash dividend per share by XD date
    snapshot: Callable[[str], dict]  # like fundamentals.get_snapshot
    financials: Callable[[str], pd.DataFrame]  # like fundamentals.get_financials


class UpdateError(RuntimeError):
    pass


class Report(NamedTuple):
    updated: list[str]
    failed: list[str]


def _q(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


@contextmanager
def connect(path: Path, read_only: bool = False) -> Generator[duckdb.DuckDBPyConnection]:
    con = duckdb.connect(str(path), read_only=read_only)
    try:
        if not read_only:
            _create_tables(con)
        yield con
    finally:
        con.close()


def _create_tables(con: duckdb.DuckDBPyConnection) -> None:
    snap_cols = ", ".join(f"{_q(c)} {'TIMESTAMP' if c in DATE_SNAPSHOT_COLUMNS else 'DOUBLE'}"
                          for c in SNAPSHOT_COLUMNS if c != "symbol")
    fin_cols = ", ".join(f"{_q(c)} DOUBLE" for c in FIN_COLUMNS)
    con.execute("""CREATE TABLE IF NOT EXISTS prices (symbol VARCHAR, date DATE, "Open" DOUBLE, "High" DOUBLE,
                   "Low" DOUBLE, "Close" DOUBLE, "Volume" DOUBLE, PRIMARY KEY (symbol, date))""")
    con.execute("CREATE TABLE IF NOT EXISTS dividends (symbol VARCHAR, date DATE, amount DOUBLE, "
                "PRIMARY KEY (symbol, date))")
    con.execute(f"CREATE TABLE IF NOT EXISTS snapshots (symbol VARCHAR, date DATE, {snap_cols}, "
                "PRIMARY KEY (symbol, date))")
    con.execute(f"CREATE TABLE IF NOT EXISTS financials (symbol VARCHAR, year INTEGER, {fin_cols}, "
                "source VARCHAR, PRIMARY KEY (symbol, year))")
    con.execute("CREATE TABLE IF NOT EXISTS meta (key VARCHAR PRIMARY KEY, value VARCHAR)")


# ---------- update ----------

def update_store(path: Path, symbols: list[str], fetch: Fetchers, now: datetime | None = None,
                 workers: int = 8) -> Report:
    """Fetch every symbol, check, then write all in one transaction. Raises UpdateError (store untouched)
    when more than 20% of the symbols fail or any price is zero or negative."""
    now = now or datetime.now()
    last_dates = _last_price_dates(path, symbols)

    def one(sym: str):
        start = last_dates[sym] + timedelta(days=1) if sym in last_dates else None
        for attempt in range(1 + RETRIES):  # Yahoo often fails a request once ("Invalid Crumb", DNS timeout)
            try:
                return fetch.prices(sym, start), fetch.dividends(sym), fetch.snapshot(sym), fetch.financials(sym)
            except Exception:
                if attempt == RETRIES:
                    return None

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = dict(zip(symbols, pool.map(one, symbols)))
    fetched = {s: r for s, r in results.items() if r is not None}
    failed = [s for s in symbols if results[s] is None]
    if symbols and len(failed) / len(symbols) > MAX_FAILED:
        raise UpdateError(f"{len(failed)} of {len(symbols)} stocks failed to download ({', '.join(failed)}); "
                          "the store was not changed. Try again later.")
    for sym, (prices, *_rest) in fetched.items():
        if not prices.empty and (prices[["Open", "High", "Low", "Close"]] <= 0).any().any():
            raise UpdateError(f"{sym} has a zero or negative price; the store was not changed.")

    with connect(path) as con:
        con.execute("BEGIN TRANSACTION")
        for sym, (prices, dividends, snap, fin) in fetched.items():
            _write(con, sym, prices, dividends, snap, fin, now.date())
        con.execute("INSERT OR REPLACE INTO meta VALUES ('last_update', ?)", [now.isoformat()])
        con.execute("COMMIT")
    return Report(sorted(fetched), failed)


def _last_price_dates(path: Path, symbols: list[str]) -> dict[str, date]:
    if not path.exists():
        return {}
    with connect(path, read_only=True) as con:
        rows = con.execute("SELECT symbol, max(date) FROM prices GROUP BY symbol").fetchall()
    return {s: d for s, d in rows if s in symbols}


def _write(con, sym: str, prices: pd.DataFrame, dividends: pd.Series, snap: dict, fin: pd.DataFrame,
           day: date) -> None:
    if not prices.empty:
        p = prices[PRICE_COLUMNS].copy()
        p.insert(0, "date", pd.DatetimeIndex(p.index).date)
        p.insert(0, "symbol", sym)
        con.execute("INSERT OR REPLACE INTO prices BY NAME SELECT * FROM p")
    con.execute("DELETE FROM dividends WHERE symbol = ?", [sym])
    if not dividends.empty:
        d = pd.DataFrame({"symbol": sym, "date": pd.DatetimeIndex(dividends.index).date,
                          "amount": dividends.to_numpy(dtype=float)}).groupby(["symbol", "date"], as_index=False).sum()
        con.execute("INSERT INTO dividends BY NAME SELECT * FROM d")
    s = pd.DataFrame([snap]).reindex(columns=SNAPSHOT_COLUMNS)
    for c in DATE_SNAPSHOT_COLUMNS:
        s[c] = pd.to_datetime(s[c]).dt.tz_localize(None) if s[c].notna().any() else pd.NaT
    s["symbol"], s["date"] = sym, day
    num = [c for c in SNAPSHOT_COLUMNS if c not in ("symbol", *DATE_SNAPSHOT_COLUMNS)]
    s[num] = s[num].astype(float)
    con.execute("INSERT OR REPLACE INTO snapshots BY NAME SELECT * FROM s")
    con.execute("DELETE FROM financials WHERE symbol = ?", [sym])
    if not fin.empty:
        f = fin.reindex(columns=FIN_COLUMNS).astype(float)
        f.insert(0, "year", [int(y) for y in f.index])
        f.insert(0, "symbol", sym)
        f["source"] = fin.attrs.get("source", "?")
        con.execute("INSERT INTO financials BY NAME SELECT * FROM f")


# ---------- read ----------

def as_of(path: Path) -> datetime | None:
    """When the store was last updated successfully, or None without a store."""
    if not path.exists():
        return None
    with connect(path, read_only=True) as con:
        row = con.execute("SELECT value FROM meta WHERE key = 'last_update'").fetchone()
    return datetime.fromisoformat(row[0]) if row else None


def has(path: Path, symbol: str) -> bool:
    if not path.exists():
        return False
    with connect(path, read_only=True) as con:
        return con.execute("SELECT 1 FROM snapshots WHERE symbol = ? LIMIT 1", [symbol]).fetchone() is not None


def adjust_for_dividends(raw: pd.DataFrame, dividends: pd.Series) -> pd.DataFrame:
    """Back-adjust prices for cash dividends, like Yahoo's adjusted close: every price before an XD date is
    multiplied by (1 - dividend / close of the day before the XD date). Volume is not changed."""
    if raw.empty or dividends.empty:
        return raw
    factor = pd.Series(1.0, index=raw.index)
    close = raw["Close"]
    for xd, amount in zip(pd.DatetimeIndex(dividends.index), dividends.to_numpy(dtype=float)):
        before = close[close.index < xd]
        if before.empty:
            continue
        factor[factor.index < xd] *= 1 - amount / before.iloc[-1]
    adj = raw.copy()
    for c in ["Open", "High", "Low", "Close"]:
        adj[c] = raw[c] * factor
    return adj


def _raw_prices(con, symbol: str) -> pd.DataFrame:
    df = con.execute('SELECT date, "Open", "High", "Low", "Close", "Volume" FROM prices WHERE symbol = ? '
                     "ORDER BY date", [symbol]).df()
    return df.set_index(pd.DatetimeIndex(df.pop("date"), name="Date"))


def _dividends(con, symbol: str) -> pd.Series:
    df = con.execute("SELECT date, amount FROM dividends WHERE symbol = ? ORDER BY date", [symbol]).df()
    return pd.Series(df["amount"].to_numpy(), index=pd.DatetimeIndex(df["date"]), dtype=float)


def load_prices(path: Path, symbol: str) -> pd.DataFrame:
    """Daily OHLCV adjusted for dividends (like src.data.load_prices), oldest first."""
    with connect(path, read_only=True) as con:
        return adjust_for_dividends(_raw_prices(con, symbol), _dividends(con, symbol))


def load_close(path: Path, symbol: str) -> pd.Series:
    """Daily close as traded (not adjusted for dividends)."""
    with connect(path, read_only=True) as con:
        return _raw_prices(con, symbol)["Close"]


def load_dividends(path: Path, symbol: str) -> pd.Series:
    """Cash dividend per share, one row per XD date, as traded."""
    with connect(path, read_only=True) as con:
        return _dividends(con, symbol)


def load_dividends_per_year(path: Path, symbol: str) -> pd.Series:
    """Cash dividend per share summed by calendar year of the XD date (like get_dividends_per_year)."""
    with connect(path, read_only=True) as con:
        div = _dividends(con, symbol)
    return div.groupby(pd.DatetimeIndex(div.index).year).sum() if not div.empty else div


def load_financials(path: Path, symbol: str) -> pd.DataFrame:
    """Yearly figures like get_financials (FIN_COLUMNS, index = year, attrs source / de_definition)."""
    with connect(path, read_only=True) as con:
        df = con.execute("SELECT * FROM financials WHERE symbol = ? ORDER BY year", [symbol]).df()
    source = str(df["source"].iloc[0]) if len(df) else "?"
    fin = df.set_index("year")[FIN_COLUMNS].astype(float)
    fin.index = [int(y) for y in fin.index]
    fin.attrs = {"source": source, "de_definition": DE_DEFINITION.get(source, "Debt / equity"),
                 "fallback_note": None}
    return fin


def load_snapshots(path: Path, symbols: list[str]) -> pd.DataFrame:
    """The latest stored snapshot of each symbol (SNAPSHOT_COLUMNS); NaN row for a symbol not stored."""
    with connect(path, read_only=True) as con:
        df = con.execute("SELECT * FROM snapshots QUALIFY row_number() OVER (PARTITION BY symbol ORDER BY date DESC) = 1"
                         ).df()
    out = pd.DataFrame({"symbol": symbols}).merge(df.drop(columns="date"), on="symbol", how="left")
    out = out.reindex(columns=SNAPSHOT_COLUMNS)
    out[list(DATE_SNAPSHOT_COLUMNS)] = out[list(DATE_SNAPSHOT_COLUMNS)].apply(pd.to_datetime)
    return out.replace({None: np.nan})


# ---------- live sources ----------

def live_fetchers() -> Fetchers:
    """Fetchers that download from Yahoo Finance (prices, dividends, snapshot) and thaifin (financials)."""
    import yfinance as yf

    from src import fundamentals as fd
    from src.universe import yahoo_symbol

    def prices(symbol: str, start: date | None) -> pd.DataFrame:
        if start is not None and start > date.today():
            return pd.DataFrame(columns=PRICE_COLUMNS)
        # Not "max" / "20y": Yahoo returned nothing for some Thai stocks with those (checked 2026-11-21).
        df = yf.download(yahoo_symbol(symbol), start=start, period=None if start else "15y", interval="1d",
                         auto_adjust=False, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        if df.empty:
            if start is None:
                raise ConnectionError(f"No price history for {symbol}")
            return pd.DataFrame(columns=PRICE_COLUMNS)
        return df[PRICE_COLUMNS].dropna()

    def dividends(symbol: str) -> pd.Series:
        div = yf.Ticker(yahoo_symbol(symbol)).dividends
        return pd.Series(div.to_numpy(dtype=float), index=pd.DatetimeIndex(div.index).tz_localize(None).normalize())

    def snapshot(symbol: str) -> dict:
        snap = fd.get_snapshot(symbol)
        if not snap.get("price"):
            raise ConnectionError(f"No price for {symbol}")
        return snap

    return Fetchers(prices, dividends, snapshot, fd.get_financials)
