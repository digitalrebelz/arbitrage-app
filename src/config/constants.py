"""Application constants."""

from decimal import Decimal

# Supported symbols for trading
DEFAULT_SYMBOLS = [
    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT",
    "BNB/USDT",
    "XRP/USDT",
]

# Minimum volumes for trading
MIN_TRADE_VOLUME_USD = Decimal("10")
MIN_TRADE_VOLUME_BTC = Decimal("0.0001")
MIN_TRADE_VOLUME_ETH = Decimal("0.001")

# Fee estimates by exchange (as decimal, e.g., 0.001 = 0.1%)
EXCHANGE_FEES = {
    "binance": {
        "maker": Decimal("0.001"),
        "taker": Decimal("0.001"),
    },
    "kraken": {
        "maker": Decimal("0.0016"),
        "taker": Decimal("0.0026"),
    },
    "coinbase": {
        "maker": Decimal("0.004"),
        "taker": Decimal("0.006"),
    },
}

# Timing constants
OPPORTUNITY_WINDOW_MS = 5000  # 5 seconds
ORDERBOOK_STALE_MS = 100  # 100ms max cache age
MAX_EXECUTION_LATENCY_MS = 100  # Target execution time

# Risk constants
DEFAULT_RISK_SCORE = Decimal("0.5")
MAX_RISK_SCORE = Decimal("0.8")  # Don't trade above this risk

# Slippage constants
BASE_SLIPPAGE_BPS = 5  # 5 basis points base slippage
MAX_SLIPPAGE_PERCENT = Decimal("2")  # 2% max slippage

# Portfolio constants
DEFAULT_POSITION_SIZE_PERCENT = Decimal("10")  # 10% of portfolio per trade

# API rate limits (requests per minute)
RATE_LIMITS = {
    "binance": 1200,
    "kraken": 60,
    "coinbase": 100,
}
