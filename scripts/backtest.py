#!/usr/bin/env python3
"""Backtesting script for arbitrage strategies."""

import argparse
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal

from loguru import logger

from src.arbitrage.calculator import ArbitrageCalculator
from src.config.logging_config import setup_logging
from src.execution.paper_trader import PaperTrader


async def run_backtest(
    start_date: datetime,
    end_date: datetime,
    symbols: list[str],
    initial_balance: Decimal,
) -> dict:
    """
    Run a backtest simulation.

    Args:
        start_date: Start date for backtest
        end_date: End date for backtest
        symbols: List of symbols to trade
        initial_balance: Initial portfolio balance

    Returns:
        Dictionary with backtest results
    """
    setup_logging()
    logger.info(f"Starting backtest from {start_date} to {end_date}")
    logger.info(f"Symbols: {symbols}")
    logger.info(f"Initial balance: ${initial_balance}")

    calculator = ArbitrageCalculator()
    paper_trader = PaperTrader()

    # Simulate some trades (in real implementation, load historical data)
    num_days = (end_date - start_date).days
    trades_per_day = 10

    for day in range(num_days):
        current_date = start_date + timedelta(days=day)
        logger.info(f"Processing {current_date.date()}")

        for _ in range(trades_per_day):
            # Simulate a trade (simplified)
            import random

            profit = Decimal(str(random.uniform(-5, 10)))
            paper_trader.portfolio.record_trade(profit)

    # Get final results
    portfolio = paper_trader.get_portfolio()

    results = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "initial_balance": float(initial_balance),
        "final_balance": float(portfolio.total_value_usd),
        "total_pnl": float(portfolio.total_pnl_usd),
        "total_pnl_percent": float(portfolio.total_pnl_percent),
        "total_trades": portfolio.total_trades,
        "winning_trades": portfolio.winning_trades,
        "losing_trades": portfolio.losing_trades,
        "win_rate": float(portfolio.win_rate),
        "max_drawdown_percent": float(portfolio.max_drawdown_percent),
    }

    logger.info("=" * 50)
    logger.info("BACKTEST RESULTS")
    logger.info("=" * 50)
    for key, value in results.items():
        logger.info(f"{key}: {value}")
    logger.info("=" * 50)

    return results


def main() -> None:
    """Main entry point for backtesting."""
    parser = argparse.ArgumentParser(description="Backtest arbitrage strategies")
    parser.add_argument(
        "--start",
        type=str,
        default="2024-01-01",
        help="Start date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end",
        type=str,
        default="2024-01-31",
        help="End date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=["BTC/USDT", "ETH/USDT"],
        help="Symbols to trade",
    )
    parser.add_argument(
        "--balance",
        type=float,
        default=10000,
        help="Initial balance",
    )

    args = parser.parse_args()

    start_date = datetime.strptime(args.start, "%Y-%m-%d")
    end_date = datetime.strptime(args.end, "%Y-%m-%d")

    asyncio.run(
        run_backtest(
            start_date=start_date,
            end_date=end_date,
            symbols=args.symbols,
            initial_balance=Decimal(str(args.balance)),
        )
    )


if __name__ == "__main__":
    main()
