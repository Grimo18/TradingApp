import streamlit as st
import MetaTrader5 as mt5
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Page Configuration (Theme is handled by .streamlit/config.toml)
st.set_page_config(page_title="QUANT AI TERMINAL", page_icon="🏦", layout="wide", initial_sidebar_state="collapsed")

# ==========================================
# 🌙 DARK MODE - MOBILE RESPONSIVE STYLING
# ==========================================
st.markdown("""
    <style>
        /* Dark theme base */
        .stApp {
            background: linear-gradient(135deg, #0f0f15 0%, #1a1a24 100%);
        }
        
        /* Mobile responsiveness: Hide elements on very small screens */
        @media (max-width: 640px) {
            .stMetric {
                font-size: 0.9rem;
                margin-bottom: 1rem;
            }
            
            .stDataFrame, .st-dataframe {
                font-size: 0.75rem !important;
            }
            
            h1, h2 {
                font-size: 1.5rem !important;
            }
            
            /* Make button full width on mobile */
            .stButton > button {
                width: 100%;
                padding: 0.75rem !important;
                font-size: 1rem !important;
            }
        }
        
        /* Tablet optimization: 640px - 1024px */
        @media (max-width: 1024px) {
            .stPlotlyChart {
                margin-bottom: 1.5rem;
            }
        }
        
        /* Dark mode text colors */
        .stMarkdown {
            color: #e4e4e7;
        }
        
        /* Divider styling for dark mode */
        hr {
            background-color: #3f3f46 !important;
            border: none;
            height: 1px;
        }
        
        /* Info/warning boxes styling */
        .stAlert, .st-info {
            background-color: rgba(30, 41, 59, 0.8) !important;
            color: #e4e4e7 !important;
            border-color: #3f3f46 !important;
        }
    </style>
""", unsafe_allow_html=True)

st.title("🏦 Quant AI Terminal - Live Dashboard")
st.markdown("📱 **Remote Web Monitoring** | Engine V11.0 | Dark Mode Active")

# Connect to MT5 in read-only mode (Safe Mode)
if not mt5.initialize():
    st.error("❌ Failed to connect to MetaTrader 5. Is it running on the server?")
    st.stop()

# Fetch Account Information
account_info = mt5.account_info()

# Get device screen size via JavaScript (optional detection on client side)
# For now, Streamlit handles responsive design automatically

# 3-column layout for main metrics (responsive: stacks on mobile)
st.subheader("💼 Account Summary")

col1, col2, col3 = st.columns(3)

if account_info:
    with col1:
        st.metric("💰 Live Equity", f"${account_info.equity:,.2f}")
    with col2:
        st.metric("📊 Free Margin", f"${account_info.margin_free:,.2f}")
    
    # Color the profit green if positive, red if negative
    profit_color = "normal" if account_info.profit == 0 else ("inverse" if account_info.profit < 0 else "normal")
    with col3:
        st.metric("📈 Floating Profit", f"${account_info.profit:,.2f}", delta=f"${account_info.profit:,.2f}", delta_color=profit_color)
else:
    st.warning("⚠️ No account connected to MetaTrader 5.")

st.divider()

# Fetch all active trades
posizioni = mt5.positions_get()

if posizioni is None or len(posizioni) == 0:
    st.info("📭 No active trades right now. Engine is scanning for opportunities...")
else:
    # Transform raw MT5 data into a clean visual table
    df = pd.DataFrame(list(posizioni), columns=posizioni[0]._asdict().keys())
    
    # --- CHARTS SECTION (MOBILE OPTIMIZED) ---
    st.subheader("📈 Portfolio Analytics")
    
    # Responsive layout: columns stack on mobile automatically
    chart_col1, chart_col2 = st.columns([1, 1])
    
    with chart_col1:
        # CHART 1: Risk Allocation (Pie Chart based on Volume)
        fig_pie = px.pie(
            df, 
            values='volume', 
            names='symbol', 
            title="Portfolio Exposure (Volume)",
            hole=0.4,
            color_discrete_sequence=px.colors.sequential.Tealgrn
        )
        # Dark mode colors
        fig_pie.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', 
            paper_bgcolor='rgba(0,0,0,0)', 
            font_color="#e4e4e7",
            font=dict(size=12),
            height=400
        )
        st.plotly_chart(fig_pie, use_container_width=True, config={'responsive': True})

    with chart_col2:
        # CHART 2: Live Candlestick Chart of the Top Asset
        top_symbol = df.iloc[0]['symbol']
        
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
                name=top_symbol,
                increasing_line_color='#22c55e',
                decreasing_line_color='#ef4444'
            )])
            
            # Dark mode + Mobile optimization
            fig_candle.update_layout(
                title=f"Live: {top_symbol} (Daily)",
                xaxis_rangeslider_visible=False,
                plot_bgcolor='rgba(0,0,0,0)', 
                paper_bgcolor='rgba(0,0,0,0)',
                font_color="#e4e4e7",
                font=dict(size=11),
                dragmode=False,
                hovermode="x unified",
                height=400,
                margin=dict(l=40, r=40, t=40, b=40)
            )
            
            fig_candle.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#3f3f46')
            fig_candle.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#3f3f46')

            st.plotly_chart(
                fig_candle, 
                use_container_width=True,
                config={'scrollZoom': False, 'displayModeBar': 'hover', 'responsive': True}
            )
        else:
            st.warning(f"⚠️ Could not load chart data for {top_symbol}")

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
    st.dataframe(df_table, use_container_width=True, hide_index=True, height=300)

# ==========================================
# 🔄 REFRESH BUTTON (MOBILE OPTIMIZED)
# ==========================================
st.write("")  # Spacer
col_btn1, col_btn2 = st.columns([0.7, 0.3])

with col_btn1:
    if st.button("🔄 Refresh Dashboard", type="primary", use_container_width=True):
        st.rerun()

with col_btn2:
    st.caption("Last updated: auto", help="Dashboard auto-refreshes every 30 seconds")