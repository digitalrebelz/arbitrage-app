"""Exchange connectors module."""

from loguru import logger

from src.exchanges.base import BaseExchange
from src.exchanges.crypto.binance import BinanceExchange
from src.models.market import Exchange


class ExchangeFactory:
    """Factory for creating and managing exchange instances."""

    _instances: dict[Exchange, BaseExchange] = {}

    @classmethod
    async def get_exchange(cls, exchange: Exchange, **kwargs: str) -> BaseExchange:
        """Get or create an exchange instance."""
        if exchange not in cls._instances:
            instance = cls._create_exchange(exchange, **kwargs)
            connected = await instance.connect()
            if not connected:
                raise ConnectionError(f"Failed to connect to {exchange}")
            cls._instances[exchange] = instance
        return cls._instances[exchange]

    @classmethod
    def _create_exchange(cls, exchange: Exchange, **kwargs: str) -> BaseExchange:
        """Create a new exchange instance."""
        if exchange == Exchange.BINANCE:
            return BinanceExchange(**kwargs)
        raise ValueError(f"Unknown exchange: {exchange}")

    @classmethod
    async def close_all(cls) -> None:
        """Close all exchange connections."""
        for exchange in list(cls._instances.values()):
            await exchange.disconnect()
        cls._instances.clear()
        logger.info("All exchange connections closed")


__all__ = ["ExchangeFactory", "BaseExchange", "BinanceExchange"]
