"""Funding rate arbitrage detection."""

from datetime import datetime
from decimal import Decimal

from src.models.opportunity import ArbitrageOpportunity, ArbitrageType, OpportunityStatus


class FundingRateArbitrage:
    """Detect funding rate arbitrage opportunities."""

    def __init__(self) -> None:
        """Initialize funding rate arbitrage detector."""
        self.min_funding_rate_percent = Decimal("0.01")  # 0.01% minimum
        self.funding_intervals_per_day = 3  # Most exchanges: every 8 hours

    async def scan_funding_opportunities(
        self,
        symbol: str,
        spot_price: Decimal,
        perp_price: Decimal,
        funding_rate: Decimal,
        next_funding_time: datetime,
    ) -> ArbitrageOpportunity | None:
        """
        Scan for funding rate arbitrage opportunities.

        Funding rate arbitrage works by:
        - If funding is positive: short perpetual, long spot
        - If funding is negative: long perpetual, short spot

        Args:
            symbol: Trading pair symbol
            spot_price: Current spot price
            perp_price: Current perpetual price
            funding_rate: Current funding rate (as decimal, e.g., 0.0001 = 0.01%)
            next_funding_time: Time of next funding payment

        Returns:
            ArbitrageOpportunity if profitable, None otherwise
        """
        funding_rate_percent = funding_rate * 100

        # Check minimum threshold
        if abs(funding_rate_percent) < self.min_funding_rate_percent:
            return None

        now = datetime.utcnow()
        time_to_funding = (next_funding_time - now).total_seconds()

        # Must be before funding time
        if time_to_funding < 0:
            return None

        # Calculate basis (difference between perp and spot)
        basis_percent = ((perp_price - spot_price) / spot_price) * 100

        # Determine direction and calculate profit
        if funding_rate > 0:
            # Positive funding: short perp, long spot
            # Shorts receive funding payment
            direction = "short_perp_long_spot"
            # Net profit = funding received - basis cost (entry/exit)
            net_profit_percent = funding_rate_percent - abs(basis_percent) * Decimal("0.5")
        else:
            # Negative funding: long perp, short spot
            # Longs receive funding payment
            direction = "long_perp_short_spot"
            net_profit_percent = abs(funding_rate_percent) - abs(basis_percent) * Decimal("0.5")

        # Subtract estimated trading fees (0.1% round trip)
        net_profit_percent -= Decimal("0.1")

        if net_profit_percent < self.min_funding_rate_percent:
            return None

        return ArbitrageOpportunity(
            type=ArbitrageType.FUNDING_RATE,
            status=OpportunityStatus.DETECTED,
            buy_exchange="spot" if direction == "short_perp_long_spot" else "perpetual",
            sell_exchange="perpetual" if direction == "short_perp_long_spot" else "spot",
            symbol=symbol,
            buy_price=spot_price if direction == "short_perp_long_spot" else perp_price,
            sell_price=perp_price if direction == "short_perp_long_spot" else spot_price,
            max_volume=Decimal("10"),  # Conservative limit
            recommended_volume=Decimal("1"),
            gross_profit_percent=abs(funding_rate_percent),
            net_profit_percent=net_profit_percent,
            estimated_profit_usd=net_profit_percent * spot_price / 100,
            buy_fee_percent=Decimal("0.05"),
            sell_fee_percent=Decimal("0.05"),
            estimated_slippage_percent=Decimal("0.02"),
            detected_at=now,
            expires_at=next_funding_time,
            window_ms=int(time_to_funding * 1000),
            orderbook_depth_ok=True,
            liquidity_ok=True,
            risk_score=Decimal("0.3"),  # Generally lower risk
        )

    def calculate_daily_return(
        self,
        funding_rate: Decimal,
        intervals_per_day: int = 3,
    ) -> Decimal:
        """
        Calculate expected daily return from funding.

        Args:
            funding_rate: Funding rate per interval
            intervals_per_day: Number of funding intervals per day

        Returns:
            Expected daily return as percentage
        """
        return funding_rate * 100 * intervals_per_day

    def calculate_annualized_return(
        self,
        funding_rate: Decimal,
        intervals_per_day: int = 3,
    ) -> Decimal:
        """
        Calculate annualized return from funding.

        Args:
            funding_rate: Funding rate per interval
            intervals_per_day: Number of funding intervals per day

        Returns:
            Annualized return as percentage
        """
        daily_return = self.calculate_daily_return(funding_rate, intervals_per_day)
        return daily_return * 365

    @staticmethod
    def estimate_basis_risk(
        spot_price: Decimal,
        perp_price: Decimal,
        historical_basis_volatility: Decimal,
    ) -> Decimal:
        """
        Estimate basis risk for the position.

        Args:
            spot_price: Current spot price
            perp_price: Current perpetual price
            historical_basis_volatility: Historical volatility of the basis

        Returns:
            Risk score (0-1)
        """
        current_basis = abs((perp_price - spot_price) / spot_price)

        # Higher basis and higher volatility = higher risk
        risk = min(
            Decimal("1"),
            current_basis * 10 + historical_basis_volatility * 5,
        )

        return max(Decimal("0"), risk)
