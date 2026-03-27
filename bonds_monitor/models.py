from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional


class BoardType(Enum):
    RUB_ORDERBOOK = "rub_orderbook"
    CNY_ORDERBOOK = "cny_orderbook"
    NEGOTIATED = "negotiated"
    REPO = "repo"
    UNKNOWN = "unknown"


@dataclass
class BondStaticData:
    """Static bond data — typically from in-house lib or config."""
    isin: str
    short_name: str
    currency: str          # USD, EUR, CNH
    maturity: date
    outstanding_mm: float  # outstanding notional in millions (original ccy)
    coupon_rate: Optional[float] = None


@dataclass
class QuikRow:
    """One raw row as read from the QUIK table (after column mapping)."""
    isin: str
    short_name: str
    board: str
    board_type: BoardType
    bid: Optional[float]          # % of par
    ask: Optional[float]          # % of par
    last_price: Optional[float]   # % of par
    accrued_interest: Optional[float]  # % of par (exchange-calculated)
    volume_rub: Optional[float]   # today's volume, RUB
    currency: Optional[str]       # settlement currency from QUIK


@dataclass
class FXRates:
    """FX rates snapshot — from in-house market data source."""
    cbr_usd: float    # CBR USD/RUB fixing (previous business day)
    cbr_eur: float
    cbr_cnh: float
    market_usd: float  # live market USD/RUB
    market_eur: float
    market_cnh: float

    def cbr(self, ccy: str) -> float:
        return {"USD": self.cbr_usd, "EUR": self.cbr_eur, "CNH": self.cbr_cnh}[ccy.upper()]

    def market(self, ccy: str) -> float:
        return {"USD": self.market_usd, "EUR": self.market_eur, "CNH": self.market_cnh}[ccy.upper()]


@dataclass
class ConvertedPrices:
    """RUB-orderbook prices converted to hard-currency prices."""
    conv_bid: Optional[float]   # % of par in HCY
    conv_ask: Optional[float]


@dataclass
class BondAnalytics:
    """Output from the in-house analytics library."""
    bid_yield: Optional[float]   # decimal, e.g. 0.0725
    ask_yield: Optional[float]
    duration: Optional[float]    # modified duration, years
    z_spread: Optional[float]    # bps


@dataclass
class BondDisplayRow:
    """Fully assembled row ready for display."""
    isin: str
    short_name: str
    currency: str
    maturity: date
    # Raw orderbook prices (from best available board)
    bid: Optional[float]
    ask: Optional[float]
    # Converted HCY prices
    conv_bid: Optional[float]
    conv_ask: Optional[float]
    # Analytics
    bid_yield: Optional[float]
    ask_yield: Optional[float]
    duration: Optional[float]
    z_spread: Optional[float]
    # Volume (aggregated across boards)
    volume_rub_mm: Optional[float]
    # Repo
    avg_repo_rate: Optional[float]
    # Manual override flag
    px_overridden: bool = False
    override_bid: Optional[float] = None
    override_ask: Optional[float] = None
