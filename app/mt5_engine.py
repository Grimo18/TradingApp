"""Motore LIVE per MetaTrader 5 (V7.0 - Kill Switch, Telegram, CSV, Smart DCA)."""

import MetaTrader5 as mt5
import time
import datetime
import threading
import requests
import csv
import os
from app.ai_brain import analizza_sentiment_ollama

stato_motore = "SPENTO" 
parametri_attivi = {} 
COMMISSION_PER_LOT = 6.0 

def invia_telegram(token, chat_id, messaggio):
    """Invia notifica push su Telegram."""
    if not token or not chat_id: return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": messaggio}, timeout=2)
    except:
        pass # Ignora l'errore se manca internet

def scrivi_registro_csv(ticker, lotti, prezzo_apertura, prezzo_chiusura, profitto_netto):
    """Salva la transazione su un file Excel/CSV."""
    file_path = "live_trades_log.csv"
    file_exists = os.path.isfile(file_path)
    
    with open(file_path, mode='a', newline='') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(["Data", "Ora", "Asset", "Lotti", "Prezzo Compra", "Prezzo Vendi", "P/L Netto ($)"])
        
        adesso = datetime.datetime.now()
        writer.writerow([adesso.strftime("%Y-%m-%d"), adesso.strftime("%H:%M:%S"), ticker, lotti, prezzo_apertura, prezzo_chiusura, f"{profitto_netto:.2f}"])

def classifica_asset(ticker):
    if len(ticker) == 6 and ticker.isalpha(): return "SCALPING"
    if "USD" in ticker and len(ticker) > 6: return "SCALPING"
    return "CASSETTISTA"

def is_mercato_aperto(ticker):
    tick = mt5.symbol_info_tick(ticker)
    if not tick: return False
    if time.time() - tick.time > 300: return False
    return True

def is_spread_accettabile(ticker):
    tick = mt5.symbol_info_tick(ticker)
    if not tick or tick.ask == 0: return False
    spread_perc = ((tick.ask - tick.bid) / tick.ask) * 100
    return spread_perc < 0.2

def is_venerdi_chiusura():
    now = datetime.datetime.now()
    if now.weekday() == 4: 
        if (now.hour == 21 and now.minute >= 30) or now.hour > 21: return True
    return False

def esegui_trade_silenzioso(azione, ticker, budget_usd):
    info = mt5.symbol_info(ticker)
    if not info: return False, 0.0, 0.0
    tipo = mt5.ORDER_TYPE_BUY if azione == "BUY" else mt5.ORDER_TYPE_SELL
    tick = mt5.symbol_info_tick(ticker)
    if not tick: return False, 0.0, 0.0
    prezzo = tick.ask if azione == "BUY" else tick.bid
    margine = mt5.order_calc_margin(tipo, ticker, 1.0, prezzo)
    if margine is None or margine == 0: margine = info.volume_min
    lotti = round((budget_usd / margine) / info.volume_step) * info.volume_step
    if lotti < info.volume_min: return False, 0.0, 0.0

    req = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": ticker,
        "volume": float(lotti),
        "type": tipo,
        "price": prezzo,
        "deviation": 20,
        "magic": 1001,
        "comment": "Quant V7.0",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    res = mt5.order_send(req)
    if res.retcode != mt5.TRADE_RETCODE_DONE: return False, 0.0, 0.0
    return True, lotti, res.price

def _loop_principale(mode, callbacks, param_iniziali):
    global stato_motore, parametri_attivi
    log, imposta_ui = callbacks.get("log"), callbacks.get("running") 
    
    if not mt5.initialize():
        log("❌ ERRORE CRITICO: MetaTrader 5 chiuso.")
        stato_motore = "SPENTO"
        return
        
    acc = mt5.account_info()
    if acc: log(f"📡 Radar Istituzionale Attivo su {acc.server} (Account: {acc.login})")

    massimo_storico_pre_ingresso = {}
    prezzo_massimo_operazione = {}
    budget_impegnato = {}
    perdite_consecutive = {}
    quarantena = {}
    
    profitto_giornaliero = 0.0 # Contabilità per il Kill Switch
    session_start_time, ultimo_heartbeat = None, time.time()
    ultimo_stato_ui = None

    while stato_motore != "SPENTO":
        acc_live = mt5.account_info()
        if acc_live and callbacks.get("portfolio"):
            callbacks.get("portfolio")(acc_live.margin_free, acc_live.equity - acc_live.margin_free)
        
        if stato_motore == "TRADING":
            if ultimo_stato_ui != True:
                imposta_ui(True)
                ultimo_stato_ui = True
            
            if session_start_time is None: session_start_time = time.time()
            
            # Parametri UI
            stringa_tickers = parametri_attivi.get("ticker", "EURUSD")
            budget_totale_max = float(parametri_attivi.get("budget", 100))
            target_profit = float(parametri_attivi.get("target", 50))
            max_loss = float(parametri_attivi.get("loss", 30))
            tg_token = parametri_attivi.get("tg_token", "")
            tg_chat = parametri_attivi.get("tg_chat", "")
            
            tickers_da_scansionare = [t.strip() for t in stringa_tickers.split(",") if t.strip()]
            venerdi_sera = is_venerdi_chiusura()

            # 🛑 CONTROLLO KILL SWITCH
            if profitto_giornaliero >= target_profit:
                msg = f"🏆 TARGET RAGGIUNTO! Profitto netto oggi: +{profitto_giornaliero:.2f}$. Spegnimento motori."
                log(msg)
                invia_telegram(tg_token, tg_chat, msg)
                stato_motore = "CHIUSURA_FORZATA"
                continue
            if profitto_giornaliero <= -max_loss:
                msg = f"🛑 MAX DRAWDOWN SUPERATO! Perdita: {profitto_giornaliero:.2f}$. Blocco d'emergenza attivato."
                log(msg)
                invia_telegram(tg_token, tg_chat, msg)
                stato_motore = "CHIUSURA_FORZATA"
                continue

            for ticker in tickers_da_scansionare:
                time.sleep(0.01) # Ottimizzazione MT5
                mt5.symbol_select(ticker, True)
                
                if ticker not in massimo_storico_pre_ingresso:
                    massimo_storico_pre_ingresso[ticker] = 0
                    prezzo_massimo_operazione[ticker] = 0
                    budget_impegnato[ticker] = 0.0
                    perdite_consecutive[ticker] = 0

                # --- TELEMETRIA VS CODE (Stampa solo nel terminale di Visual Studio) ---
                if ticker in quarantena and time.time() < quarantena[ticker]:
                    print(f"[VS CODE LOG] {ticker} saltato: in quarantena.")
                    continue 
                if not is_mercato_aperto(ticker):
                    print(f"[VS CODE LOG] {ticker} saltato: Borsa chiusa o assenza scambi.")
                    continue
                if not is_spread_accettabile(ticker):
                    print(f"[VS CODE LOG] {ticker} saltato: Spread troppo alto dal broker.")
                    continue

                tick = mt5.symbol_info_tick(ticker)
                if not tick: continue
                prezzo = tick.last if tick.last > 0 else tick.ask
                posizioni = mt5.positions_get(symbol=ticker)
                
                if not posizioni: budget_impegnato[ticker] = 0.0
                
                # --- RICERCA INGRESSO (PRIMO ACQUISTO) ---
                if not posizioni:
                    if venerdi_sera: continue 
                        
                    prezzo_massimo_operazione[ticker] = 0
                    if prezzo > massimo_storico_pre_ingresso[ticker]: 
                        massimo_storico_pre_ingresso[ticker] = prezzo
                    
                    if massimo_storico_pre_ingresso[ticker] > 0:
                        dist = ((prezzo - massimo_storico_pre_ingresso[ticker]) / massimo_storico_pre_ingresso[ticker]) * 100
                        
                        if dist <= -0.01:
                            print(f"[VS CODE LOG] {ticker} ha un crollo tecnico ({dist:.3f}%). Interrogo l'AI...")
                            budget_base = budget_totale_max / max(1, len(tickers_da_scansionare))
                            budget_da_usare = min(budget_base * 3.0, budget_totale_max - sum(budget_impegnato.values()))

                            if budget_da_usare >= 1.0:
                                si, msg_ai = analizza_sentiment_ollama(ticker)
                                print(f"[VS CODE LOG] Risposta AI su {ticker}: {msg_ai}") # Ti mostra il pensiero dell'AI in VS Code
                                
                                if si: 
                                    success, lotti, p_eseguito = esegui_trade_silenzioso("BUY", ticker, budget_da_usare)
                                    if success:
                                        log(f"🤖 AI BUY | {ticker} | {msg_ai} (Lotti: {lotti})")
                                        invia_telegram(tg_token, tg_chat, f"🟢 NUOVO ACQUISTO: {ticker}\nPrezzo: {p_eseguito}\nAI: {msg_ai}")
                                        budget_impegnato[ticker] = budget_da_usare
                                    else:
                                        print(f"[VS CODE LOG] Ordine rifiutato dal broker su {ticker}. Motivo probabile: margine insufficiente.")
                            else:
                                print(f"[VS CODE LOG] Budget esaurito nel piatto. Salto {ticker}.")
                                
                            massimo_storico_pre_ingresso[ticker] = prezzo
                            
                # --- GESTIONE POSIZIONI E DCA (MEDIA AL RIBASSO) ---
                else:
                    prezzo_medio_carico = sum(p.price_open * p.volume for p in posizioni) / sum(p.volume for p in posizioni)
                    profitto_lordo = sum(p.profit for p in posizioni)
                    costo_commissioni = sum(p.volume for p in posizioni) * COMMISSION_PER_LOT
                    profitto_netto = profitto_lordo - costo_commissioni
                    
                    modalita = classifica_asset(ticker)
                    
                    if prezzo > prezzo_massimo_operazione[ticker]: 
                        prezzo_massimo_operazione[ticker] = prezzo
                    diff_dal_picco = ((prezzo - prezzo_massimo_operazione[ticker]) / prezzo_massimo_operazione[ticker]) * 100
                    
                    # 💡 SMART DCA: Se è crollata del 2% rispetto al nostro prezzo medio, ed è un'azione forte, compriamo ancora!
                    distanza_prezzo_medio = ((prezzo - prezzo_medio_carico) / prezzo_medio_carico) * 100
                    if modalita == "CASSETTISTA" and distanza_prezzo_medio <= -2.0 and len(posizioni) < 3: # Massimo 3 ingressi
                        budget_rimanente = budget_totale_max - sum(budget_impegnato.values())
                        if budget_rimanente >= 5.0:
                            si, _ = analizza_sentiment_ollama(ticker)
                            if si:
                                success, lotti_dca, p_dca = esegui_trade_silenzioso("BUY", ticker, 10.0) # Entrata fissa DCA
                                if success:
                                    log(f"📉 SMART DCA | Mediato al ribasso {ticker} a {p_dca}")
                                    invia_telegram(tg_token, tg_chat, f"🔄 DCA su {ticker}: Azione scesa, comprati altri {lotti_dca} lotti a {p_dca}")
                                    budget_impegnato[ticker] += 10.0

                    chiudi_ora, motivo_chiusura = False, ""

                    if venerdi_sera:
                        if modalita == "CASSETTISTA" and profitto_netto > (costo_commissioni * 2): pass 
                        else: chiudi_ora, motivo_chiusura = True, "Scudo Weekend"
                    else:
                        if modalita == "CASSETTISTA":
                            if diff_dal_picco <= -5.0: chiudi_ora, motivo_chiusura = True, "Stop Crollo (-5%)"
                            elif profitto_netto > 0 and diff_dal_picco <= -0.3: chiudi_ora, motivo_chiusura = True, "Take Profit"
                        else:
                            if diff_dal_picco <= -0.1: chiudi_ora, motivo_chiusura = True, "Scalping Stop"

                    if chiudi_ora:
                        # Esegue la chiusura
                        for pos in posizioni:
                            tipo_ch = mt5.ORDER_TYPE_SELL if pos.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
                            req = {"action": mt5.TRADE_ACTION_DEAL, "symbol": ticker, "volume": pos.volume, "type": tipo_ch, "position": pos.ticket, "price": prezzo, "deviation": 20, "magic": 1001, "type_filling": mt5.ORDER_FILLING_IOC}
                            mt5.order_send(req)
                            
                        # Contabilità e Log
                        profitto_giornaliero += profitto_netto
                        log(f"📉 CHIUSO {ticker} | {motivo_chiusura} | P/L Netto: {profitto_netto:.2f}$ (Giornata: {profitto_giornaliero:.2f}$)")
                        invia_telegram(tg_token, tg_chat, f"💰 CHIUSO: {ticker}\nMotivo: {motivo_chiusura}\nProfitto: {profitto_netto:.2f}$")
                        scrivi_registro_csv(ticker, sum(p.volume for p in posizioni), prezzo_medio_carico, prezzo, profitto_netto)
                        
                        budget_impegnato[ticker] = 0.0 
                        
                        if profitto_netto < 0 and not venerdi_sera:
                            perdite_consecutive[ticker] += 1
                            if perdite_consecutive[ticker] >= 2:
                                quarantena[ticker] = time.time() + 3600 
                                log(f"⏸️ QUARANTENA | {ticker} fermo per 1 ora.")
                                perdite_consecutive[ticker] = 0
                        else: perdite_consecutive[ticker] = 0 

            if time.time() - ultimo_heartbeat > 30:
                log(f"👀 Radar attivo: {len(tickers_da_scansionare)} asset | Profitto oggi: {profitto_giornaliero:.2f}$ | Piatto: {sum(budget_impegnato.values()):.2f}$/{budget_totale_max:.2f}$")
                ultimo_heartbeat = time.time()

        elif stato_motore == "CHIUSURA_FORZATA":
            if ultimo_stato_ui != False: imposta_ui(False); ultimo_stato_ui = False
            # Chiude solo tutto il resto
            stringa_tickers = parametri_attivi.get("ticker", "EURUSD")
            for t in [t.strip() for t in stringa_tickers.split(",") if t.strip()]:
                posizioni = mt5.positions_get(symbol=t)
                if posizioni:
                    for pos in posizioni:
                        mt5.order_send({"action": mt5.TRADE_ACTION_DEAL, "symbol": t, "volume": pos.volume, "type": mt5.ORDER_TYPE_SELL if pos.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY, "position": pos.ticket, "price": mt5.symbol_info_tick(t).bid, "deviation": 20, "magic": 1001, "type_filling": mt5.ORDER_FILLING_IOC})
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