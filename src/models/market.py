"""Market data models."""

from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field


class MarketType(str, Enum):
    """Type of market."""

    CRYPTO = "crypto"
    FOREX = "forex"
    PREDICTION = "prediction"


class Exchange(str, Enum):
    """Supported exchanges."""

    BINANCE = "binance"
    KRAKEN = "kraken"
    COINBASE = "coinbase"
    OANDA = "oanda"
    POLYMARKET = "polymarket"


class Ticker(BaseModel):
    """Real-time ticker data from an exchange."""

    symbol: str = Field(..., description="Trading pair symbol (e.g., BTC/USDT)")
    exchange: Exchange = Field(..., description="Exchange this ticker is from")
    bid: Decimal = Field(..., description="Best bid price")
    ask: Decimal = Field(..., description="Best ask price")
    bid_volume: Decimal = Field(default=Decimal("0"), description="Volume at best bid")
    ask_volume: Decimal = Field(default=Decimal("0"), description="Volume at best ask")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Ticker timestamp")

    @property
    def spread(self) -> Decimal:
        """Calculate absolute spread."""
        return self.ask - self.bid

    @property
    def spread_percent(self) -> Decimal:
        """Calculate spread as percentage of bid price."""
        if self.bid == 0:
            return Decimal("0")
        return (self.spread / self.bid) * 100

    @property
    def mid_price(self) -> Decimal:
        """Calculate mid-market price."""
        return (self.bid + self.ask) / 2


class OrderbookLevel(BaseModel):
    """Single level in an orderbook (price + volume)."""

    price: Decimal = Field(..., description="Price at this level")
    volume: Decimal = Field(..., description="Volume available at this price")


class Orderbook(BaseModel):
    """Orderbook snapshot with bids and asks."""

    symbol: str = Field(..., description="Trading pair symbol")
    exchange: Exchange = Field(..., description="Exchange this orderbook is from")
    bids: list[OrderbookLevel] = Field(default_factory=list, description="Bid levels (descending)")
    asks: list[OrderbookLevel] = Field(default_factory=list, description="Ask levels (ascending)")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Orderbook timestamp")

    def get_executable_price(self, side: str, volume: Decimal) -> tuple[Decimal, Decimal]:
        """
        Calculate average executable price for a given volume.

        Args:
            side: "buy" to hit asks, "sell" to hit bids
            volume: Volume to execute

        Returns:
            Tuple of (average_price, filled_volume)
        """
        levels = self.bids if side == "sell" else self.asks
        total_cost = Decimal("0")
        filled_volume = Decimal("0")

        for level in levels:
            remaining = volume - filled_volume
            if remaining <= 0:
                break
            fill_at_level = min(remaining, level.volume)
            total_cost += fill_at_level * level.price
            filled_volume += fill_at_level

        if filled_volume == 0:
            return Decimal("0"), Decimal("0")

        avg_price = total_cost / filled_volume
        return avg_price, filled_volume

    def get_total_volume(self, side: str, depth: int = 10) -> Decimal:
        """Get total volume available within top N levels."""
        levels = self.bids if side == "sell" else self.asks
        return sum(level.volume for level in levels[:depth])

    @property
    def best_bid(self) -> Decimal:
        """Get best bid price."""
        return self.bids[0].price if self.bids else Decimal("0")

    @property
    def best_ask(self) -> Decimal:
        """Get best ask price."""
        return self.asks[0].price if self.asks else Decimal("0")

    @property
    def spread(self) -> Decimal:
        """Calculate spread from orderbook."""
        if not self.bids or not self.asks:
            return Decimal("0")
        return self.best_ask - self.best_bid
