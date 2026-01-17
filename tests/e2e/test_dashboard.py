"""End-to-end tests for Streamlit dashboard."""

from pathlib import Path

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
class TestDashboard:
    """E2E tests for the dashboard."""

    def test_dashboard_loads(
        self,
        page: Page,
        streamlit_server: str,
        screenshot_dir: Path,
    ) -> None:
        """Test that dashboard loads successfully."""
        # Navigate to dashboard
        page.goto(streamlit_server)
        page.wait_for_load_state("networkidle")

        # Take screenshot BEFORE
        page.screenshot(path=str(screenshot_dir / "01_dashboard_loaded_before.png"))

        # Check title is visible
        expect(page.get_by_text("Arbitrage Bot Dashboard")).to_be_visible(timeout=10000)

        # Take screenshot AFTER
        page.screenshot(path=str(screenshot_dir / "01_dashboard_loaded_after.png"))

    def test_sidebar_settings_visible(
        self,
        page: Page,
        streamlit_server: str,
        screenshot_dir: Path,
    ) -> None:
        """Test that sidebar settings are visible."""
        page.goto(streamlit_server)
        page.wait_for_load_state("networkidle")

        # Screenshot BEFORE
        page.screenshot(path=str(screenshot_dir / "02_sidebar_before.png"))

        # Check sidebar elements
        expect(page.get_by_text("Settings")).to_be_visible(timeout=10000)
        expect(page.get_by_text("Trading Mode")).to_be_visible(timeout=10000)
        expect(page.get_by_text("Markets")).to_be_visible(timeout=10000)
        expect(page.get_by_text("Risk Settings")).to_be_visible(timeout=10000)

        # Screenshot AFTER
        page.screenshot(path=str(screenshot_dir / "02_sidebar_after.png"))

    def test_metrics_display(
        self,
        page: Page,
        streamlit_server: str,
        screenshot_dir: Path,
    ) -> None:
        """Test that top metrics are displayed."""
        page.goto(streamlit_server)
        page.wait_for_load_state("networkidle")

        # Screenshot BEFORE
        page.screenshot(path=str(screenshot_dir / "03_metrics_before.png"))

        # Check metric labels
        expect(page.get_by_text("Portfolio Value")).to_be_visible(timeout=10000)
        expect(page.get_by_text("Total P&L")).to_be_visible(timeout=10000)
        expect(page.get_by_text("Win Rate")).to_be_visible(timeout=10000)
        expect(page.get_by_text("Max Drawdown")).to_be_visible(timeout=10000)
        expect(page.get_by_text("Bot Status")).to_be_visible(timeout=10000)

        # Screenshot AFTER
        page.screenshot(path=str(screenshot_dir / "03_metrics_after.png"))

    def test_live_opportunities_tab(
        self,
        page: Page,
        streamlit_server: str,
        screenshot_dir: Path,
    ) -> None:
        """Test Live Opportunities tab."""
        page.goto(streamlit_server)
        page.wait_for_load_state("networkidle")

        # Screenshot BEFORE clicking
        page.screenshot(path=str(screenshot_dir / "04_opportunities_tab_before.png"))

        # Click on Live Opportunities tab
        page.get_by_role("tab", name="Live Opportunities").click()
        page.wait_for_timeout(1000)

        # Check content
        expect(page.get_by_text("Current Arbitrage Opportunities")).to_be_visible(timeout=10000)

        # Screenshot AFTER
        page.screenshot(path=str(screenshot_dir / "04_opportunities_tab_after.png"))

    def test_trade_history_tab(
        self,
        page: Page,
        streamlit_server: str,
        screenshot_dir: Path,
    ) -> None:
        """Test Trade History tab."""
        page.goto(streamlit_server)
        page.wait_for_load_state("networkidle")

        # Screenshot BEFORE
        page.screenshot(path=str(screenshot_dir / "05_history_tab_before.png"))

        # Click on Trade History tab
        page.get_by_role("tab", name="Trade History").click()
        page.wait_for_timeout(1000)

        # Check content
        expect(page.get_by_text("Recent Trades")).to_be_visible(timeout=10000)

        # Check filters are present
        expect(page.locator("text=Status")).first.to_be_visible(timeout=10000)

        # Screenshot AFTER
        page.screenshot(path=str(screenshot_dir / "05_history_tab_after.png"))

    def test_performance_tab(
        self,
        page: Page,
        streamlit_server: str,
        screenshot_dir: Path,
    ) -> None:
        """Test Performance tab."""
        page.goto(streamlit_server)
        page.wait_for_load_state("networkidle")

        # Screenshot BEFORE
        page.screenshot(path=str(screenshot_dir / "06_performance_tab_before.png"))

        # Click on Performance tab
        page.get_by_role("tab", name="Performance").click()
        page.wait_for_timeout(1000)

        # Check content
        expect(page.get_by_text("Performance Analytics")).to_be_visible(timeout=10000)
        expect(page.get_by_text("Equity Curve")).to_be_visible(timeout=10000)
        expect(page.get_by_text("Profit Distribution")).to_be_visible(timeout=10000)

        # Screenshot AFTER
        page.screenshot(path=str(screenshot_dir / "06_performance_tab_after.png"))

    def test_configuration_tab(
        self,
        page: Page,
        streamlit_server: str,
        screenshot_dir: Path,
    ) -> None:
        """Test Configuration tab."""
        page.goto(streamlit_server)
        page.wait_for_load_state("networkidle")

        # Screenshot BEFORE
        page.screenshot(path=str(screenshot_dir / "07_config_tab_before.png"))

        # Click on Configuration tab
        page.get_by_role("tab", name="Configuration").click()
        page.wait_for_timeout(1000)

        # Check content
        expect(page.get_by_text("Bot Configuration")).to_be_visible(timeout=10000)
        expect(page.get_by_text("Exchange Connections")).to_be_visible(timeout=10000)
        expect(page.get_by_text("Strategy Settings")).to_be_visible(timeout=10000)

        # Screenshot AFTER
        page.screenshot(path=str(screenshot_dir / "07_config_tab_after.png"))

    def test_refresh_button(
        self,
        page: Page,
        streamlit_server: str,
        screenshot_dir: Path,
    ) -> None:
        """Test refresh button in sidebar."""
        page.goto(streamlit_server)
        page.wait_for_load_state("networkidle")

        # Screenshot BEFORE
        page.screenshot(path=str(screenshot_dir / "08_refresh_before.png"))

        # Find and click refresh button
        refresh_btn = page.get_by_role("button", name="Refresh Data")
        expect(refresh_btn).to_be_visible(timeout=10000)

        # Click button
        refresh_btn.click()
        page.wait_for_timeout(2000)

        # Screenshot AFTER
        page.screenshot(path=str(screenshot_dir / "08_refresh_after.png"))

    def test_export_csv_button(
        self,
        page: Page,
        streamlit_server: str,
        screenshot_dir: Path,
    ) -> None:
        """Test export to CSV button."""
        page.goto(streamlit_server)
        page.wait_for_load_state("networkidle")

        # Go to Trade History tab
        page.get_by_role("tab", name="Trade History").click()
        page.wait_for_timeout(1000)

        # Screenshot BEFORE
        page.screenshot(path=str(screenshot_dir / "09_export_before.png"))

        # Find export button
        export_btn = page.get_by_role("button", name="Export to CSV")
        expect(export_btn).to_be_visible(timeout=10000)

        # Screenshot AFTER (button visible)
        page.screenshot(path=str(screenshot_dir / "09_export_after.png"))

    def test_test_connections_button(
        self,
        page: Page,
        streamlit_server: str,
        screenshot_dir: Path,
    ) -> None:
        """Test connections button in Configuration tab."""
        page.goto(streamlit_server)
        page.wait_for_load_state("networkidle")

        # Go to Configuration tab
        page.get_by_role("tab", name="Configuration").click()
        page.wait_for_timeout(1000)

        # Screenshot BEFORE
        page.screenshot(path=str(screenshot_dir / "10_test_conn_before.png"))

        # Find and click test connections button
        test_btn = page.get_by_role("button", name="Test Connections")
        expect(test_btn).to_be_visible(timeout=10000)
        test_btn.click()

        # Wait for spinner and success message
        page.wait_for_timeout(2000)

        # Screenshot AFTER
        page.screenshot(path=str(screenshot_dir / "10_test_conn_after.png"))

    def test_save_config_button(
        self,
        page: Page,
        streamlit_server: str,
        screenshot_dir: Path,
    ) -> None:
        """Test save configuration button."""
        page.goto(streamlit_server)
        page.wait_for_load_state("networkidle")

        # Go to Configuration tab
        page.get_by_role("tab", name="Configuration").click()
        page.wait_for_timeout(1000)

        # Screenshot BEFORE
        page.screenshot(path=str(screenshot_dir / "11_save_config_before.png"))

        # Find and click save button
        save_btn = page.get_by_role("button", name="Save Configuration")
        expect(save_btn).to_be_visible(timeout=10000)
        save_btn.click()

        # Wait for success message
        page.wait_for_timeout(1000)

        # Screenshot AFTER
        page.screenshot(path=str(screenshot_dir / "11_save_config_after.png"))

    def test_checkbox_interactions(
        self,
        page: Page,
        streamlit_server: str,
        screenshot_dir: Path,
    ) -> None:
        """Test checkbox interactions in sidebar."""
        page.goto(streamlit_server)
        page.wait_for_load_state("networkidle")

        # Screenshot BEFORE
        page.screenshot(path=str(screenshot_dir / "12_checkboxes_before.png"))

        # Find checkboxes using label text
        crypto_checkbox = page.locator('label:has-text("Crypto")').first
        expect(crypto_checkbox).to_be_visible(timeout=10000)

        # Screenshot AFTER
        page.screenshot(path=str(screenshot_dir / "12_checkboxes_after.png"))

    def test_slider_interaction(
        self,
        page: Page,
        streamlit_server: str,
        screenshot_dir: Path,
    ) -> None:
        """Test slider interaction for min profit."""
        page.goto(streamlit_server)
        page.wait_for_load_state("networkidle")

        # Screenshot BEFORE
        page.screenshot(path=str(screenshot_dir / "13_slider_before.png"))

        # Find min profit slider label
        expect(page.get_by_text("Min Profit %")).to_be_visible(timeout=10000)

        # Screenshot AFTER
        page.screenshot(path=str(screenshot_dir / "13_slider_after.png"))

    def test_all_tabs_navigation(
        self,
        page: Page,
        streamlit_server: str,
        screenshot_dir: Path,
    ) -> None:
        """Test navigating through all tabs."""
        page.goto(streamlit_server)
        page.wait_for_load_state("networkidle")

        tabs = ["Live Opportunities", "Trade History", "Performance", "Configuration"]

        for i, tab_name in enumerate(tabs):
            # Screenshot BEFORE
            page.screenshot(path=str(screenshot_dir / f"14_nav_tab{i}_before.png"))

            # Click tab
            page.get_by_role("tab", name=tab_name).click()
            page.wait_for_timeout(500)

            # Screenshot AFTER
            page.screenshot(path=str(screenshot_dir / f"14_nav_tab{i}_after.png"))
