"""
Live MetaTrader 5 Trading Engine (V11.0) with AI-Driven Portfolio Construction.

Core Architecture:
1. PHASE 1 (Initial Scan): Analyze ALL assets via AI sentiment for portfolio construction
2. CONTINUOUS MONITORING: Track open positions with asymmetric risk/reward
3. DYNAMIC RISK MANAGEMENT: Kill-switch on max drawdown, victory cooldowns on profits
4. QUARANTINE SYSTEM: Prevent over-trading losers after consecutive stops

Key Features:
- Long-Term Immunity: Separate cassettista (investor) positions from speculation
- Magic Numbers: MAGIC_SHORT_TERM (1001) vs MAGIC_LONG_TERM (2002) for classification
- Spread Filtering: Reject trades when broker spreads exceed 0.2% thresholds
- Friday Closure: Forex positions auto-closed before weekend gap risk

Position Management:
- Entry: AI sentiment score must exceed ±5 threshold to avoid noise
- Exit: Dynamic target based on position horizon (short-term aggressive, long-term conservative)
- Commission: $6.00 per lot deducted from P&L for realistic backtesting
"""

import MetaTrader5 as mt5
import time
import datetime
import threading
import requests
import csv
import os
import socket
from dotenv import load_dotenv
from app.ai_brain import analizza_sentiment_ollama

load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Global state machine: SPENTO → MONITORAGGIO → TRADING ↔ CHIUSURA_FORZATA
stato_motore = "SPENTO"
parametri_attivi = {}
COMMISSION_PER_LOT = 6.0  # USD commission per lot (bid-ask equivalent)

# Magic numbers: Unique identifiers for long-term vs short-term positions
MAGIC_SHORT_TERM = 1001  # Day-trading, high frequency, aggressive targets
MAGIC_LONG_TERM = 2002   # Cassettista (investor), low frequency, durable positions

# Telegram offset memory to avoid processing the same command twice
ultimo_update_id_telegram = 0


def invia_telegram(chat_ids_str, messaggio):
    """
    Send Telegram notifications to one or more chat IDs.
    
    Implements multi-user support: comma-separated chat IDs are parsed
    and each receives independent notification. Failures are silent to
    prevent trading errors from notification issues.
    
    Args:
        chat_ids_str (str): Single or comma-separated chat IDs (e.g., "123,456,789").
        messaggio (str): Notification text (emoji prefixes help mobile scanning).
    
    Returns:
        None: Side effect only (HTTP POST to Telegram API).
    """
    if not TELEGRAM_BOT_TOKEN or not chat_ids_str: return
    lista_chat_ids = [cid.strip() for cid in chat_ids_str.split(",") if cid.strip()]
    for chat_id in lista_chat_ids:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        try: requests.post(url, json={"chat_id": chat_id, "text": messaggio}, timeout=2)
        except: pass 

def controlla_comandi_telegram(chat_ids_str):
    """
    Listens for incoming Telegram commands and executes them remotely.
    Implements a secure two-way communication channel.
    """
    global ultimo_update_id_telegram, stato_motore
    if not TELEGRAM_BOT_TOKEN or not chat_ids_str: return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates?offset={ultimo_update_id_telegram + 1}&timeout=1"
    try:
        res = requests.get(url, timeout=2).json()
        if res.get("ok") and res.get("result"):
            for update in res["result"]:
                ultimo_update_id_telegram = update["update_id"]
                messaggio = update.get("message", {})
                testo = messaggio.get("text", "").strip().lower()
                chat_id = str(messaggio.get("chat", {}).get("id", ""))
                
                # Security check: Only accept commands from authorized Chat IDs in the UI
                chat_autorizzate = [cid.strip() for cid in chat_ids_str.split(",") if cid.strip()]
                if chat_id not in chat_autorizzate: continue

                # 🛑 COMMAND: /stop (Remote Kill-Switch)
                if testo == "/stop":
                    invia_telegram(chat_id, "🛑 RECEIVED /STOP COMMAND.\nInitiating emergency shutdown and returning to Standby...")
                    stato_motore = "CHIUSURA_FORZATA"
                
                # 📊 COMMAND: /status (Quick Portfolio Report)
                elif testo == "/status":
                    posizioni = mt5.positions_get()
                    num_pos = len(posizioni) if posizioni else 0
                    acc = mt5.account_info()
                    equity = acc.equity if acc else 0.0
                    invia_telegram(chat_id, f"📊 STATUS REPORT V11.0\nEngine State: {stato_motore}\nEquity: ${equity:.2f}\nOpen Positions: {num_pos}")
                    
    except Exception as e:
        pass

def scrivi_registro_csv(ticker, lotti, prezzo_apertura, prezzo_chiusura, profitto_netto, tipo_trade, orizzonte):
    """
    Log closed trade to persistent CSV file (audit trail).
    
    Creates or appends to storico_operazioni_chiuse.csv with:
    - Trade metadata: ticker, direction, volume, entry/exit prices
    - P&L: net profit after commission
    - Classification: SHORT_TERM or LONG_TERM (for supervision)
    
    Args:
        ticker (str): Asset symbol.
        lotti (float): Volume in lots.
        prezzo_apertura (float): Entry price.
        prezzo_chiusura (float): Exit price.
        profitto_netto (float): Profit/loss after commission (USD).
        tipo_trade (str): "LONG" or "SHORT".
        orizzonte (str): "LONG_TERM" or "SHORT_TERM".
    
    Returns:
        None: Side effect only (file I/O).
    """
    file_path = "storico_operazioni_chiuse.csv"
    file_exists = os.path.isfile(file_path)
    with open(file_path, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(["Close Date", "Time", "Asset", "Type", "Lots", "Entry Price", "Exit Price", "Net P/L ($)", "Horizon"])
        adesso = datetime.datetime.now()
        writer.writerow([adesso.strftime("%Y-%m-%d"), adesso.strftime("%H:%M:%S"), ticker, tipo_trade, lotti, prezzo_apertura, prezzo_chiusura, f"{profitto_netto:.2f}", orizzonte])

def aggiorna_csv_portafoglio_aperto(posizioni):
    """
    Update open portfolio CSV with live position data.
    
    Regenerates portafoglio_aperto_live.csv with current positions,
    useful for real-time dashboard display and risk monitoring.
    
    Args:
        posizioni (list): MT5 position objects from mt5.positions_get().
    
    Returns:
        None: Side effect only (file I/O).
    """
    file_path = "portafoglio_aperto_live.csv"
    with open(file_path, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["Ticker", "Entry Date", "Hold Days", "Trade Type", "Lots", "Entry Price", "Current Profit ($)", "Horizon (Magic)"])
        
        adesso = datetime.datetime.now()
        for pos in posizioni:
            data_acquisto = datetime.datetime.fromtimestamp(pos.time)
            giorni_hold = (adesso - data_acquisto).days
            tipo_trade = "LONG" if pos.type == mt5.POSITION_TYPE_BUY else "SHORT"
            orizzonte = "LONG TERM 🛡️" if pos.magic == MAGIC_LONG_TERM else "SHORT TERM ⚡"
            profitto_netto = pos.profit - (pos.volume * COMMISSION_PER_LOT)
            
            writer.writerow([pos.symbol, data_acquisto.strftime("%Y-%m-%d %H:%M"), giorni_hold, tipo_trade, pos.volume, pos.price_open, f"{profitto_netto:.2f}", orizzonte])

def classifica_asset(ticker):
    """
    Classify asset into category and recommended holding horizon.
    
    Classification logic:
    - Crypto (BTC, ETH): Long-term cassettista (high volatility, secular uptrend)
    - Forex (6-letter codes): Short-term speculation (tight spreads, mean reversion)
    - Equities: Long-term cassettista (company value fundamentals)
    
    Args:
        ticker (str): Asset symbol.
    
    Returns:
        tuple: (category, holding_horizon)
            - category: "CRYPTO", "FOREX", or "CASSETTISTA"
            - holding_horizon: "LONG_TERM" or "SHORT_TERM"
    """
    if "BTC" in ticker or "ETH" in ticker: return "CRYPTO", "LONG_TERM"
    if len(ticker) == 6 and ticker.isalpha(): return "FOREX", "SHORT_TERM"
    return "CASSETTISTA", "LONG_TERM"

def is_mercato_aperto(ticker):
    """
    Check if market is currently open for live trading.
    
    Verification:
    - Symbol must have valid tick data from MT5
    - Tick age must be < 5 minutes (staleness check)
    
    Args:
        ticker (str): Asset symbol.
    
    Returns:
        bool: True if market is open and data is fresh, False otherwise.
    """
    tick = mt5.symbol_info_tick(ticker)
    if not tick: return False
    if time.time() - tick.time > 300: return False
    return True

def is_spread_accettabile(ticker):
    """
    Verify broker spread is within acceptable limits.
    
    Threshold: 0.2% of mid-price
    Example: 1% price level with 0.2% spread = 0.002 max spread
    
    Args:
        ticker (str): Asset symbol.
    
    Returns:
        bool: True if spread < 0.2%, False otherwise.
    """
    tick = mt5.symbol_info_tick(ticker)
    if not tick or tick.ask == 0: return False
    return (((tick.ask - tick.bid) / tick.ask) * 100) < 0.2

def is_venerdi_chiusura():
    """
    Check if it's Friday closing hours (high gap risk).
    
    Threshold: Friday after 21:30 UTC (forex weekly close)
    Used to force exit forex positions before weekend halts.
    
    Returns:
        bool: True if Friday 21:30+ UTC, False otherwise.
    """
    now = datetime.datetime.now()
    return now.weekday() == 4 and ((now.hour == 21 and now.minute >= 30) or now.hour > 21)

def esegui_trade_silenzioso(azione, ticker, budget_usd, orizzonte_temporale):
    """
    Execute a market order with intelligent position sizing.
    
    Position Sizing Algorithm:
    1. Query margin requirement for 1 lot
    2. Calculate max lots: budget_usd / margin_per_lot
    3. Round down to minimum lot step from broker
    4. Validate against broker minimums
    
    Args:
        azione (str): "BUY" or "SELL".
        ticker (str): Asset symbol.
        budget_usd (float): USD capital allocation for this trade.
        orizzonte_temporale (str): "LONG_TERM" or "SHORT_TERM".
    
    Returns:
        tuple: (success, lots_executed, price_executed)
            - success (bool): True if order executed
            - lots_executed (float): Volume actually sent to market
            - price_executed (float): Fill price
    """
    info = mt5.symbol_info(ticker)
    if not info: return False, 0.0, 0.0
    tipo = mt5.ORDER_TYPE_BUY if azione == "BUY" else mt5.ORDER_TYPE_SELL
    tick = mt5.symbol_info_tick(ticker)
    if not tick: return False, 0.0, 0.0
    prezzo = tick.ask if azione == "BUY" else tick.bid
    margine = mt5.order_calc_margin(tipo, ticker, 1.0, prezzo)
    if margine is None or margine == 0: margine = info.volume_min
    
    # 🛡️ LEVERAGE PROTECTOR: Use only 50% of the allocated budget as margin 
    # to avoid over-leveraging and instant stop-outs.
    safe_budget = budget_usd * 0.5
    lotti = round((safe_budget / margine) / info.volume_step) * info.volume_step
    
    if lotti < info.volume_min: return False, 0.0, 0.0

    magic_num = MAGIC_LONG_TERM if orizzonte_temporale == "LONG_TERM" else MAGIC_SHORT_TERM
    commento = "LongTerm_V11.0" if orizzonte_temporale == "LONG_TERM" else "ShortTerm_V11.0"

    req = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": ticker,
        "volume": float(lotti),
        "type": tipo,
        "price": prezzo,
        "deviation": 20,
        "magic": magic_num,
        "comment": commento,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    res = mt5.order_send(req)
    if res.retcode != mt5.TRADE_RETCODE_DONE: return False, 0.0, 0.0
    return True, lotti, res.price

def _loop_principale(mode, callbacks, param_iniziali):
    global stato_motore, parametri_attivi
    
    def custom_log(msg, replace=False):
        try: callbacks.get("log")(msg, replace_last=replace)
        except: callbacks.get("log")(msg)
        
    imposta_ui = callbacks.get("running") 
    
    if not mt5.initialize():
        custom_log("❌ CRITICAL ERROR: MetaTrader 5 closed.")
        stato_motore = "SPENTO"
        return
        
    acc = mt5.account_info()
    if acc: custom_log(f"📡 Radar V11.0 (Massive Scan) connected to {acc.server}")

    memoria_asset = {} 
    profitto_giornaliero = 0.0 
    session_start_time, ultimo_heartbeat = None, time.time()
    ultimo_stato_ui = None
    radar_ticks = 0 
    
    primo_giro_completato = False # 🚀 FLAG PER LA COSTRUZIONE MASSIVA

    giorno_corrente = datetime.datetime.now().day # 🕒 Tiene traccia del giorno attuale

    while stato_motore != "SPENTO":
        
        # 📱 Listen for incoming remote commands via Telegram
        tg_chat_attuale = parametri_attivi.get("tg_chat", "")
        if tg_chat_attuale:
            controlla_comandi_telegram(tg_chat_attuale)

        acc_live = mt5.account_info()
        if acc_live and callbacks.get("portfolio"):
            callbacks.get("portfolio")(acc_live.margin_free, acc_live.equity - acc_live.margin_free)
        
        if stato_motore == "TRADING":
            if ultimo_stato_ui != True: imposta_ui(True); ultimo_stato_ui = True
            
            # Reset variables on START button press
            if session_start_time is None:
                session_start_time = time.time()
                primo_giro_completato = False
                autopilot_tickers = [] # 🧠 Dynamic Autopilot memory
                
                # ==========================================
                # 🩺 SYSTEM HEALTH CHECK (Pre-Flight Test)
                # ==========================================
                custom_log("🔄 Executing System Health Check pre-startup...")
                health_passed = True
                
                # 1. Test Internet Connection
                try:
                    requests.get("https://8.8.8.8", timeout=3)
                    custom_log("   ✅ Internet Connection: OK")
                except:
                    custom_log("   ❌ Internet Connection: UNAVAILABLE")
                    health_passed = False

                # 2 & 3. Test MetaTrader 5 Terminal and Auto-Trading
                term_info = mt5.terminal_info()
                if term_info is not None:
                    custom_log("   ✅ MetaTrader 5 Terminal: OPEN")
                    if term_info.trade_allowed:
                        custom_log("   ✅ MT5 Algo Trading: ENABLED")
                    else:
                        custom_log("   ❌ MT5 Algo Trading: DISABLED (Press 'Auto Trading' in MT5!)")
                        health_passed = False
                else:
                    custom_log("   ❌ MetaTrader 5 Terminal: CLOSED/DISCONNECTED")
                    health_passed = False

                # 4. Test Account Broker
                if mt5.account_info() is not None:
                    custom_log("   ✅ Account Broker: CONNECTED")
                else:
                    custom_log("   ❌ Account Broker: DISCONNECTED (Log in to MT5!)")
                    health_passed = False

                # 5. Test API Groq
                if not os.getenv("GROQ_API_KEY"):
                    custom_log("   ❌ Groq API Key: MISSING IN .env FILE")
                    health_passed = False
                else:
                    custom_log("   ✅ Groq API Key: CONFIGURED")
                    
                # 6. Test API News
                if not os.getenv("NEWS_API_KEY"):
                    custom_log("   ❌ News API Key: MISSING IN .env FILE")
                    health_passed = False
                else:
                    custom_log("   ✅ News API Key: CONFIGURED")

                # 7. Resolve Local IP for Web Dashboard
                try:
                    # Connects to a dummy external address to find the active local network IP
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    s.connect(("8.8.8.8", 80))
                    local_ip = s.getsockname()[0]
                    s.close()
                    custom_log(f"   🌐 Web Dashboard (LAN): http://{local_ip}:8501")
                    custom_log(f"   💻 Web Dashboard (Local): http://localhost:8501")
                except Exception:
                    custom_log("   🌐 Web Dashboard: http://localhost:8501")

                if not health_passed:
                    custom_log("🛑 HEALTH CHECK FAILED. Fix errors and retry.")
                    stato_motore = "CHIUSURA_FORZATA"
                    continue
                else:
                    custom_log("🚀 ALL SYSTEMS OPERATIONAL. Starting PHASE 1: Market Scan...")
                # ==========================================

            stringa_tickers = parametri_attivi.get("ticker", "EURUSD")
            budget_totale_max = float(parametri_attivi.get("budget", 100))
            max_loss = float(parametri_attivi.get("loss", "30"))
            tg_chat = parametri_attivi.get("tg_chat", "")

            tickers_da_scansionare = [t.strip() for t in stringa_tickers.split(",") if t.strip()]

            # ==========================================
            # 🧠 AUTOPILOT: "FOLLOW THE SUN" GLOBAL DISCOVERY
            # ==========================================
            if "AUTOPILOT" in tickers_da_scansionare:
                # Initialize persistent scan timer if not present in globals
                if 'last_autopilot_scan' not in globals():
                    global last_autopilot_scan
                    last_autopilot_scan = 0

                # Execute web discovery ONLY once per hour (3600s) to prevent loop spam
                if time.time() - last_autopilot_scan > 3600:
                    last_autopilot_scan = time.time()
                    
                    # Determine active region based on UTC clock
                    utc_h = datetime.datetime.utcnow().hour
                    if 14 <= utc_h < 21:
                        region, market_label = "US", "🇺🇸 Wall Street (US)"
                        fallback = ["NVDA", "TSLA", "PLTR", "MSTR", "AAPL"]
                    elif 8 <= utc_h < 14:
                        region, market_label = "GB", "🇪🇺 Europe (UK/DE/FR)"
                        fallback = ["SAP.DE", "ASML.AS", "LVMH.PA", "HSBA.L", "RACE.MI"] 
                    else:
                        region, market_label = "HK", "🌏 Asia (HK/JP)"
                        fallback = ["9988.HK", "0700.HK", "SONY.T", "7203.T", "BABA"] 

                    custom_log(f"⚙️ AUTOPILOT (Follow The Sun): Target ➔ {market_label}")
                    
                    trending_pool = []
                    try:
                        # Query Yahoo Finance for region-specific trending tickers
                        url = f"https://query1.finance.yahoo.com/v1/finance/trending/{region}"
                        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
                        if res.status_code == 200:
                            data = res.json()
                            trending_pool = [q['symbol'] for q in data['finance']['result'][0]['quotes'] if '^' not in q['symbol']]
                    except Exception:
                        pass

                    # Merge discovered assets with region-specific fallbacks
                    candidate_pool = list(set(trending_pool + fallback))
                    valid_trends = []
                    
                    for tk in candidate_pool:
                        base_tk = tk.split('.')[0]
                        mt5_tk = tk
                        
                        # Resolve broker-specific suffixes (e.g., .OQ, .DE)
                        if not mt5.symbol_info(mt5_tk):
                            variants = [tk, base_tk, f"{base_tk}.OQ", f"{base_tk}.DE", f"{base_tk}.L", f"{base_tk}.HK", f"{base_tk}USD"]
                            for v in variants:
                                if mt5.symbol_info(v):
                                    mt5_tk = v
                                    break

                        # Validate asset availability and bullish momentum
                        if mt5.symbol_info(mt5_tk) and is_mercato_aperto(mt5_tk):
                            mt5.symbol_select(mt5_tk, True)
                            rates = mt5.copy_rates_from_pos(mt5_tk, mt5.TIMEFRAME_D1, 0, 5)
                            if rates is not None and len(rates) > 1:
                                p_now, p_start = rates[-1]['close'], rates[0]['open']
                                if p_now > 2: # Filter out low-liquidity penny stocks
                                    perf = ((p_now - p_start) / p_start) * 100
                                    if perf > 1.0: # Minimum momentum threshold
                                        valid_trends.append((mt5_tk, perf))

                    # Sort by performance and limit to top 10 assets
                    valid_trends.sort(key=lambda x: x[1], reverse=True)
                    autopilot_tickers = [x[0] for x in valid_trends[:10]]

                    if not autopilot_tickers:
                        custom_log(f"⚠️ AUTOPILOT: No strong momentum detected in {market_label} at this time.")
                    else:
                        custom_log(f"🎯 AUTOPILOT: Added {len(autopilot_tickers)} trending assets from {market_label}!")

                # Silently merge memory-stored autopilot assets into the scanning queue
                tickers_da_scansionare.remove("AUTOPILOT")
                tickers_da_scansionare = list(set(tickers_da_scansionare + autopilot_tickers))
            # ==========================================

            venerdi_sera = is_venerdi_chiusura()

            # 🔄 MIDNIGHT RESET
            oggi = datetime.datetime.now().day
            if oggi != giorno_corrente:
                profitto_giornaliero = 0.0
                giorno_corrente = oggi
                custom_log("🌒 New Day: Profit and drawdown counter reset. Starting fresh!")

            # 🛑 KILL SWITCH (Only for losses! Profits run free)
            if profitto_giornaliero <= -max_loss:
                msg = f"🛑 MAX DRAWDOWN REACHED ({profitto_giornaliero:.2f}$). Closing speculations, securing long-term positions."
                custom_log(msg)
                invia_telegram(tg_chat, msg)
                stato_motore = "CHIUSURA_FORZATA"
                continue

            for ticker in tickers_da_scansionare:
                time.sleep(0.01)
                mt5.symbol_select(ticker, True)
                
                if ticker not in memoria_asset:
                    memoria_asset[ticker] = {"high": 0, "low": 0, "picco_trade": 0, "impegnato": 0.0, "quarantena": 0, "perdite": 0}

                if time.time() < memoria_asset[ticker]["quarantena"]: continue 
                if not is_mercato_aperto(ticker): continue
                if not is_spread_accettabile(ticker): continue

                tick = mt5.symbol_info_tick(ticker)
                if not tick: continue
                prezzo = tick.last if tick.last > 0 else tick.ask
                posizioni = mt5.positions_get(symbol=ticker)
                
                if not posizioni: memoria_asset[ticker]["impegnato"] = 0.0
                
                categoria, orizzonte = classifica_asset(ticker)
                
                # ==========================================
                # 1. ENTRY SEARCH
                # ==========================================
                if not posizioni:
                    if venerdi_sera and orizzonte == "SHORT_TERM": continue 
                        
                    if memoria_asset[ticker]["high"] == 0: 
                        memoria_asset[ticker]["high"] = prezzo
                        memoria_asset[ticker]["low"] = prezzo
                        
                    if prezzo > memoria_asset[ticker]["high"]: memoria_asset[ticker]["high"] = prezzo
                    if prezzo < memoria_asset[ticker]["low"]: memoria_asset[ticker]["low"] = prezzo
                    
                    dist_dal_max = ((prezzo - memoria_asset[ticker]["high"]) / memoria_asset[ticker]["high"]) * 100
                    dist_dal_min = ((prezzo - memoria_asset[ticker]["low"]) / memoria_asset[ticker]["low"]) * 100
                    
                    # If there is technical movement OR we are in Phase 1 (Portfolio Construction)
                    trigger_tecnico = (dist_dal_max <= -0.01 or dist_dal_min >= 0.01)
                    trigger_massivo = not primo_giro_completato
                    
                    if trigger_tecnico or trigger_massivo:
                        if trigger_massivo:
                            custom_log(f"🚀 MASSIVE ANALYSIS: Checking {ticker} for portfolio construction...")
                        else:
                            custom_log(f"Movement on {ticker}. Querying AI...")
                            
                        # 🛡️ KICKSTART PROTECTOR: Force a small $15 investment during Phase 1
                        # This prevents the bot from dumping $200 on weak initial signals.
                        if not primo_giro_completato:
                            budget_da_usare = 15.0 
                        else:
                            # Standard dynamic allocation for the active Radar phase
                            budget_usato_tot = sum(d["impegnato"] for d in memoria_asset.values())
                            budget_base = budget_totale_max / max(1, len(tickers_da_scansionare))
                            budget_da_usare = min(budget_base * 1.2, budget_totale_max - budget_usato_tot)

                        if budget_da_usare >= 1.0:
                            # V11: Extract Sentiment, Score, and Message
                            sentiment, ai_score, msg_ai = analizza_sentiment_ollama(ticker)
                            
                            azione = None
                            
                            # 🧠 SELECTIVE ENTRY THRESHOLD
                            # We ignore weak noise (Scores 1, 2, 3). 
                            # A minimum score of 4 is required to open ANY position.
                            min_threshold = 4
                            
                            if sentiment == "POSITIVO" and ai_score >= min_threshold: 
                                azione = "BUY"  
                            elif sentiment == "NEGATIVO" and ai_score <= -min_threshold: 
                                azione = "SELL" 
                            else:
                                # Log skipped weak signals during Phase 1 for transparency
                                if trigger_massivo:
                                    custom_log(f"🧠 AI Scan | {ticker}: Score {ai_score}/10. Too weak (needs {min_threshold}), skipped.")
                                success, lotti, p_eseguito = esegui_trade_silenzioso(azione, ticker, budget_da_usare, orizzonte)
                                if success:
                                    radar_ticks = 0 
                                    icona = "🛡️" if orizzonte == "LONG_TERM" else "⚡"
                                    custom_log(f"🤖 AI {azione} {icona} | {ticker} | 🤖 Score: {ai_score}/10 | {msg_ai} (Ord: {lotti})")
                                    invia_telegram(tg_chat, f"{'🟢' if azione=='BUY' else '🔴'} NEW {azione} {icona}: {ticker}\nPrice: {p_eseguito}\nAI Score: {ai_score}/10\nDetails: {msg_ai}")
                                    memoria_asset[ticker]["impegnato"] = budget_da_usare
                                    memoria_asset[ticker]["picco_trade"] = p_eseguito
                                    time.sleep(1.0) # Anti-spam delay ONLY after successful execution
                                    
                        memoria_asset[ticker]["high"] = prezzo
                        memoria_asset[ticker]["low"] = prezzo
                            
                # ==========================================
                # 2. POSITION MANAGEMENT & IMMUNITY
                # ==========================================
                else:
                    is_long = posizioni[0].type == mt5.POSITION_TYPE_BUY
                    is_immune = posizioni[0].magic == MAGIC_LONG_TERM
                    prezzo_medio = sum(p.price_open * p.volume for p in posizioni) / sum(p.volume for p in posizioni)
                    costo_commissioni = sum(p.volume for p in posizioni) * COMMISSION_PER_LOT
                    profitto_netto = sum(p.profit for p in posizioni) - costo_commissioni
                    
                    if is_long:
                        if prezzo > memoria_asset[ticker]["picco_trade"]: memoria_asset[ticker]["picco_trade"] = prezzo
                        diff_dal_picco = ((prezzo - memoria_asset[ticker]["picco_trade"]) / memoria_asset[ticker]["picco_trade"]) * 100
                        perdita_perc = ((prezzo_medio - prezzo) / prezzo_medio) * 100 
                    else:
                        if prezzo < memoria_asset[ticker]["picco_trade"] or memoria_asset[ticker]["picco_trade"]==0: memoria_asset[ticker]["picco_trade"] = prezzo
                        diff_dal_picco = ((memoria_asset[ticker]["picco_trade"] - prezzo) / memoria_asset[ticker]["picco_trade"]) * 100
                        perdita_perc = ((prezzo - prezzo_medio) / prezzo_medio) * 100 
                    
                    chiudi_ora, motivo_chiusura = False, ""
                    limite_base = budget_totale_max * 0.03
                    
                    if is_immune:
                        hard_stop_loss = -max(limite_base * 4.0, costo_commissioni * 5.0) 
                        
                        if profitto_netto <= hard_stop_loss:
                            chiudi_ora, motivo_chiusura = True, f"Structural Collapse Stop ({hard_stop_loss:.1f}$)"
                        elif profitto_netto > (costo_commissioni * 3) and diff_dal_picco <= -3.0: 
                            chiudi_ora, motivo_chiusura = True, "Long-Term Trailing Profit"
                    else:
                        hard_take_profit = max(limite_base, costo_commissioni * 2.0)
                        hard_stop_loss = -max(limite_base * 1.5, costo_commissioni * 2.5)

                        if profitto_netto >= hard_take_profit: 
                            chiudi_ora, motivo_chiusura = True, f"Target Reached (+{hard_take_profit:.1f}$)"
                        elif profitto_netto <= hard_stop_loss:
                            chiudi_ora, motivo_chiusura = True, f"Leverage Stop Loss ({hard_stop_loss:.1f}$)"
                        elif venerdi_sera:
                            chiudi_ora, motivo_chiusura = True, "Friday Weekend Shield"
                        elif profitto_netto > 0 and diff_dal_picco <= -0.05: 
                            chiudi_ora, motivo_chiusura = True, "Trailing Profit Forex"

                    if chiudi_ora:
                        for pos in posizioni:
                            tipo_ch = mt5.ORDER_TYPE_SELL if pos.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
                            mt5.order_send({"action": mt5.TRADE_ACTION_DEAL, "symbol": ticker, "volume": pos.volume, "type": tipo_ch, "position": pos.ticket, "price": prezzo, "deviation": 20, "magic": pos.magic, "type_filling": mt5.ORDER_FILLING_IOC})
                            
                        profitto_giornaliero += profitto_netto
                        tipo_str = "LONG" if is_long else "SHORT"
                        etichetta = "LONG_TERM" if is_immune else "SHORT_TERM"
                        
                        radar_ticks = 0 
                        custom_log(f"💰 CHIUSO {ticker} ({tipo_str}) | {motivo_chiusura} | P/L Netto: {profitto_netto:.2f}$")
                        invia_telegram(tg_chat, f"💰 CHIUSO {tipo_str}: {ticker}\nMotivo: {motivo_chiusura}\nProfitto: {profitto_netto:.2f}$")
                        scrivi_registro_csv(ticker, sum(p.volume for p in posizioni), prezzo_medio, prezzo, profitto_netto, tipo_str, etichetta)
                        
                        memoria_asset[ticker]["impegnato"] = 0.0 
                        memoria_asset[ticker]["high"] = prezzo
                        memoria_asset[ticker]["low"] = prezzo
                        
                         # --- QUARANTINE SYSTEM & COOL-DOWN ---
                        if profitto_netto < 0 and not is_immune:
                            memoria_asset[ticker]["perdite"] += 1
                            if memoria_asset[ticker]["perdite"] >= 2:
                                memoria_asset[ticker]["quarantena"] = time.time() + 3600 # 1 hour for too many stops
                                memoria_asset[ticker]["perdite"] = 0
                        elif profitto_netto > 0:
                            memoria_asset[ticker]["perdite"] = 0
                            
                            # 🏆 VICTORY QUARANTINE (Anti ping-pong cool-down)
                            ore_pausa = 2 # Wait 2 hours before retrading this asset
                            memoria_asset[ticker]["quarantena"] = time.time() + (3600 * ore_pausa)
                            custom_log(f"⏳ COOL-DOWN | {ticker} paused for {ore_pausa}h after Take Profit.")
                        else: 
                            memoria_asset[ticker]["perdite"] = 0

            # End of scan cycle for all tickers
            if not primo_giro_completato:
                primo_giro_completato = True
                custom_log("✅ PHASE 1 Complete. Portfolio Built. Moving to standard Radar.")

            if time.time() - ultimo_heartbeat > 30:
                radar_ticks += 1
                budget_attivo = sum(d["impegnato"] for d in memoria_asset.values())
                
                # 🌍 Determine active session for the UI heartbeat
                ora_utc_radar = datetime.datetime.utcnow().hour
                if 14 <= ora_utc_radar < 21: sessione_ui = "🇺🇸 US"
                elif 8 <= ora_utc_radar < 14: sessione_ui = "🇪🇺 EU"
                else: sessione_ui = "🌏 ASIA"
                custom_log(f"👀 Radar [{sessione_ui}]: {len(tickers_da_scansionare)} assets | Today's profit: {profitto_giornaliero:.2f}$ | Deployment: {budget_attivo:.2f}$/{budget_totale_max:.2f}$ (Update {radar_ticks}x)", replace=(radar_ticks > 1))

                tutte_le_posizioni = mt5.positions_get()
                if tutte_le_posizioni: aggiorna_csv_portafoglio_aperto(tutte_le_posizioni)
                
                ultimo_heartbeat = time.time()

        elif stato_motore == "CHIUSURA_FORZATA":
            if ultimo_stato_ui != False: imposta_ui(False); ultimo_stato_ui = False
            
            tutte_le_posizioni = mt5.positions_get()
            if tutte_le_posizioni:
                for pos in tutte_le_posizioni:
                    if pos.magic == MAGIC_SHORT_TERM:
                        mt5.order_send({"action": mt5.TRADE_ACTION_DEAL, "symbol": pos.symbol, "volume": pos.volume, "type": mt5.ORDER_TYPE_SELL if pos.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY, "position": pos.ticket, "price": mt5.symbol_info_tick(pos.symbol).bid, "deviation": 20, "magic": pos.magic, "type_filling": mt5.ORDER_FILLING_IOC})
            
            stato_motore = "MONITORAGGIO"
            
        else:
            if ultimo_stato_ui != False: imposta_ui(False); ultimo_stato_ui = False

        time.sleep(1.0)
    mt5.shutdown()

def cerca_simboli_broker(query):
    if not mt5.initialize(): return ["ERRORE_MT5"]
    simboli = mt5.symbols_get()
    return [s.name for s in simboli if query.upper() in s.name.upper() or query.upper() in s.description.upper()][:15]

def gestisci_connessione(mode, callbacks, parametri_ui):
    global stato_motore
    if stato_motore == "SPENTO":
        stato_motore = "MONITORAGGIO"
        threading.Thread(target=_loop_principale, args=(mode, callbacks, parametri_ui), daemon=True).start()

def aggiorna_parametri_e_avvia(nuovi_parametri):
    global stato_motore, parametri_attivi
    parametri_attivi = nuovi_parametri
    if stato_motore == "MONITORAGGIO": stato_motore = "TRADING"

def ferma_trading():
    global stato_motore
    if stato_motore == "TRADING": stato_motore = "CHIUSURA_FORZATA"

def spegni_tutto():
    global stato_motore; stato_motore = "SPENTO"