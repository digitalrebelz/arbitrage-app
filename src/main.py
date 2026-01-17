"""Main entry point for the arbitrage bot."""

import argparse
import asyncio
from datetime import datetime

from loguru import logger

from src.arbitrage.detector import ArbitrageDetector
from src.config.logging_config import setup_logging
from src.config.settings import settings
from src.database.db_manager import close_db, init_db
from src.exchanges import ExchangeFactory
from src.execution.paper_trader import PaperTrader
from src.models.market import Exchange
from src.risk.manager import RiskManager


async def main(mode: str = "paper", duration: int = 0) -> None:
    """
    Main entry point for the arbitrage bot.

    Args:
        mode: Trading mode ("paper" or "live")
        duration: Duration to run in seconds (0 = infinite)
    """
    setup_logging()
    logger.info(f"Starting Arbitrage Bot in {mode} mode")

    # Initialize database
    await init_db()

    # Initialize components
    detector = ArbitrageDetector()
    paper_trader = PaperTrader()
    risk_manager = RiskManager(paper_trader.portfolio)

    # Initialize exchanges
    exchanges = [Exchange.BINANCE]
    await detector.initialize(exchanges)

    # Symbols to scan
    symbols = ["BTC/USDT", "ETH/USDT"]

    logger.info(f"Scanning symbols: {symbols}")
    logger.info(f"Initial portfolio: ${paper_trader.portfolio.total_value_usd}")

    start_time = datetime.utcnow()
    iteration = 0
    opportunities_found = 0
    trades_executed = 0

    try:
        while True:
            iteration += 1

            for symbol in symbols:
                try:
                    # Scan for opportunities
                    opportunities = await detector.scan_cross_exchange_opportunities(symbol)

                    for opp in opportunities:
                        opportunities_found += 1

                        # Check risk limits
                        can_trade, reason = risk_manager.can_trade(opp)
                        if not can_trade:
                            logger.debug(f"Skipping opportunity: {reason}")
                            continue

                        if opp.net_profit_percent >= settings.MIN_PROFIT_THRESHOLD_PERCENT:
                            logger.info(
                                f"Opportunity: {opp.symbol} "
                                f"{opp.buy_exchange} -> {opp.sell_exchange} "
                                f"profit={opp.net_profit_percent:.4f}%"
                            )

                            # Execute paper trade
                            if mode == "paper":
                                buy_ob = await detector.exchanges[
                                    Exchange(opp.buy_exchange)
                                ].get_orderbook(symbol)
                                sell_ob = await detector.exchanges[
                                    Exchange(opp.sell_exchange)
                                ].get_orderbook(symbol)
                                trade = await paper_trader.execute_arbitrage(opp, buy_ob, sell_ob)
                                trades_executed += 1

                                # Update risk exposure
                                if trade.status == "completed":
                                    trade_value = opp.recommended_volume * opp.buy_price
                                    risk_manager.update_exposure(trade_value, is_open=False)

                except Exception as e:
                    logger.error(f"Error scanning {symbol}: {e}")

            # Check stop loss conditions
            should_stop, stop_reason = risk_manager.check_stop_loss()
            if should_stop:
                logger.warning(f"Stop loss triggered: {stop_reason}")
                break

            # Log status periodically
            if iteration % 100 == 0:
                portfolio = paper_trader.get_portfolio()
                logger.info(
                    f"Status: iteration={iteration} "
                    f"opportunities={opportunities_found} "
                    f"trades={portfolio.total_trades} "
                    f"pnl=${portfolio.total_pnl_usd:.2f} "
                    f"win_rate={portfolio.win_rate:.1f}%"
                )

            # Check duration limit
            if duration > 0:
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                if elapsed >= duration:
                    logger.info(f"Duration limit reached ({duration}s)")
                    break

            # Wait before next scan
            await asyncio.sleep(settings.SCAN_INTERVAL_MS / 1000)

    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        # Print final report
        portfolio = paper_trader.get_portfolio()
        elapsed = (datetime.utcnow() - start_time).total_seconds()

        logger.info("=" * 50)
        logger.info("FINAL REPORT")
        logger.info("=" * 50)
        logger.info(f"Runtime: {elapsed:.1f}s")
        logger.info(f"Iterations: {iteration}")
        logger.info(f"Opportunities Found: {opportunities_found}")
        logger.info(f"Total Trades: {portfolio.total_trades}")
        logger.info(f"Winning Trades: {portfolio.winning_trades}")
        logger.info(f"Losing Trades: {portfolio.losing_trades}")
        logger.info(f"Win Rate: {portfolio.win_rate:.1f}%")
        logger.info(
            f"Total P&L: ${portfolio.total_pnl_usd:.2f} ({portfolio.total_pnl_percent:.2f}%)"
        )
        logger.info(f"Max Drawdown: {portfolio.max_drawdown_percent:.2f}%")
        logger.info(f"Final Portfolio Value: ${portfolio.total_value_usd:.2f}")
        logger.info("=" * 50)

        # Cleanup
        await ExchangeFactory.close_all()
        await close_db()


def run() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Arbitrage Trading Bot")
    parser.add_argument(
        "--mode",
        choices=["paper", "live"],
        default="paper",
        help="Trading mode (default: paper)",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=0,
        help="Duration in seconds (0=infinite)",
    )
    args = parser.parse_args()

    asyncio.run(main(mode=args.mode, duration=args.duration))


if __name__ == "__main__":
    run()
