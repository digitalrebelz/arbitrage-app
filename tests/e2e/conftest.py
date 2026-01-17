"""Pytest configuration for E2E tests."""

import os
import subprocess
import time
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def screenshot_dir() -> Path:
    """Create and return screenshot directory."""
    screenshots = Path("tests/screenshots/e2e")
    screenshots.mkdir(parents=True, exist_ok=True)
    return screenshots


@pytest.fixture(scope="module")
def streamlit_server():
    """Start Streamlit server for testing."""
    # Start Streamlit in background
    env = os.environ.copy()
    env["STREAMLIT_SERVER_HEADLESS"] = "true"
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"

    process = subprocess.Popen(
        ["streamlit", "run", "src/ui/dashboard.py", "--server.port", "8502"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for server to start
    time.sleep(5)

    yield "http://localhost:8502"

    # Cleanup
    process.terminate()
    process.wait(timeout=5)


@pytest.fixture(scope="function")
def page_with_screenshots(page, screenshot_dir: Path):
    """Page fixture that takes screenshots on failure."""
    yield page

    # Take screenshot if test failed
    if hasattr(page, "_last_test_failed") and page._last_test_failed:
        screenshot_path = screenshot_dir / f"failure_{time.time()}.png"
        page.screenshot(path=str(screenshot_path))
