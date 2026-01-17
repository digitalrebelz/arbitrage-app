"""Binance exchange connector using CCXT."""

from datetime import datetime
from decimal import Decimal
from typing import Any

import ccxt.async_support as ccxt
from loguru import logger

from src.exchanges.base import BaseExchange
from src.models.market import Exchange, MarketType, Orderbook, OrderbookLevel, Ticker
from src.models.trade import Order, OrderSide, OrderStatus, OrderType, TradeMode


class BinanceExchange(BaseExchange):
    """Binance exchange connector using CCXT async."""

    def __init__(
        self,
        api_key: str = "",
        secret: str = "",
        testnet: bool = False,
    ) -> None:
        """
        Initialize Binance connector.

        Args:
            api_key: Binance API key (optional for public data)
            secret: Binance API secret (optional for public data)
            testnet: Use testnet if True
        """
        super().__init__(api_key, secret)
        self.exchange_name = Exchange.BINANCE
        self.market_type = MarketType.CRYPTO
        self.fees = {
            "maker": Decimal("0.001"),
            "taker": Decimal("0.001"),
        }
        self.testnet = testnet
        self._client: ccxt.binance | None = None
        self._symbols: list[str] = []

    async def connect(self) -> bool:
        """Connect to Binance API."""
        try:
            options: dict[str, Any] = {
                "defaultType": "spot",
                "enableRateLimit": True,
            }
            if self.testnet:
                options["sandbox"] = True

            self._client = ccxt.binance(
                {
                    "apiKey": self.api_key or None,
                    "secret": self.secret or None,
                    "options": options,
                }
            )

            await self._client.load_markets()
            self._symbols = list(self._client.symbols)
            self._connected = True
            logger.info(f"Connected to Binance, {len(self._symbols)} symbols available")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Binance: {e}")
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """Disconnect from Binance."""
        if self._client:
            await self._client.close()
            self._client = None
            self._connected = False
            logger.info("Disconnected from Binance")

    async def get_ticker(self, symbol: str) -> Ticker:
        """Get real-time ticker for a symbol."""
        # Check cache first
        cached = await self.get_cached_ticker(symbol)
        if cached:
            return cached

        if not self._client:
            raise RuntimeError("Not connected to Binance")

        data = await self._client.fetch_ticker(symbol)

        ticker = Ticker(
            symbol=symbol,
            exchange=self.exchange_name,
            bid=Decimal(str(data["bid"])) if data["bid"] else Decimal("0"),
            ask=Decimal(str(data["ask"])) if data["ask"] else Decimal("0"),
            bid_volume=Decimal(str(data.get("bidVolume", 0) or 0)),
            ask_volume=Decimal(str(data.get("askVolume", 0) or 0)),
            timestamp=datetime.utcnow(),
        )

        self._cache_ticker(symbol, ticker)
        return ticker

    async def get_orderbook(self, symbol: str, depth: int = 20) -> Orderbook:
        """Get orderbook snapshot."""
        # Check cache first
        cached = await self.get_cached_orderbook(symbol)
        if cached:
            return cached

        if not self._client:
            raise RuntimeError("Not connected to Binance")

        data = await self._client.fetch_order_book(symbol, limit=depth)

        bids = [
            OrderbookLevel(price=Decimal(str(b[0])), volume=Decimal(str(b[1])))
            for b in data["bids"]
        ]
        asks = [
            OrderbookLevel(price=Decimal(str(a[0])), volume=Decimal(str(a[1])))
            for a in data["asks"]
        ]

        orderbook = Orderbook(
            symbol=symbol,
            exchange=self.exchange_name,
            bids=bids,
            asks=asks,
            timestamp=datetime.utcnow(),
        )

        self._cache_orderbook(symbol, orderbook)
        return orderbook

    async def get_balance(self, currency: str) -> Decimal:
        """Get balance for a currency."""
        if not self._client:
            raise RuntimeError("Not connected to Binance")

        try:
            balance = await self._client.fetch_balance()
            if currency in balance:
                return Decimal(str(balance[currency]["free"]))
            return Decimal("0")
        except Exception as e:
            logger.error(f"Error fetching balance for {currency}: {e}")
            return Decimal("0")

    async def place_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        volume: Decimal,
        price: Decimal | None = None,
    ) -> Order:
        """Place an order on Binance."""
        if not self._client:
            raise RuntimeError("Not connected to Binance")

        ccxt_side = "buy" if side == OrderSide.BUY else "sell"
        ccxt_type = "market" if order_type == OrderType.MARKET else "limit"

        result = await self._client.create_order(
            symbol=symbol,
            type=ccxt_type,
            side=ccxt_side,
            amount=float(volume),
            price=float(price) if price else None,
        )

        return Order(
            id=result["id"],
            opportunity_id="",
            exchange=self.exchange_name.value,
            symbol=symbol,
            side=side,
            type=order_type,
            requested_volume=volume,
            filled_volume=Decimal(str(result.get("filled", 0))),
            requested_price=price,
            average_fill_price=(Decimal(str(result["average"])) if result.get("average") else None),
            status=self._map_order_status(result["status"]),
            mode=TradeMode.LIVE,
            fee_paid=Decimal(str(result.get("fee", {}).get("cost", 0) or 0)),
            fee_currency=result.get("fee", {}).get("currency", "USDT"),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

    def get_supported_symbols(self) -> list[str]:
        """Get list of supported trading pairs."""
        return self._symbols

    def _map_order_status(self, ccxt_status: str) -> OrderStatus:
        """Map CCXT order status to our OrderStatus."""
        mapping = {
            "open": OrderStatus.OPEN,
            "closed": OrderStatus.FILLED,
            "canceled": OrderStatus.CANCELLED,
            "expired": OrderStatus.CANCELLED,
            "rejected": OrderStatus.FAILED,
        }
        return mapping.get(ccxt_status, OrderStatus.PENDING)

    async def get_funding_rate(self, symbol: str) -> Decimal | None:
        """
        Get current funding rate for a perpetual contract.

        Args:
            symbol: Trading pair

        Returns:
            Funding rate as decimal or None
        """
        if not self._client:
            raise RuntimeError("Not connected to Binance")

        try:
            # Switch to futures for funding rate
            funding = await self._client.fetch_funding_rate(symbol)
            if funding and "fundingRate" in funding:
                return Decimal(str(funding["fundingRate"]))
            return None
        except Exception as e:
            logger.debug(f"Could not fetch funding rate for {symbol}: {e}")
            return None
