#!/bin/bash
# Setup script for arbitrage bot

set -e

echo "=== Arbitrage Bot Setup ==="

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
REQUIRED_VERSION="3.11"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "Error: Python $REQUIRED_VERSION or higher is required (found $PYTHON_VERSION)"
    exit 1
fi

echo "Python version: $PYTHON_VERSION ✓"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements-dev.txt

# Install Playwright browsers
echo "Installing Playwright browsers..."
playwright install chromium

# Create required directories
echo "Creating directories..."
mkdir -p data logs tests/screenshots/e2e

# Copy .env.example if .env doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
fi

# Initialize database
echo "Initializing database..."
python -c "
import asyncio
from src.database.db_manager import init_db
asyncio.run(init_db())
print('Database initialized')
"

# Run initial lint
echo "Running initial lint check..."
ruff check src/ tests/ --fix || true

echo ""
echo "=== Setup Complete ==="
echo ""
echo "To activate the virtual environment:"
echo "  source venv/bin/activate"
echo ""
echo "Available commands:"
echo "  make run        - Run the bot in paper trading mode"
echo "  make dashboard  - Start the Streamlit dashboard"
echo "  make test       - Run all tests"
echo "  make lint       - Run linters"
echo ""
