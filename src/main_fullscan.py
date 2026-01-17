"""Full market scan - monitors ALL pairs and logs fill probability for ML training."""

import asyncio
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import ccxt.async_support as ccxt
from loguru import logger

from src.config.logging_config import setup_logging
from src.execution.paper_trader import PaperTrader
from src.models.market import Exchange, Orderbook, OrderbookLevel
from src.models.opportunity import ArbitrageOpportunity, ArbitrageType, OpportunityStatus

# Data storage
STATE_FILE = Path("data/simulation_state.json")
OPPORTUNITIES_LOG = Path("data/opportunities_log.jsonl")  # Line-delimited JSON for ML
SPREADS_LOG = Path("data/spreads_log.jsonl")  # All spread data for analysis

# Exchanges
EXCHANGES = {
    "binance": ccxt.binance,
    "kraken": ccxt.kraken,
    "kucoin": ccxt.kucoin,
    "bybit": ccxt.bybit,
}

# Real trading fees (taker)
EXCHANGE_FEES = {
    "binance": Decimal("0.10"),
    "kraken": Decimal("0.26"),
    "kucoin": Decimal("0.10"),
    "bybit": Decimal("0.10"),
}

# Common trading pairs to scan (expanded list)
SYMBOLS = [
    # Major pairs
    "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
    "ADA/USDT", "DOGE/USDT", "AVAX/USDT", "DOT/USDT", "MATIC/USDT",
    "LINK/USDT", "UNI/USDT", "ATOM/USDT", "LTC/USDT", "ETC/USDT",
    "XLM/USDT", "ALGO/USDT", "NEAR/USDT", "FTM/USDT", "SAND/USDT",
    # More volatile / less liquid (potentially better spreads)
    "APE/USDT", "GALA/USDT", "MANA/USDT", "AXS/USDT", "ENJ/USDT",
    "CHZ/USDT", "FLOW/USDT", "IMX/USDT", "LRC/USDT", "ENS/USDT",
    "OP/USDT", "ARB/USDT", "SUI/USDT", "SEI/USDT", "TIA/USDT",
    "PEPE/USDT", "SHIB/USDT", "FLOKI/USDT", "WIF/USDT", "BONK/USDT",
]


def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def append_jsonl(filepath: Path, data: dict) -> None:
    """Append a JSON line to file for ML training data."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "a") as f:
        f.write(json.dumps(data, default=decimal_default) + "\n")


def save_state(state: dict) -> None:
    """Save dashboard state."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, default=decimal_default, indent=2))


def calculate_fill_probability(
    orderbook: dict | None,
    volume: Decimal,
    side: str,  # "buy" or "sell"
) -> dict:
    """
    Calculate probability that an order would be filled based on orderbook.

    Returns dict with:
    - fill_probability: 0-100%
    - depth_available: volume available at best prices
    - levels_needed: how many orderbook levels needed
    - slippage_estimate: estimated slippage %
    - confidence: how confident we are in this estimate
    """
    if not orderbook:
        return {
            "fill_probability": 0,
            "depth_available": 0,
            "levels_needed": 0,
            "slippage_estimate": 100,
            "confidence": "none",
            "reason": "no_orderbook",
        }

    levels = orderbook.get("asks" if side == "buy" else "bids", [])

    if not levels:
        return {
            "fill_probability": 0,
            "depth_available": 0,
            "levels_needed": 0,
            "slippage_estimate": 100,
            "confidence": "none",
            "reason": "empty_orderbook",
        }

    # Calculate cumulative volume and price impact
    cumulative_volume = Decimal("0")
    weighted_price = Decimal("0")
    best_price = Decimal(str(levels[0][0]))
    levels_needed = 0

    for price, vol in levels:
        price = Decimal(str(price))
        vol = Decimal(str(vol))

        levels_needed += 1
        take_volume = min(vol, volume - cumulative_volume)
        weighted_price += price * take_volume
        cumulative_volume += take_volume

        if cumulative_volume >= volume:
            break

    # Calculate metrics
    if cumulative_volume > 0:
        avg_price = weighted_price / cumulative_volume
        slippage = abs((avg_price - best_price) / best_price * 100)
    else:
        slippage = Decimal("100")

    # Fill probability based on multiple factors
    volume_ratio = float(cumulative_volume / volume) if volume > 0 else 0

    # Factors affecting fill probability
    depth_score = min(100, volume_ratio * 100)  # How much volume is available
    slippage_score = max(0, 100 - float(slippage) * 10)  # Penalty for slippage
    levels_score = max(0, 100 - (levels_needed - 1) * 10)  # Penalty for needing many levels

    fill_probability = (depth_score * 0.5 + slippage_score * 0.3 + levels_score * 0.2)

    # Confidence based on orderbook depth
    if len(levels) >= 10 and cumulative_volume >= volume:
        confidence = "high"
    elif len(levels) >= 5 and cumulative_volume >= volume * Decimal("0.8"):
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "fill_probability": round(fill_probability, 1),
        "depth_available": float(cumulative_volume),
        "volume_requested": float(volume),
        "levels_needed": levels_needed,
        "slippage_estimate": round(float(slippage), 4),
        "confidence": confidence,
        "reason": "calculated",
    }


async def fetch_ticker_and_orderbook(exchange, symbol: str) -> dict | None:
    """Fetch ticker and orderbook for a symbol."""
    try:
        ticker = await exchange.fetch_ticker(symbol)
        orderbook = await exchange.fetch_order_book(symbol, limit=20)

        if ticker and ticker.get("bid") and ticker.get("ask"):
            return {
                "bid": Decimal(str(ticker["bid"])),
                "ask": Decimal(str(ticker["ask"])),
                "last": Decimal(str(ticker.get("last", ticker["bid"]))),
                "volume_24h": ticker.get("quoteVolume", 0),
                "orderbook": orderbook,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
    except Exception as e:
        logger.debug(f"Could not fetch {symbol}: {e}")
    return None


async def scan_symbol(symbol: str, exchanges: dict) -> list[dict]:
    """Scan a single symbol across all exchanges."""
    results = []

    # Fetch from all exchanges in parallel
    tasks = {
        name: fetch_ticker_and_orderbook(ex, symbol)
        for name, ex in exchanges.items()
    }

    fetched = {}
    for name, task in tasks.items():
        try:
            result = await task
            if result:
                fetched[name] = result
        except Exception:
            pass

    if len(fetched) < 2:
        return results

    # Compare all exchange pairs
    exchange_list = list(fetched.keys())

    for i, ex1 in enumerate(exchange_list):
        for ex2 in exchange_list[i+1:]:
            data1 = fetched[ex1]
            data2 = fetched[ex2]

            # Direction 1: Buy on ex1, sell on ex2
            spread1 = (data2["bid"] - data1["ask"]) / data1["ask"] * 100
            fees1 = EXCHANGE_FEES[ex1] + EXCHANGE_FEES[ex2]
            net1 = spread1 - fees1

            # Direction 2: Buy on ex2, sell on ex1
            spread2 = (data1["bid"] - data2["ask"]) / data2["ask"] * 100
            fees2 = fees1  # Same fees
            net2 = spread2 - fees2

            # Calculate fill probabilities
            volume = Decimal("0.01") if "BTC" in symbol else Decimal("1.0")

            fill_prob_buy1 = calculate_fill_probability(data1["orderbook"], volume, "buy")
            fill_prob_sell2 = calculate_fill_probability(data2["orderbook"], volume, "sell")
            fill_prob_buy2 = calculate_fill_probability(data2["orderbook"], volume, "buy")
            fill_prob_sell1 = calculate_fill_probability(data1["orderbook"], volume, "sell")

            # Combined fill probability (both sides must fill)
            combined_prob1 = (fill_prob_buy1["fill_probability"] * fill_prob_sell2["fill_probability"]) / 100
            combined_prob2 = (fill_prob_buy2["fill_probability"] * fill_prob_sell1["fill_probability"]) / 100

            timestamp = datetime.now(timezone.utc).isoformat()

            # Record spread data (for all spreads, profitable or not)
            spread_record = {
                "id": str(uuid4()),
                "timestamp": timestamp,
                "symbol": symbol,
                "exchange_buy": ex1,
                "exchange_sell": ex2,
                "buy_price": data1["ask"],
                "sell_price": data2["bid"],
                "spread_pct": spread1,
                "fees_pct": fees1,
                "net_pct": net1,
                "fill_probability": combined_prob1,
                "buy_fill_prob": fill_prob_buy1,
                "sell_fill_prob": fill_prob_sell2,
                "is_profitable": net1 > 0,
                "volume_24h_buy": data1.get("volume_24h", 0),
                "volume_24h_sell": data2.get("volume_24h", 0),
            }

            # Log all spreads for ML training
            append_jsonl(SPREADS_LOG, spread_record)

            # If profitable, also log as opportunity
            if net1 > 0:
                opp = {
                    **spread_record,
                    "type": "cross_exchange",
                    "recommended_volume": float(volume),
                    "estimated_profit_usd": float(volume * data1["ask"] * net1 / 100),
                    "execution_window_ms": 5000,
                    "status": "detected",
                }
                append_jsonl(OPPORTUNITIES_LOG, opp)
                results.append(opp)

                logger.info(
                    f"🎯 {symbol} {ex1}->{ex2}: "
                    f"spread={spread1:.4f}% net={net1:.4f}% "
                    f"fill_prob={combined_prob1:.1f}%"
                )

            # Check reverse direction too
            spread_record_rev = {
                "id": str(uuid4()),
                "timestamp": timestamp,
                "symbol": symbol,
                "exchange_buy": ex2,
                "exchange_sell": ex1,
                "buy_price": data2["ask"],
                "sell_price": data1["bid"],
                "spread_pct": spread2,
                "fees_pct": fees2,
                "net_pct": net2,
                "fill_probability": combined_prob2,
                "buy_fill_prob": fill_prob_buy2,
                "sell_fill_prob": fill_prob_sell1,
                "is_profitable": net2 > 0,
                "volume_24h_buy": data2.get("volume_24h", 0),
                "volume_24h_sell": data1.get("volume_24h", 0),
            }

            append_jsonl(SPREADS_LOG, spread_record_rev)

            if net2 > 0:
                opp = {
                    **spread_record_rev,
                    "type": "cross_exchange",
                    "recommended_volume": float(volume),
                    "estimated_profit_usd": float(volume * data2["ask"] * net2 / 100),
                    "execution_window_ms": 5000,
                    "status": "detected",
                }
                append_jsonl(OPPORTUNITIES_LOG, opp)
                results.append(opp)

                logger.info(
                    f"🎯 {symbol} {ex2}->{ex1}: "
                    f"spread={spread2:.4f}% net={net2:.4f}% "
                    f"fill_prob={combined_prob2:.1f}%"
                )

    return results


async def main() -> None:
    """Full market scan with fill probability tracking."""
    setup_logging()
    logger.info("Starting FULL MARKET SCAN with fill probability tracking")
    logger.info(f"Monitoring {len(SYMBOLS)} symbols across {len(EXCHANGES)} exchanges")
    logger.info(f"Data logged to: {SPREADS_LOG} and {OPPORTUNITIES_LOG}")

    # Initialize exchanges
    exchanges = {}
    for name, exchange_class in EXCHANGES.items():
        try:
            exchange = exchange_class({"enableRateLimit": True})
            await exchange.load_markets()
            exchanges[name] = exchange
            logger.info(f"✅ {name}: {len(exchange.symbols)} symbols")
        except Exception as e:
            logger.warning(f"❌ {name}: {e}")

    if len(exchanges) < 2:
        logger.error("Need at least 2 exchanges")
        return

    # Initialize paper trader
    paper_trader = PaperTrader()

    all_opportunities = []
    all_trades = []
    total_spreads_logged = 0

    iteration = 0
    start_time = datetime.now(timezone.utc)

    logger.info(f"Initial portfolio: ${paper_trader.portfolio.total_value_usd}")

    try:
        while True:
            iteration += 1
            iteration_opportunities = []

            # Scan all symbols
            for symbol in SYMBOLS:
                try:
                    opps = await scan_symbol(symbol, exchanges)
                    iteration_opportunities.extend(opps)
                    total_spreads_logged += len(EXCHANGES) * (len(EXCHANGES) - 1)  # Rough estimate
                except Exception as e:
                    logger.debug(f"Error scanning {symbol}: {e}")

                # Small delay to respect rate limits
                await asyncio.sleep(0.1)

            all_opportunities.extend(iteration_opportunities)

            # Execute paper trades for profitable opportunities
            for opp in iteration_opportunities:
                try:
                    # Create orderbook for paper trading
                    buy_ob = Orderbook(
                        symbol=opp["symbol"],
                        exchange=Exchange.BINANCE,
                        bids=[OrderbookLevel(price=Decimal(str(opp["sell_price"])), volume=Decimal("100"))],
                        asks=[OrderbookLevel(price=Decimal(str(opp["buy_price"])), volume=Decimal("100"))],
                        timestamp=datetime.now(timezone.utc),
                    )
                    sell_ob = buy_ob  # Simplified

                    arb_opp = ArbitrageOpportunity(
                        id=opp["id"],
                        type=ArbitrageType.CROSS_EXCHANGE,
                        status=OpportunityStatus.DETECTED,
                        buy_exchange=opp["exchange_buy"],
                        sell_exchange=opp["exchange_sell"],
                        symbol=opp["symbol"],
                        buy_price=Decimal(str(opp["buy_price"])),
                        sell_price=Decimal(str(opp["sell_price"])),
                        max_volume=Decimal(str(opp["recommended_volume"])) * 10,
                        recommended_volume=Decimal(str(opp["recommended_volume"])),
                        gross_profit_percent=Decimal(str(opp["spread_pct"])),
                        net_profit_percent=Decimal(str(opp["net_pct"])),
                        estimated_profit_usd=Decimal(str(opp["estimated_profit_usd"])),
                        buy_fee_percent=EXCHANGE_FEES[opp["exchange_buy"]],
                        sell_fee_percent=EXCHANGE_FEES[opp["exchange_sell"]],
                        estimated_slippage_percent=Decimal("0.02"),
                        detected_at=datetime.now(timezone.utc),
                        expires_at=datetime.now(timezone.utc),
                        window_ms=5000,
                        orderbook_depth_ok=True,
                        liquidity_ok=opp["fill_probability"] > 50,
                        risk_score=Decimal(str(1 - opp["fill_probability"] / 100)),
                    )

                    trade = await paper_trader.execute_arbitrage(arb_opp, buy_ob, sell_ob)

                    trade_record = {
                        "id": trade.id,
                        "opportunity_id": opp["id"],
                        "symbol": opp["symbol"],
                        "buy_exchange": opp["exchange_buy"],
                        "sell_exchange": opp["exchange_sell"],
                        "predicted_fill_prob": opp["fill_probability"],
                        "actual_filled": trade.status == "completed",
                        "net_profit": float(trade.net_profit),
                        "executed_at": datetime.now(timezone.utc).isoformat(),
                    }
                    all_trades.append(trade_record)

                    # Log for ML training (prediction vs actual)
                    append_jsonl(OPPORTUNITIES_LOG, {
                        **opp,
                        "trade_result": trade_record,
                    })

                except Exception as e:
                    logger.debug(f"Trade error: {e}")

            # Update dashboard state
            portfolio = paper_trader.get_portfolio()

            state = {
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "is_running": True,
                "mode": "FULL SCAN + ML DATA",
                "iteration": iteration,
                "symbols_monitored": len(SYMBOLS),
                "exchanges": list(exchanges.keys()),
                "total_spreads_logged": total_spreads_logged,
                "portfolio": {
                    "total_value_usd": portfolio.total_value_usd,
                    "total_pnl_usd": portfolio.total_pnl_usd,
                    "total_pnl_percent": portfolio.total_pnl_percent,
                    "total_trades": portfolio.total_trades,
                    "winning_trades": portfolio.winning_trades,
                    "losing_trades": portfolio.losing_trades,
                    "win_rate": portfolio.win_rate,
                    "max_drawdown_percent": portfolio.max_drawdown_percent,
                },
                "recent_opportunities": all_opportunities[-20:],
                "recent_trades": all_trades[-20:],
            }
            save_state(state)

            # Log progress
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.info(
                f"[{elapsed:.0f}s] Iter {iteration}: "
                f"scanned={len(SYMBOLS)} symbols | "
                f"opportunities={len(iteration_opportunities)} | "
                f"total_logged={total_spreads_logged} | "
                f"trades={portfolio.total_trades} | "
                f"P&L=${portfolio.total_pnl_usd:+.2f}"
            )

            # Wait before next full scan
            await asyncio.sleep(5)

    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        for name, exchange in exchanges.items():
            await exchange.close()

        # Final stats
        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
        portfolio = paper_trader.get_portfolio()

        logger.info("=" * 60)
        logger.info("FULL SCAN FINAL REPORT")
        logger.info("=" * 60)
        logger.info(f"Runtime: {elapsed:.1f}s")
        logger.info(f"Iterations: {iteration}")
        logger.info(f"Symbols Monitored: {len(SYMBOLS)}")
        logger.info(f"Total Spreads Logged: {total_spreads_logged}")
        logger.info(f"Opportunities Found: {len(all_opportunities)}")
        logger.info(f"Trades Executed: {portfolio.total_trades}")
        logger.info(f"Final P&L: ${portfolio.total_pnl_usd:+.2f}")
        logger.info(f"Data saved to: {SPREADS_LOG}")
        logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
