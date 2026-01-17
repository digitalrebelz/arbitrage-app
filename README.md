# Arbitrage Bot

High-frequency arbitrage trading bot with paper trading capabilities. Detects and executes arbitrage opportunities across multiple cryptocurrency exchanges.

## Features

- **Real-time Arbitrage Detection**: Scans for cross-exchange and funding rate arbitrage opportunities
- **Paper Trading**: Realistic simulation with slippage, fees, and orderbook validation
- **Would-Have-Executed Tracking**: Validates if simulated trades would have actually executed
- **Risk Management**: Position limits, max drawdown, and risk scoring
- **Streamlit Dashboard**: Real-time monitoring and analytics
- **Async Architecture**: High-performance async/await design for low latency

## Quick Start

### Prerequisites

- Python 3.11+
- pip

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/arbitrage-bot.git
cd arbitrage-bot

# Run setup script
chmod +x scripts/setup.sh
./scripts/setup.sh

# Or manual setup
python -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
playwright install chromium
```

### Configuration

Copy the example environment file and configure:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```env
TRADING_MODE=paper
INITIAL_BALANCE_USD=10000
MIN_PROFIT_THRESHOLD_PERCENT=0.1
# Add exchange API keys for live data (optional)
BINANCE_API_KEY=
BINANCE_SECRET=
```

### Running

**Start the bot in paper trading mode:**

```bash
make run
# or
python -m src.main --mode paper --duration 60
```

**Start the dashboard:**

```bash
make dashboard
# or
streamlit run src/ui/dashboard.py
```

## Project Structure

```
arbitrage-bot/
├── src/
│   ├── arbitrage/       # Opportunity detection and calculation
│   ├── config/          # Settings and configuration
│   ├── database/        # SQLAlchemy models and CRUD
│   ├── exchanges/       # Exchange connectors (CCXT)
│   ├── execution/       # Paper trading and order validation
│   ├── models/          # Pydantic data models
│   ├── risk/            # Risk management
│   └── ui/              # Streamlit dashboard
├── tests/
│   ├── unit/            # Unit tests
│   ├── integration/     # Integration tests
│   └── e2e/             # Playwright E2E tests
├── scripts/             # Utility scripts
└── data/                # Database and data files
```

## Available Commands

```bash
make install      # Install production dependencies
make install-dev  # Install dev dependencies + playwright
make test         # Run all tests with coverage
make test-fast    # Run unit tests only
make test-e2e     # Run E2E tests with Playwright
make lint         # Run linters (ruff, mypy)
make format       # Format code (black, isort)
make run          # Start bot in paper trading mode
make dashboard    # Start Streamlit dashboard
make clean        # Remove cache and build artifacts
```

## Architecture

### Core Components

- **ArbitrageDetector**: Scans for opportunities across exchanges
- **ArbitrageCalculator**: Computes profits considering fees and slippage
- **PaperTrader**: Simulates trade execution realistically
- **OrderValidator**: Checks if orders would have executed
- **SlippageSimulator**: Estimates slippage based on orderbook depth

### Financial Precision

All monetary calculations use Python's `Decimal` type to ensure accuracy. Never use `float` for financial values.

```python
from decimal import Decimal

price = Decimal("67000.50")
fee = Decimal("0.001")  # 0.1%
```

### Async Design

All I/O operations are async for optimal performance:

```python
async def scan_opportunities():
    tasks = [exchange.get_ticker(symbol) for symbol in symbols]
    results = await asyncio.gather(*tasks)
```

## Testing

### Run all tests

```bash
make test
```

### Run unit tests only

```bash
make test-fast
```

### Run E2E tests

```bash
make test-e2e
```

Screenshots are saved to `tests/screenshots/e2e/`.

## Dashboard

The Streamlit dashboard provides:

- **Live Opportunities**: Current arbitrage opportunities
- **Trade History**: All executed trades with filters
- **Performance**: Equity curve, profit distribution, metrics
- **Configuration**: Exchange connections, strategy settings

Access at `http://localhost:8501` after running `make dashboard`.

## Risk Management

The bot includes built-in risk controls:

- Maximum position size per trade
- Maximum total exposure
- Maximum drawdown limit
- Risk scoring per opportunity
- Would-have-executed validation

## Development

### Code Style

- Type hints required for all functions
- Google-style docstrings
- Max 80 lines per function
- Black + isort formatting

### Pre-commit Hooks

```bash
pre-commit install
pre-commit run --all-files
```

## License

MIT License

## Disclaimer

This software is for educational purposes only. Trading cryptocurrencies involves substantial risk of loss. Always do your own research and never trade with money you cannot afford to lose.
