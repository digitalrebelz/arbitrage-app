.PHONY: install install-dev test test-fast test-e2e lint format clean run dashboard help

# Default target
help:
	@echo "Arbitrage Bot - Available Commands"
	@echo "=================================="
	@echo "make install      - Install production dependencies"
	@echo "make install-dev  - Install development dependencies + playwright"
	@echo "make test         - Run all tests with coverage"
	@echo "make test-fast    - Run unit tests only"
	@echo "make test-e2e     - Run E2E tests with Playwright"
	@echo "make lint         - Run linters (ruff, mypy)"
	@echo "make format       - Format code (black, isort)"
	@echo "make clean        - Remove cache and build artifacts"
	@echo "make run          - Start bot in paper trading mode"
	@echo "make dashboard    - Start Streamlit dashboard"

# Installation
install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt
	playwright install chromium

# Testing
test:
	pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=html

test-fast:
	pytest tests/unit/ -v

test-e2e:
	@mkdir -p tests/screenshots/e2e
	pytest tests/e2e/ -v --headed

# Code quality
lint:
	ruff check src/ tests/
	mypy src/

format:
	black src/ tests/
	isort src/ tests/

# Clean
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	rm -rf dist/ build/ *.egg-info/

# Run
run:
	python -m src.main --mode paper --duration 60

dashboard:
	streamlit run src/ui/dashboard.py

# Pre-commit
pre-commit:
	pre-commit run --all-files

# Security
security:
	pip-audit
	bandit -r src/
