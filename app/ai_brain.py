"""Modulo AI V9.5 - Integrazione Statistica Stagionale (Live Heatmap) & Sentiment."""

import yfinance as yf
from groq import Groq
from newsapi import NewsApiClient
import time
import datetime
import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")

cache_analisi = {}
cache_stagionalita = {} # Memoria per le statistiche (Heatmap)
DURATA_CACHE = 600 # 10 minuti per le notizie

def ottieni_bias_stagionale(ticker_pulito):
    """Calcola la media statistica degli ultimi 5 anni per il mese corrente."""
    mese_corrente = datetime.datetime.now().month
    nome_mese = datetime.datetime.now().strftime("%B")
    
    # Se abbiamo già calcolato la statistica per questo asset oggi, usiamo la cache
    if ticker_pulito in cache_stagionalita:
        return cache_stagionalita[ticker_pulito]
        
    try:
        stock = yf.Ticker(ticker_pulito)
        # Scarica i dati storici degli ultimi 5 anni, raggruppati per mese
        hist = stock.history(period="5y", interval="1mo")
        if not hist.empty and len(hist) > 1:
            # Calcola il rendimento percentuale di ogni mese
            hist['Rendimento'] = hist['Close'].pct_change() * 100
            # Filtra solo i mesi uguali a quello in cui ci troviamo ora
            rendimenti_mese = hist[hist.index.month == mese_corrente]['Rendimento'].dropna()
            
            if not rendimenti_mese.empty:
                media_storica = rendimenti_mese.mean()
                trend = "BULLISH 📈" if media_storica > 0 else "BEARISH 📉"
                testo_bias = f"STATISTICAL SEASONALITY: In the last 5 years, {ticker_pulito} has an average return of {media_storica:.2f}% during the month of {nome_mese} ({trend})."
                cache_stagionalita[ticker_pulito] = testo_bias
                return testo_bias
    except Exception:
        pass
        
    cache_stagionalita[ticker_pulito] = "STATISTICAL SEASONALITY: No reliable 5-year data available for this month."
    return cache_stagionalita[ticker_pulito]

def ottieni_notizie_top(ticker):
    ticker_pulito = ticker.split('.')[0]
    
    if ticker_pulito == "BTCUSD": ticker_pulito = "BTC-USD"
    elif ticker_pulito == "ETHUSD": ticker_pulito = "ETH-USD"
    elif len(ticker_pulito) == 6 and ticker_pulito.isalpha(): ticker_pulito = f"{ticker_pulito}=X"
        
    txt = f"LATEST FINANCIAL NEWS FOR {ticker_pulito}:\n"
    
    try:
        # FONTE 1: YAHOO FINANCE NEWS
        stock = yf.Ticker(ticker_pulito)
        yahoo_news = stock.news
        if yahoo_news:
            txt += "--- YAHOO FINANCE ---\n"
            for art in yahoo_news[:3]: 
                txt += f"- {art.get('title', '')}\n"
        
        # FONTE 2: NEWS API
        nome = stock.info.get('longName', ticker_pulito)
        newsapi = NewsApiClient(api_key=NEWS_API_KEY)
        query = f"{nome} OR {ticker_pulito}"
        top = newsapi.get_everything(q=query, language='en', sort_by='relevancy', page_size=5)
        
        if top['totalResults'] > 0:
            txt += "--- GLOBAL WEB ---\n"
            for art in top['articles']: 
                desc = str(art.get('description', ''))[:80]
                txt += f"- {art['title']} | {desc}...\n"
                
        return txt, ticker_pulito
    except Exception as e: 
        return txt + "No major news found.", ticker_pulito

def analizza_sentiment_ollama(ticker):
    global cache_analisi
    ora_attuale = time.time()

    if ticker in cache_analisi:
        sentiment, msg, scadenza = cache_analisi[ticker]
        if ora_attuale < scadenza:
            return sentiment, f"{msg} (⚡ CACHE)"

    notizie, ticker_pulito = ottieni_notizie_top(ticker)
    
    # 💡 NOVITÀ: Estraiamo la statistica e la fondiamo con le notizie!
    bias_statistico = ottieni_bias_stagionale(ticker_pulito)
    
    prompt = f"""
    Analyze the financial asset {ticker}. 
    1. {bias_statistico}
    2. {notizie}
    
    Based on BOTH the historical seasonality and current news, determine the direction.
    Reply STRICTLY with ONE word: POSITIVO, NEGATIVO or NEUTRO. 
    Then add 20 words max justification explaining if you relied more on news or on historical stats.
    """

    try:
        client = Groq(api_key=GROQ_API_KEY)
        res = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.1
        ).choices[0].message.content.strip().split('\n')
        
        testo_grezzo = res[0].strip().upper()
        
        if "POSITIVO" in testo_grezzo: sentiment = "POSITIVO"
        elif "NEGATIVO" in testo_grezzo: sentiment = "NEGATIVO"
        else: sentiment = "NEUTRO"
        
        motivazione = res[1] if len(res) > 1 else testo_grezzo
        messaggio = f"🤖 AI: {sentiment} | {motivazione}"
        
        cache_analisi[ticker] = (sentiment, messaggio, ora_attuale + DURATA_CACHE)
        return sentiment, messaggio
        
    except Exception as e:
        messaggio_errore = f"⚠️ ERRORE AI ({ticker}): {str(e)}"
        cache_analisi[ticker] = ("NEUTRO", messaggio_errore, ora_attuale + 60)
        return "NEUTRO", messaggio_errore