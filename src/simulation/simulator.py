"""Simulation engine for generating realistic mock arbitrage opportunities."""

import random
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from loguru import logger

from src.models.market import Exchange, Orderbook, OrderbookLevel
from src.models.opportunity import ArbitrageOpportunity, ArbitrageType, OpportunityStatus


class ArbitrageSimulator:
    """Generate realistic simulated arbitrage opportunities."""

    # Realistic price ranges for major pairs
    PRICE_RANGES = {
        "BTC/USDT": (95000, 105000),
        "ETH/USDT": (3200, 3600),
        "SOL/USDT": (180, 220),
        "XRP/USDT": (2.0, 2.8),
        "ADA/USDT": (0.8, 1.2),
        "DOGE/USDT": (0.30, 0.45),
    }

    EXCHANGES = ["binance", "kraken", "coinbase", "kucoin", "bybit"]

    def __init__(
        self,
        opportunity_rate: float = 0.3,  # 30% chance per scan
        profit_range: tuple[float, float] = (0.05, 0.5),  # 0.05% to 0.5% profit
        execution_success_rate: float = 0.7,  # 70% of trades succeed
    ) -> None:
        """
        Initialize simulator.

        Args:
            opportunity_rate: Probability of finding an opportunity per scan
            profit_range: Range of profit percentages (min, max)
            execution_success_rate: Probability that a trade executes successfully
        """
        self.opportunity_rate = opportunity_rate
        self.profit_range = profit_range
        self.execution_success_rate = execution_success_rate
        self.symbols = list(self.PRICE_RANGES.keys())

    def maybe_generate_opportunity(self) -> ArbitrageOpportunity | None:
        """
        Maybe generate a simulated arbitrage opportunity.

        Returns:
            ArbitrageOpportunity if one is "found", None otherwise
        """
        if random.random() > self.opportunity_rate:
            return None

        # Pick random symbol and exchanges
        symbol = random.choice(self.symbols)
        buy_exchange, sell_exchange = random.sample(self.EXCHANGES, 2)

        # Generate realistic prices
        price_range = self.PRICE_RANGES[symbol]
        base_price = Decimal(str(random.uniform(*price_range)))

        # Generate profit spread
        profit_percent = Decimal(str(random.uniform(*self.profit_range)))
        spread = base_price * profit_percent / 100

        buy_price = base_price
        sell_price = base_price + spread

        # Calculate volumes based on price (smaller for expensive coins)
        if base_price > 10000:
            volume = Decimal(str(random.uniform(0.01, 0.1)))
        elif base_price > 100:
            volume = Decimal(str(random.uniform(0.1, 2.0)))
        else:
            volume = Decimal(str(random.uniform(10, 500)))

        # Fees (typically 0.05% to 0.1% per side)
        buy_fee = Decimal(str(random.uniform(0.04, 0.1)))
        sell_fee = Decimal(str(random.uniform(0.04, 0.1)))

        # Calculate net profit after fees
        gross_profit = profit_percent
        total_fees = buy_fee + sell_fee
        net_profit = gross_profit - total_fees
        estimated_profit_usd = volume * buy_price * net_profit / 100

        # Slippage estimate
        slippage = Decimal(str(random.uniform(0.01, 0.05)))

        now = datetime.utcnow()

        opportunity = ArbitrageOpportunity(
            id=str(uuid4()),
            type=ArbitrageType.CROSS_EXCHANGE,
            status=OpportunityStatus.DETECTED,
            buy_exchange=buy_exchange,
            sell_exchange=sell_exchange,
            symbol=symbol,
            buy_price=buy_price.quantize(Decimal("0.01")),
            sell_price=sell_price.quantize(Decimal("0.01")),
            max_volume=volume * 2,
            recommended_volume=volume.quantize(Decimal("0.0001")),
            gross_profit_percent=gross_profit.quantize(Decimal("0.0001")),
            net_profit_percent=net_profit.quantize(Decimal("0.0001")),
            estimated_profit_usd=estimated_profit_usd.quantize(Decimal("0.01")),
            buy_fee_percent=buy_fee.quantize(Decimal("0.0001")),
            sell_fee_percent=sell_fee.quantize(Decimal("0.0001")),
            estimated_slippage_percent=slippage.quantize(Decimal("0.0001")),
            detected_at=now,
            expires_at=now + timedelta(seconds=random.randint(2, 10)),
            window_ms=random.randint(1000, 5000),
            orderbook_depth_ok=True,
            liquidity_ok=True,
            risk_score=Decimal(str(random.uniform(0.1, 0.4))).quantize(Decimal("0.01")),
        )

        logger.info(
            f"Simulated opportunity: {symbol} {buy_exchange}->{sell_exchange} "
            f"profit={net_profit:.4f}% (${estimated_profit_usd:.2f})"
        )

        return opportunity

    def generate_orderbook(
        self, symbol: str, exchange: str, base_price: Decimal
    ) -> Orderbook:
        """
        Generate a realistic orderbook for simulation.

        Args:
            symbol: Trading pair symbol
            exchange: Exchange name
            base_price: Base price for the orderbook

        Returns:
            Simulated Orderbook
        """
        spread = base_price * Decimal("0.0001")  # 0.01% spread

        bids = []
        asks = []

        for i in range(10):
            bid_price = base_price - spread * (i + 1)
            ask_price = base_price + spread * (i + 1)

            # High volume for simulation to ensure trades execute
            volume = Decimal(str(random.uniform(50, 200)))

            bids.append(OrderbookLevel(
                price=bid_price.quantize(Decimal("0.01")),
                volume=volume.quantize(Decimal("0.0001")),
            ))
            asks.append(OrderbookLevel(
                price=ask_price.quantize(Decimal("0.01")),
                volume=volume.quantize(Decimal("0.0001")),
            ))

        return Orderbook(
            symbol=symbol,
            exchange=Exchange.BINANCE,  # Use enum for validation
            bids=bids,
            asks=asks,
            timestamp=datetime.utcnow(),
        )

    def should_execute_successfully(self) -> bool:
        """
        Determine if a simulated trade should execute successfully.

        Returns:
            True if trade should succeed, False otherwise
        """
        return random.random() < self.execution_success_rate
