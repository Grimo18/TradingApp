import streamlit as st
import MetaTrader5 as mt5
import pandas as pd

# Page Configuration (Institutional Dark Mode)
st.set_page_config(page_title="QUANT AI TERMINAL", page_icon="🏦", layout="wide")

st.title("🏦 Quant AI Terminal - Live Dashboard")
st.markdown("Remote Web Monitoring via Tailscale | Engine V11.0")

# Connect to MT5 in read-only mode (Safe Mode)
if not mt5.initialize():
    st.error("❌ Failed to connect to MetaTrader 5. Is it running on the server?")
    st.stop()

# Fetch Account Information
account_info = mt5.account_info()

# 3-column layout for main metrics
col1, col2, col3 = st.columns(3)

if account_info:
    col1.metric("Live Equity", f"${account_info.equity:,.2f}")
    col2.metric("Free Margin", f"${account_info.margin_free:,.2f}")
    
    # Color the profit green if positive, red if negative
    profit_color = "normal" if account_info.profit == 0 else ("inverse" if account_info.profit < 0 else "normal")
    col3.metric("Floating Profit", f"${account_info.profit:,.2f}", delta=f"${account_info.profit:,.2f}", delta_color=profit_color)
else:
    st.warning("⚠️ No account connected to MT5.")

st.divider()
st.subheader("📊 Open Positions")

# Fetch all active trades
posizioni = mt5.positions_get()

if posizioni is None or len(posizioni) == 0:
    st.info("No active trades right now. Engine is scanning...")
else:
    # Transform raw MT5 data into a clean visual table
    df = pd.DataFrame(list(posizioni), columns=posizioni[0]._asdict().keys())
    
    # Select only relevant columns for the dashboard
    df = df[['ticket', 'symbol', 'type', 'volume', 'price_open', 'price_current', 'profit', 'comment']]
    
    # Map order types: 0 becomes BUY, 1 becomes SELL
    df['type'] = df['type'].map({0: 'BUY 🟢', 1: 'SELL 🔴'})
    
    # Format profit as currency
    df['profit'] = df['profit'].apply(lambda x: f"${x:.2f}")
    
    # Display full-width dataframe
    st.dataframe(df, use_container_width=True, hide_index=True)

# Button to refresh dashboard data manually
if st.button("🔄 Refresh Data"):
    st.rerun()