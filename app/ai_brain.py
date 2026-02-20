"""Modulo AI V4.3 - Sistema di Cache delle Analisi."""

import yfinance as yf
from groq import Groq
from newsapi import NewsApiClient
import time

GROQ_API_KEY = "NULL"
NEWS_API_KEY = "NULL"

# --- SISTEMA CACHE ---
cache_analisi = {}
DURATA_CACHE = 600 # 10 minuti (600 secondi)

def ottieni_notizie_top(ticker):
    ticker_pulito = ticker.split('.')[0]
    try:
        stock = yf.Ticker(ticker_pulito)
        nome = stock.info.get('longName', ticker_pulito)
        newsapi = NewsApiClient(api_key=NEWS_API_KEY)
        top = newsapi.get_everything(q=nome, language='en', sort_by='relevancy', page_size=5)
        txt = f"SOURCES FOR {nome.upper()}:\n"
        if top['totalResults'] > 0:
            for art in top['articles']: txt += f"- {art['title']}\n"
        return txt
    except: return "No major news found."

def analizza_sentiment_ollama(ticker):
    global cache_analisi
    ora_attuale = time.time()

    # CONTROLLO CACHE
    if ticker in cache_analisi:
        verdetto, msg, scadenza = cache_analisi[ticker]
        if ora_attuale < scadenza:
            return verdetto, f"{msg} (⚡ CACHE)"

    notizie = ottieni_notizie_top(ticker)
    prompt = f"Analyze sentiment for {ticker}: {notizie}. Reply: POSITIVO/NEGATIVO/NEUTRO + 15 words max."

    try:
        client = Groq(api_key=GROQ_API_KEY)
        res = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.1
        ).choices[0].message.content.strip().split('\n')
        
        sentiment = res[0].strip().upper()
        motivazione = res[1] if len(res) > 1 else "Market analysis completed."
        verdetto = ("NEGATIVO" not in sentiment)
        messaggio = f"🤖 AI: {sentiment} | {motivazione}"
        
        # Salviamo in cache
        cache_analisi[ticker] = (verdetto, messaggio, ora_attuale + DURATA_CACHE)
        return verdetto, messaggio
    except:
        return True, "⚠️ Errore AI, procedo con analisi tecnica."