"""Base exchange connector interface."""

from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal

from src.models.market import Exchange, MarketType, Orderbook, Ticker
from src.models.trade import Order, OrderSide, OrderType


class BaseExchange(ABC):
    """Abstract base class for exchange connectors."""

    def __init__(self, api_key: str = "", secret: str = "") -> None:
        """
        Initialize exchange connector.

        Args:
            api_key: API key (optional for public endpoints)
            secret: API secret (optional for public endpoints)
        """
        self.api_key = api_key
        self.secret = secret
        self.exchange_name: Exchange | None = None
        self.market_type: MarketType | None = None
        self.fees: dict[str, Decimal] = {
            "maker": Decimal("0.001"),
            "taker": Decimal("0.001"),
        }
        self._orderbook_cache: dict[str, Orderbook] = {}
        self._ticker_cache: dict[str, Ticker] = {}
        self._last_update: dict[str, datetime] = {}
        self._connected: bool = False

    @abstractmethod
    async def connect(self) -> bool:
        """
        Connect to the exchange.

        Returns:
            True if connection successful
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the exchange."""
        pass

    @abstractmethod
    async def get_ticker(self, symbol: str) -> Ticker:
        """
        Get real-time ticker for a symbol.

        Args:
            symbol: Trading pair (e.g., "BTC/USDT")

        Returns:
            Ticker with bid/ask prices
        """
        pass

    @abstractmethod
    async def get_orderbook(self, symbol: str, depth: int = 20) -> Orderbook:
        """
        Get orderbook snapshot.

        Args:
            symbol: Trading pair
            depth: Number of levels to fetch

        Returns:
            Orderbook with bids and asks
        """
        pass

    @abstractmethod
    async def get_balance(self, currency: str) -> Decimal:
        """
        Get balance for a currency.

        Args:
            currency: Currency code (e.g., "BTC")

        Returns:
            Available balance
        """
        pass

    @abstractmethod
    async def place_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        volume: Decimal,
        price: Decimal | None = None,
    ) -> Order:
        """
        Place an order.

        Args:
            symbol: Trading pair
            side: Buy or sell
            order_type: Market or limit
            volume: Order volume
            price: Limit price (required for limit orders)

        Returns:
            Order object with status
        """
        pass

    @abstractmethod
    def get_supported_symbols(self) -> list[str]:
        """
        Get list of supported trading pairs.

        Returns:
            List of symbol strings
        """
        pass

    def get_fee(self, order_type: str = "taker") -> Decimal:
        """
        Get trading fee for order type.

        Args:
            order_type: "maker" or "taker"

        Returns:
            Fee as decimal (e.g., 0.001 for 0.1%)
        """
        return self.fees.get(order_type, Decimal("0.001"))

    async def get_cached_orderbook(self, symbol: str, max_age_ms: int = 100) -> Orderbook | None:
        """
        Get cached orderbook if fresh enough.

        Args:
            symbol: Trading pair
            max_age_ms: Maximum cache age in milliseconds

        Returns:
            Cached orderbook or None if stale/missing
        """
        cache_key = f"{self.exchange_name}_{symbol}"
        if cache_key in self._orderbook_cache:
            last_update = self._last_update.get(cache_key)
            if last_update:
                age_ms = (datetime.utcnow() - last_update).total_seconds() * 1000
                if age_ms < max_age_ms:
                    return self._orderbook_cache[cache_key]
        return None

    def _cache_orderbook(self, symbol: str, orderbook: Orderbook) -> None:
        """
        Cache an orderbook.

        Args:
            symbol: Trading pair
            orderbook: Orderbook to cache
        """
        cache_key = f"{self.exchange_name}_{symbol}"
        self._orderbook_cache[cache_key] = orderbook
        self._last_update[cache_key] = datetime.utcnow()

    async def get_cached_ticker(self, symbol: str, max_age_ms: int = 100) -> Ticker | None:
        """
        Get cached ticker if fresh enough.

        Args:
            symbol: Trading pair
            max_age_ms: Maximum cache age in milliseconds

        Returns:
            Cached ticker or None if stale/missing
        """
        cache_key = f"{self.exchange_name}_{symbol}_ticker"
        if cache_key in self._ticker_cache:
            last_update = self._last_update.get(cache_key)
            if last_update:
                age_ms = (datetime.utcnow() - last_update).total_seconds() * 1000
                if age_ms < max_age_ms:
                    return self._ticker_cache[cache_key]
        return None

    def _cache_ticker(self, symbol: str, ticker: Ticker) -> None:
        """
        Cache a ticker.

        Args:
            symbol: Trading pair
            ticker: Ticker to cache
        """
        cache_key = f"{self.exchange_name}_{symbol}_ticker"
        self._ticker_cache[cache_key] = ticker
        self._last_update[cache_key] = datetime.utcnow()

    @property
    def is_connected(self) -> bool:
        """Check if exchange is connected."""
        return self._connected
