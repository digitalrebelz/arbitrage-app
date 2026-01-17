"""Unit tests for execution module (paper trader, validator, slippage)."""

from datetime import datetime
from decimal import Decimal

import pytest

from src.execution.order_validator import OrderValidator
from src.execution.slippage import SlippageSimulator
from src.models.market import Exchange, Orderbook, OrderbookLevel
from src.models.trade import Order, OrderSide, OrderStatus, OrderType, TradeMode


class TestOrderValidator:
    """Tests for OrderValidator."""

    @pytest.fixture
    def validator(self) -> OrderValidator:
        """Create validator instance."""
        return OrderValidator()

    def test_would_have_executed_sufficient_liquidity(
        self,
        validator: OrderValidator,
        sample_orderbook: Orderbook,
    ) -> None:
        """Test order would execute with sufficient liquidity."""
        order = Order(
            id="test-1",
            opportunity_id="opp-1",
            exchange="binance",
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            type=OrderType.MARKET,
            requested_volume=Decimal("1.0"),
            average_fill_price=Decimal("67010"),
            status=OrderStatus.PENDING,
            mode=TradeMode.PAPER,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        result = validator.would_have_executed(order, sample_orderbook, "buy")
        assert result is True

    def test_would_have_executed_insufficient_liquidity(
        self,
        validator: OrderValidator,
        sample_orderbook: Orderbook,
    ) -> None:
        """Test order would fail with insufficient liquidity."""
        order = Order(
            id="test-1",
            opportunity_id="opp-1",
            exchange="binance",
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            type=OrderType.MARKET,
            requested_volume=Decimal("1000"),  # Way more than available
            average_fill_price=Decimal("67010"),
            status=OrderStatus.PENDING,
            mode=TradeMode.PAPER,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        result = validator.would_have_executed(order, sample_orderbook, "buy")
        assert result is False

    def test_would_have_executed_price_deviation(
        self,
        validator: OrderValidator,
        sample_orderbook: Orderbook,
    ) -> None:
        """Test order would fail with excessive price deviation."""
        order = Order(
            id="test-1",
            opportunity_id="opp-1",
            exchange="binance",
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            type=OrderType.MARKET,
            requested_volume=Decimal("1.0"),
            average_fill_price=Decimal("60000"),  # Way off from market
            status=OrderStatus.PENDING,
            mode=TradeMode.PAPER,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        result = validator.would_have_executed(order, sample_orderbook, "buy")
        assert result is False

    def test_validate_orderbook_depth_sufficient(
        self,
        validator: OrderValidator,
        sample_orderbook: Orderbook,
    ) -> None:
        """Test orderbook depth validation with sufficient depth."""
        is_valid, reason = validator.validate_orderbook_depth(
            sample_orderbook, Decimal("1.0"), "buy"
        )
        assert is_valid is True

    def test_validate_orderbook_depth_insufficient(
        self,
        validator: OrderValidator,
        sample_orderbook: Orderbook,
    ) -> None:
        """Test orderbook depth validation with insufficient depth."""
        is_valid, reason = validator.validate_orderbook_depth(
            sample_orderbook, Decimal("100"), "buy"
        )
        assert is_valid is False
        assert "Insufficient" in reason

    def test_validate_spread_acceptable(
        self,
        validator: OrderValidator,
        sample_orderbook: Orderbook,
    ) -> None:
        """Test spread validation with acceptable spread."""
        is_valid, reason = validator.validate_spread(sample_orderbook, Decimal("0.5"))
        assert is_valid is True
        assert reason == "OK"

    def test_validate_spread_too_wide(
        self,
        validator: OrderValidator,
    ) -> None:
        """Test spread validation with too wide spread."""
        orderbook = Orderbook(
            symbol="BTC/USDT",
            exchange=Exchange.BINANCE,
            bids=[OrderbookLevel(price=Decimal("60000"), volume=Decimal("1"))],
            asks=[OrderbookLevel(price=Decimal("70000"), volume=Decimal("1"))],
            timestamp=datetime.utcnow(),
        )

        is_valid, reason = validator.validate_spread(orderbook, Decimal("0.5"))
        assert is_valid is False
        assert "too wide" in reason

    def test_estimate_fill_probability_high(
        self,
        validator: OrderValidator,
        sample_orderbook: Orderbook,
    ) -> None:
        """Test fill probability estimation with good liquidity."""
        order = Order(
            id="test-1",
            opportunity_id="opp-1",
            exchange="binance",
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            type=OrderType.MARKET,
            requested_volume=Decimal("0.5"),
            status=OrderStatus.PENDING,
            mode=TradeMode.PAPER,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        prob = validator.estimate_fill_probability(order, sample_orderbook, "buy")
        assert prob >= Decimal("0.5")

    def test_check_execution_window(
        self,
        validator: OrderValidator,
    ) -> None:
        """Test execution window check."""
        now = int(datetime.utcnow().timestamp() * 1000)

        # Fresh data
        assert validator.check_execution_window(now, now, 100) is True

        # Stale data
        assert validator.check_execution_window(now, now - 200, 100) is False


class TestSlippageSimulator:
    """Tests for SlippageSimulator."""

    @pytest.fixture
    def simulator(self) -> SlippageSimulator:
        """Create simulator instance."""
        return SlippageSimulator()

    def test_simulate_small_volume(
        self,
        simulator: SlippageSimulator,
        sample_orderbook: Orderbook,
    ) -> None:
        """Test slippage for small volume."""
        slippage = simulator.simulate(sample_orderbook, "buy", Decimal("0.1"))
        # Small volume should have low slippage
        assert slippage >= Decimal("0")
        assert slippage < Decimal("1")

    def test_simulate_large_volume(
        self,
        simulator: SlippageSimulator,
        sample_orderbook: Orderbook,
    ) -> None:
        """Test slippage for large volume."""
        slippage = simulator.simulate(sample_orderbook, "buy", Decimal("10"))
        # Larger volume should have more slippage
        assert slippage > Decimal("0")

    def test_simulate_capped_at_max(
        self,
        simulator: SlippageSimulator,
        sample_orderbook: Orderbook,
    ) -> None:
        """Test slippage is capped at maximum."""
        slippage = simulator.simulate(sample_orderbook, "buy", Decimal("1000"))
        assert slippage <= Decimal("2")  # Max 2%

    def test_simulate_with_orderbook_depth(
        self,
        simulator: SlippageSimulator,
        sample_orderbook: Orderbook,
    ) -> None:
        """Test slippage with full orderbook depth."""
        avg_price, slippage = simulator.simulate_with_orderbook_depth(
            sample_orderbook, "buy", Decimal("2.0")
        )
        assert avg_price > Decimal("0")
        assert slippage >= Decimal("0")

    def test_simulate_with_orderbook_depth_no_liquidity(
        self,
        simulator: SlippageSimulator,
    ) -> None:
        """Test slippage with no liquidity."""
        empty_orderbook = Orderbook(
            symbol="BTC/USDT",
            exchange=Exchange.BINANCE,
            bids=[],
            asks=[],
            timestamp=datetime.utcnow(),
        )

        avg_price, slippage = simulator.simulate_with_orderbook_depth(
            empty_orderbook, "buy", Decimal("1.0")
        )
        assert avg_price == Decimal("0")
        assert slippage == Decimal("100")

    def test_estimate_market_impact(
        self,
        simulator: SlippageSimulator,
        sample_orderbook: Orderbook,
    ) -> None:
        """Test market impact estimation."""
        impact = simulator.estimate_market_impact(sample_orderbook, Decimal("1.0"), "buy")
        assert impact >= Decimal("0")
        assert impact <= Decimal("1")

    def test_adjust_for_volatility(
        self,
        simulator: SlippageSimulator,
    ) -> None:
        """Test volatility adjustment."""
        base_slippage = Decimal("0.1")

        # High volatility should increase slippage
        high_vol = simulator.adjust_for_volatility(base_slippage, Decimal("50"))
        # Low volatility should keep slippage similar
        low_vol = simulator.adjust_for_volatility(base_slippage, Decimal("5"))

        assert high_vol > low_vol
