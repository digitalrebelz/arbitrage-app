"""Pytest configuration and fixtures."""

from datetime import datetime
from decimal import Decimal

import pytest

from src.models.market import Exchange, Orderbook, OrderbookLevel, Ticker
from src.models.opportunity import ArbitrageOpportunity, ArbitrageType, OpportunityStatus
from src.models.portfolio import Balance, Portfolio
from src.models.trade import Order, OrderSide, OrderStatus, OrderType, TradeMode


@pytest.fixture
def sample_ticker() -> Ticker:
    """Create a sample ticker for testing."""
    return Ticker(
        symbol="BTC/USDT",
        exchange=Exchange.BINANCE,
        bid=Decimal("67000.00"),
        ask=Decimal("67010.00"),
        bid_volume=Decimal("10.5"),
        ask_volume=Decimal("8.2"),
        timestamp=datetime.utcnow(),
    )


@pytest.fixture
def sample_ticker_higher() -> Ticker:
    """Create a sample ticker with higher price."""
    return Ticker(
        symbol="BTC/USDT",
        exchange=Exchange.KRAKEN,
        bid=Decimal("67100.00"),
        ask=Decimal("67110.00"),
        bid_volume=Decimal("5.0"),
        ask_volume=Decimal("4.0"),
        timestamp=datetime.utcnow(),
    )


@pytest.fixture
def sample_orderbook() -> Orderbook:
    """Create a sample orderbook for testing."""
    return Orderbook(
        symbol="BTC/USDT",
        exchange=Exchange.BINANCE,
        bids=[
            OrderbookLevel(price=Decimal("67000.00"), volume=Decimal("1.0")),
            OrderbookLevel(price=Decimal("66995.00"), volume=Decimal("2.0")),
            OrderbookLevel(price=Decimal("66990.00"), volume=Decimal("3.0")),
            OrderbookLevel(price=Decimal("66985.00"), volume=Decimal("5.0")),
            OrderbookLevel(price=Decimal("66980.00"), volume=Decimal("10.0")),
        ],
        asks=[
            OrderbookLevel(price=Decimal("67010.00"), volume=Decimal("1.5")),
            OrderbookLevel(price=Decimal("67015.00"), volume=Decimal("2.5")),
            OrderbookLevel(price=Decimal("67020.00"), volume=Decimal("3.5")),
            OrderbookLevel(price=Decimal("67025.00"), volume=Decimal("5.0")),
            OrderbookLevel(price=Decimal("67030.00"), volume=Decimal("10.0")),
        ],
        timestamp=datetime.utcnow(),
    )


@pytest.fixture
def sample_orderbook_sell() -> Orderbook:
    """Create a sample orderbook for sell side."""
    return Orderbook(
        symbol="BTC/USDT",
        exchange=Exchange.KRAKEN,
        bids=[
            OrderbookLevel(price=Decimal("67100.00"), volume=Decimal("1.0")),
            OrderbookLevel(price=Decimal("67095.00"), volume=Decimal("2.0")),
            OrderbookLevel(price=Decimal("67090.00"), volume=Decimal("3.0")),
            OrderbookLevel(price=Decimal("67085.00"), volume=Decimal("5.0")),
            OrderbookLevel(price=Decimal("67080.00"), volume=Decimal("10.0")),
        ],
        asks=[
            OrderbookLevel(price=Decimal("67110.00"), volume=Decimal("1.5")),
            OrderbookLevel(price=Decimal("67115.00"), volume=Decimal("2.5")),
            OrderbookLevel(price=Decimal("67120.00"), volume=Decimal("3.5")),
            OrderbookLevel(price=Decimal("67125.00"), volume=Decimal("5.0")),
            OrderbookLevel(price=Decimal("67130.00"), volume=Decimal("10.0")),
        ],
        timestamp=datetime.utcnow(),
    )


@pytest.fixture
def sample_opportunity() -> ArbitrageOpportunity:
    """Create a sample arbitrage opportunity."""
    now = datetime.utcnow()
    from datetime import timedelta

    return ArbitrageOpportunity(
        id="test-opp-123",
        type=ArbitrageType.CROSS_EXCHANGE,
        status=OpportunityStatus.DETECTED,
        buy_exchange="binance",
        sell_exchange="kraken",
        symbol="BTC/USDT",
        buy_price=Decimal("67010.00"),
        sell_price=Decimal("67100.00"),
        max_volume=Decimal("1.0"),
        recommended_volume=Decimal("0.5"),
        gross_profit_percent=Decimal("0.134"),
        net_profit_percent=Decimal("0.034"),
        estimated_profit_usd=Decimal("11.42"),
        buy_fee_percent=Decimal("0.1"),
        sell_fee_percent=Decimal("0.1"),
        estimated_slippage_percent=Decimal("0.02"),
        detected_at=now,
        expires_at=now + timedelta(seconds=5),
        window_ms=5000,
        orderbook_depth_ok=True,
        liquidity_ok=True,
        risk_score=Decimal("0.3"),
    )


@pytest.fixture
def sample_order() -> Order:
    """Create a sample order."""
    return Order(
        id="test-order-123",
        opportunity_id="test-opp-123",
        exchange="binance",
        symbol="BTC/USDT",
        side=OrderSide.BUY,
        type=OrderType.MARKET,
        requested_volume=Decimal("0.5"),
        filled_volume=Decimal("0.5"),
        average_fill_price=Decimal("67010.00"),
        status=OrderStatus.FILLED,
        mode=TradeMode.PAPER,
        fee_paid=Decimal("33.505"),
        fee_currency="USD",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        would_have_executed=True,
        simulated_slippage=Decimal("0.01"),
    )


@pytest.fixture
def sample_portfolio() -> Portfolio:
    """Create a sample portfolio."""
    return Portfolio(
        balances={
            "USD": Balance(currency="USD", available=Decimal("10000")),
            "BTC": Balance(currency="BTC", available=Decimal("1.0")),
            "ETH": Balance(currency="ETH", available=Decimal("10.0")),
            "USDT": Balance(currency="USDT", available=Decimal("10000")),
        },
        total_value_usd=Decimal("10000"),
        initial_value_usd=Decimal("10000"),
        total_pnl_usd=Decimal("0"),
        total_pnl_percent=Decimal("0"),
        realized_pnl=Decimal("0"),
        unrealized_pnl=Decimal("0"),
        total_trades=0,
        winning_trades=0,
        losing_trades=0,
        max_drawdown_usd=Decimal("0"),
        max_drawdown_percent=Decimal("0"),
        last_updated=datetime.utcnow(),
    )
