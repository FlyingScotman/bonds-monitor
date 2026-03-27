"""Core data assembly engine.

Pulls raw data from all providers, applies conversion and analytics,
and assembles BondDisplayRow objects ready for the UI.
"""
from collections import defaultdict
from datetime import date
from typing import Optional

from bonds_monitor.calc.conversion import rub_to_hcy
from bonds_monitor.models import (
    BoardType,
    BondDisplayRow,
    FXRates,
    QuikRow,
)
from bonds_monitor.providers.base import (
    AnalyticsProvider,
    MarketDataProvider,
    QuikProvider,
    StaticDataProvider,
)


class Engine:
    def __init__(
        self,
        quik: QuikProvider,
        market_data: MarketDataProvider,
        static_data: StaticDataProvider,
        analytics: AnalyticsProvider,
        config: dict,
    ):
        self._quik = quik
        self._market_data = market_data
        self._static_data = static_data
        self._analytics = analytics
        self._config = config
        # Price overrides: isin -> (bid, ask)
        self._overrides: dict[str, tuple[Optional[float], Optional[float]]] = {}

    def set_override(self, isin: str, bid: Optional[float], ask: Optional[float]):
        self._overrides[isin] = (bid, ask)

    def clear_override(self, isin: str):
        self._overrides.pop(isin, None)

    def refresh(self) -> list[BondDisplayRow]:
        """Fetch fresh data from all providers and return display rows."""
        all_rows: list[QuikRow] = self._quik.get_rows()
        fx: FXRates = self._market_data.get_fx_rates()

        # Group rows by ISIN
        by_isin: dict[str, list[QuikRow]] = defaultdict(list)
        for row in all_rows:
            by_isin[row.isin].append(row)

        result: list[BondDisplayRow] = []
        for isin, rows in by_isin.items():
            static = self._static_data.get_bond(isin)

            # Determine bond currency
            currency = (static.currency if static else None) or "USD"

            # Find the best RUB orderbook row (primary source of live prices)
            rub_rows = [r for r in rows if r.board_type == BoardType.RUB_ORDERBOOK]
            rub_row = rub_rows[0] if rub_rows else None

            # Fallback to CNY orderbook if available and no RUB quotes
            cny_rows = [r for r in rows if r.board_type == BoardType.CNY_ORDERBOOK]

            # Accrued interest (prefer from exchange data)
            accrued = 0.0
            if rub_row and rub_row.accrued_interest is not None:
                accrued = rub_row.accrued_interest

            # Price override takes priority
            override = self._overrides.get(isin)
            if override:
                conv_bid, conv_ask = override
                px_overridden = True
            elif rub_row:
                conv = rub_to_hcy(
                    rub_row.bid, rub_row.ask, accrued, fx, currency
                )
                conv_bid, conv_ask = conv.conv_bid, conv.conv_ask
                px_overridden = False
            elif cny_rows:
                cny_row = cny_rows[0]
                conv_bid, conv_ask = cny_row.bid, cny_row.ask
                px_overridden = False
            else:
                conv_bid, conv_ask = None, None
                px_overridden = False

            # Analytics (use mid converted price)
            analytics = None
            price_for_analytics = None
            if conv_bid is not None and conv_ask is not None:
                price_for_analytics = (conv_bid + conv_ask) / 2
            elif conv_bid is not None:
                price_for_analytics = conv_bid
            elif conv_ask is not None:
                price_for_analytics = conv_ask

            bid_yield = ask_yield = duration = z_spread = None
            if price_for_analytics is not None:
                analytics = self._analytics.calculate(isin, price_for_analytics, accrued)
                if analytics:
                    bid_yield = analytics.bid_yield
                    ask_yield = analytics.ask_yield
                    duration = analytics.duration
                    z_spread = analytics.z_spread

            # Volume: sum across RUB OB + negotiated
            vol_rows = [r for r in rows if r.board_type in (BoardType.RUB_ORDERBOOK, BoardType.NEGOTIATED)]
            total_vol_rub = sum(r.volume_rub for r in vol_rows if r.volume_rub)

            # Repo rate
            repo_rows = [r for r in rows if r.board_type == BoardType.REPO]
            avg_repo = None
            if repo_rows and repo_rows[0].last_price:
                avg_repo = repo_rows[0].last_price

            maturity = static.maturity if static else date(9999, 1, 1)
            short_name = (static.short_name if static else None) or (rub_row.short_name if rub_row else isin)

            # Pre-filter: skip bonds that don't pass config filters
            if not self._passes_filter(static):
                continue

            result.append(BondDisplayRow(
                isin=isin,
                short_name=short_name,
                currency=currency,
                maturity=maturity,
                bid=rub_row.bid if rub_row else None,
                ask=rub_row.ask if rub_row else None,
                conv_bid=conv_bid,
                conv_ask=conv_ask,
                bid_yield=bid_yield,
                ask_yield=ask_yield,
                duration=duration,
                z_spread=z_spread,
                volume_rub_mm=round(total_vol_rub / 1e6, 1) if total_vol_rub else None,
                avg_repo_rate=avg_repo,
                px_overridden=px_overridden,
            ))

        return result

    def _passes_filter(self, static) -> bool:
        if static is None:
            return True
        filters = self._config.get("filters", {})
        min_out = filters.get("min_outstanding_mm")
        if min_out and static.outstanding_mm < min_out:
            return False
        ccys = filters.get("currencies")
        if ccys and static.currency not in ccys:
            return False
        return True
