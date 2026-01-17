"""Order validation for paper trading."""

from decimal import Decimal

from loguru import logger

from src.models.market import Orderbook
from src.models.trade import Order


class OrderValidator:
    """Validate if orders would have executed in live trading."""

    def __init__(self) -> None:
        """Initialize order validator."""
        self.min_fill_ratio = Decimal("0.95")  # 95% fill required
        self.max_price_deviation = Decimal("0.01")  # 1% max deviation

    def would_have_executed(
        self,
        order: Order,
        orderbook: Orderbook,
        side: str,
    ) -> bool:
        """
        Check if an order would have executed based on orderbook state.

        Args:
            order: The order to validate
            orderbook: Current orderbook state
            side: "buy" (hit asks) or "sell" (hit bids)

        Returns:
            True if order would have executed
        """
        # Get executable price and volume from orderbook
        avg_price, available_volume = orderbook.get_executable_price(side, order.requested_volume)

        # Check if sufficient liquidity
        if available_volume < order.requested_volume * self.min_fill_ratio:
            logger.debug(
                f"Order would fail: insufficient liquidity. "
                f"Requested={order.requested_volume}, Available={available_volume}"
            )
            return False

        # Check price deviation
        if order.average_fill_price:
            if side == "buy":
                # For buys, actual price should not be much higher than expected
                if avg_price > order.average_fill_price * (1 + self.max_price_deviation):
                    logger.debug(
                        f"Order would fail: price too high. "
                        f"Expected={order.average_fill_price}, Actual={avg_price}"
                    )
                    return False
            else:
                # For sells, actual price should not be much lower than expected
                if avg_price < order.average_fill_price * (1 - self.max_price_deviation):
                    logger.debug(
                        f"Order would fail: price too low. "
                        f"Expected={order.average_fill_price}, Actual={avg_price}"
                    )
                    return False

        return True

    def validate_orderbook_depth(
        self,
        orderbook: Orderbook,
        volume: Decimal,
        side: str,
    ) -> tuple[bool, str]:
        """
        Validate orderbook has sufficient depth.

        Args:
            orderbook: Current orderbook state
            volume: Required volume
            side: "buy" or "sell"

        Returns:
            Tuple of (is_valid, reason)
        """
        total_volume = orderbook.get_total_volume(side, depth=10)

        if total_volume < volume:
            return False, f"Insufficient depth: {total_volume} < {volume}"

        if total_volume < volume * 2:
            return True, "Warning: Limited depth, high slippage expected"

        return True, "OK"

    def validate_spread(
        self,
        orderbook: Orderbook,
        max_spread_percent: Decimal = Decimal("0.5"),
    ) -> tuple[bool, str]:
        """
        Validate orderbook spread is acceptable.

        Args:
            orderbook: Current orderbook state
            max_spread_percent: Maximum acceptable spread

        Returns:
            Tuple of (is_valid, reason)
        """
        if not orderbook.bids or not orderbook.asks:
            return False, "Empty orderbook"

        spread = orderbook.spread
        best_bid = orderbook.best_bid

        if best_bid == 0:
            return False, "Invalid bid price"

        spread_percent = (spread / best_bid) * 100

        if spread_percent > max_spread_percent:
            return False, f"Spread too wide: {spread_percent:.2f}% > {max_spread_percent}%"

        return True, "OK"

    def estimate_fill_probability(
        self,
        order: Order,
        orderbook: Orderbook,
        side: str,
    ) -> Decimal:
        """
        Estimate probability that order would fill.

        Args:
            order: The order to estimate
            orderbook: Current orderbook state
            side: "buy" or "sell"

        Returns:
            Probability between 0 and 1
        """
        _, available_volume = orderbook.get_executable_price(side, order.requested_volume)

        if available_volume == 0:
            return Decimal("0")

        # Full fill likely
        if available_volume >= order.requested_volume * 2:
            return Decimal("0.95")

        # Sufficient volume
        if available_volume >= order.requested_volume:
            volume_ratio = available_volume / order.requested_volume
            return min(Decimal("0.9"), volume_ratio * Decimal("0.5"))

        # Partial fill likely
        fill_ratio = available_volume / order.requested_volume
        return fill_ratio * Decimal("0.5")

    def check_execution_window(
        self,
        order_timestamp_ms: int,
        orderbook_timestamp_ms: int,
        max_age_ms: int = 100,
    ) -> bool:
        """
        Check if orderbook data is fresh enough for order validation.

        Args:
            order_timestamp_ms: When order was placed
            orderbook_timestamp_ms: When orderbook was captured
            max_age_ms: Maximum acceptable age

        Returns:
            True if orderbook is fresh enough
        """
        age = abs(order_timestamp_ms - orderbook_timestamp_ms)
        return age <= max_age_ms
