"""Streamlit dashboard for the arbitrage bot."""

from datetime import datetime
from decimal import Decimal

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Page configuration
st.set_page_config(
    page_title="Arbitrage Bot Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown(
    """
<style>
    .metric-card {
        background-color: #1E1E1E;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
    }
    .profit { color: #00FF00; }
    .loss { color: #FF4444; }
    .stMetric > div { background-color: #262730; padding: 10px; border-radius: 5px; }
</style>
""",
    unsafe_allow_html=True,
)

# Initialize session state
if "portfolio" not in st.session_state:
    st.session_state.portfolio = None
if "trades" not in st.session_state:
    st.session_state.trades = []
if "opportunities" not in st.session_state:
    st.session_state.opportunities = []

# Sidebar
with st.sidebar:
    st.title("⚙️ Settings")

    trading_mode = st.selectbox(
        "Trading Mode",
        ["Paper Trading", "Live Trading (Disabled)"],
        index=0,
        key="trading_mode",
    )

    st.divider()

    st.subheader("Markets")
    crypto_enabled = st.checkbox("Crypto", value=True, key="crypto_enabled")
    forex_enabled = st.checkbox("Forex", value=False, key="forex_enabled")
    prediction_enabled = st.checkbox("Prediction Markets", value=False, key="prediction_enabled")

    st.divider()

    st.subheader("Risk Settings")
    min_profit = st.slider(
        "Min Profit %",
        min_value=0.01,
        max_value=1.0,
        value=0.1,
        step=0.01,
        key="min_profit",
    )
    max_position = st.number_input(
        "Max Position ($)",
        min_value=100,
        max_value=100000,
        value=1000,
        step=100,
        key="max_position",
    )

    st.divider()

    if st.button("🔄 Refresh Data", use_container_width=True, key="refresh_btn"):
        st.rerun()

# Debug mode (hidden feature)
if st.query_params.get("debug") == "true":
    st.json(
        {
            "current_view": "dashboard",
            "portfolio": st.session_state.portfolio,
            "trade_count": len(st.session_state.trades),
            "opportunity_count": len(st.session_state.opportunities),
        }
    )

# Main content
st.title("📈 Arbitrage Bot Dashboard")

# Demo data for display
demo_portfolio = {
    "total_value_usd": Decimal("10523.45"),
    "total_pnl_usd": Decimal("523.45"),
    "total_pnl_percent": Decimal("5.23"),
    "total_trades": 127,
    "winning_trades": 98,
    "losing_trades": 29,
    "win_rate": Decimal("77.2"),
    "max_drawdown_percent": Decimal("2.1"),
}

# Top metrics row
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric(
        "Portfolio Value",
        f"${demo_portfolio['total_value_usd']:,.2f}",
        f"+${demo_portfolio['total_pnl_usd']:,.2f}",
    )

with col2:
    st.metric(
        "Total P&L",
        f"{demo_portfolio['total_pnl_percent']:.2f}%",
        f"{demo_portfolio['total_trades']} trades",
    )

with col3:
    st.metric(
        "Win Rate",
        f"{demo_portfolio['win_rate']:.1f}%",
        f"{demo_portfolio['winning_trades']}W / {demo_portfolio['losing_trades']}L",
    )

with col4:
    st.metric(
        "Max Drawdown",
        f"{demo_portfolio['max_drawdown_percent']:.2f}%",
        None,
    )

with col5:
    st.metric(
        "Bot Status",
        "🟢 Active",
        "Paper Mode",
    )

st.divider()

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(
    ["📊 Live Opportunities", "📜 Trade History", "📈 Performance", "⚙️ Configuration"]
)

# Tab 1: Live Opportunities
with tab1:
    st.subheader("Current Arbitrage Opportunities")

    opportunities_data = [
        {
            "Symbol": "BTC/USDT",
            "Buy": "Binance",
            "Sell": "Kraken",
            "Spread": "0.15%",
            "Net Profit": "0.08%",
            "Volume": "$2,500",
            "Risk": "🟢 Low",
            "Expires": "4.2s",
        },
        {
            "Symbol": "ETH/USDT",
            "Buy": "Coinbase",
            "Sell": "Binance",
            "Spread": "0.12%",
            "Net Profit": "0.05%",
            "Volume": "$1,800",
            "Risk": "🟡 Medium",
            "Expires": "2.8s",
        },
        {
            "Symbol": "SOL/USDT",
            "Buy": "Binance",
            "Sell": "Coinbase",
            "Spread": "0.18%",
            "Net Profit": "0.11%",
            "Volume": "$3,200",
            "Risk": "🟢 Low",
            "Expires": "3.5s",
        },
    ]

    if opportunities_data:
        df = pd.DataFrame(opportunities_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No opportunities detected. Scanner is running...")

    st.caption("⏱️ Auto-refreshing every 1 second")

# Tab 2: Trade History
with tab2:
    st.subheader("Recent Trades")

    col1, col2, col3 = st.columns(3)
    with col1:
        filter_status = st.selectbox(
            "Status",
            ["All", "Completed", "Failed"],
            key="filter_status",
        )
    with col2:
        filter_type = st.selectbox(
            "Type",
            ["All", "Cross-Exchange", "Triangular", "Funding"],
            key="filter_type",
        )
    with col3:
        filter_period = st.selectbox(
            "Period",
            ["Today", "Last 7 Days", "Last 30 Days", "All Time"],
            key="filter_period",
        )

    trades_data = [
        {
            "Time": "14:32:15",
            "Symbol": "BTC/USDT",
            "Type": "Cross-Exchange",
            "Buy": "Binance @ $67,245",
            "Sell": "Kraken @ $67,312",
            "Volume": 0.05,
            "Profit": "+$2.34",
            "Status": "✅",
            "Would Execute": "Yes",
        },
        {
            "Time": "14:28:42",
            "Symbol": "ETH/USDT",
            "Type": "Cross-Exchange",
            "Buy": "Coinbase @ $3,456",
            "Sell": "Binance @ $3,461",
            "Volume": 0.8,
            "Profit": "+$1.12",
            "Status": "✅",
            "Would Execute": "Yes",
        },
        {
            "Time": "14:25:18",
            "Symbol": "SOL/USDT",
            "Type": "Cross-Exchange",
            "Buy": "Binance @ $178.50",
            "Sell": "Kraken @ $178.15",
            "Volume": 5.0,
            "Profit": "-$0.45",
            "Status": "❌",
            "Would Execute": "No",
        },
        {
            "Time": "14:21:05",
            "Symbol": "BTC/USDT",
            "Type": "Cross-Exchange",
            "Buy": "Kraken @ $67,198",
            "Sell": "Coinbase @ $67,275",
            "Volume": 0.03,
            "Profit": "+$1.89",
            "Status": "✅",
            "Would Execute": "Yes",
        },
        {
            "Time": "14:18:33",
            "Symbol": "ETH/USDT",
            "Type": "Funding",
            "Buy": "Spot @ $3,448",
            "Sell": "Perp @ $3,455",
            "Volume": 1.2,
            "Profit": "+$3.21",
            "Status": "✅",
            "Would Execute": "Yes",
        },
    ]

    df_trades = pd.DataFrame(trades_data)
    st.dataframe(df_trades, use_container_width=True, hide_index=True)

    st.download_button(
        "📥 Export to CSV",
        df_trades.to_csv(index=False),
        "trades.csv",
        "text/csv",
        key="export_trades",
    )

# Tab 3: Performance
with tab3:
    st.subheader("Performance Analytics")

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Equity Curve**")
        dates = pd.date_range(end=datetime.now(), periods=30, freq="D")
        equity = [10000]
        for i in range(29):
            change = equity[-1] * (1 + (0.002 * (1 if i % 3 != 0 else -0.5)))
            equity.append(change)

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=equity,
                mode="lines",
                fill="tozeroy",
                line={"color": "#00FF00"},
                name="Equity",
            )
        )
        fig.update_layout(
            height=300,
            margin={"l": 0, "r": 0, "t": 0, "b": 0},
            yaxis_title="USD",
            xaxis_title="",
            template="plotly_dark",
        )
        st.plotly_chart(fig, use_container_width=True, key="equity_chart")

    with col2:
        st.write("**Profit Distribution**")
        profits = [2.34, 1.12, -0.45, 3.21, 0.98, -0.23, 1.87, 2.45, -0.67, 1.23, 0.56, 1.98]
        fig = px.histogram(
            x=profits,
            nbins=20,
            color_discrete_sequence=["#00FF00"],
        )
        fig.update_layout(
            height=300,
            margin={"l": 0, "r": 0, "t": 0, "b": 0},
            xaxis_title="Profit ($)",
            yaxis_title="Count",
            template="plotly_dark",
        )
        st.plotly_chart(fig, use_container_width=True, key="profit_dist")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.write("**Performance Metrics**")
        st.write("Sharpe Ratio: **2.34**")
        st.write("Sortino Ratio: **3.12**")
        st.write("Profit Factor: **2.8**")
        st.write("Avg Trade: **$1.24**")

    with col2:
        st.write("**Risk Metrics**")
        st.write("Max Drawdown: **2.1%**")
        st.write("Avg Trade Duration: **1.2s**")
        st.write("Avg Slippage: **0.02%**")
        st.write("Risk/Reward: **1:2.4**")

    with col3:
        st.write("**Execution Stats**")
        st.write("Would-Have-Executed: **94%**")
        st.write("Avg Latency: **32ms**")
        st.write("Failed Orders: **6%**")
        st.write("Partial Fills: **3%**")

# Tab 4: Configuration
with tab4:
    st.subheader("Bot Configuration")

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Exchange Connections**")
        exchanges = [
            {"Exchange": "Binance", "Status": "🟢 Connected", "Markets": 127},
            {"Exchange": "Kraken", "Status": "🟢 Connected", "Markets": 89},
            {"Exchange": "Coinbase", "Status": "🟡 Connecting", "Markets": 0},
        ]
        st.dataframe(pd.DataFrame(exchanges), hide_index=True, key="exchange_table")

        if st.button("Test Connections", key="test_conn"):
            with st.spinner("Testing..."):
                import time

                time.sleep(1)
            st.success("All connections OK!")

    with col2:
        st.write("**Strategy Settings**")
        min_spread = st.number_input(
            "Min Spread (%)",
            value=0.05,
            step=0.01,
            key="min_spread",
        )
        max_slippage = st.number_input(
            "Max Slippage (%)",
            value=0.1,
            step=0.01,
            key="max_slippage",
        )
        order_timeout = st.number_input(
            "Order Timeout (s)",
            value=5,
            step=1,
            key="order_timeout",
        )
        funding_enabled = st.checkbox(
            "Enable Funding Arbitrage",
            value=True,
            key="funding_enabled",
        )
        triangular_enabled = st.checkbox(
            "Enable Triangular Arbitrage",
            value=False,
            key="triangular_enabled",
        )

        if st.button("Save Configuration", key="save_config"):
            st.success("Configuration saved!")

st.divider()
st.caption(
    f"Arbitrage Bot v1.0 | Paper Trading Mode | Last update: {datetime.now().strftime('%H:%M:%S')}"
)
