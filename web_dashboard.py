import streamlit as st
import MetaTrader5 as mt5
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime
import json
import os

# Page Configuration
st.set_page_config(page_title="QUANT AI TERMINAL", page_icon="🏦", layout="wide")

# 🌍 GLOBAL SENSOR (Calculated at the top)
ora_utc = datetime.datetime.utcnow().hour
if 14 <= ora_utc < 21:
    mercato_attivo = "🇺🇸 Wall Street (US)"
    bandiera = "🇺🇸"
elif 8 <= ora_utc < 14:
    mercato_attivo = "🇪🇺 Europe (UK/DE/FR)"
    bandiera = "🇪🇺"
else:
    mercato_attivo = "🌏 Asia (HK/JP)"
    bandiera = "🌏"

# --- SIDEBAR & SETTINGS ---
with st.sidebar:
    st.header("⚙️ Terminal Settings")
    
    orario_str = datetime.datetime.utcnow().strftime("%H:%M UTC")
    st.metric("🌍 Active Global Market", mercato_attivo, f"Time: {orario_str}")
    st.divider()
    
    st.info("💡 **Theme Settings:**\nTo switch between Dark and Light mode, click the 3 dots in the top right corner ➔ **Settings** ➔ **Theme**.")
    st.divider()
    st.success("🟢 Multi-Speed Data Stream Active\n• Metrics: 2s\n• Charts: 60s")

# --- MAIN HEADER ---
st.title(f"🏦 Quant AI Terminal {bandiera}")
st.markdown(f"**Engine V11.0 | Active Global Market: {mercato_attivo}**")

# 🎯 RADAR LOCK-ON (Reads the active config)
config_path = os.path.join(os.path.dirname(__file__), "config.json")
try:
    with open(config_path, "r") as f:
        config_data = json.load(f)
        tickers_target = config_data.get("ticker", "N/A")
        # Aggiunge la bandiera visivamente se c'è l'Autopilot
        display_tickers = tickers_target.replace("AUTOPILOT", f"AUTOPILOT {bandiera}")
except Exception:
    display_tickers = "Scanning configuration..."

st.info(f"📡 **Radar Lock-On:** {display_tickers}")
st.divider()

# Connect to MT5 in read-only mode
if not mt5.initialize():
    st.error("❌ Failed to connect to MetaTrader 5. Is it running on the server?")
    st.stop()

# ==========================================
# ⚡ LIVE FRAGMENT 1: TOP METRICS (Every 2s)
# ==========================================
@st.fragment(run_every=2)
def render_live_metrics():
    account_info = mt5.account_info()
    col1, col2, col3 = st.columns(3)
    
    if account_info:
        col1.metric("Live Equity", f"${account_info.equity:,.2f}")
        col2.metric("Free Margin", f"${account_info.margin_free:,.2f}")
        
        profit_color = "normal" if account_info.profit == 0 else ("inverse" if account_info.profit < 0 else "normal")
        col3.metric("Floating Profit", f"${account_info.profit:,.2f}", delta=f"${account_info.profit:,.2f}", delta_color=profit_color)
    else:
        st.warning("⚠️ No account connected to MT5.")

# Render the metrics block
render_live_metrics()
st.divider()

@st.fragment(run_every=5)
def render_daily_performance():
    try:
        if os.path.exists("storico_operazioni_chiuse.csv"):
            df_storico = pd.read_csv("storico_operazioni_chiuse.csv")
            # Filtra solo le operazioni di oggi
            oggi = datetime.datetime.now().strftime("%Y-%m-%d")
            df_oggi = df_storico[df_storico['Close Date'] == oggi]
            
            profitto_oggi = df_oggi['Net P/L ($)'].astype(float).sum()
            win_rate = (len(df_oggi[df_oggi['Net P/L ($)'].astype(float) > 0]) / len(df_oggi) * 100) if len(df_oggi) > 0 else 0
            
            st.write("### 🏆 Daily Realized Performance")
            col1, col2, col3 = st.columns(3)
            col1.metric("Today's Closed P&L", f"${profitto_oggi:,.2f}")
            col2.metric("Trades Closed Today", len(df_oggi))
            col3.metric("Win Rate", f"{win_rate:.1f}%")
            st.divider()
    except Exception as e:
        pass

render_daily_performance()
# ==========================================
# 📊 LIVE FRAGMENT 2: HEAVY CHARTS (Every 60s)
# ==========================================
@st.fragment(run_every=60)
def render_live_charts():
    posizioni = mt5.positions_get()

    if posizioni is None or len(posizioni) == 0:
        st.info("No active trades right now. Engine is scanning...")
    else:
        df = pd.DataFrame(list(posizioni), columns=posizioni[0]._asdict().keys())
        
        st.subheader("📈 Portfolio Analytics")
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            # CHART 1: Risk Allocation
            fig_pie = px.pie(
                df, values='volume', names='symbol', title="Portfolio Exposure (by Volume)",
                hole=0.4, color_discrete_sequence=px.colors.sequential.Tealgrn
            )
            st.plotly_chart(fig_pie, use_container_width=True, theme="streamlit")

        with chart_col2:
            # Drop-down menu to choose which graph to view
            lista_simboli = df['symbol'].unique().tolist()
            simbolo_scelto = st.selectbox("Seleziona Asset da visualizzare", lista_simboli, key="grafico_selettore")
            
            rates = mt5.copy_rates_from_pos(simbolo_scelto, mt5.TIMEFRAME_H1, 0, 100) # Better H1 for live
            
            if rates is not None and len(rates) > 0:
                df_rates = pd.DataFrame(rates)
                df_rates['time'] = pd.to_datetime(df_rates['time'], unit='s')
                
                fig_candle = go.Figure(data=[go.Candlestick(
                    x=df_rates['time'], open=df_rates['open'], high=df_rates['high'],
                    low=df_rates['low'], close=df_rates['close'], name=simbolo_scelto,
                    increasing_line_color='#22c55e', decreasing_line_color='#ef4444'
                )])
                
                fig_candle.update_layout(
                    title=f"Market Trend: {simbolo_scelto} (H1)", xaxis_rangeslider_visible=False, 
                    dragmode=False, hovermode="x unified", margin=dict(l=0, r=0, t=40, b=0)
                )
                
                st.plotly_chart(fig_candle, use_container_width=True, theme="streamlit")

# Render the charts block
render_live_charts()
st.divider()

# ==========================================
# ⚡ LIVE FRAGMENT 3: POSITIONS TABLE (Every 2s)
# ==========================================
@st.fragment(run_every=2)
def render_live_table():
    live_pos = mt5.positions_get()
    if live_pos:
        st.subheader("📋 Open Positions Details")
        df_live = pd.DataFrame(list(live_pos), columns=live_pos[0]._asdict().keys())
        df_live = df_live[['ticket', 'symbol', 'type', 'volume', 'price_open', 'price_current', 'profit', 'comment']].copy()
        
        # Mappatura e formattazione
        df_live['type'] = df_live['type'].map({0: 'BUY 🟢', 1: 'SELL 🔴'})
        df_live.rename(columns={'comment': '🤖 AI Insights'}, inplace=True)
        
        # Funzione per colorare la colonna profitto
        def color_profit(val):
            color = '#22c55e' if val > 0 else '#ef4444' if val < 0 else 'white'
            return f'color: {color}; font-weight: bold'
            
        # Applichiamo lo stile prima di renderizzare
        styled_df = df_live.style.map(color_profit, subset=['profit']).format({'profit': "${:.2f}"})
        
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
        
# Render the table block
render_live_table()

# Manual refresh for the heavy charts if needed
st.write("")
if st.button("🔄 Force Charts Update", type="primary"):
    st.rerun()