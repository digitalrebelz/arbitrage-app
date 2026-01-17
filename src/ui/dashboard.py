"""Streamlit dashboard for the arbitrage bot - Real-time view."""

import json
import time
from datetime import datetime
from pathlib import Path

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

# State file from simulation
STATE_FILE = Path("data/simulation_state.json")


def load_state() -> dict:
    """Load current state from simulation."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {
        "is_running": False,
        "portfolio": {
            "total_value_usd": 10000,
            "initial_value_usd": 10000,
            "total_pnl_usd": 0,
            "total_pnl_percent": 0,
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": 0,
            "max_drawdown_percent": 0,
        },
        "recent_trades": [],
        "recent_opportunities": [],
        "statistics": {},
    }


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
    .profit { color: #00FF00 !important; }
    .loss { color: #FF4444 !important; }
    .stMetric > div { background-color: #262730; padding: 10px; border-radius: 5px; }
    .live-indicator {
        display: inline-block;
        width: 10px;
        height: 10px;
        background-color: #00FF00;
        border-radius: 50%;
        animation: pulse 1s infinite;
        margin-right: 8px;
    }
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.5; }
        100% { opacity: 1; }
    }
</style>
""",
    unsafe_allow_html=True,
)

# Load current state
state = load_state()
portfolio = state.get("portfolio", {})
trades = state.get("recent_trades", [])
opportunities = state.get("recent_opportunities", [])
is_running = state.get("is_running", False)

# Sidebar
with st.sidebar:
    st.title("⚙️ Control Panel")

    # Auto-refresh toggle
    auto_refresh = st.toggle("Auto Refresh", value=True, key="auto_refresh")
    refresh_rate = st.slider("Refresh Rate (s)", 1, 10, 2, key="refresh_rate")

    st.divider()

    st.subheader("Bot Status")
    if is_running:
        st.markdown('<span class="live-indicator"></span> **RUNNING**', unsafe_allow_html=True)
        st.success("Simulation active")
    else:
        st.warning("Bot stopped")

    st.divider()

    st.subheader("Quick Stats")
    st.metric("Total Trades", portfolio.get("total_trades", 0))
    st.metric("Win Rate", f"{portfolio.get('win_rate', 0):.1f}%")

    st.divider()

    if st.button("🔄 Manual Refresh", use_container_width=True, key="refresh_btn"):
        st.rerun()

    updated_at = state.get("updated_at", "Never")
    if updated_at != "Never":
        try:
            dt = datetime.fromisoformat(updated_at)
            updated_at = dt.strftime("%H:%M:%S")
        except Exception:
            pass
    st.caption(f"Last update: {updated_at}")

# Main content
col_title, col_status = st.columns([4, 1])
with col_title:
    st.title("📈 Arbitrage Bot Dashboard")
with col_status:
    if is_running:
        st.markdown(
            '<div style="text-align:right;padding-top:20px;">'
            '<span class="live-indicator"></span> <b>LIVE</b></div>',
            unsafe_allow_html=True,
        )

# Top metrics row
col1, col2, col3, col4, col5 = st.columns(5)

pnl = portfolio.get("total_pnl_usd", 0)
pnl_pct = portfolio.get("total_pnl_percent", 0)
total_value = portfolio.get("total_value_usd", 10000)

with col1:
    delta_color = "normal" if pnl >= 0 else "inverse"
    st.metric(
        "Portfolio Value",
        f"${total_value:,.2f}",
        f"{pnl:+,.2f}" if pnl != 0 else None,
        delta_color=delta_color,
    )

with col2:
    st.metric(
        "Total P&L",
        f"${pnl:+,.2f}",
        f"{pnl_pct:+.2f}%",
        delta_color="normal" if pnl >= 0 else "inverse",
    )

with col3:
    win_rate = portfolio.get("win_rate", 0)
    wins = portfolio.get("winning_trades", 0)
    losses = portfolio.get("losing_trades", 0)
    st.metric(
        "Win Rate",
        f"{win_rate:.1f}%",
        f"{wins}W / {losses}L",
    )

with col4:
    drawdown = portfolio.get("max_drawdown_percent", 0)
    st.metric(
        "Max Drawdown",
        f"{drawdown:.2f}%",
        None,
    )

with col5:
    st.metric(
        "Total Trades",
        portfolio.get("total_trades", 0),
        "Paper Mode",
    )

st.divider()

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(
    ["📊 Live Opportunities", "📜 Trade History", "📈 Performance", "⚙️ Configuration"]
)

# Tab 1: Live Opportunities
with tab1:
    st.subheader("Recent Arbitrage Opportunities")

    if opportunities:
        # Show last 20 opportunities
        recent_opps = opportunities[-20:][::-1]  # Reverse to show newest first

        opp_display = []
        for opp in recent_opps:
            opp_display.append({
                "Time": datetime.fromisoformat(opp["detected_at"]).strftime("%H:%M:%S") if opp.get("detected_at") else "-",
                "Symbol": opp.get("symbol", "-"),
                "Buy": opp.get("buy_exchange", "-").title(),
                "Sell": opp.get("sell_exchange", "-").title(),
                "Buy Price": f"${opp.get('buy_price', 0):,.2f}",
                "Sell Price": f"${opp.get('sell_price', 0):,.2f}",
                "Profit %": f"{opp.get('net_profit_percent', 0):.4f}%",
                "Est. Profit": f"${opp.get('estimated_profit_usd', 0):.2f}",
                "Status": "✅ Executed" if opp.get("status") == "executed" else "⏳ Detected" if opp.get("status") == "detected" else "❌ Failed",
            })

        df = pd.DataFrame(opp_display)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("🔍 Waiting for arbitrage opportunities... Bot is scanning markets.")

    st.caption(f"📊 Total opportunities found: {len(opportunities)}")

# Tab 2: Trade History
with tab2:
    st.subheader("Executed Trades")

    if trades:
        # Show trades newest first
        recent_trades = trades[::-1]

        trades_display = []
        for t in recent_trades:
            profit = t.get("net_profit", 0)
            trades_display.append({
                "Time": datetime.fromisoformat(t["executed_at"]).strftime("%H:%M:%S") if t.get("executed_at") else "-",
                "Symbol": t.get("symbol", "-"),
                "Buy": f"{t.get('buy_exchange', '-').title()} @ ${t.get('buy_price', 0):,.2f}",
                "Sell": f"{t.get('sell_exchange', '-').title()} @ ${t.get('sell_price', 0):,.2f}",
                "Volume": f"{t.get('volume', 0):.4f}",
                "Gross P/L": f"${t.get('gross_profit', 0):+.2f}",
                "Fees": f"${t.get('fees', 0):.2f}",
                "Net P/L": f"${profit:+.2f}",
                "Status": "✅" if t.get("status") == "completed" else "❌",
                "Exec Time": f"{t.get('execution_ms', 0)}ms",
            })

        df_trades = pd.DataFrame(trades_display)
        st.dataframe(df_trades, use_container_width=True, hide_index=True)

        # Summary stats
        total_gross = sum(t.get("gross_profit", 0) for t in recent_trades)
        total_fees = sum(t.get("fees", 0) for t in recent_trades)
        total_net = sum(t.get("net_profit", 0) for t in recent_trades)

        col1, col2, col3 = st.columns(3)
        col1.metric("Gross Profit", f"${total_gross:+.2f}")
        col2.metric("Total Fees", f"${total_fees:.2f}")
        col3.metric("Net Profit", f"${total_net:+.2f}")

        # Export button
        st.download_button(
            "📥 Export to CSV",
            df_trades.to_csv(index=False),
            "trades.csv",
            "text/csv",
            key="export_trades",
        )
    else:
        st.info("📭 No trades executed yet. Waiting for profitable opportunities...")

# Tab 3: Performance
with tab3:
    st.subheader("Performance Analytics")

    if trades:
        col1, col2 = st.columns(2)

        with col1:
            st.write("**Equity Curve**")

            # Build equity curve from trades
            equity = [10000]
            times = [datetime.fromisoformat(trades[0]["executed_at"]) if trades else datetime.now()]

            for t in trades:
                profit = t.get("net_profit", 0)
                equity.append(equity[-1] + profit)
                if t.get("executed_at"):
                    times.append(datetime.fromisoformat(t["executed_at"]))
                else:
                    times.append(times[-1])

            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=list(range(len(equity))),
                    y=equity,
                    mode="lines",
                    fill="tozeroy",
                    line={"color": "#00FF00" if equity[-1] >= 10000 else "#FF4444"},
                    name="Equity",
                )
            )
            fig.update_layout(
                height=300,
                margin={"l": 0, "r": 0, "t": 0, "b": 0},
                yaxis_title="USD",
                xaxis_title="Trade #",
                template="plotly_dark",
            )
            st.plotly_chart(fig, use_container_width=True, key="equity_chart")

        with col2:
            st.write("**Profit Distribution**")
            profits = [t.get("net_profit", 0) for t in trades]

            if profits:
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

        # Stats
        profits = [t.get("net_profit", 0) for t in trades]
        winning = [p for p in profits if p > 0]
        losing = [p for p in profits if p < 0]

        col1, col2, col3 = st.columns(3)

        with col1:
            st.write("**Performance Metrics**")
            avg_profit = sum(profits) / len(profits) if profits else 0
            avg_win = sum(winning) / len(winning) if winning else 0
            avg_loss = sum(losing) / len(losing) if losing else 0
            st.write(f"Avg Trade: **${avg_profit:.2f}**")
            st.write(f"Avg Win: **${avg_win:.2f}**")
            st.write(f"Avg Loss: **${avg_loss:.2f}**")
            profit_factor = abs(sum(winning) / sum(losing)) if losing and sum(losing) != 0 else float('inf')
            st.write(f"Profit Factor: **{profit_factor:.2f}**")

        with col2:
            st.write("**Risk Metrics**")
            st.write(f"Max Drawdown: **{portfolio.get('max_drawdown_percent', 0):.2f}%**")
            exec_times = [t.get("execution_ms", 0) for t in trades]
            avg_exec = sum(exec_times) / len(exec_times) if exec_times else 0
            st.write(f"Avg Exec Time: **{avg_exec:.0f}ms**")
            st.write(f"Total Trades: **{len(trades)}**")

        with col3:
            st.write("**Success Rate**")
            completed = len([t for t in trades if t.get("status") == "completed"])
            failed = len(trades) - completed
            st.write(f"Completed: **{completed}** ({100*completed/len(trades):.1f}%)")
            st.write(f"Failed: **{failed}**")
            st.write(f"Win Rate: **{portfolio.get('win_rate', 0):.1f}%**")
    else:
        st.info("📊 Performance data will appear after trades are executed.")

# Tab 4: Configuration
with tab4:
    st.subheader("Simulation Configuration")

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Simulated Exchanges**")
        exchanges = [
            {"Exchange": "Binance", "Status": "🟢 Simulated", "Type": "CEX"},
            {"Exchange": "Kraken", "Status": "🟢 Simulated", "Type": "CEX"},
            {"Exchange": "Coinbase", "Status": "🟢 Simulated", "Type": "CEX"},
            {"Exchange": "KuCoin", "Status": "🟢 Simulated", "Type": "CEX"},
            {"Exchange": "Bybit", "Status": "🟢 Simulated", "Type": "CEX"},
        ]
        st.dataframe(pd.DataFrame(exchanges), hide_index=True, key="exchange_table")

    with col2:
        st.write("**Simulation Settings**")
        st.info("""
        **Current Settings:**
        - Opportunity Rate: 40% per scan
        - Profit Range: 0.03% - 0.35%
        - Execution Success: 75%
        - Scan Interval: 1.5s
        - Initial Capital: $10,000
        """)

    st.write("**How it works:**")
    st.markdown("""
    1. The simulator generates realistic arbitrage opportunities between exchanges
    2. Each opportunity has a random profit margin (0.03% - 0.35%)
    3. The paper trader executes trades with simulated slippage and fees
    4. 75% of trades execute successfully (simulating real market conditions)
    5. Portfolio tracks all P&L, win rate, and drawdown in real-time
    """)

st.divider()

# Footer
col1, col2 = st.columns([3, 1])
with col1:
    st.caption(
        f"Arbitrage Bot v1.0 | Simulation Mode | "
        f"Updated: {datetime.now().strftime('%H:%M:%S')}"
    )
with col2:
    if is_running:
        st.caption("🟢 Bot Running")
    else:
        st.caption("⚪ Bot Stopped")

# Auto-refresh
if auto_refresh and is_running:
    time.sleep(refresh_rate)
    st.rerun()
