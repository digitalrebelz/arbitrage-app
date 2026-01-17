"""Arbitrage opportunity detector."""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

from loguru import logger

from src.arbitrage.calculator import ArbitrageCalculator
from src.config.settings import settings
from src.models.market import Exchange, Orderbook, Ticker
from src.models.opportunity import ArbitrageOpportunity, ArbitrageType, OpportunityStatus


class ArbitrageDetector:
    """Detects arbitrage opportunities across exchanges."""

    def __init__(self) -> None:
        """Initialize the arbitrage detector."""
        self.calculator = ArbitrageCalculator()
        self.exchanges: dict[Exchange, Any] = {}
        self.min_profit_threshold = settings.MIN_PROFIT_THRESHOLD_PERCENT
        self.opportunity_window_ms = 5000  # 5 seconds

    async def initialize(self, exchanges: list[Exchange]) -> None:
        """
        Initialize connections to specified exchanges.

        Args:
            exchanges: List of exchanges to connect to
        """
        from src.exchanges import ExchangeFactory

        for exchange in exchanges:
            try:
                self.exchanges[exchange] = await ExchangeFactory.get_exchange(exchange)
                logger.info(f"Initialized {exchange.value}")
            except Exception as e:
                logger.error(f"Failed to initialize {exchange.value}: {e}")

    async def scan_cross_exchange_opportunities(self, symbol: str) -> list[ArbitrageOpportunity]:
        """
        Scan for cross-exchange arbitrage opportunities.

        Args:
            symbol: Trading pair to scan (e.g., "BTC/USDT")

        Returns:
            List of detected opportunities
        """
        opportunities = []
        exchange_list = list(self.exchanges.keys())

        # Fetch market data from all exchanges concurrently
        tasks = [self._fetch_market_data(exchange, symbol) for exchange in exchange_list]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter successful results
        market_data: dict[Exchange, dict[str, Any]] = {}
        for exchange, result in zip(exchange_list, results, strict=True):
            if not isinstance(result, Exception) and result is not None:
                market_data[exchange] = result

        # Compare all pairs of exchanges
        exchanges_with_data = list(market_data.keys())
        for i, buy_exchange in enumerate(exchanges_with_data):
            for sell_exchange in exchanges_with_data[i + 1 :]:
                # Check buy on exchange1, sell on exchange2
                opp = await self._check_pair(
                    symbol,
                    buy_exchange,
                    sell_exchange,
                    market_data[buy_exchange],
                    market_data[sell_exchange],
                )
                if opp:
                    opportunities.append(opp)

                # Check buy on exchange2, sell on exchange1 (reverse)
                opp_reverse = await self._check_pair(
                    symbol,
                    sell_exchange,
                    buy_exchange,
                    market_data[sell_exchange],
                    market_data[buy_exchange],
                )
                if opp_reverse:
                    opportunities.append(opp_reverse)

        return opportunities

    async def _fetch_market_data(self, exchange: Exchange, symbol: str) -> dict[str, Any] | None:
        """
        Fetch ticker and orderbook from an exchange.

        Args:
            exchange: Exchange to fetch from
            symbol: Trading pair

        Returns:
            Dict with ticker, orderbook, and fee data
        """
        try:
            ex = self.exchanges[exchange]
            ticker, orderbook = await asyncio.gather(
                ex.get_ticker(symbol),
                ex.get_orderbook(symbol, depth=20),
            )
            return {
                "ticker": ticker,
                "orderbook": orderbook,
                "fee": ex.get_fee("taker"),
            }
        except Exception as e:
            logger.debug(f"Failed to fetch data from {exchange.value}: {e}")
            return None

    async def _check_pair(
        self,
        symbol: str,
        buy_exchange: Exchange,
        sell_exchange: Exchange,
        buy_data: dict[str, Any],
        sell_data: dict[str, Any],
    ) -> ArbitrageOpportunity | None:
        """
        Check if there's a profitable opportunity between two exchanges.

        Args:
            symbol: Trading pair
            buy_exchange: Exchange to buy from
            sell_exchange: Exchange to sell on
            buy_data: Market data from buy exchange
            sell_data: Market data from sell exchange

        Returns:
            ArbitrageOpportunity if profitable, None otherwise
        """
        buy_ticker: Ticker = buy_data["ticker"]
        sell_ticker: Ticker = sell_data["ticker"]
        buy_fee: Decimal = buy_data["fee"]
        sell_fee: Decimal = sell_data["fee"]

        # Quick check: buy price must be lower than sell price
        if buy_ticker.ask >= sell_ticker.bid:
            return None

        # Calculate profit
        gross_profit, net_profit, profit_usd = self.calculator.calculate_cross_exchange_profit(
            buy_ticker=buy_ticker,
            sell_ticker=sell_ticker,
            buy_fee_percent=buy_fee * 100,
            sell_fee_percent=sell_fee * 100,
            volume=Decimal("1"),
        )

        # Check minimum profit threshold
        if net_profit < self.min_profit_threshold:
            return None

        # Calculate max executable volume
        buy_orderbook: Orderbook = buy_data["orderbook"]
        sell_orderbook: Orderbook = sell_data["orderbook"]

        max_volume = self.calculator.calculate_max_executable_volume(
            buy_orderbook=buy_orderbook,
            sell_orderbook=sell_orderbook,
            min_profit_percent=self.min_profit_threshold,
            buy_fee_percent=buy_fee * 100,
            sell_fee_percent=sell_fee * 100,
        )

        if max_volume == 0:
            return None

        # Estimate slippage
        buy_slippage = self.calculator.estimate_slippage(buy_orderbook, "buy", max_volume)
        sell_slippage = self.calculator.estimate_slippage(sell_orderbook, "sell", max_volume)
        total_slippage = buy_slippage + sell_slippage

        # Recalculate net profit with slippage
        net_profit_with_slippage = net_profit - total_slippage
        if net_profit_with_slippage < self.min_profit_threshold:
            return None

        # Calculate recommended volume (capped by max position size)
        max_position_volume = Decimal(str(settings.MAX_POSITION_SIZE_USD)) / buy_ticker.ask
        recommended_volume = min(max_volume, max_position_volume)

        # Calculate estimated profit for recommended volume
        _, _, estimated_profit = self.calculator.calculate_cross_exchange_profit(
            buy_ticker=buy_ticker,
            sell_ticker=sell_ticker,
            buy_fee_percent=buy_fee * 100,
            sell_fee_percent=sell_fee * 100,
            volume=recommended_volume,
        )

        now = datetime.utcnow()

        return ArbitrageOpportunity(
            id=str(uuid4()),
            type=ArbitrageType.CROSS_EXCHANGE,
            status=OpportunityStatus.DETECTED,
            buy_exchange=buy_exchange.value,
            sell_exchange=sell_exchange.value,
            symbol=symbol,
            buy_price=buy_ticker.ask,
            sell_price=sell_ticker.bid,
            max_volume=max_volume,
            recommended_volume=recommended_volume,
            gross_profit_percent=gross_profit,
            net_profit_percent=net_profit_with_slippage,
            estimated_profit_usd=estimated_profit,
            buy_fee_percent=buy_fee * 100,
            sell_fee_percent=sell_fee * 100,
            estimated_slippage_percent=total_slippage,
            detected_at=now,
            expires_at=now + timedelta(milliseconds=self.opportunity_window_ms),
            window_ms=self.opportunity_window_ms,
            orderbook_depth_ok=max_volume > Decimal("0.01"),
            liquidity_ok=(
                buy_ticker.bid_volume > recommended_volume
                and sell_ticker.ask_volume > recommended_volume
            ),
            risk_score=self._calculate_risk_score(
                net_profit_with_slippage, total_slippage, max_volume
            ),
        )

    def _calculate_risk_score(
        self,
        profit_percent: Decimal,
        slippage_percent: Decimal,
        volume: Decimal,
    ) -> Decimal:
        """
        Calculate risk score (0-1, higher = riskier).

        Args:
            profit_percent: Net profit after costs
            slippage_percent: Estimated slippage
            volume: Maximum executable volume

        Returns:
            Risk score between 0 and 1
        """
        # Lower profit = higher risk
        profit_factor = max(Decimal("0"), Decimal("1") - profit_percent / 10)

        # Higher slippage = higher risk
        slippage_factor = min(Decimal("1"), slippage_percent / 5)

        # Lower volume = higher risk (less liquid)
        volume_factor = max(Decimal("0"), Decimal("1") - volume / 10)

        # Weighted average
        risk = (
            profit_factor * Decimal("0.3")
            + slippage_factor * Decimal("0.4")
            + volume_factor * Decimal("0.3")
        )

        return min(Decimal("1"), max(Decimal("0"), risk))

    async def scan_all_symbols(self, symbols: list[str]) -> list[ArbitrageOpportunity]:
        """
        Scan multiple symbols for opportunities.

        Args:
            symbols: List of trading pairs

        Returns:
            All detected opportunities across all symbols
        """
        all_opportunities = []

        tasks = [self.scan_cross_exchange_opportunities(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, list):
                all_opportunities.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"Error scanning: {result}")

        return all_opportunities
