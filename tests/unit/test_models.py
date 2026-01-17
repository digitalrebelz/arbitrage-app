"""Unit tests for Pydantic models."""

from datetime import datetime, timedelta
from decimal import Decimal

from src.models.market import Exchange, Orderbook, Ticker
from src.models.opportunity import ArbitrageOpportunity, ArbitrageType
from src.models.portfolio import Balance, Portfolio
from src.models.trade import Order


class TestTicker:
    """Tests for Ticker model."""

    def test_ticker_creation(self, sample_ticker: Ticker) -> None:
        """Test basic ticker creation."""
        assert sample_ticker.symbol == "BTC/USDT"
        assert sample_ticker.exchange == Exchange.BINANCE
        assert sample_ticker.bid == Decimal("67000.00")
        assert sample_ticker.ask == Decimal("67010.00")

    def test_ticker_spread(self, sample_ticker: Ticker) -> None:
        """Test spread calculation."""
        assert sample_ticker.spread == Decimal("10.00")

    def test_ticker_spread_percent(self, sample_ticker: Ticker) -> None:
        """Test spread percentage calculation."""
        expected = (Decimal("10.00") / Decimal("67000.00")) * 100
        assert sample_ticker.spread_percent == expected

    def test_ticker_mid_price(self, sample_ticker: Ticker) -> None:
        """Test mid price calculation."""
        expected = (Decimal("67000.00") + Decimal("67010.00")) / 2
        assert sample_ticker.mid_price == expected

    def test_ticker_zero_bid_spread_percent(self) -> None:
        """Test spread percent with zero bid."""
        ticker = Ticker(
            symbol="TEST/USD",
            exchange=Exchange.BINANCE,
            bid=Decimal("0"),
            ask=Decimal("100"),
            timestamp=datetime.utcnow(),
        )
        assert ticker.spread_percent == Decimal("0")


class TestOrderbook:
    """Tests for Orderbook model."""

    def test_orderbook_creation(self, sample_orderbook: Orderbook) -> None:
        """Test basic orderbook creation."""
        assert sample_orderbook.symbol == "BTC/USDT"
        assert len(sample_orderbook.bids) == 5
        assert len(sample_orderbook.asks) == 5

    def test_best_bid(self, sample_orderbook: Orderbook) -> None:
        """Test best bid price."""
        assert sample_orderbook.best_bid == Decimal("67000.00")

    def test_best_ask(self, sample_orderbook: Orderbook) -> None:
        """Test best ask price."""
        assert sample_orderbook.best_ask == Decimal("67010.00")

    def test_spread(self, sample_orderbook: Orderbook) -> None:
        """Test orderbook spread."""
        assert sample_orderbook.spread == Decimal("10.00")

    def test_get_executable_price_buy_small(self, sample_orderbook: Orderbook) -> None:
        """Test executable price for small buy order."""
        avg_price, filled = sample_orderbook.get_executable_price("buy", Decimal("1.0"))
        assert filled == Decimal("1.0")
        assert avg_price == Decimal("67010.00")  # First ask level

    def test_get_executable_price_buy_large(self, sample_orderbook: Orderbook) -> None:
        """Test executable price for large buy order spanning levels."""
        avg_price, filled = sample_orderbook.get_executable_price("buy", Decimal("4.0"))
        assert filled == Decimal("4.0")
        # 1.5 @ 67010 + 2.5 @ 67015 = 100515 + 167537.5 = 268052.5 / 4 = 67013.125
        expected = (
            Decimal("1.5") * Decimal("67010") + Decimal("2.5") * Decimal("67015")
        ) / Decimal("4")
        assert avg_price == expected

    def test_get_executable_price_sell_small(self, sample_orderbook: Orderbook) -> None:
        """Test executable price for small sell order."""
        avg_price, filled = sample_orderbook.get_executable_price("sell", Decimal("1.0"))
        assert filled == Decimal("1.0")
        assert avg_price == Decimal("67000.00")  # First bid level

    def test_get_total_volume(self, sample_orderbook: Orderbook) -> None:
        """Test total volume calculation."""
        buy_volume = sample_orderbook.get_total_volume("buy", depth=5)
        sell_volume = sample_orderbook.get_total_volume("sell", depth=5)
        assert buy_volume == Decimal("22.5")  # Sum of ask volumes
        assert sell_volume == Decimal("21.0")  # Sum of bid volumes


class TestArbitrageOpportunity:
    """Tests for ArbitrageOpportunity model."""

    def test_opportunity_creation(self, sample_opportunity: ArbitrageOpportunity) -> None:
        """Test basic opportunity creation."""
        assert sample_opportunity.type == ArbitrageType.CROSS_EXCHANGE
        assert sample_opportunity.buy_exchange == "binance"
        assert sample_opportunity.sell_exchange == "kraken"

    def test_is_profitable(self, sample_opportunity: ArbitrageOpportunity) -> None:
        """Test profitability check."""
        assert sample_opportunity.is_profitable is True

    def test_is_valid(self, sample_opportunity: ArbitrageOpportunity) -> None:
        """Test validity check."""
        assert sample_opportunity.is_valid is True

    def test_is_valid_expired(self) -> None:
        """Test validity check for expired opportunity."""
        now = datetime.utcnow()
        opp = ArbitrageOpportunity(
            type=ArbitrageType.CROSS_EXCHANGE,
            buy_exchange="binance",
            sell_exchange="kraken",
            symbol="BTC/USDT",
            buy_price=Decimal("67010"),
            sell_price=Decimal("67100"),
            max_volume=Decimal("1"),
            recommended_volume=Decimal("0.5"),
            gross_profit_percent=Decimal("0.1"),
            net_profit_percent=Decimal("0.05"),
            estimated_profit_usd=Decimal("10"),
            buy_fee_percent=Decimal("0.1"),
            sell_fee_percent=Decimal("0.1"),
            estimated_slippage_percent=Decimal("0.01"),
            detected_at=now - timedelta(seconds=10),
            expires_at=now - timedelta(seconds=5),  # Expired
            window_ms=5000,
            orderbook_depth_ok=True,
            liquidity_ok=True,
        )
        assert opp.is_valid is False

    def test_total_fee_percent(self, sample_opportunity: ArbitrageOpportunity) -> None:
        """Test total fee calculation."""
        assert sample_opportunity.total_fee_percent == Decimal("0.2")

    def test_time_remaining_ms(self, sample_opportunity: ArbitrageOpportunity) -> None:
        """Test time remaining calculation."""
        remaining = sample_opportunity.time_remaining_ms
        assert remaining > 0
        assert remaining <= 5000


class TestBalance:
    """Tests for Balance model."""

    def test_balance_total(self) -> None:
        """Test balance total calculation."""
        balance = Balance(currency="USD", available=Decimal("1000"), locked=Decimal("500"))
        assert balance.total == Decimal("1500")

    def test_can_afford(self) -> None:
        """Test can_afford check."""
        balance = Balance(currency="USD", available=Decimal("1000"))
        assert balance.can_afford(Decimal("500")) is True
        assert balance.can_afford(Decimal("1500")) is False

    def test_lock(self) -> None:
        """Test locking funds."""
        balance = Balance(currency="USD", available=Decimal("1000"))
        result = balance.lock(Decimal("300"))
        assert result is True
        assert balance.available == Decimal("700")
        assert balance.locked == Decimal("300")

    def test_lock_insufficient(self) -> None:
        """Test locking with insufficient funds."""
        balance = Balance(currency="USD", available=Decimal("100"))
        result = balance.lock(Decimal("300"))
        assert result is False
        assert balance.available == Decimal("100")

    def test_unlock(self) -> None:
        """Test unlocking funds."""
        balance = Balance(currency="USD", available=Decimal("700"), locked=Decimal("300"))
        balance.unlock(Decimal("300"))
        assert balance.available == Decimal("1000")
        assert balance.locked == Decimal("0")


class TestPortfolio:
    """Tests for Portfolio model."""

    def test_win_rate_no_trades(self, sample_portfolio: Portfolio) -> None:
        """Test win rate with no trades."""
        assert sample_portfolio.win_rate == Decimal("0")

    def test_win_rate_with_trades(self, sample_portfolio: Portfolio) -> None:
        """Test win rate calculation."""
        sample_portfolio.total_trades = 10
        sample_portfolio.winning_trades = 7
        sample_portfolio.losing_trades = 3
        assert sample_portfolio.win_rate == Decimal("70")

    def test_get_balance(self, sample_portfolio: Portfolio) -> None:
        """Test getting balance."""
        btc = sample_portfolio.get_balance("BTC")
        assert btc.available == Decimal("1.0")

    def test_get_balance_creates_if_missing(self, sample_portfolio: Portfolio) -> None:
        """Test getting balance creates new if missing."""
        sol = sample_portfolio.get_balance("SOL")
        assert sol.currency == "SOL"
        assert sol.available == Decimal("0")

    def test_record_trade_winning(self, sample_portfolio: Portfolio) -> None:
        """Test recording a winning trade."""
        sample_portfolio.record_trade(Decimal("100"))
        assert sample_portfolio.total_trades == 1
        assert sample_portfolio.winning_trades == 1
        assert sample_portfolio.losing_trades == 0
        assert sample_portfolio.total_pnl_usd == Decimal("100")

    def test_record_trade_losing(self, sample_portfolio: Portfolio) -> None:
        """Test recording a losing trade."""
        sample_portfolio.record_trade(Decimal("-50"))
        assert sample_portfolio.total_trades == 1
        assert sample_portfolio.winning_trades == 0
        assert sample_portfolio.losing_trades == 1
        assert sample_portfolio.total_pnl_usd == Decimal("-50")

    def test_record_trade_updates_drawdown(self, sample_portfolio: Portfolio) -> None:
        """Test that recording losses updates drawdown."""
        sample_portfolio.record_trade(Decimal("-500"))
        assert sample_portfolio.max_drawdown_usd == Decimal("500")
        assert sample_portfolio.max_drawdown_percent == Decimal("5")


class TestOrder:
    """Tests for Order model."""

    def test_order_is_filled(self, sample_order: Order) -> None:
        """Test is_filled property."""
        assert sample_order.is_filled is True

    def test_order_fill_percent(self, sample_order: Order) -> None:
        """Test fill percentage."""
        assert sample_order.fill_percent == Decimal("100")

    def test_order_total_cost(self, sample_order: Order) -> None:
        """Test total cost calculation."""
        expected = Decimal("0.5") * Decimal("67010.00") + Decimal("33.505")
        assert sample_order.total_cost == expected
