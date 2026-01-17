"""Paper trading engine for simulating trades."""

import asyncio
import random
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from loguru import logger

from src.config.settings import settings
from src.execution.order_validator import OrderValidator
from src.execution.slippage import SlippageSimulator
from src.models.market import Orderbook
from src.models.opportunity import ArbitrageOpportunity
from src.models.portfolio import Balance, Portfolio
from src.models.trade import Order, OrderSide, OrderStatus, OrderType, Trade, TradeMode


class PaperTrader:
    """Simulate paper trading with realistic execution."""

    def __init__(self) -> None:
        """Initialize paper trader."""
        self.portfolio = Portfolio(last_updated=datetime.utcnow())
        self.validator = OrderValidator()
        self.slippage_sim = SlippageSimulator()
        self.trades: dict[str, Trade] = {}
        self.orders: dict[str, Order] = {}
        self._initialize_portfolio()

    def _initialize_portfolio(self) -> None:
        """Initialize portfolio with default balances."""
        initial_balance = Decimal(str(settings.INITIAL_BALANCE_USD))
        self.portfolio = Portfolio(
            balances={
                "USD": Balance(
                    currency="USD",
                    available=initial_balance,
                ),
                "BTC": Balance(
                    currency="BTC",
                    available=Decimal(str(settings.INITIAL_BALANCE_BTC)),
                ),
                "ETH": Balance(
                    currency="ETH",
                    available=Decimal(str(settings.INITIAL_BALANCE_ETH)),
                ),
                "USDT": Balance(
                    currency="USDT",
                    available=initial_balance,
                ),
            },
            initial_value_usd=initial_balance,
            total_value_usd=initial_balance,
            last_updated=datetime.utcnow(),
        )
        logger.info(f"Portfolio initialized with ${settings.INITIAL_BALANCE_USD}")

    async def execute_arbitrage(
        self,
        opportunity: ArbitrageOpportunity,
        buy_orderbook: Orderbook,
        sell_orderbook: Orderbook,
    ) -> Trade:
        """
        Execute a paper arbitrage trade.

        Args:
            opportunity: The arbitrage opportunity
            buy_orderbook: Orderbook for the buy side
            sell_orderbook: Orderbook for the sell side

        Returns:
            Completed Trade object
        """
        start_time = datetime.utcnow()

        # Simulate network latency
        latency_ms = await self._simulate_latency()

        # Create paper orders
        buy_order = await self._create_paper_order(
            opportunity,
            OrderSide.BUY,
            buy_orderbook,
            opportunity.buy_exchange,
        )
        sell_order = await self._create_paper_order(
            opportunity,
            OrderSide.SELL,
            sell_orderbook,
            opportunity.sell_exchange,
        )

        # Validate if orders would have executed
        buy_would_execute = self.validator.would_have_executed(buy_order, buy_orderbook, "buy")
        sell_would_execute = self.validator.would_have_executed(sell_order, sell_orderbook, "sell")

        buy_order.would_have_executed = buy_would_execute
        sell_order.would_have_executed = sell_would_execute

        # Calculate results
        if buy_would_execute and sell_would_execute:
            buy_order.status = OrderStatus.FILLED
            sell_order.status = OrderStatus.FILLED
            buy_order.filled_volume = buy_order.requested_volume
            sell_order.filled_volume = sell_order.requested_volume

            gross_profit = self._calculate_gross_profit(buy_order, sell_order)
            total_fees = buy_order.fee_paid + sell_order.fee_paid
            net_profit = gross_profit - total_fees

            # Update portfolio
            self._update_portfolio(buy_order, sell_order, net_profit)
            status = "completed"
        else:
            buy_order.status = OrderStatus.FAILED if not buy_would_execute else OrderStatus.FILLED
            sell_order.status = OrderStatus.FAILED if not sell_would_execute else OrderStatus.FILLED
            gross_profit = Decimal("0")
            total_fees = Decimal("0")
            net_profit = Decimal("0")
            status = "failed"

        end_time = datetime.utcnow()
        total_ms = int((end_time - start_time).total_seconds() * 1000) + latency_ms

        # Calculate net profit percent
        if buy_order.average_fill_price and buy_order.requested_volume > 0:
            trade_value = buy_order.requested_volume * buy_order.average_fill_price
            net_profit_percent = (
                (net_profit / trade_value) * 100 if trade_value > 0 else Decimal("0")
            )
        else:
            net_profit_percent = Decimal("0")

        # Create trade record
        trade = Trade(
            id=str(uuid4()),
            opportunity_id=opportunity.id,
            type=opportunity.type,
            mode=TradeMode.PAPER,
            buy_order=buy_order,
            sell_order=sell_order,
            gross_profit=gross_profit,
            total_fees=total_fees,
            net_profit=net_profit,
            net_profit_percent=net_profit_percent,
            status=status,
            started_at=start_time,
            completed_at=end_time,
            total_execution_ms=total_ms,
            both_orders_would_have_executed=buy_would_execute and sell_would_execute,
        )

        # Store trade and orders
        self.trades[trade.id] = trade
        self.orders[buy_order.id] = buy_order
        self.orders[sell_order.id] = sell_order

        # Log result
        if status == "completed":
            logger.info(
                f"Paper trade completed: {opportunity.symbol} "
                f"profit=${net_profit:.4f} ({net_profit_percent:.4f}%) "
                f"execution={total_ms}ms"
            )
        else:
            logger.warning(
                f"Paper trade failed: {opportunity.symbol} "
                f"buy_executed={buy_would_execute} sell_executed={sell_would_execute}"
            )

        return trade

    async def _create_paper_order(
        self,
        opportunity: ArbitrageOpportunity,
        side: OrderSide,
        orderbook: Orderbook,
        exchange: str,
    ) -> Order:
        """
        Create a paper order with simulated execution.

        Args:
            opportunity: The arbitrage opportunity
            side: Buy or sell
            orderbook: Current orderbook
            exchange: Exchange name

        Returns:
            Simulated Order object
        """
        volume = opportunity.recommended_volume

        # Simulate slippage
        slippage = self.slippage_sim.simulate(orderbook, side.value, volume)

        # Calculate execution price
        if side == OrderSide.BUY:
            base_price = opportunity.buy_price
            fee_percent = opportunity.buy_fee_percent
            execution_price = base_price * (1 + slippage / 100)
        else:
            base_price = opportunity.sell_price
            fee_percent = opportunity.sell_fee_percent
            execution_price = base_price * (1 - slippage / 100)

        # Calculate fee
        fee_paid = volume * execution_price * fee_percent / 100

        now = datetime.utcnow()

        return Order(
            id=str(uuid4()),
            opportunity_id=opportunity.id,
            exchange=exchange,
            symbol=opportunity.symbol,
            side=side,
            type=OrderType.MARKET,
            requested_volume=volume,
            filled_volume=Decimal("0"),
            requested_price=None,
            average_fill_price=execution_price,
            status=OrderStatus.PENDING,
            mode=TradeMode.PAPER,
            fee_paid=fee_paid,
            fee_currency="USD",
            created_at=now,
            updated_at=now,
            simulated_slippage=slippage,
        )

    async def _simulate_latency(self) -> int:
        """
        Simulate network/exchange latency.

        Returns:
            Latency in milliseconds
        """
        # Simulate 10-50ms latency
        latency_ms = random.randint(10, 50)
        await asyncio.sleep(latency_ms / 1000)
        return latency_ms

    def _calculate_gross_profit(self, buy_order: Order, sell_order: Order) -> Decimal:
        """
        Calculate gross profit from a pair of orders.

        Args:
            buy_order: The buy order
            sell_order: The sell order

        Returns:
            Gross profit in USD
        """
        if not buy_order.average_fill_price or not sell_order.average_fill_price:
            return Decimal("0")

        buy_cost = buy_order.filled_volume * buy_order.average_fill_price
        sell_revenue = sell_order.filled_volume * sell_order.average_fill_price
        return sell_revenue - buy_cost

    def _update_portfolio(
        self,
        buy_order: Order,
        sell_order: Order,
        net_profit: Decimal,
    ) -> None:
        """
        Update portfolio after a trade.

        Args:
            buy_order: The buy order
            sell_order: The sell order
            net_profit: Net profit from the trade
        """
        # Update P&L
        self.portfolio.total_pnl_usd += net_profit
        self.portfolio.realized_pnl += net_profit
        self.portfolio.total_value_usd += net_profit
        self.portfolio.total_trades += 1

        # Update win/loss counters
        if net_profit > 0:
            self.portfolio.winning_trades += 1
        else:
            self.portfolio.losing_trades += 1

        # Update P&L percentage
        if self.portfolio.initial_value_usd > 0:
            self.portfolio.total_pnl_percent = (
                self.portfolio.total_pnl_usd / self.portfolio.initial_value_usd * 100
            )

        # Update max drawdown
        if self.portfolio.total_pnl_usd < 0:
            drawdown = abs(self.portfolio.total_pnl_usd)
            if drawdown > self.portfolio.max_drawdown_usd:
                self.portfolio.max_drawdown_usd = drawdown
                if self.portfolio.initial_value_usd > 0:
                    self.portfolio.max_drawdown_percent = (
                        drawdown / self.portfolio.initial_value_usd * 100
                    )

        self.portfolio.last_updated = datetime.utcnow()

    def get_portfolio(self) -> Portfolio:
        """Get current portfolio state."""
        return self.portfolio

    def get_trade_history(self) -> list[Trade]:
        """Get all completed trades."""
        return list(self.trades.values())

    def get_trade(self, trade_id: str) -> Trade | None:
        """Get a specific trade by ID."""
        return self.trades.get(trade_id)

    def get_order(self, order_id: str) -> Order | None:
        """Get a specific order by ID."""
        return self.orders.get(order_id)

    def get_statistics(self) -> dict:
        """Get trading statistics."""
        portfolio = self.portfolio

        return {
            "total_trades": portfolio.total_trades,
            "winning_trades": portfolio.winning_trades,
            "losing_trades": portfolio.losing_trades,
            "win_rate": float(portfolio.win_rate),
            "total_pnl_usd": float(portfolio.total_pnl_usd),
            "total_pnl_percent": float(portfolio.total_pnl_percent),
            "max_drawdown_usd": float(portfolio.max_drawdown_usd),
            "max_drawdown_percent": float(portfolio.max_drawdown_percent),
            "portfolio_value": float(portfolio.total_value_usd),
        }

    def reset(self) -> None:
        """Reset paper trader to initial state."""
        self.trades.clear()
        self.orders.clear()
        self._initialize_portfolio()
        logger.info("Paper trader reset to initial state")
