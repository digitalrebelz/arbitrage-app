"""Simulation mode entry point - generates realistic fake arbitrage trades."""

import asyncio
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from loguru import logger

from src.config.logging_config import setup_logging
from src.config.settings import settings
from src.execution.paper_trader import PaperTrader
from src.simulation.simulator import ArbitrageSimulator


# Shared state file for dashboard
STATE_FILE = Path("data/simulation_state.json")


def decimal_default(obj):
    """JSON serializer for Decimal objects."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def save_state(
    portfolio: dict,
    trades: list,
    opportunities: list,
    stats: dict,
    is_running: bool,
) -> None:
    """Save current state to JSON file for dashboard."""
    state = {
        "updated_at": datetime.utcnow().isoformat(),
        "is_running": is_running,
        "portfolio": portfolio,
        "recent_trades": trades[-50:],  # Last 50 trades
        "recent_opportunities": opportunities[-20:],  # Last 20 opportunities
        "statistics": stats,
    }
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, default=decimal_default, indent=2))


async def main() -> None:
    """Run simulation with realistic fake arbitrage opportunities."""
    setup_logging()
    logger.info("Starting Arbitrage Bot in SIMULATION mode")

    # Initialize components
    paper_trader = PaperTrader()
    simulator = ArbitrageSimulator(
        opportunity_rate=0.4,  # 40% chance per scan
        profit_range=(0.03, 0.35),  # 0.03% to 0.35% profit
        execution_success_rate=0.75,  # 75% success rate
    )

    # Track all opportunities and trades for dashboard
    all_opportunities: list[dict] = []
    all_trades: list[dict] = []

    iteration = 0
    start_time = datetime.utcnow()

    logger.info(f"Initial portfolio: ${paper_trader.portfolio.total_value_usd}")

    try:
        while True:
            iteration += 1

            # Maybe generate an opportunity
            opportunity = simulator.maybe_generate_opportunity()

            if opportunity:
                # Store opportunity for dashboard
                opp_dict = {
                    "id": opportunity.id,
                    "symbol": opportunity.symbol,
                    "buy_exchange": opportunity.buy_exchange,
                    "sell_exchange": opportunity.sell_exchange,
                    "buy_price": opportunity.buy_price,
                    "sell_price": opportunity.sell_price,
                    "net_profit_percent": opportunity.net_profit_percent,
                    "estimated_profit_usd": opportunity.estimated_profit_usd,
                    "volume": opportunity.recommended_volume,
                    "detected_at": opportunity.detected_at,
                    "status": "detected",
                }
                all_opportunities.append(opp_dict)

                # Check if meets minimum profit threshold
                if opportunity.net_profit_percent >= Decimal(str(settings.MIN_PROFIT_THRESHOLD_PERCENT)):
                    # Generate orderbooks for the trade
                    buy_orderbook = simulator.generate_orderbook(
                        opportunity.symbol,
                        opportunity.buy_exchange,
                        opportunity.buy_price,
                    )
                    sell_orderbook = simulator.generate_orderbook(
                        opportunity.symbol,
                        opportunity.sell_exchange,
                        opportunity.sell_price,
                    )

                    # Execute paper trade
                    trade = await paper_trader.execute_arbitrage(
                        opportunity, buy_orderbook, sell_orderbook
                    )

                    # Store trade for dashboard
                    trade_dict = {
                        "id": trade.id,
                        "symbol": opportunity.symbol,
                        "buy_exchange": opportunity.buy_exchange,
                        "sell_exchange": opportunity.sell_exchange,
                        "buy_price": float(trade.buy_order.average_fill_price or 0),
                        "sell_price": float(trade.sell_order.average_fill_price or 0),
                        "volume": float(opportunity.recommended_volume),
                        "gross_profit": trade.gross_profit,
                        "net_profit": trade.net_profit,
                        "net_profit_percent": trade.net_profit_percent,
                        "fees": trade.total_fees,
                        "status": trade.status,
                        "executed_at": trade.completed_at,
                        "execution_ms": trade.total_execution_ms,
                    }
                    all_trades.append(trade_dict)

                    # Update opportunity status
                    opp_dict["status"] = "executed" if trade.status == "completed" else "failed"

            # Save state for dashboard every iteration
            portfolio = paper_trader.get_portfolio()
            stats = paper_trader.get_statistics()

            portfolio_dict = {
                "total_value_usd": portfolio.total_value_usd,
                "initial_value_usd": portfolio.initial_value_usd,
                "total_pnl_usd": portfolio.total_pnl_usd,
                "total_pnl_percent": portfolio.total_pnl_percent,
                "total_trades": portfolio.total_trades,
                "winning_trades": portfolio.winning_trades,
                "losing_trades": portfolio.losing_trades,
                "win_rate": portfolio.win_rate,
                "max_drawdown_percent": portfolio.max_drawdown_percent,
            }

            save_state(
                portfolio=portfolio_dict,
                trades=all_trades,
                opportunities=all_opportunities,
                stats=stats,
                is_running=True,
            )

            # Log status periodically
            if iteration % 20 == 0:
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                logger.info(
                    f"[{elapsed:.0f}s] Iteration {iteration}: "
                    f"trades={portfolio.total_trades} "
                    f"P&L=${portfolio.total_pnl_usd:+.2f} ({portfolio.total_pnl_percent:+.2f}%) "
                    f"win_rate={portfolio.win_rate:.1f}%"
                )

            # Wait before next scan (faster for simulation)
            await asyncio.sleep(1.5)  # 1.5 second between scans

    except KeyboardInterrupt:
        logger.info("Shutting down simulation...")
    finally:
        # Save final state
        portfolio = paper_trader.get_portfolio()
        stats = paper_trader.get_statistics()

        portfolio_dict = {
            "total_value_usd": portfolio.total_value_usd,
            "initial_value_usd": portfolio.initial_value_usd,
            "total_pnl_usd": portfolio.total_pnl_usd,
            "total_pnl_percent": portfolio.total_pnl_percent,
            "total_trades": portfolio.total_trades,
            "winning_trades": portfolio.winning_trades,
            "losing_trades": portfolio.losing_trades,
            "win_rate": portfolio.win_rate,
            "max_drawdown_percent": portfolio.max_drawdown_percent,
        }

        save_state(
            portfolio=portfolio_dict,
            trades=all_trades,
            opportunities=all_opportunities,
            stats=stats,
            is_running=False,
        )

        # Print final report
        elapsed = (datetime.utcnow() - start_time).total_seconds()
        logger.info("=" * 50)
        logger.info("SIMULATION FINAL REPORT")
        logger.info("=" * 50)
        logger.info(f"Runtime: {elapsed:.1f}s")
        logger.info(f"Iterations: {iteration}")
        logger.info(f"Opportunities Found: {len(all_opportunities)}")
        logger.info(f"Trades Executed: {portfolio.total_trades}")
        logger.info(f"Winning Trades: {portfolio.winning_trades}")
        logger.info(f"Losing Trades: {portfolio.losing_trades}")
        logger.info(f"Win Rate: {portfolio.win_rate:.1f}%")
        logger.info(f"Total P&L: ${portfolio.total_pnl_usd:+.2f} ({portfolio.total_pnl_percent:+.2f}%)")
        logger.info(f"Max Drawdown: {portfolio.max_drawdown_percent:.2f}%")
        logger.info(f"Final Portfolio: ${portfolio.total_value_usd:.2f}")
        logger.info("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
