import streamlit as st
import MetaTrader5 as mt5
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

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

# Fetch all active trades
posizioni = mt5.positions_get()

if posizioni is None or len(posizioni) == 0:
    st.info("No active trades right now. Engine is scanning...")
else:
    # Transform raw MT5 data into a clean visual table
    df = pd.DataFrame(list(posizioni), columns=posizioni[0]._asdict().keys())
    
    # --- CHARTS SECTION ---
    st.subheader("📈 Portfolio Analytics")
    
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        # CHART 1: Risk Allocation (Pie Chart based on Volume)
        fig_pie = px.pie(
            df, 
            values='volume', 
            names='symbol', 
            title="Portfolio Exposure (by Volume)",
            hole=0.4, # Makes it a donut chart
            color_discrete_sequence=px.colors.sequential.Tealgrn
        )
        fig_pie.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color="white")
        st.plotly_chart(fig_pie, use_container_width=True)

    with chart_col2:
        # CHART 2: Live Candlestick Chart of the Top Asset
        top_symbol = df.iloc[0]['symbol'] # Gets the first open symbol
        
        # Fetch last 50 D1 candles for this symbol
        rates = mt5.copy_rates_from_pos(top_symbol, mt5.TIMEFRAME_D1, 0, 50)
        if rates is not None and len(rates) > 0:
            df_rates = pd.DataFrame(rates)
            df_rates['time'] = pd.to_datetime(df_rates['time'], unit='s')
            
            fig_candle = go.Figure(data=[go.Candlestick(
                x=df_rates['time'],
                open=df_rates['open'],
                high=df_rates['high'],
                low=df_rates['low'],
                close=df_rates['close'],
                name=top_symbol
            )])
            fig_candle.update_layout(
                title=f"Live Market: {top_symbol} (Daily)",
                xaxis_rangeslider_visible=False,
                plot_bgcolor='rgba(0,0,0,0)', 
                paper_bgcolor='rgba(0,0,0,0)',
                font_color="white"
            )
            st.plotly_chart(fig_candle, use_container_width=True)
        else:
            st.warning(f"Could not load chart data for {top_symbol}")

    st.divider()
    # --- END CHARTS SECTION ---

    st.subheader("📋 Open Positions Details")
    
    # Select only relevant columns for the dashboard
    df_table = df[['ticket', 'symbol', 'type', 'volume', 'price_open', 'price_current', 'profit', 'comment']].copy()
    
    # Map order types: 0 becomes BUY, 1 becomes SELL
    df_table['type'] = df_table['type'].map({0: 'BUY 🟢', 1: 'SELL 🔴'})
    
    # Format profit as currency
    df_table['profit'] = df_table['profit'].apply(lambda x: f"${x:.2f}")
    
    # Display full-width dataframe
    st.dataframe(df_table, use_container_width=True, hide_index=True)

# Button to refresh dashboard data manually
st.write("") # Spacer
if st.button("🔄 Refresh Data", type="primary"):
    st.rerun()