"""Real market data mode - fetches live prices from multiple exchanges without API keys."""

import asyncio
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import ccxt.async_support as ccxt
from loguru import logger

from src.config.logging_config import setup_logging
from src.execution.paper_trader import PaperTrader
from src.models.market import Exchange, Orderbook, OrderbookLevel
from src.models.opportunity import ArbitrageOpportunity, ArbitrageType, OpportunityStatus

# Shared state file for dashboard
STATE_FILE = Path("data/simulation_state.json")

# Exchanges that support public data without API keys
EXCHANGES = {
    "binance": ccxt.binance,
    "kraken": ccxt.kraken,
    "coinbase": ccxt.coinbase,
    "kucoin": ccxt.kucoin,
    "bybit": ccxt.bybit,
}

# Real trading fees (taker fees - we use market orders for arbitrage)
# Source: https://learncrypto.com/feed/articles/crypto-exchange-fees-2024
EXCHANGE_FEES = {
    "binance": Decimal("0.10"),   # 0.10% taker (0.075% with BNB)
    "kraken": Decimal("0.26"),    # 0.26% taker base tier
    "coinbase": Decimal("0.60"),  # 0.60% taker (expensive!)
    "kucoin": Decimal("0.10"),    # 0.10% taker
    "bybit": Decimal("0.10"),     # 0.10% taker
}

# Symbols to monitor
SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT"]


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
    prices: dict | None = None,
) -> None:
    """Save current state to JSON file for dashboard."""
    state = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "is_running": is_running,
        "mode": "REAL DATA",
        "portfolio": portfolio,
        "recent_trades": trades[-50:],
        "recent_opportunities": opportunities[-50:],
        "statistics": stats,
        "live_prices": prices or {},
    }
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, default=decimal_default, indent=2))


async def fetch_prices(exchanges: dict) -> dict:
    """Fetch current prices from all exchanges."""
    prices = {}

    for name, exchange in exchanges.items():
        prices[name] = {}
        for symbol in SYMBOLS:
            try:
                ticker = await exchange.fetch_ticker(symbol)
                if ticker and ticker.get("bid") and ticker.get("ask"):
                    prices[name][symbol] = {
                        "bid": Decimal(str(ticker["bid"])),
                        "ask": Decimal(str(ticker["ask"])),
                        "last": Decimal(str(ticker.get("last", ticker["bid"]))),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
            except Exception as e:
                logger.debug(f"Could not fetch {symbol} from {name}: {e}")

    return prices


def find_arbitrage_opportunities(prices: dict, min_profit_pct: Decimal = Decimal("0.01")) -> list:
    """Find arbitrage opportunities across exchanges using real fees."""
    opportunities = []

    for symbol in SYMBOLS:
        # Get all exchanges that have this symbol
        exchange_prices = []
        for exchange, syms in prices.items():
            if symbol in syms:
                exchange_prices.append({
                    "exchange": exchange,
                    "bid": syms[symbol]["bid"],
                    "ask": syms[symbol]["ask"],
                    "fee": EXCHANGE_FEES.get(exchange, Decimal("0.1")),
                })

        if len(exchange_prices) < 2:
            continue

        # Compare all pairs
        for i, buy_ex in enumerate(exchange_prices):
            for sell_ex in exchange_prices[i+1:]:
                # Try buy on exchange i, sell on exchange j
                spread1 = (sell_ex["bid"] - buy_ex["ask"]) / buy_ex["ask"] * 100
                # Try buy on exchange j, sell on exchange i
                spread2 = (buy_ex["bid"] - sell_ex["ask"]) / sell_ex["ask"] * 100

                # Calculate actual fees for this pair (taker on both sides)
                fee_pct_1 = buy_ex["fee"] + sell_ex["fee"]  # buy on i, sell on j
                fee_pct_2 = sell_ex["fee"] + buy_ex["fee"]  # buy on j, sell on i

                if spread1 > fee_pct_1:
                    net_profit = spread1 - fee_pct_1
                    opportunities.append({
                        "symbol": symbol,
                        "buy_exchange": buy_ex["exchange"],
                        "sell_exchange": sell_ex["exchange"],
                        "buy_price": buy_ex["ask"],
                        "sell_price": sell_ex["bid"],
                        "gross_spread_pct": spread1,
                        "total_fees_pct": fee_pct_1,
                        "net_profit_pct": net_profit,
                        "detected_at": datetime.now(timezone.utc).isoformat(),
                    })

                if spread2 > fee_pct_2:
                    net_profit = spread2 - fee_pct_2
                    opportunities.append({
                        "symbol": symbol,
                        "buy_exchange": sell_ex["exchange"],
                        "sell_exchange": buy_ex["exchange"],
                        "buy_price": sell_ex["ask"],
                        "sell_price": buy_ex["bid"],
                        "gross_spread_pct": spread2,
                        "total_fees_pct": fee_pct_2,
                        "net_profit_pct": net_profit,
                        "detected_at": datetime.now(timezone.utc).isoformat(),
                    })

    return opportunities


def create_orderbook_from_price(symbol: str, price: Decimal) -> Orderbook:
    """Create a simple orderbook from a price for paper trading."""
    spread = price * Decimal("0.0001")

    bids = [
        OrderbookLevel(price=price - spread * (i + 1), volume=Decimal("100"))
        for i in range(5)
    ]
    asks = [
        OrderbookLevel(price=price + spread * (i + 1), volume=Decimal("100"))
        for i in range(5)
    ]

    return Orderbook(
        symbol=symbol,
        exchange=Exchange.BINANCE,
        bids=bids,
        asks=asks,
        timestamp=datetime.now(timezone.utc),
    )


async def main() -> None:
    """Run with real market data from multiple exchanges."""
    setup_logging()
    logger.info("Starting Arbitrage Bot with REAL MARKET DATA")
    logger.info("Connecting to exchanges (public data, no API keys)...")

    # Initialize exchanges
    exchanges = {}
    for name, exchange_class in EXCHANGES.items():
        try:
            exchange = exchange_class({"enableRateLimit": True})
            await exchange.load_markets()
            exchanges[name] = exchange
            logger.info(f"Connected to {name} ({len(exchange.symbols)} symbols)")
        except Exception as e:
            logger.warning(f"Could not connect to {name}: {e}")

    if len(exchanges) < 2:
        logger.error("Need at least 2 exchanges for arbitrage. Exiting.")
        return

    logger.info(f"Connected to {len(exchanges)} exchanges: {list(exchanges.keys())}")

    # Initialize paper trader
    paper_trader = PaperTrader()

    all_opportunities: list[dict] = []
    all_trades: list[dict] = []

    iteration = 0
    start_time = datetime.now(timezone.utc)

    logger.info(f"Monitoring symbols: {SYMBOLS}")
    logger.info(f"Initial portfolio: ${paper_trader.portfolio.total_value_usd}")

    try:
        while True:
            iteration += 1

            # Fetch real prices
            prices = await fetch_prices(exchanges)

            # Log sample prices and best spreads
            if iteration == 1 or iteration % 20 == 0:
                for ex, syms in prices.items():
                    if "BTC/USDT" in syms:
                        btc = syms["BTC/USDT"]
                        logger.info(f"{ex}: BTC/USDT bid=${btc['bid']:.2f} ask=${btc['ask']:.2f}")

                # Show best spread analysis
                for symbol in SYMBOLS:
                    best_buy = None
                    best_sell = None
                    for ex, syms in prices.items():
                        if symbol in syms:
                            if best_buy is None or syms[symbol]["ask"] < best_buy[1]:
                                best_buy = (ex, syms[symbol]["ask"])
                            if best_sell is None or syms[symbol]["bid"] > best_sell[1]:
                                best_sell = (ex, syms[symbol]["bid"])

                    if best_buy and best_sell and best_buy[0] != best_sell[0]:
                        spread = (best_sell[1] - best_buy[1]) / best_buy[1] * 100
                        fees = EXCHANGE_FEES[best_buy[0]] + EXCHANGE_FEES[best_sell[0]]
                        net = spread - fees
                        status = "✅" if net > 0 else "❌"
                        logger.info(
                            f"{symbol} best: buy@{best_buy[0]} ${best_buy[1]:.2f} -> "
                            f"sell@{best_sell[0]} ${best_sell[1]:.2f} | "
                            f"spread={spread:.4f}% fees={fees:.2f}% net={net:.4f}% {status}"
                        )

            # Find arbitrage opportunities
            opps = find_arbitrage_opportunities(prices)

            for opp in opps:
                all_opportunities.append(opp)

                logger.info(
                    f"🎯 OPPORTUNITY: {opp['symbol']} "
                    f"{opp['buy_exchange']}->{opp['sell_exchange']} "
                    f"spread={opp['gross_spread_pct']:.4f}% "
                    f"fees={opp.get('total_fees_pct', 0):.2f}% "
                    f"net={opp['net_profit_pct']:.4f}%"
                )

                # Create ArbitrageOpportunity for paper trading
                volume = Decimal("0.01") if "BTC" in opp["symbol"] else Decimal("0.1")

                arb_opp = ArbitrageOpportunity(
                    id=f"opp-{iteration}-{len(all_opportunities)}",
                    type=ArbitrageType.CROSS_EXCHANGE,
                    status=OpportunityStatus.DETECTED,
                    buy_exchange=opp["buy_exchange"],
                    sell_exchange=opp["sell_exchange"],
                    symbol=opp["symbol"],
                    buy_price=opp["buy_price"],
                    sell_price=opp["sell_price"],
                    max_volume=volume * 10,
                    recommended_volume=volume,
                    gross_profit_percent=opp["gross_spread_pct"],
                    net_profit_percent=opp["net_profit_pct"],
                    estimated_profit_usd=volume * opp["buy_price"] * opp["net_profit_pct"] / 100,
                    buy_fee_percent=Decimal("0.1"),
                    sell_fee_percent=Decimal("0.1"),
                    estimated_slippage_percent=Decimal("0.02"),
                    detected_at=datetime.now(timezone.utc),
                    expires_at=datetime.now(timezone.utc),
                    window_ms=5000,
                    orderbook_depth_ok=True,
                    liquidity_ok=True,
                    risk_score=Decimal("0.3"),
                )

                # Execute paper trade
                buy_ob = create_orderbook_from_price(opp["symbol"], opp["buy_price"])
                sell_ob = create_orderbook_from_price(opp["symbol"], opp["sell_price"])

                trade = await paper_trader.execute_arbitrage(arb_opp, buy_ob, sell_ob)

                trade_dict = {
                    "id": trade.id,
                    "symbol": opp["symbol"],
                    "buy_exchange": opp["buy_exchange"],
                    "sell_exchange": opp["sell_exchange"],
                    "buy_price": float(opp["buy_price"]),
                    "sell_price": float(opp["sell_price"]),
                    "volume": float(volume),
                    "gross_profit": float(trade.gross_profit),
                    "net_profit": float(trade.net_profit),
                    "fees": float(trade.total_fees),
                    "status": trade.status,
                    "executed_at": datetime.now(timezone.utc).isoformat(),
                    "execution_ms": trade.total_execution_ms,
                    "real_data": True,
                }
                all_trades.append(trade_dict)
                opp["status"] = "executed" if trade.status == "completed" else "failed"

            # Save state for dashboard
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

            # Format prices for dashboard
            price_display = {}
            for ex, syms in prices.items():
                for sym, data in syms.items():
                    if sym not in price_display:
                        price_display[sym] = {}
                    price_display[sym][ex] = {
                        "bid": float(data["bid"]),
                        "ask": float(data["ask"]),
                    }

            save_state(
                portfolio=portfolio_dict,
                trades=all_trades,
                opportunities=all_opportunities,
                stats=stats,
                is_running=True,
                prices=price_display,
            )

            # Log status periodically
            if iteration % 10 == 0:
                elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
                logger.info(
                    f"[{elapsed:.0f}s] Iteration {iteration}: "
                    f"opportunities={len(all_opportunities)} "
                    f"trades={portfolio.total_trades} "
                    f"P&L=${portfolio.total_pnl_usd:+.2f}"
                )

            # Wait before next scan
            await asyncio.sleep(3)  # 3 seconds between scans

    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        # Close exchange connections
        for name, exchange in exchanges.items():
            await exchange.close()
            logger.info(f"Disconnected from {name}")

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
        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.info("=" * 50)
        logger.info("REAL DATA - FINAL REPORT")
        logger.info("=" * 50)
        logger.info(f"Runtime: {elapsed:.1f}s")
        logger.info(f"Iterations: {iteration}")
        logger.info(f"Opportunities Found: {len(all_opportunities)}")
        logger.info(f"Trades Executed: {portfolio.total_trades}")
        logger.info(f"Win Rate: {portfolio.win_rate:.1f}%")
        logger.info(f"Total P&L: ${portfolio.total_pnl_usd:+.2f}")
        logger.info(f"Final Portfolio: ${portfolio.total_value_usd:.2f}")
        logger.info("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
