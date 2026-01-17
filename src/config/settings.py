"""Application settings using Pydantic."""

from decimal import Decimal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Trading mode
    TRADING_MODE: str = "paper"

    # Initial balances
    INITIAL_BALANCE_USD: float = 10000.0
    INITIAL_BALANCE_BTC: float = 1.0
    INITIAL_BALANCE_ETH: float = 10.0

    # Position limits
    MAX_POSITION_SIZE_USD: float = 1000.0
    MAX_TOTAL_EXPOSURE_USD: float = 5000.0

    # Risk limits
    MAX_DRAWDOWN_PERCENT: float = 10.0
    MIN_PROFIT_THRESHOLD_PERCENT: Decimal = Decimal("0.1")

    # Performance settings
    ORDERBOOK_CACHE_TTL_MS: int = 100
    MAX_CONCURRENT_REQUESTS: int = 50
    SCAN_INTERVAL_MS: int = 500

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/arbitrage.log"

    # Exchange API keys (optional for paper trading)
    BINANCE_API_KEY: str = ""
    BINANCE_SECRET: str = ""
    KRAKEN_API_KEY: str = ""
    KRAKEN_SECRET: str = ""

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///data/arbitrage.db"

    # Dashboard
    DASHBOARD_PORT: int = 8501

    class Config:
        """Pydantic config."""

        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
