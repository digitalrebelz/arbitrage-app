"""CRUD operations for database models."""

import json
from datetime import datetime
from decimal import Decimal

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import (
    DBMarketData,
    DBOpportunity,
    DBOrder,
    DBPortfolioSnapshot,
    DBTrade,
)
from src.models.opportunity import ArbitrageOpportunity
from src.models.portfolio import Portfolio
from src.models.trade import Order, Trade


class OpportunityCRUD:
    """CRUD operations for opportunities."""

    @staticmethod
    async def create(
        session: AsyncSession,
        opportunity: ArbitrageOpportunity,
    ) -> DBOpportunity:
        """Create a new opportunity record."""
        db_opp = DBOpportunity(
            id=opportunity.id,
            type=opportunity.type.value,
            status=opportunity.status.value,
            buy_exchange=opportunity.buy_exchange,
            sell_exchange=opportunity.sell_exchange,
            symbol=opportunity.symbol,
            buy_price=opportunity.buy_price,
            sell_price=opportunity.sell_price,
            max_volume=opportunity.max_volume,
            recommended_volume=opportunity.recommended_volume,
            gross_profit_percent=opportunity.gross_profit_percent,
            net_profit_percent=opportunity.net_profit_percent,
            estimated_profit_usd=opportunity.estimated_profit_usd,
            buy_fee_percent=opportunity.buy_fee_percent,
            sell_fee_percent=opportunity.sell_fee_percent,
            estimated_slippage_percent=opportunity.estimated_slippage_percent,
            detected_at=opportunity.detected_at,
            expires_at=opportunity.expires_at,
            window_ms=opportunity.window_ms,
            orderbook_depth_ok=opportunity.orderbook_depth_ok,
            liquidity_ok=opportunity.liquidity_ok,
            would_have_executed=opportunity.would_have_executed,
            risk_score=opportunity.risk_score,
        )
        session.add(db_opp)
        await session.flush()
        return db_opp

    @staticmethod
    async def get_by_id(
        session: AsyncSession,
        opportunity_id: str,
    ) -> DBOpportunity | None:
        """Get opportunity by ID."""
        result = await session.execute(
            select(DBOpportunity).where(DBOpportunity.id == opportunity_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_recent(
        session: AsyncSession,
        limit: int = 100,
    ) -> list[DBOpportunity]:
        """Get recent opportunities."""
        result = await session.execute(
            select(DBOpportunity).order_by(desc(DBOpportunity.detected_at)).limit(limit)
        )
        return list(result.scalars().all())


class TradeCRUD:
    """CRUD operations for trades."""

    @staticmethod
    async def create(
        session: AsyncSession,
        trade: Trade,
    ) -> DBTrade:
        """Create a new trade record."""
        db_trade = DBTrade(
            id=trade.id,
            opportunity_id=trade.opportunity_id,
            type=trade.type.value,
            mode=trade.mode.value,
            gross_profit=trade.gross_profit,
            total_fees=trade.total_fees,
            net_profit=trade.net_profit,
            net_profit_percent=trade.net_profit_percent,
            status=trade.status,
            error_message=trade.error_message,
            started_at=trade.started_at,
            completed_at=trade.completed_at,
            total_execution_ms=trade.total_execution_ms,
            both_orders_would_have_executed=trade.both_orders_would_have_executed,
        )
        session.add(db_trade)
        await session.flush()

        # Create order records
        for order in [trade.buy_order, trade.sell_order]:
            await OrderCRUD.create(session, order, db_trade.id)

        return db_trade

    @staticmethod
    async def get_by_id(
        session: AsyncSession,
        trade_id: str,
    ) -> DBTrade | None:
        """Get trade by ID."""
        result = await session.execute(select(DBTrade).where(DBTrade.id == trade_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_recent(
        session: AsyncSession,
        limit: int = 100,
        status: str | None = None,
    ) -> list[DBTrade]:
        """Get recent trades."""
        query = select(DBTrade).order_by(desc(DBTrade.started_at)).limit(limit)
        if status:
            query = query.where(DBTrade.status == status)
        result = await session.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_profitable_trades(
        session: AsyncSession,
        limit: int = 100,
    ) -> list[DBTrade]:
        """Get profitable trades."""
        result = await session.execute(
            select(DBTrade)
            .where(DBTrade.net_profit > 0)
            .order_by(desc(DBTrade.net_profit))
            .limit(limit)
        )
        return list(result.scalars().all())


class OrderCRUD:
    """CRUD operations for orders."""

    @staticmethod
    async def create(
        session: AsyncSession,
        order: Order,
        trade_id: str,
    ) -> DBOrder:
        """Create a new order record."""
        db_order = DBOrder(
            id=order.id,
            trade_id=trade_id,
            exchange=order.exchange,
            symbol=order.symbol,
            side=order.side.value,
            type=order.type.value,
            requested_volume=order.requested_volume,
            filled_volume=order.filled_volume,
            requested_price=order.requested_price,
            average_fill_price=order.average_fill_price,
            status=order.status.value,
            mode=order.mode.value,
            fee_paid=order.fee_paid,
            fee_currency=order.fee_currency,
            created_at=order.created_at,
            updated_at=order.updated_at,
            filled_at=order.filled_at,
            would_have_executed=order.would_have_executed,
            simulated_slippage=order.simulated_slippage,
            execution_latency_ms=order.execution_latency_ms,
        )
        session.add(db_order)
        await session.flush()
        return db_order

    @staticmethod
    async def get_by_trade_id(
        session: AsyncSession,
        trade_id: str,
    ) -> list[DBOrder]:
        """Get orders for a trade."""
        result = await session.execute(select(DBOrder).where(DBOrder.trade_id == trade_id))
        return list(result.scalars().all())


class PortfolioSnapshotCRUD:
    """CRUD operations for portfolio snapshots."""

    @staticmethod
    async def create(
        session: AsyncSession,
        portfolio: Portfolio,
    ) -> DBPortfolioSnapshot:
        """Create a portfolio snapshot."""
        # Serialize balances to JSON
        balances_dict = {
            currency: {
                "available": str(balance.available),
                "locked": str(balance.locked),
            }
            for currency, balance in portfolio.balances.items()
        }

        db_snapshot = DBPortfolioSnapshot(
            timestamp=portfolio.last_updated,
            total_value_usd=portfolio.total_value_usd,
            total_pnl_usd=portfolio.total_pnl_usd,
            total_pnl_percent=portfolio.total_pnl_percent,
            realized_pnl=portfolio.realized_pnl,
            total_trades=portfolio.total_trades,
            winning_trades=portfolio.winning_trades,
            losing_trades=portfolio.losing_trades,
            max_drawdown_usd=portfolio.max_drawdown_usd,
            max_drawdown_percent=portfolio.max_drawdown_percent,
            balances_json=json.dumps(balances_dict),
        )
        session.add(db_snapshot)
        await session.flush()
        return db_snapshot

    @staticmethod
    async def get_latest(
        session: AsyncSession,
    ) -> DBPortfolioSnapshot | None:
        """Get most recent portfolio snapshot."""
        result = await session.execute(
            select(DBPortfolioSnapshot).order_by(desc(DBPortfolioSnapshot.timestamp)).limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_history(
        session: AsyncSession,
        start_time: datetime,
        end_time: datetime | None = None,
    ) -> list[DBPortfolioSnapshot]:
        """Get portfolio history for a time range."""
        query = select(DBPortfolioSnapshot).where(DBPortfolioSnapshot.timestamp >= start_time)
        if end_time:
            query = query.where(DBPortfolioSnapshot.timestamp <= end_time)
        query = query.order_by(DBPortfolioSnapshot.timestamp)
        result = await session.execute(query)
        return list(result.scalars().all())


class MarketDataCRUD:
    """CRUD operations for market data."""

    @staticmethod
    async def create(
        session: AsyncSession,
        timestamp: datetime,
        exchange: str,
        symbol: str,
        bid: Decimal,
        ask: Decimal,
        bid_volume: Decimal = Decimal("0"),
        ask_volume: Decimal = Decimal("0"),
    ) -> DBMarketData:
        """Create a market data record."""
        spread_percent = ((ask - bid) / bid * 100) if bid > 0 else Decimal("0")

        db_data = DBMarketData(
            timestamp=timestamp,
            exchange=exchange,
            symbol=symbol,
            bid=bid,
            ask=ask,
            bid_volume=bid_volume,
            ask_volume=ask_volume,
            spread_percent=spread_percent,
        )
        session.add(db_data)
        await session.flush()
        return db_data

    @staticmethod
    async def get_latest(
        session: AsyncSession,
        exchange: str,
        symbol: str,
    ) -> DBMarketData | None:
        """Get latest market data for exchange/symbol."""
        result = await session.execute(
            select(DBMarketData)
            .where(DBMarketData.exchange == exchange)
            .where(DBMarketData.symbol == symbol)
            .order_by(desc(DBMarketData.timestamp))
            .limit(1)
        )
        return result.scalar_one_or_none()
