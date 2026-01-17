"""Slippage simulation for paper trading."""

import random
from decimal import Decimal

from src.models.market import Orderbook


class SlippageSimulator:
    """Simulate realistic slippage for paper trading."""

    def __init__(self) -> None:
        """Initialize slippage simulator."""
        self.base_slippage_bps = Decimal("5")  # 5 basis points = 0.05%
        self.volume_impact_factor = Decimal("0.1")  # Impact per unit of volume ratio
        self.volatility_factor = Decimal("0.5")  # Impact of market volatility
        self.random_factor_range = (0.8, 1.2)  # Random variation range

    def simulate(
        self,
        orderbook: Orderbook,
        side: str,
        volume: Decimal,
    ) -> Decimal:
        """
        Simulate slippage for an order.

        Args:
            orderbook: Current orderbook state
            side: "buy" or "sell"
            volume: Order volume

        Returns:
            Estimated slippage as percentage
        """
        # Base slippage (market impact)
        slippage = self.base_slippage_bps / 100

        # Volume impact - larger orders have more slippage
        if orderbook.bids and orderbook.asks:
            if side == "buy":
                top_level_volume = orderbook.asks[0].volume if orderbook.asks else Decimal("1")
            else:
                top_level_volume = orderbook.bids[0].volume if orderbook.bids else Decimal("1")

            if top_level_volume > 0:
                volume_ratio = volume / top_level_volume
                volume_slippage = volume_ratio * self.volume_impact_factor
                slippage += volume_slippage

        # Add randomness to simulate real-world variation
        random_factor = Decimal(str(random.uniform(*self.random_factor_range)))
        slippage *= random_factor

        # Cap maximum slippage
        slippage = min(slippage, Decimal("2"))  # Max 2%

        return slippage

    def simulate_with_orderbook_depth(
        self,
        orderbook: Orderbook,
        side: str,
        volume: Decimal,
    ) -> tuple[Decimal, Decimal]:
        """
        Simulate slippage using full orderbook depth.

        Args:
            orderbook: Current orderbook state
            side: "buy" (hit asks) or "sell" (hit bids)
            volume: Order volume

        Returns:
            Tuple of (average_fill_price, slippage_percent)
        """
        avg_price, filled_volume = orderbook.get_executable_price(side, volume)

        if filled_volume == 0 or avg_price == 0:
            return Decimal("0"), Decimal("100")  # No liquidity

        # Get best price
        best_price = orderbook.best_ask if side == "buy" else orderbook.best_bid

        if best_price == 0:
            return avg_price, Decimal("0")

        # Calculate actual slippage from orderbook
        actual_slippage = abs((avg_price - best_price) / best_price) * 100

        # Add some randomness
        random_factor = Decimal(str(random.uniform(0.9, 1.1)))
        final_slippage = actual_slippage * random_factor

        return avg_price, final_slippage

    def estimate_market_impact(
        self,
        orderbook: Orderbook,
        volume: Decimal,
        side: str,
    ) -> Decimal:
        """
        Estimate permanent market impact of a trade.

        Args:
            orderbook: Current orderbook state
            volume: Order volume
            side: "buy" or "sell"

        Returns:
            Estimated market impact as percentage
        """
        # Simple square-root market impact model
        # Impact ~ sqrt(volume / daily_volume)
        # We approximate daily volume from orderbook depth

        total_depth = orderbook.get_total_volume(side, depth=10)

        if total_depth == 0:
            return Decimal("1")  # 1% impact if no depth

        volume_ratio = volume / total_depth
        impact = Decimal(str(float(volume_ratio) ** 0.5)) * Decimal("0.1")

        return min(impact, Decimal("1"))

    def adjust_for_volatility(
        self,
        base_slippage: Decimal,
        volatility_percent: Decimal,
    ) -> Decimal:
        """
        Adjust slippage based on market volatility.

        Args:
            base_slippage: Base slippage estimate
            volatility_percent: Current market volatility

        Returns:
            Adjusted slippage
        """
        volatility_multiplier = 1 + (volatility_percent / 100) * self.volatility_factor
        return base_slippage * Decimal(str(volatility_multiplier))
