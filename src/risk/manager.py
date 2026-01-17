"""Risk management module."""

from decimal import Decimal

from loguru import logger

from src.config.settings import settings
from src.models.opportunity import ArbitrageOpportunity
from src.models.portfolio import Portfolio


class RiskManager:
    """Manage trading risk and position limits."""

    def __init__(self, portfolio: Portfolio) -> None:
        """
        Initialize risk manager.

        Args:
            portfolio: Portfolio to manage risk for
        """
        self.portfolio = portfolio
        self.max_position_size = Decimal(str(settings.MAX_POSITION_SIZE_USD))
        self.max_exposure = Decimal(str(settings.MAX_TOTAL_EXPOSURE_USD))
        self.max_drawdown_percent = Decimal(str(settings.MAX_DRAWDOWN_PERCENT))
        self.current_exposure = Decimal("0")

    def can_trade(self, opportunity: ArbitrageOpportunity) -> tuple[bool, str]:
        """
        Check if a trade is allowed based on risk parameters.

        Args:
            opportunity: The opportunity to evaluate

        Returns:
            Tuple of (allowed, reason)
        """
        # Check max drawdown
        if self.portfolio.max_drawdown_percent >= self.max_drawdown_percent:
            return False, f"Max drawdown exceeded: {self.portfolio.max_drawdown_percent}%"

        # Check position size
        trade_value = opportunity.recommended_volume * opportunity.buy_price
        if trade_value > self.max_position_size:
            return False, f"Position too large: ${trade_value} > ${self.max_position_size}"

        # Check total exposure
        new_exposure = self.current_exposure + trade_value
        if new_exposure > self.max_exposure:
            return False, f"Max exposure exceeded: ${new_exposure} > ${self.max_exposure}"

        # Check risk score
        if opportunity.risk_score > Decimal("0.8"):
            return False, f"Risk score too high: {opportunity.risk_score}"

        # Check minimum profit
        if opportunity.net_profit_percent < settings.MIN_PROFIT_THRESHOLD_PERCENT:
            return False, f"Profit too low: {opportunity.net_profit_percent}%"

        return True, "OK"

    def calculate_position_size(
        self,
        opportunity: ArbitrageOpportunity,
        max_loss_percent: Decimal = Decimal("1"),
    ) -> Decimal:
        """
        Calculate optimal position size based on risk.

        Uses Kelly Criterion simplified for arbitrage.

        Args:
            opportunity: The opportunity to size
            max_loss_percent: Maximum loss as percent of portfolio

        Returns:
            Recommended position size in base currency
        """
        # Base position size from settings
        base_size = self.max_position_size / opportunity.buy_price

        # Adjust for risk score (lower risk = larger position)
        risk_multiplier = 1 - float(opportunity.risk_score)
        adjusted_size = base_size * Decimal(str(risk_multiplier))

        # Adjust for profit potential (higher profit = larger position)
        profit_multiplier = min(float(opportunity.net_profit_percent) / 0.5, 2)
        adjusted_size *= Decimal(str(profit_multiplier))

        # Cap at max volume available
        adjusted_size = min(adjusted_size, opportunity.max_volume)

        # Apply max loss constraint
        max_loss_usd = self.portfolio.total_value_usd * max_loss_percent / 100
        max_size_from_loss = max_loss_usd / opportunity.buy_price
        adjusted_size = min(adjusted_size, max_size_from_loss)

        return adjusted_size

    def update_exposure(self, trade_value: Decimal, is_open: bool = True) -> None:
        """
        Update current exposure after a trade.

        Args:
            trade_value: Value of the trade
            is_open: True if opening position, False if closing
        """
        if is_open:
            self.current_exposure += trade_value
        else:
            self.current_exposure = max(Decimal("0"), self.current_exposure - trade_value)

    def check_stop_loss(self) -> tuple[bool, str | None]:
        """
        Check if stop loss conditions are met.

        Returns:
            Tuple of (should_stop, reason)
        """
        # Check max drawdown
        if self.portfolio.max_drawdown_percent >= self.max_drawdown_percent:
            return True, f"Max drawdown reached: {self.portfolio.max_drawdown_percent}%"

        # Check absolute loss
        max_loss = self.portfolio.initial_value_usd * self.max_drawdown_percent / 100
        if abs(self.portfolio.total_pnl_usd) >= max_loss and self.portfolio.total_pnl_usd < 0:
            return True, f"Max loss reached: ${abs(self.portfolio.total_pnl_usd)}"

        return False, None

    def get_risk_metrics(self) -> dict:
        """Get current risk metrics."""
        return {
            "current_exposure": float(self.current_exposure),
            "max_exposure": float(self.max_exposure),
            "exposure_percent": (
                float(self.current_exposure / self.max_exposure * 100)
                if self.max_exposure > 0
                else 0
            ),
            "current_drawdown": float(self.portfolio.max_drawdown_percent),
            "max_drawdown_limit": float(self.max_drawdown_percent),
            "total_pnl": float(self.portfolio.total_pnl_usd),
            "win_rate": float(self.portfolio.win_rate),
        }

    def reset_daily_limits(self) -> None:
        """Reset daily trading limits."""
        self.current_exposure = Decimal("0")
        logger.info("Daily risk limits reset")
