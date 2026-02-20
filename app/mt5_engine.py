"""Motore LIVE per MetaTrader 5 (V4.2 - Trailing Stop & Ricerca Globale)."""

import MetaTrader5 as mt5
import time
import threading
from app.ai_brain import analizza_sentiment_ollama

# --- CONFIGURAZIONI ---
stato_motore = "SPENTO" 
parametri_attivi = {} 
TRAILING_STOP_DIST = 0.2 # Paracadute mobile allo 0.2%

def calcola_lotti_da_budget(azione, ticker, budget_usd, prezzo, log):
    info = mt5.symbol_info(ticker)
    tipo_ordine = mt5.ORDER_TYPE_BUY if azione == "BUY" else mt5.ORDER_TYPE_SELL
    margine_per_1_lotto = mt5.order_calc_margin(tipo_ordine, ticker, 1.0, prezzo)
    
    if margine_per_1_lotto is None or margine_per_1_lotto == 0:
        return info.volume_min

    lotti_calcolati = budget_usd / margine_per_1_lotto
    step = info.volume_step
    lotti_arrotondati = round(lotti_calcolati / step) * step
    
    if lotti_arrotondati < info.volume_min:
        log(f"❌ Budget di {budget_usd}$ insufficiente per {ticker}.")
        return 0.0 
        
    return min(lotti_arrotondati, info.volume_max)

def esegui_trade(azione, ticker, budget_usd, log):
    tick = mt5.symbol_info_tick(ticker)
    if not tick: return False
    prezzo = tick.ask if azione == "BUY" else tick.bid
    lotti = calcola_lotti_da_budget(azione, ticker, budget_usd, prezzo, log)
    
    if lotti <= 0.0: return False

    tipo = mt5.ORDER_TYPE_BUY if azione == "BUY" else mt5.ORDER_TYPE_SELL
    req = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": ticker,
        "volume": float(lotti),
        "type": tipo,
        "price": prezzo,
        "deviation": 20,
        "magic": 1001,
        "comment": "Quant AI V4.2",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    log(f"⏳ Invio {azione} su {ticker} (Lotti: {lotti})...")
    res = mt5.order_send(req)
    if res.retcode != mt5.TRADE_RETCODE_DONE:
        log(f"❌ FALLITO: {res.comment}")
        return False
    log(f"✅ ESEGUITO {azione} a {res.price}")
    return True

def chiudi_tutte_posizioni(ticker, log):
    if not ticker: return
    posizioni = mt5.positions_get(symbol=ticker)
    if not posizioni: return

    log(f"🧹 Chiusura di {len(posizioni)} posizioni su {ticker}...")
    for pos in posizioni:
        tick = mt5.symbol_info_tick(ticker)
        tipo_chiusura = mt5.ORDER_TYPE_SELL if pos.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
        prezzo = tick.bid if pos.type == mt5.POSITION_TYPE_BUY else tick.ask
        
        req = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": ticker,
            "volume": pos.volume,
            "type": tipo_chiusura,
            "position": pos.ticket, 
            "price": prezzo,
            "deviation": 20,
            "magic": 1001,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        res = mt5.order_send(req)
        if res.retcode == mt5.TRADE_RETCODE_DONE:
            log(f"✅ Ticket {pos.ticket} CHIUSO!")

def _loop_principale(mode, callbacks, param_iniziali):
    global stato_motore, parametri_attivi
    log, imposta_ui = callbacks.get("log"), callbacks.get("running") 
    mt5.initialize()
    
    ultimo_ticker, massimo_storico_pre_ingresso, prezzo_massimo_operazione = "", 0, 0
    session_start_time, session_start_equity, trades_fatti = None, 0.0, 0

    while stato_motore != "SPENTO":
        acc_live = mt5.account_info()
        
        if stato_motore == "TRADING":
            imposta_ui(True) # Diciamo alla UI che stiamo correndo
            if session_start_time is None:
                session_start_time, session_start_equity = time.time(), acc_live.equity
            
            ticker = parametri_attivi.get("ticker", "EURUSD")
            budget = float(parametri_attivi.get("budget", 100))
            
            if ticker != ultimo_ticker:
                mt5.symbol_select(ticker, True)
                ultimo_ticker, massimo_storico_pre_ingresso = ticker, 0
                log(f"🎯 Target: {ticker}")

            tick = mt5.symbol_info_tick(ticker)
            if tick:
                prezzo = tick.last if tick.last > 0 else tick.ask
                posizioni = mt5.positions_get(symbol=ticker)
                
                if not posizioni:
                    prezzo_massimo_operazione = 0
                    if prezzo > massimo_storico_pre_ingresso: massimo_storico_pre_ingresso = prezzo
                    dist = ((prezzo - massimo_storico_pre_ingresso) / massimo_storico_pre_ingresso) * 100
                    if dist <= -0.01:
                        log(f"⚠️ Segnale tecnico. Consulto AI...")
                        si, msg = analizza_sentiment_ollama(ticker)
                        log(msg)
                        if si: 
                            if esegui_trade("BUY", ticker, budget, log): trades_fatti += 1
                        massimo_storico_pre_ingresso = prezzo
                else:
                    if prezzo > prezzo_massimo_operazione: prezzo_massimo_operazione = prezzo
                    diff = ((prezzo - prezzo_massimo_operazione) / prezzo_massimo_operazione) * 100
                    if diff <= -TRAILING_STOP_DIST:
                        log(f"📉 Trailing Stop! Esco a {prezzo}")
                        chiudi_tutte_posizioni(ticker, log)
                        trades_fatti += 1

        elif stato_motore == "CHIUSURA_FORZATA":
            imposta_ui(False) # <--- FIX: Avvisa subito la UI che stiamo chiudendo
            chiudi_tutte_posizioni(ultimo_ticker, log)
            if session_start_time:
                prof = acc_live.equity - session_start_equity
                log(f"📑 REPORT: Profitto {prof:.2f}$ | Trades: {trades_fatti}")
                session_start_time = None
            stato_motore = "MONITORAGGIO"

        else:
            imposta_ui(False) # <--- FIX: Stato di attesa, tasto deve essere AVVIA

        time.sleep(1.0)
    mt5.shutdown()

# --- COMANDI UI (Ripristinati da V3.5) ---

def cerca_simboli_broker(query):
    if not mt5.initialize(): return ["ERRORE_MT5"]
    simboli = mt5.symbols_get()
    q = query.upper()
    # Questa riga ora cerca di nuovo sia nel nome che nella descrizione!
    return [s.name for s in simboli if q in s.name.upper() or q in s.description.upper()][:15]

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
    global stato_motore
    stato_motore = "SPENTO"