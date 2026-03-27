"""Stub implementations of all providers — for testing without real data sources.

Replace these with real adapters when integrating QUIK / in-house libs.
"""
import math
import random
from datetime import date, timedelta
from typing import Optional

from bonds_monitor.models import (
    BondAnalytics,
    BondStaticData,
    BoardType,
    FXRates,
    QuikRow,
)
from bonds_monitor.providers.base import (
    AnalyticsProvider,
    MarketDataProvider,
    QuikProvider,
    StaticDataProvider,
)

# ---------------------------------------------------------------------------
# Fake bond universe
# ---------------------------------------------------------------------------

_FAKE_BONDS: list[BondStaticData] = [
    BondStaticData("XS2519604605", "MINFIN 28",   "USD", date(2028, 3, 15), 2000.0, 0.0650),
    BondStaticData("XS2066805513", "MINFIN 30",   "USD", date(2030, 11, 27), 3000.0, 0.0475),
    BondStaticData("RU000A106375", "GAZPROM 26",  "USD", date(2026, 9, 22),  600.0, 0.0800),
    BondStaticData("RU000A107BR6", "LUKOIL 28",   "USD", date(2028, 5, 21),  500.0, 0.0680),
    BondStaticData("RU000A104ZK3", "NOVATEK 27",  "USD", date(2027, 7, 11),  400.0, 0.0720),
    BondStaticData("RU000A1060K7", "SBERBANK 26", "USD", date(2026, 10, 15), 350.0, 0.0550),
    BondStaticData("XS0971721963", "VTB 27",      "USD", date(2027, 2, 5),   300.0, 0.0600),
    BondStaticData("RU000A105146", "RUSAL 25",    "CNH", date(2025, 9, 1),   200.0, 0.0350),
    BondStaticData("XS1577952010", "EVRAZ 26",    "USD", date(2026, 4, 8),   250.0, 0.0575),
    BondStaticData("RU000A106SK4", "SEVERSTAL 27","USD", date(2027, 12, 3),  300.0, 0.0625),
]


class StubQuikProvider(QuikProvider):
    """Returns fake QUIK rows with slight random noise on each call."""

    # Base mid prices per ISIN (% of par)
    _BASE_PRICES = {
        "XS2519604605": 87.50,
        "XS2066805513": 79.00,
        "RU000A106375": 94.25,
        "RU000A107BR6": 91.00,
        "RU000A104ZK3": 92.50,
        "RU000A1060K7": 95.00,
        "XS0971721963": 88.00,
        "RU000A105146": 99.50,
        "XS1577952010": 90.00,
        "RU000A106SK4": 93.75,
    }

    # Simulated FX rates so RUB prices are consistent
    _CBR_USD = 89.50
    _MKT_USD = 90.25

    def get_rows(self) -> list[QuikRow]:
        rows: list[QuikRow] = []
        for bond in _FAKE_BONDS:
            mid = self._BASE_PRICES[bond.isin]
            noise = random.uniform(-0.25, 0.25)
            mid += noise
            spread = random.uniform(0.25, 0.75)
            bid_hcy = mid - spread / 2
            ask_hcy = mid + spread / 2
            ai = self._accrued(bond)

            # RUB board: prices adjusted for FX ratio
            fx_ratio = self._CBR_USD / self._MKT_USD
            bid_rub = (bid_hcy + ai) / fx_ratio - ai
            ask_rub = (ask_hcy + ai) / fx_ratio - ai

            # RUB orderbook row
            rows.append(QuikRow(
                isin=bond.isin,
                short_name=bond.short_name,
                board="TQOD",
                board_type=BoardType.RUB_ORDERBOOK,
                bid=round(bid_rub, 4),
                ask=round(ask_rub, 4),
                last_price=round((bid_rub + ask_rub) / 2, 4),
                accrued_interest=round(ai, 4),
                volume_rub=round(random.uniform(10, 500) * 1e6, 0),
                currency="RUB",
            ))

            # Negotiated deals row (no live bid/ask, just volume)
            rows.append(QuikRow(
                isin=bond.isin,
                short_name=bond.short_name,
                board="PSAU",
                board_type=BoardType.NEGOTIATED,
                bid=None,
                ask=None,
                last_price=round(mid, 4),
                accrued_interest=round(ai, 4),
                volume_rub=round(random.uniform(0, 200) * 1e6, 0),
                currency="RUB",
            ))

            # Repo row
            rows.append(QuikRow(
                isin=bond.isin,
                short_name=bond.short_name,
                board="RPMO",
                board_type=BoardType.REPO,
                bid=None,
                ask=None,
                last_price=round(random.uniform(5.0, 18.0), 2),  # repo rate %
                accrued_interest=None,
                volume_rub=round(random.uniform(0, 100) * 1e6, 0),
                currency="RUB",
            ))

        return rows

    @staticmethod
    def _accrued(bond: BondStaticData) -> float:
        """Very rough accrued interest approximation for stub purposes."""
        if bond.coupon_rate is None:
            return 0.0
        today = date.today()
        # Assume semi-annual coupon, 30/360
        days_into_period = (today.timetuple().tm_yday % 182)
        return round(bond.coupon_rate / 2 * (days_into_period / 182) * 100, 4)


class StubMarketDataProvider(MarketDataProvider):
    """Returns fixed FX rates with tiny random noise."""

    def get_fx_rates(self) -> FXRates:
        base_cbr_usd = 89.50
        base_mkt_usd = 90.25
        noise = random.uniform(-0.10, 0.10)
        return FXRates(
            cbr_usd=base_cbr_usd,
            cbr_eur=97.20,
            cbr_cnh=12.40,
            market_usd=round(base_mkt_usd + noise, 4),
            market_eur=round(98.10 + noise * 1.1, 4),
            market_cnh=round(12.45 + noise * 0.14, 4),
        )


class StubStaticDataProvider(StaticDataProvider):
    """Returns static data from the hard-coded fake bond universe."""

    _INDEX = {b.isin: b for b in _FAKE_BONDS}

    def get_bond(self, isin: str) -> Optional[BondStaticData]:
        return self._INDEX.get(isin)


class StubAnalyticsProvider(AnalyticsProvider):
    """
    Approximates yield / duration using simple formulas.
    Replace with real in-house lib adapter.
    """

    def calculate(
        self,
        isin: str,
        price: float,
        accrued: float,
        settlement_date=None,
    ) -> BondAnalytics:
        static = StubStaticDataProvider().get_bond(isin)
        if static is None or static.coupon_rate is None:
            return BondAnalytics(None, None, None, None)

        dirty = price + accrued
        coupon = static.coupon_rate * 100  # in %

        today = date.today()
        years_to_mat = max((static.maturity - today).days / 365.25, 0.01)

        # Rough YTM approximation (street convention): (C + (100-dirty)/T) / ((100+dirty)/2)
        ytm = (coupon + (100 - dirty) / years_to_mat) / ((100 + dirty) / 2)

        # Modified duration approximation
        dur = years_to_mat / (1 + ytm / 2)  # very rough

        # Stub z-spread (vs flat curve at 6%)
        risk_free = 0.06
        z_spread = (ytm - risk_free) * 10000  # bps

        return BondAnalytics(
            bid_yield=round(ytm, 6),
            ask_yield=round(ytm * 1.005, 6),  # ask yield slightly lower
            duration=round(dur, 3),
            z_spread=round(z_spread, 1),
        )
