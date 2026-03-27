"""Abstract interfaces for all external data providers.

When integrating real data sources, implement these ABCs:
  - QuikProvider     -> adapter around your QUIK Python lib
  - MarketDataProvider -> adapter around your in-house FX/CBR feed
  - AnalyticsProvider  -> adapter around your in-house bond math lib
"""
from abc import ABC, abstractmethod
from typing import Optional

from bonds_monitor.models import BondAnalytics, BondStaticData, FXRates, QuikRow


class QuikProvider(ABC):
    """Yields rows from the QUIK 'current trading' table."""

    @abstractmethod
    def get_rows(self) -> list[QuikRow]:
        """Return all rows from the QUIK table (one row per board per ISIN)."""
        ...


class MarketDataProvider(ABC):
    """Provides FX and CBR rate snapshots."""

    @abstractmethod
    def get_fx_rates(self) -> FXRates:
        ...


class StaticDataProvider(ABC):
    """Provides bond static data (maturity, coupon, outstanding, etc.)."""

    @abstractmethod
    def get_bond(self, isin: str) -> Optional[BondStaticData]:
        """Return static data for the given ISIN, or None if not found."""
        ...


class AnalyticsProvider(ABC):
    """Calculates yield, duration, z-spread etc. using in-house bond math."""

    @abstractmethod
    def calculate(
        self,
        isin: str,
        price: float,         # clean price, % of par, in HCY
        accrued: float,       # accrued interest, % of par
        settlement_date: Optional[object] = None,
    ) -> BondAnalytics:
        """
        Return analytics for the given bond at the given price.
        settlement_date defaults to T+1 if None.
        """
        ...
