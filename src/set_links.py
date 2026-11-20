"""Links to the SET website for what has no free data feed (spec categories 5-8), and free float.

Every URL was opened in a browser on 2026-11-21. SET has no per-stock page for investor types, NVDR,
short sales or warning lists, so those links go to the all-stocks page (`market_wide=True`).
"""

from typing import NamedTuple
from urllib.parse import quote as url_quote

import pandas as pd

QUOTE = "https://www.set.or.th/en/market/product/stock/quote/{symbol}/{page}"
MARKET = "https://www.set.or.th/en/market/"


class Link(NamedTuple):
    label: str
    url: str
    market_wide: bool  # True: a page for all stocks, where the user looks the symbol up


def set_links(symbol: str) -> list[Link]:
    def quote(label: str, page: str) -> Link:
        return Link(label, QUOTE.format(symbol=url_quote(symbol, safe=""), page=page), False)

    def market(label: str, path: str) -> Link:
        return Link(label, MARKET + path, True)

    return [
        quote("Price and trading signs", "price"),
        quote("Major shareholders and free float", "major-shareholders"),
        quote("Rights & benefits (XD, XR)", "rights-benefits"),
        quote("News", "news"),
        market("Investor types", "statistics/investor-type"),
        market("NVDR", "statistics/nvdr/main"),
        market("Short sales", "statistics/short-sales/total-short-sales"),
        market("Caution signs (C)", "news-and-alert/surveillance-c-sign-temporary-trading/c-sign"),
        market("Cash balance and turnover list",
               "news-and-alert/surveillance-c-sign-temporary-trading/market-surveillance-measure-list"),
        market("Auto Pause", "news-and-alert/trading-halt-suspension-pause"),
    ]


def free_float(float_shares: float | None, shares_outstanding: float | None) -> float:
    """Share of shares freely traded (0.46 = 46%), Yahoo's estimate. NaN when either number is missing.

    Yahoo's floatShares is not SET's free-float definition, so it can differ from the SET website.
    """
    if float_shares is None or shares_outstanding is None or pd.isna(float_shares) or pd.isna(shares_outstanding) \
            or not shares_outstanding:
        return float("nan")
    return float_shares / shares_outstanding
