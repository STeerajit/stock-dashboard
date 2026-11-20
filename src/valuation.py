"""Fair-value models: dividend discount (Gordon growth) and discounted free cash flow.

The answers depend entirely on the assumptions (growth, required return), so the app shows them next to
a sensitivity table. An estimate based on your assumptions — not investment advice.
"""

from collections.abc import Callable

import pandas as pd

MAX_DIVIDEND_GROWTH = 0.10  # cap for the default growth: a long, fast past rarely repeats forever
DEFAULT_REQUIRED_RETURN = 0.08
# Gordon growth needs growth below the required return (forever), so the default growth stays 2 points under it.
DDM_GROWTH_GAP = 0.02


def ddm_value(next_dps: float, growth: float, required_return: float) -> float:
    """Gordon growth: value = next year's dividend per share / (required return - growth)."""
    if required_return <= growth:
        raise ValueError("The required return must be higher than the dividend growth rate.")
    return next_dps / (required_return - growth)


def dcf_value(fcf: float, growth: float, years: int, terminal_growth: float, discount_rate: float,
              net_debt: float, shares: float) -> float:
    """Value per share: free cash flow grows at `growth` for `years`, then at `terminal_growth` forever.

    All cash flows are discounted at `discount_rate`; net debt is subtracted from the enterprise value.
    """
    if discount_rate <= terminal_growth:
        raise ValueError("The discount rate must be higher than the terminal growth rate.")
    if shares <= 0:
        raise ValueError("The number of shares must be positive.")
    flows = [fcf * (1 + growth) ** t for t in range(1, years + 1)]
    present = sum(f / (1 + discount_rate) ** t for t, f in enumerate(flows, start=1))
    terminal = flows[-1] * (1 + terminal_growth) / (discount_rate - terminal_growth)
    enterprise = present + terminal / (1 + discount_rate) ** years
    return (enterprise - net_debt) / shares


def sensitivity(value: Callable[[float, float], float], rates: list[float], growths: list[float]) -> pd.DataFrame:
    """value(rate, growth) for every pair: rows = rates, columns = growths. NaN where the model has no answer."""
    def safe(r: float, g: float) -> float:
        try:
            return value(r, g)
        except ValueError:
            return float("nan")

    return pd.DataFrame([[safe(r, g) for g in growths] for r in rates], index=rates, columns=growths)


def default_ddm_growth(dividends_per_year: pd.Series, this_year: int) -> float:
    """The DDM growth to start the slider at: past dividend growth (capped at 10%), at most 2 points below the
    default required return, so the model has an answer for fast growers too."""
    return min(dividend_growth(dividends_per_year, this_year), DEFAULT_REQUIRED_RETURN - DDM_GROWTH_GAP)


def dividend_growth(dividends_per_year: pd.Series, this_year: int, years: int = 5) -> float:
    """Default dividend growth: yearly growth of dividends per share over the last `years` complete years,
    capped at MAX_DIVIDEND_GROWTH. 0 when it can't be computed (too little history, no dividend at the start)."""
    end_year, start_year = this_year - 1, this_year - 1 - years
    start, end = dividends_per_year.get(start_year, 0.0), dividends_per_year.get(end_year, 0.0)
    if not start > 0 or not end > 0:
        return 0.0
    return min(float((end / start) ** (1 / years) - 1), MAX_DIVIDEND_GROWTH)
