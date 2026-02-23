"""Modulo AI V6.1 - Doppia Fonte Notizie (NewsAPI + Yahoo News)."""

import yfinance as yf
from groq import Groq
from newsapi import NewsApiClient
import time
import os
from dotenv import load_dotenv

# Carica variabili da .env
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")

cache_analisi = {}
DURATA_CACHE = 600 # 10 minuti

def ottieni_notizie_top(ticker):
    ticker_pulito = ticker.split('.')[0]
    
    if ticker_pulito == "BTCUSD": ticker_pulito = "BTC-USD"
    elif ticker_pulito == "ETHUSD": ticker_pulito = "ETH-USD"
    elif len(ticker_pulito) == 6 and ticker_pulito.isalpha(): ticker_pulito = f"{ticker_pulito}=X"
        
    txt = f"LATEST FINANCIAL NEWS FOR {ticker_pulito}:\n"
    
    try:
        # FONTE 1: YAHOO FINANCE NEWS (Velocissime, finanziarie, gratuite)
        stock = yf.Ticker(ticker_pulito)
        yahoo_news = stock.news
        if yahoo_news:
            txt += "--- FROM YAHOO FINANCE ---\n"
            for art in yahoo_news[:3]: # Prende le ultime 3 notizie fresche
                titolo = art.get('title', '')
                txt += f"- {titolo}\n"
        
        # FONTE 2: NEWS API (Notizie dal web mondiale)
        nome = stock.info.get('longName', ticker_pulito)
        newsapi = NewsApiClient(api_key=NEWS_API_KEY)
        query_potenziata = f"{nome} OR {ticker_pulito}"
        top = newsapi.get_everything(q=query_potenziata, language='en', sort_by='relevancy', page_size=5)
        
        if top['totalResults'] > 0:
            txt += "--- FROM GLOBAL WEB ---\n"
            for art in top['articles']: 
                desc = str(art.get('description', ''))[:80]
                txt += f"- {art['title']} | {desc}...\n"
                
        return txt
    except Exception as e: 
        return txt + "No major news found."

def analizza_sentiment_ollama(ticker):
    global cache_analisi
    ora_attuale = time.time()

    if ticker in cache_analisi:
        verdetto, msg, scadenza = cache_analisi[ticker]
        if ora_attuale < scadenza:
            return verdetto, f"{msg} (⚡ CACHE)"

    notizie = ottieni_notizie_top(ticker)
    prompt = f"Analyze sentiment for {ticker} based on these news: {notizie}. Is it strongly positive for long-term growth? Reply strictly: POSITIVO/NEGATIVO/NEUTRO + 20 words max justification."

    try:
        client = Groq(api_key=GROQ_API_KEY)
        res = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.1
        ).choices[0].message.content.strip().split('\n')
        
        sentiment = res[0].strip().upper()
        motivazione = res[1] if len(res) > 1 else "Market analysis completed."
        
        verdetto = ("POSITIVO" in sentiment)
        messaggio = f"🤖 AI: {sentiment} | {motivazione}"
        
        cache_analisi[ticker] = (verdetto, messaggio, ora_attuale + DURATA_CACHE)
        return verdetto, messaggio
        
    except Exception as e:
        # Ora l'errore VERO verrà stampato nel terminale!
        messaggio_errore = f"⚠️ ERRORE AI ({ticker}): {str(e)}"
        cache_analisi[ticker] = (True, messaggio_errore, ora_attuale + 60)
        return True, messaggio_errore