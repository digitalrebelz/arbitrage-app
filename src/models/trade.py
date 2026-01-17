"""Trade and order models."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field

from src.models.opportunity import ArbitrageType


class OrderSide(str, Enum):
    """Order side (buy or sell)."""

    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    """Order type."""

    MARKET = "market"
    LIMIT = "limit"


class OrderStatus(str, Enum):
    """Order execution status."""

    PENDING = "pending"
    OPEN = "open"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELLED = "cancelled"
    FAILED = "failed"


class TradeMode(str, Enum):
    """Trading mode."""

    PAPER = "paper"
    LIVE = "live"


class Order(BaseModel):
    """Represents a single order (buy or sell)."""

    id: str = Field(default_factory=lambda: str(uuid4()), description="Unique order ID")
    opportunity_id: str = Field(..., description="Associated opportunity ID")

    # Order details
    exchange: str = Field(..., description="Exchange to execute on")
    symbol: str = Field(..., description="Trading pair symbol")
    side: OrderSide = Field(..., description="Buy or sell")
    type: OrderType = Field(..., description="Market or limit order")

    # Volumes
    requested_volume: Decimal = Field(..., description="Requested volume")
    filled_volume: Decimal = Field(default=Decimal("0"), description="Filled volume")

    # Prices
    requested_price: Decimal | None = Field(default=None, description="Limit price if set")
    average_fill_price: Decimal | None = Field(
        default=None, description="Average execution price"
    )

    # Status
    status: OrderStatus = Field(default=OrderStatus.PENDING, description="Order status")
    mode: TradeMode = Field(..., description="Paper or live trading")

    # Fees
    fee_paid: Decimal = Field(default=Decimal("0"), description="Total fee paid")
    fee_currency: str = Field(default="USD", description="Fee currency")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation time")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update time")
    filled_at: datetime | None = Field(default=None, description="Fill time")

    # Paper trading specifics
    would_have_executed: bool = Field(
        default=True, description="Would this have executed in live trading"
    )
    simulated_slippage: Decimal = Field(default=Decimal("0"), description="Simulated slippage %")
    execution_latency_ms: int = Field(default=0, description="Execution latency in ms")

    @property
    def is_filled(self) -> bool:
        """Check if order is fully filled."""
        return self.status == OrderStatus.FILLED

    @property
    def fill_percent(self) -> Decimal:
        """Get fill percentage."""
        if self.requested_volume == 0:
            return Decimal("0")
        return (self.filled_volume / self.requested_volume) * 100

    @property
    def total_cost(self) -> Decimal:
        """Get total cost including fees."""
        if self.average_fill_price is None:
            return Decimal("0")
        return self.filled_volume * self.average_fill_price + self.fee_paid


class Trade(BaseModel):
    """Represents a complete arbitrage trade (buy + sell)."""

    id: str = Field(default_factory=lambda: str(uuid4()), description="Unique trade ID")
    opportunity_id: str = Field(..., description="Associated opportunity ID")
    type: ArbitrageType = Field(..., description="Type of arbitrage")
    mode: TradeMode = Field(..., description="Paper or live trading")

    # Orders
    buy_order: Order = Field(..., description="Buy order")
    sell_order: Order = Field(..., description="Sell order")

    # P&L
    gross_profit: Decimal = Field(default=Decimal("0"), description="Gross profit")
    total_fees: Decimal = Field(default=Decimal("0"), description="Total fees paid")
    net_profit: Decimal = Field(default=Decimal("0"), description="Net profit after fees")
    net_profit_percent: Decimal = Field(default=Decimal("0"), description="Net profit %")

    # Status
    status: str = Field(default="pending", description="Trade status")
    error_message: str | None = Field(default=None, description="Error message if failed")

    # Timestamps
    started_at: datetime = Field(default_factory=datetime.utcnow, description="Start time")
    completed_at: datetime | None = Field(default=None, description="Completion time")
    total_execution_ms: int = Field(default=0, description="Total execution time in ms")

    # Validation
    both_orders_would_have_executed: bool = Field(
        default=True, description="Would both orders have executed"
    )

    @property
    def is_successful(self) -> bool:
        """Check if trade completed successfully."""
        return self.status == "completed" and self.both_orders_would_have_executed

    @property
    def is_profitable(self) -> bool:
        """Check if trade was profitable."""
        return self.net_profit > 0
