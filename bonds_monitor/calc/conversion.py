"""RUB orderbook price -> hard-currency price conversion.

Formula from task spec:
    PX_hcy + AI = (PX_rub + AI) * FX_cbr / FX_market

Solved for PX_hcy:
    PX_hcy = (PX_rub + AI) * FX_cbr / FX_market - AI

All prices are % of par (clean prices); AI is % of par.
"""
from typing import Optional

from bonds_monitor.models import ConvertedPrices, FXRates


def rub_to_hcy(
    bid_rub: Optional[float],
    ask_rub: Optional[float],
    accrued_interest: float,
    fx: FXRates,
    currency: str,
) -> ConvertedPrices:
    """Convert RUB clean prices to hard-currency clean prices.

    Args:
        bid_rub: best bid in RUB orderbook, % of par (clean). None if no quote.
        ask_rub: best ask in RUB orderbook, % of par (clean). None if no quote.
        accrued_interest: AI in % of par (exchange-calculated).
        fx: current FX snapshot.
        currency: bond currency ('USD', 'EUR', 'CNH').

    Returns:
        ConvertedPrices with clean HCY bid/ask.
    """
    cbr = fx.cbr(currency)
    mkt = fx.market(currency)

    def convert(px_rub: Optional[float]) -> Optional[float]:
        if px_rub is None:
            return None
        dirty_rub = px_rub + accrued_interest
        hcy_clean = dirty_rub * cbr / mkt - accrued_interest
        return round(hcy_clean, 4)

    return ConvertedPrices(
        conv_bid=convert(bid_rub),
        conv_ask=convert(ask_rub),
    )
