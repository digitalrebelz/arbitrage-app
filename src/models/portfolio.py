"""Portfolio and balance models."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class Balance(BaseModel):
    """Balance for a single currency."""

    currency: str = Field(..., description="Currency code (e.g., USD, BTC)")
    available: Decimal = Field(default=Decimal("0"), description="Available balance")
    locked: Decimal = Field(default=Decimal("0"), description="Locked in open orders")

    @property
    def total(self) -> Decimal:
        """Get total balance."""
        return self.available + self.locked

    def can_afford(self, amount: Decimal) -> bool:
        """Check if available balance covers the amount."""
        return self.available >= amount

    def lock(self, amount: Decimal) -> bool:
        """Lock an amount for an order."""
        if not self.can_afford(amount):
            return False
        self.available -= amount
        self.locked += amount
        return True

    def unlock(self, amount: Decimal) -> None:
        """Unlock an amount (order cancelled)."""
        unlock_amount = min(amount, self.locked)
        self.locked -= unlock_amount
        self.available += unlock_amount

    def fill(self, locked_amount: Decimal, received_amount: Decimal) -> None:
        """Complete a fill (locked amount spent, received amount added)."""
        self.locked -= min(locked_amount, self.locked)
        # Received amount would be in a different currency, handled separately


class Portfolio(BaseModel):
    """Complete portfolio state."""

    # Balances
    balances: dict[str, Balance] = Field(default_factory=dict, description="Currency balances")

    # Values
    total_value_usd: Decimal = Field(default=Decimal("0"), description="Total portfolio value")
    initial_value_usd: Decimal = Field(default=Decimal("0"), description="Initial portfolio value")

    # P&L
    total_pnl_usd: Decimal = Field(default=Decimal("0"), description="Total P&L in USD")
    total_pnl_percent: Decimal = Field(default=Decimal("0"), description="Total P&L %")
    realized_pnl: Decimal = Field(default=Decimal("0"), description="Realized P&L")
    unrealized_pnl: Decimal = Field(default=Decimal("0"), description="Unrealized P&L")

    # Trade statistics
    total_trades: int = Field(default=0, description="Total number of trades")
    winning_trades: int = Field(default=0, description="Number of winning trades")
    losing_trades: int = Field(default=0, description="Number of losing trades")

    # Risk metrics
    max_drawdown_usd: Decimal = Field(default=Decimal("0"), description="Maximum drawdown in USD")
    max_drawdown_percent: Decimal = Field(default=Decimal("0"), description="Maximum drawdown %")
    sharpe_ratio: Decimal | None = Field(default=None, description="Sharpe ratio")

    # Timestamp
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="Last update time")

    @property
    def win_rate(self) -> Decimal:
        """Calculate win rate percentage."""
        if self.total_trades == 0:
            return Decimal("0")
        return Decimal(self.winning_trades) / Decimal(self.total_trades) * 100

    @property
    def loss_rate(self) -> Decimal:
        """Calculate loss rate percentage."""
        if self.total_trades == 0:
            return Decimal("0")
        return Decimal(self.losing_trades) / Decimal(self.total_trades) * 100

    @property
    def profit_factor(self) -> Decimal | None:
        """Calculate profit factor (gross profits / gross losses)."""
        if self.losing_trades == 0 or self.winning_trades == 0:
            return None
        # Simplified - in real implementation, track gross profits/losses separately
        return Decimal(self.winning_trades) / Decimal(self.losing_trades)

    def get_balance(self, currency: str) -> Balance:
        """Get balance for a currency, creating if not exists."""
        if currency not in self.balances:
            self.balances[currency] = Balance(currency=currency, available=Decimal("0"))
        return self.balances[currency]

    def set_balance(
        self, currency: str, available: Decimal, locked: Decimal = Decimal("0")
    ) -> None:
        """Set balance for a currency."""
        self.balances[currency] = Balance(currency=currency, available=available, locked=locked)

    def add_balance(self, currency: str, amount: Decimal) -> None:
        """Add to available balance."""
        balance = self.get_balance(currency)
        balance.available += amount

    def subtract_balance(self, currency: str, amount: Decimal) -> bool:
        """Subtract from available balance."""
        balance = self.get_balance(currency)
        if not balance.can_afford(amount):
            return False
        balance.available -= amount
        return True

    def record_trade(self, profit: Decimal) -> None:
        """Record a completed trade."""
        self.total_trades += 1
        self.total_pnl_usd += profit
        self.realized_pnl += profit
        self.total_value_usd += profit

        if profit > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1

        # Update P&L percentage
        if self.initial_value_usd > 0:
            self.total_pnl_percent = self.total_pnl_usd / self.initial_value_usd * 100

        # Update max drawdown
        if self.total_pnl_usd < 0:
            drawdown = abs(self.total_pnl_usd)
            if drawdown > self.max_drawdown_usd:
                self.max_drawdown_usd = drawdown
                if self.initial_value_usd > 0:
                    self.max_drawdown_percent = drawdown / self.initial_value_usd * 100

        self.last_updated = datetime.utcnow()
