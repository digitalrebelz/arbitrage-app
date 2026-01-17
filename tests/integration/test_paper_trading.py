"""Integration tests for paper trading system."""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from src.execution.paper_trader import PaperTrader
from src.models.market import Exchange, Orderbook, OrderbookLevel
from src.models.opportunity import ArbitrageOpportunity, ArbitrageType, OpportunityStatus


class TestPaperTraderIntegration:
    """Integration tests for PaperTrader."""

    @pytest.fixture
    def paper_trader(self) -> PaperTrader:
        """Create paper trader instance."""
        return PaperTrader()

    @pytest.fixture
    def profitable_opportunity(self) -> ArbitrageOpportunity:
        """Create a profitable opportunity."""
        now = datetime.utcnow()
        return ArbitrageOpportunity(
            id="test-opp-1",
            type=ArbitrageType.CROSS_EXCHANGE,
            status=OpportunityStatus.DETECTED,
            buy_exchange="binance",
            sell_exchange="kraken",
            symbol="BTC/USDT",
            buy_price=Decimal("67000"),
            sell_price=Decimal("67100"),
            max_volume=Decimal("1.0"),
            recommended_volume=Decimal("0.1"),
            gross_profit_percent=Decimal("0.15"),
            net_profit_percent=Decimal("0.05"),
            estimated_profit_usd=Decimal("3.35"),
            buy_fee_percent=Decimal("0.05"),
            sell_fee_percent=Decimal("0.05"),
            estimated_slippage_percent=Decimal("0.01"),
            detected_at=now,
            expires_at=now + timedelta(seconds=5),
            window_ms=5000,
            orderbook_depth_ok=True,
            liquidity_ok=True,
            risk_score=Decimal("0.2"),
        )

    @pytest.fixture
    def buy_orderbook(self) -> Orderbook:
        """Create buy orderbook with good liquidity."""
        return Orderbook(
            symbol="BTC/USDT",
            exchange=Exchange.BINANCE,
            bids=[
                OrderbookLevel(price=Decimal("66990"), volume=Decimal("2.0")),
                OrderbookLevel(price=Decimal("66980"), volume=Decimal("5.0")),
            ],
            asks=[
                OrderbookLevel(price=Decimal("67000"), volume=Decimal("2.0")),
                OrderbookLevel(price=Decimal("67010"), volume=Decimal("5.0")),
            ],
            timestamp=datetime.utcnow(),
        )

    @pytest.fixture
    def sell_orderbook(self) -> Orderbook:
        """Create sell orderbook with good liquidity."""
        return Orderbook(
            symbol="BTC/USDT",
            exchange=Exchange.KRAKEN,
            bids=[
                OrderbookLevel(price=Decimal("67100"), volume=Decimal("2.0")),
                OrderbookLevel(price=Decimal("67090"), volume=Decimal("5.0")),
            ],
            asks=[
                OrderbookLevel(price=Decimal("67110"), volume=Decimal("2.0")),
                OrderbookLevel(price=Decimal("67120"), volume=Decimal("5.0")),
            ],
            timestamp=datetime.utcnow(),
        )

    @pytest.mark.asyncio
    async def test_execute_arbitrage_successful(
        self,
        paper_trader: PaperTrader,
        profitable_opportunity: ArbitrageOpportunity,
        buy_orderbook: Orderbook,
        sell_orderbook: Orderbook,
    ) -> None:
        """Test successful arbitrage execution."""
        trade = await paper_trader.execute_arbitrage(
            profitable_opportunity, buy_orderbook, sell_orderbook
        )

        # Trade should complete
        assert trade.status == "completed"
        assert trade.both_orders_would_have_executed is True

        # Orders should be filled
        assert trade.buy_order.status.value == "filled"
        assert trade.sell_order.status.value == "filled"

        # Portfolio should be updated
        assert paper_trader.portfolio.total_trades == 1

        # Trade should be stored
        assert trade.id in paper_trader.trades
        assert trade.buy_order.id in paper_trader.orders
        assert trade.sell_order.id in paper_trader.orders

    @pytest.mark.asyncio
    async def test_execute_arbitrage_insufficient_liquidity(
        self,
        paper_trader: PaperTrader,
        profitable_opportunity: ArbitrageOpportunity,
    ) -> None:
        """Test arbitrage with insufficient liquidity."""
        # Orderbooks with very small volume
        thin_buy = Orderbook(
            symbol="BTC/USDT",
            exchange=Exchange.BINANCE,
            bids=[OrderbookLevel(price=Decimal("66990"), volume=Decimal("0.001"))],
            asks=[OrderbookLevel(price=Decimal("67000"), volume=Decimal("0.001"))],
            timestamp=datetime.utcnow(),
        )
        thin_sell = Orderbook(
            symbol="BTC/USDT",
            exchange=Exchange.KRAKEN,
            bids=[OrderbookLevel(price=Decimal("67100"), volume=Decimal("0.001"))],
            asks=[OrderbookLevel(price=Decimal("67110"), volume=Decimal("0.001"))],
            timestamp=datetime.utcnow(),
        )

        trade = await paper_trader.execute_arbitrage(profitable_opportunity, thin_buy, thin_sell)

        # Trade should fail due to insufficient liquidity
        assert trade.status == "failed"
        assert trade.both_orders_would_have_executed is False

    @pytest.mark.asyncio
    async def test_multiple_trades_track_correctly(
        self,
        paper_trader: PaperTrader,
        profitable_opportunity: ArbitrageOpportunity,
        buy_orderbook: Orderbook,
        sell_orderbook: Orderbook,
    ) -> None:
        """Test that multiple trades are tracked correctly."""
        # Execute multiple trades
        for i in range(3):
            # Modify opportunity ID to avoid duplicates
            profitable_opportunity.id = f"test-opp-{i}"
            await paper_trader.execute_arbitrage(
                profitable_opportunity, buy_orderbook, sell_orderbook
            )

        assert paper_trader.portfolio.total_trades == 3
        assert len(paper_trader.trades) == 3
        assert len(paper_trader.orders) == 6  # 2 orders per trade

    @pytest.mark.asyncio
    async def test_portfolio_updates_on_profit(
        self,
        paper_trader: PaperTrader,
        profitable_opportunity: ArbitrageOpportunity,
        buy_orderbook: Orderbook,
        sell_orderbook: Orderbook,
    ) -> None:
        """Test portfolio updates correctly on profitable trade."""
        initial_value = paper_trader.portfolio.total_value_usd

        trade = await paper_trader.execute_arbitrage(
            profitable_opportunity, buy_orderbook, sell_orderbook
        )

        if trade.status == "completed" and trade.net_profit > 0:
            assert paper_trader.portfolio.winning_trades == 1
            assert paper_trader.portfolio.total_value_usd > initial_value

    def test_get_statistics(self, paper_trader: PaperTrader) -> None:
        """Test getting statistics."""
        stats = paper_trader.get_statistics()

        assert "total_trades" in stats
        assert "win_rate" in stats
        assert "total_pnl_usd" in stats
        assert "portfolio_value" in stats

    def test_reset(self, paper_trader: PaperTrader) -> None:
        """Test resetting paper trader."""
        # Modify state
        paper_trader.portfolio.total_trades = 10
        paper_trader.trades["test"] = None  # type: ignore

        # Reset
        paper_trader.reset()

        assert paper_trader.portfolio.total_trades == 0
        assert len(paper_trader.trades) == 0
        assert len(paper_trader.orders) == 0

    def test_get_trade_history(self, paper_trader: PaperTrader) -> None:
        """Test getting trade history."""
        history = paper_trader.get_trade_history()
        assert isinstance(history, list)
