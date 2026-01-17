"""Arbitrage opportunity models."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class ArbitrageType(str, Enum):
    """Type of arbitrage opportunity."""

    CROSS_EXCHANGE = "cross_exchange"
    TRIANGULAR = "triangular"
    FUNDING_RATE = "funding_rate"
    STATISTICAL = "statistical"


class OpportunityStatus(str, Enum):
    """Status of an arbitrage opportunity."""

    DETECTED = "detected"
    ANALYZING = "analyzing"
    EXECUTABLE = "executable"
    EXPIRED = "expired"
    EXECUTED = "executed"
    FAILED = "failed"


class ArbitrageOpportunity(BaseModel):
    """Represents a detected arbitrage opportunity."""

    id: str = Field(default_factory=lambda: str(uuid4()), description="Unique opportunity ID")
    type: ArbitrageType = Field(..., description="Type of arbitrage")
    status: OpportunityStatus = Field(
        default=OpportunityStatus.DETECTED, description="Current status"
    )

    # Exchange info
    buy_exchange: str = Field(..., description="Exchange to buy from")
    sell_exchange: str = Field(..., description="Exchange to sell on")
    symbol: str = Field(..., description="Trading pair symbol")

    # Prices
    buy_price: Decimal = Field(..., description="Buy price (ask on buy exchange)")
    sell_price: Decimal = Field(..., description="Sell price (bid on sell exchange)")

    # Volumes
    max_volume: Decimal = Field(..., description="Maximum executable volume")
    recommended_volume: Decimal = Field(..., description="Recommended trade volume")

    # Profit calculations
    gross_profit_percent: Decimal = Field(..., description="Gross profit before fees (%)")
    net_profit_percent: Decimal = Field(..., description="Net profit after fees and slippage (%)")
    estimated_profit_usd: Decimal = Field(..., description="Estimated profit in USD")

    # Fees
    buy_fee_percent: Decimal = Field(..., description="Fee on buy exchange (%)")
    sell_fee_percent: Decimal = Field(..., description="Fee on sell exchange (%)")
    transfer_fee: Decimal = Field(default=Decimal("0"), description="Transfer/withdrawal fee")

    # Slippage
    estimated_slippage_percent: Decimal = Field(..., description="Estimated slippage (%)")

    # Timing
    detected_at: datetime = Field(default_factory=datetime.utcnow, description="Detection time")
    expires_at: datetime = Field(..., description="Expiration time")
    window_ms: int = Field(..., description="Opportunity window in milliseconds")

    # Validation flags
    orderbook_depth_ok: bool = Field(default=False, description="Sufficient orderbook depth")
    liquidity_ok: bool = Field(default=False, description="Sufficient liquidity")
    would_have_executed: bool | None = Field(
        default=None, description="Would trade have executed"
    )

    # Risk
    risk_score: Decimal = Field(
        default=Decimal("0.5"), ge=Decimal("0"), le=Decimal("1"), description="Risk score 0-1"
    )

    @property
    def is_profitable(self) -> bool:
        """Check if opportunity is profitable after all costs."""
        return self.net_profit_percent > 0

    @property
    def is_valid(self) -> bool:
        """Check if opportunity is still valid."""
        return (
            datetime.utcnow() < self.expires_at
            and self.status in (OpportunityStatus.DETECTED, OpportunityStatus.EXECUTABLE)
            and self.orderbook_depth_ok
            and self.liquidity_ok
        )

    @property
    def time_remaining_ms(self) -> int:
        """Get remaining time in milliseconds."""
        remaining = (self.expires_at - datetime.utcnow()).total_seconds() * 1000
        return max(0, int(remaining))

    @property
    def total_fee_percent(self) -> Decimal:
        """Get total fees as percentage."""
        return self.buy_fee_percent + self.sell_fee_percent
