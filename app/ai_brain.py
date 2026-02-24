"""Modulo AI V11.0 - JSON Scoring (-10/+10) & Macro-Regime Globale (RSS)."""

import yfinance as yf
from groq import Groq
from newsapi import NewsApiClient
import feedparser
import time
import datetime
import os
import json
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")

cache_analisi = {}
cache_stagionalita = {}
cache_macro = {"testo": "", "scadenza": 0}
DURATA_CACHE = 600 # 10 minuti per le notizie

def ottieni_macro_globale():
    """Legge i feed RSS mondiali per capire se c'è guerra, crisi o pace."""
    global cache_macro
    if time.time() < cache_macro["scadenza"]:
        return cache_macro["testo"]
        
    url_feed = [
        "http://feeds.bbci.co.uk/news/world/rss.xml",
        "http://feeds.bbci.co.uk/news/business/rss.xml"
    ]
    
    macro_news = "GLOBAL MACRO CONTEXT (RSS Feeds):\n"
    try:
        for url in url_feed:
            feed = feedparser.parse(url)
            for entry in feed.entries[:4]: # Prende le prime 4 notizie per feed
                macro_news += f"- {entry.title}\n"
        
        cache_macro["testo"] = macro_news
        cache_macro["scadenza"] = time.time() + 1800 # Aggiorna la macro ogni 30 min
        return macro_news
    except Exception:
        return "GLOBAL MACRO CONTEXT: Unavailable. Assume normal market conditions."

def ottieni_bias_stagionale(ticker_pulito):
    """Calcola la media statistica degli ultimi 5 anni per il mese corrente."""
    mese_corrente = datetime.datetime.now().month
    nome_mese = datetime.datetime.now().strftime("%B")
    
    if ticker_pulito in cache_stagionalita:
        return cache_stagionalita[ticker_pulito]
        
    try:
        stock = yf.Ticker(ticker_pulito)
        hist = stock.history(period="5y", interval="1mo")
        if not hist.empty and len(hist) > 1:
            hist['Rendimento'] = hist['Close'].pct_change() * 100
            rendimenti_mese = hist[hist.index.month == mese_corrente]['Rendimento'].dropna()
            
            if not rendimenti_mese.empty:
                media_storica = rendimenti_mese.mean()
                trend = "BULLISH 📈" if media_storica > 0 else "BEARISH 📉"
                testo_bias = f"STATISTICAL SEASONALITY: In the last 5 years, {ticker_pulito} averages {media_storica:.2f}% in {nome_mese} ({trend})."
                cache_stagionalita[ticker_pulito] = testo_bias
                return testo_bias
    except Exception:
        pass
        
    cache_stagionalita[ticker_pulito] = "STATISTICAL SEASONALITY: No reliable 5-year data available."
    return cache_stagionalita[ticker_pulito]

def ottieni_notizie_top(ticker):
    ticker_pulito = ticker.split('.')[0]
    
    if ticker_pulito == "BTCUSD": ticker_pulito = "BTC-USD"
    elif ticker_pulito == "ETHUSD": ticker_pulito = "ETH-USD"
    elif len(ticker_pulito) == 6 and ticker_pulito.isalpha(): ticker_pulito = f"{ticker_pulito}=X"
        
    txt = f"LATEST FINANCIAL NEWS FOR {ticker_pulito}:\n"
    
    try:
        stock = yf.Ticker(ticker_pulito)
        yahoo_news = stock.news
        if yahoo_news:
            for art in yahoo_news[:3]: 
                txt += f"- {art.get('title', '')}\n"
        
        nome = stock.info.get('longName', ticker_pulito)
        newsapi = NewsApiClient(api_key=NEWS_API_KEY)
        query = f"{nome} OR {ticker_pulito}"
        top = newsapi.get_everything(q=query, language='en', sort_by='relevancy', page_size=4)
        
        if top['totalResults'] > 0:
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
        data = cache_analisi[ticker]
        if ora_attuale < data["scadenza"]:
            return data["sentiment"], data["score"], f"{data['msg']} (⚡ CACHE)"

    macro_contesto = ottieni_macro_globale()
    notizie_specifiche, ticker_pulito = ottieni_notizie_top(ticker)
    bias_statistico = ottieni_bias_stagionale(ticker_pulito)
    
    prompt = f"""
    You are an elite quantitative trading AI. Analyze {ticker} using the following data:
    
    1. {macro_contesto}
    2. {bias_statistico}
    3. {notizie_specifiche}
    
    STRICT RULES:
    - DISCARD irrelevant local news or generic crime.
    - HIGH PRIORITY: Wars, geopolitical tension, terrorist attacks, Central Bank rates, major CEO statements.
    - If there is a major global crisis (e.g. war), IGNORE seasonality. Crisis overrides history.
    - If global context is calm, use seasonality and specific news.
    
    Provide your output STRICTLY in valid JSON format with no markdown formatting and no extra text:
    {{
        "trend": "POSITIVO" or "NEGATIVO" or "NEUTRO",
        "score": <integer from -10 to 10. -10 is max crash, +10 is max pump. 0 is flat>,
        "macro_context": "<brief 10-word summary of the world situation>",
        "reason": "<brief 15-word reason for the score>"
    }}
    """

    try:
        client = Groq(api_key=GROQ_API_KEY)
        res = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.1,
            response_format={"type": "json_object"}
        ).choices[0].message.content.strip()
        
        dati_json = json.loads(res)
        
        sentiment = dati_json.get("trend", "NEUTRO").upper()
        score = int(dati_json.get("score", 0))
        motivo = dati_json.get("reason", "")
        
        messaggio = f"🤖 Score: {score}/10 | {motivo}"
        
        cache_analisi[ticker] = {
            "sentiment": sentiment, 
            "score": score, 
            "msg": messaggio, 
            "scadenza": ora_attuale + DURATA_CACHE
        }
        return sentiment, score, messaggio
        
    except Exception as e:
        messaggio_errore = f"⚠️ ERRORE AI ({ticker}): JSON Parse Failed"
        return "NEUTRO", 0, messaggio_errore