"""Unit tests for arbitrage calculator and detector."""

from datetime import datetime
from decimal import Decimal

import pytest

from src.arbitrage.calculator import ArbitrageCalculator
from src.models.market import Exchange, Orderbook, OrderbookLevel, Ticker


class TestArbitrageCalculator:
    """Tests for ArbitrageCalculator."""

    @pytest.fixture
    def calculator(self) -> ArbitrageCalculator:
        """Create calculator instance."""
        return ArbitrageCalculator()

    def test_calculate_cross_exchange_profit_positive(
        self,
        calculator: ArbitrageCalculator,
    ) -> None:
        """Test profit calculation with positive spread."""
        # Create tickers with a spread large enough to profit after fees
        buy_ticker = Ticker(
            symbol="BTC/USDT",
            exchange=Exchange.BINANCE,
            bid=Decimal("67000"),
            ask=Decimal("67010"),  # Buy at 67010
            timestamp=datetime.utcnow(),
        )
        sell_ticker = Ticker(
            symbol="BTC/USDT",
            exchange=Exchange.KRAKEN,
            bid=Decimal("67300"),  # Sell at 67300 (0.43% higher)
            ask=Decimal("67310"),
            timestamp=datetime.utcnow(),
        )

        gross, net, profit_usd = calculator.calculate_cross_exchange_profit(
            buy_ticker=buy_ticker,
            sell_ticker=sell_ticker,
            buy_fee_percent=Decimal("0.1"),
            sell_fee_percent=Decimal("0.1"),
            volume=Decimal("1"),
        )

        # Gross should be positive (buy at 67010, sell at 67300)
        assert gross > 0
        # Net should be gross minus fees
        assert net < gross
        # With 0.43% spread and 0.2% fees, profit should be positive
        assert profit_usd > 0

    def test_calculate_cross_exchange_profit_negative(
        self,
        calculator: ArbitrageCalculator,
    ) -> None:
        """Test profit calculation with negative spread."""
        buy_ticker = Ticker(
            symbol="BTC/USDT",
            exchange=Exchange.BINANCE,
            bid=Decimal("67100"),
            ask=Decimal("67110"),  # Buy price higher
            timestamp=datetime.utcnow(),
        )
        sell_ticker = Ticker(
            symbol="BTC/USDT",
            exchange=Exchange.KRAKEN,
            bid=Decimal("67000"),  # Sell price lower
            ask=Decimal("67010"),
            timestamp=datetime.utcnow(),
        )

        gross, net, profit_usd = calculator.calculate_cross_exchange_profit(
            buy_ticker=buy_ticker,
            sell_ticker=sell_ticker,
            buy_fee_percent=Decimal("0.1"),
            sell_fee_percent=Decimal("0.1"),
            volume=Decimal("1"),
        )

        assert gross < 0
        assert net < 0
        assert profit_usd < 0

    def test_calculate_cross_exchange_profit_zero_prices(
        self,
        calculator: ArbitrageCalculator,
    ) -> None:
        """Test profit calculation with zero prices."""
        ticker = Ticker(
            symbol="BTC/USDT",
            exchange=Exchange.BINANCE,
            bid=Decimal("0"),
            ask=Decimal("0"),
            timestamp=datetime.utcnow(),
        )

        gross, net, profit_usd = calculator.calculate_cross_exchange_profit(
            buy_ticker=ticker,
            sell_ticker=ticker,
            buy_fee_percent=Decimal("0.1"),
            sell_fee_percent=Decimal("0.1"),
            volume=Decimal("1"),
        )

        assert gross == Decimal("0")
        assert net == Decimal("0")
        assert profit_usd == Decimal("0")

    def test_calculate_max_executable_volume(
        self,
        calculator: ArbitrageCalculator,
        sample_orderbook: Orderbook,
        sample_orderbook_sell: Orderbook,
    ) -> None:
        """Test max executable volume calculation."""
        max_volume = calculator.calculate_max_executable_volume(
            buy_orderbook=sample_orderbook,
            sell_orderbook=sample_orderbook_sell,
            min_profit_percent=Decimal("0.05"),
            buy_fee_percent=Decimal("0.1"),
            sell_fee_percent=Decimal("0.1"),
        )

        # Should be able to execute some volume
        assert max_volume >= 0

    def test_calculate_max_executable_volume_no_spread(
        self,
        calculator: ArbitrageCalculator,
    ) -> None:
        """Test max volume with no profitable spread."""
        # Same orderbook for both sides - no spread
        orderbook = Orderbook(
            symbol="BTC/USDT",
            exchange=Exchange.BINANCE,
            bids=[OrderbookLevel(price=Decimal("67000"), volume=Decimal("1"))],
            asks=[OrderbookLevel(price=Decimal("67010"), volume=Decimal("1"))],
            timestamp=datetime.utcnow(),
        )

        max_volume = calculator.calculate_max_executable_volume(
            buy_orderbook=orderbook,
            sell_orderbook=orderbook,
            min_profit_percent=Decimal("1"),  # 1% min profit
            buy_fee_percent=Decimal("0.1"),
            sell_fee_percent=Decimal("0.1"),
        )

        # Should be 0 since spread doesn't cover fees + min profit
        assert max_volume == Decimal("0")

    def test_estimate_slippage_small_volume(
        self,
        calculator: ArbitrageCalculator,
        sample_orderbook: Orderbook,
    ) -> None:
        """Test slippage estimation for small volume."""
        slippage = calculator.estimate_slippage(
            orderbook=sample_orderbook,
            side="buy",
            volume=Decimal("0.5"),
        )

        # Small volume should have minimal slippage
        assert slippage >= Decimal("0")
        assert slippage < Decimal("1")

    def test_estimate_slippage_large_volume(
        self,
        calculator: ArbitrageCalculator,
        sample_orderbook: Orderbook,
    ) -> None:
        """Test slippage estimation for large volume."""
        slippage = calculator.estimate_slippage(
            orderbook=sample_orderbook,
            side="buy",
            volume=Decimal("100"),  # Larger than available
        )

        # Large volume should have high slippage
        assert slippage > Decimal("0")

    def test_estimate_slippage_zero_volume(
        self,
        calculator: ArbitrageCalculator,
        sample_orderbook: Orderbook,
    ) -> None:
        """Test slippage estimation for zero volume."""
        slippage = calculator.estimate_slippage(
            orderbook=sample_orderbook,
            side="buy",
            volume=Decimal("0"),
        )

        assert slippage == Decimal("0")

    def test_calculate_triangular_profit(
        self,
        calculator: ArbitrageCalculator,
    ) -> None:
        """Test triangular arbitrage profit calculation."""
        # USD -> BTC -> ETH -> USD
        profit, is_forward = calculator.calculate_triangular_profit(
            price_ab=Decimal("67000"),  # BTC/USD
            price_bc=Decimal("0.05"),  # ETH/BTC
            price_ca=Decimal("3350"),  # USD/ETH
            fee_percent=Decimal("0.1"),
        )

        # Should return some value
        assert isinstance(profit, Decimal)
        assert isinstance(is_forward, bool)

    def test_calculate_effective_rate(
        self,
        calculator: ArbitrageCalculator,
    ) -> None:
        """Test effective rate calculation."""
        effective = calculator.calculate_effective_rate(
            rate=Decimal("1"),
            fee_percent=Decimal("0.2"),
            slippage_percent=Decimal("0.1"),
        )

        assert effective == Decimal("0.7")
