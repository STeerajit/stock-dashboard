"""Backlog #21: links to the SET website and free float."""

import numpy as np
import pytest

from src.set_links import free_float, set_links


def test_per_stock_links_point_to_that_stock():
    links = set_links("MAJOR")
    per_stock = [link for link in links if not link.market_wide]
    assert {link.label for link in per_stock} >= {"Price and trading signs", "Major shareholders and free float",
                                                  "Rights & benefits (XD, XR)", "News"}
    for link in per_stock:
        assert link.url.startswith("https://www.set.or.th/en/market/product/stock/quote/MAJOR/"), link


def test_market_wide_links_name_no_other_stock():
    market = [link for link in set_links("MAJOR") if link.market_wide]
    assert {link.label for link in market} >= {"Investor types", "NVDR", "Short sales", "Caution signs (C)",
                                               "Cash balance and turnover list", "Auto Pause"}
    for link in market:
        assert link.url.startswith(("https://www.set.or.th/en/market/", "https://market.sec.or.th/")), link
        assert "/quote/" not in link.url, link


def test_form_59_links_to_the_sec_search():
    form59 = [link for link in set_links("PTT") if "Form 59" in link.label]
    assert [link.url for link in form59] == ["https://market.sec.or.th/public/idisc/en/r59"]


def test_every_link_is_https_and_unique():
    urls = [link.url for link in set_links("PTT")]
    assert all(u.startswith("https://") for u in urls) and len(urls) == len(set(urls))


def test_free_float_is_float_shares_over_shares_outstanding():
    assert free_float(12_989_823_664, 28_324_335_850) == pytest.approx(0.4586, abs=1e-4)


@pytest.mark.parametrize("float_shares, outstanding", [(None, 100), (50, None), (np.nan, 100), (50, 0)])
def test_free_float_is_nan_when_data_is_missing(float_shares, outstanding):
    assert np.isnan(free_float(float_shares, outstanding))
