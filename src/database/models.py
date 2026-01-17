"""SQLAlchemy database models."""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class DBOpportunity(Base):
    """Database model for arbitrage opportunities."""

    __tablename__ = "opportunities"

    id = Column(String(36), primary_key=True)
    type = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False)
    buy_exchange = Column(String(50), nullable=False)
    sell_exchange = Column(String(50), nullable=False)
    symbol = Column(String(20), nullable=False)
    buy_price = Column(Numeric(20, 10), nullable=False)
    sell_price = Column(Numeric(20, 10), nullable=False)
    max_volume = Column(Numeric(20, 10), nullable=False)
    recommended_volume = Column(Numeric(20, 10), nullable=False)
    gross_profit_percent = Column(Numeric(10, 6), nullable=False)
    net_profit_percent = Column(Numeric(10, 6), nullable=False)
    estimated_profit_usd = Column(Numeric(20, 10), nullable=False)
    buy_fee_percent = Column(Numeric(10, 6), nullable=False)
    sell_fee_percent = Column(Numeric(10, 6), nullable=False)
    estimated_slippage_percent = Column(Numeric(10, 6), nullable=False)
    detected_at = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    window_ms = Column(Integer, nullable=False)
    orderbook_depth_ok = Column(Boolean, default=False)
    liquidity_ok = Column(Boolean, default=False)
    would_have_executed = Column(Boolean, nullable=True)
    risk_score = Column(Numeric(5, 4), default=0.5)

    # Relationships
    trades = relationship("DBTrade", back_populates="opportunity")


class DBTrade(Base):
    """Database model for completed trades."""

    __tablename__ = "trades"

    id = Column(String(36), primary_key=True)
    opportunity_id = Column(String(36), ForeignKey("opportunities.id"), nullable=False)
    type = Column(String(50), nullable=False)
    mode = Column(String(10), nullable=False)
    gross_profit = Column(Numeric(20, 10), default=0)
    total_fees = Column(Numeric(20, 10), default=0)
    net_profit = Column(Numeric(20, 10), default=0)
    net_profit_percent = Column(Numeric(10, 6), default=0)
    status = Column(String(20), nullable=False)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    total_execution_ms = Column(Integer, default=0)
    both_orders_would_have_executed = Column(Boolean, default=True)

    # Relationships
    opportunity = relationship("DBOpportunity", back_populates="trades")
    orders = relationship("DBOrder", back_populates="trade")


class DBOrder(Base):
    """Database model for individual orders."""

    __tablename__ = "orders"

    id = Column(String(36), primary_key=True)
    trade_id = Column(String(36), ForeignKey("trades.id"), nullable=False)
    exchange = Column(String(50), nullable=False)
    symbol = Column(String(20), nullable=False)
    side = Column(String(10), nullable=False)
    type = Column(String(10), nullable=False)
    requested_volume = Column(Numeric(20, 10), nullable=False)
    filled_volume = Column(Numeric(20, 10), default=0)
    requested_price = Column(Numeric(20, 10), nullable=True)
    average_fill_price = Column(Numeric(20, 10), nullable=True)
    status = Column(String(20), nullable=False)
    mode = Column(String(10), nullable=False)
    fee_paid = Column(Numeric(20, 10), default=0)
    fee_currency = Column(String(10), default="USD")
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    filled_at = Column(DateTime, nullable=True)
    would_have_executed = Column(Boolean, default=True)
    simulated_slippage = Column(Numeric(10, 6), default=0)
    execution_latency_ms = Column(Integer, default=0)

    # Relationships
    trade = relationship("DBTrade", back_populates="orders")


class DBPortfolioSnapshot(Base):
    """Database model for portfolio snapshots."""

    __tablename__ = "portfolio_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    total_value_usd = Column(Numeric(20, 10), nullable=False)
    total_pnl_usd = Column(Numeric(20, 10), nullable=False)
    total_pnl_percent = Column(Numeric(10, 6), nullable=False)
    realized_pnl = Column(Numeric(20, 10), nullable=False)
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    max_drawdown_usd = Column(Numeric(20, 10), default=0)
    max_drawdown_percent = Column(Numeric(10, 6), default=0)
    balances_json = Column(Text, nullable=False)  # JSON serialized balances


class DBMarketData(Base):
    """Database model for historical market data."""

    __tablename__ = "market_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    exchange = Column(String(50), nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    bid = Column(Numeric(20, 10), nullable=False)
    ask = Column(Numeric(20, 10), nullable=False)
    bid_volume = Column(Numeric(20, 10), default=0)
    ask_volume = Column(Numeric(20, 10), default=0)
    spread_percent = Column(Numeric(10, 6), nullable=False)
