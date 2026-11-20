"""Links to the SET website for what has no free data feed (spec categories 5-8), and free float.

Every URL was opened in a browser on 2026-11-21. SET has no per-stock page for investor types, NVDR,
short sales or warning lists, so those links go to the all-stocks page (`market_wide=True`).
"""

from typing import NamedTuple
from urllib.parse import quote as url_quote

import pandas as pd

from src.i18n import text

QUOTE = "https://www.set.or.th/en/market/product/stock/quote/{symbol}/{page}"
MARKET = "https://www.set.or.th/en/market/"
FORM_59 = "https://market.sec.or.th/public/idisc/en/r59"


class Link(NamedTuple):
    label: str
    url: str
    market_wide: bool  # True: a page for all stocks, where the user looks the symbol up


def set_links(symbol: str, lang: str = "en") -> list[Link]:
    def quote(label: str, page: str) -> Link:
        return Link(text(label, lang), QUOTE.format(symbol=url_quote(symbol, safe=""), page=page), False)

    def market(label: str, path: str) -> Link:
        return Link(text(label, lang), MARKET + path, True)

    return [
        quote("link.price", "price"),
        quote("link.shareholders", "major-shareholders"),
        quote("link.rights", "rights-benefits"),
        quote("link.news", "news"),
        market("link.investor_types", "statistics/investor-type"),
        market("link.nvdr", "statistics/nvdr/main"),
        market("link.short_sales", "statistics/short-sales/total-short-sales"),
        market("link.c_sign", "news-and-alert/surveillance-c-sign-temporary-trading/c-sign"),
        market("link.surveillance",
               "news-and-alert/surveillance-c-sign-temporary-trading/market-surveillance-measure-list"),
        market("link.auto_pause", "news-and-alert/trading-halt-suspension-pause"),
        # Form 59 is published by the SEC, not SET. The user opened this page in their browser on 2026-11-21.
        Link(text("link.form59", lang), FORM_59, True),
    ]


def free_float(float_shares: float | None, shares_outstanding: float | None) -> float:
    """Share of shares freely traded (0.46 = 46%), Yahoo's estimate. NaN when either number is missing.

    Yahoo's floatShares is not SET's free-float definition, so it can differ from the SET website.
    """
    if float_shares is None or shares_outstanding is None or pd.isna(float_shares) or pd.isna(shares_outstanding) \
            or not shares_outstanding:
        return float("nan")
    return float_shares / shares_outstanding
