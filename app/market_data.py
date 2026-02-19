"""Recupero dati di mercato con yfinance per la UI."""

import datetime
from pathlib import Path

import pandas as pd
import yfinance as yf


def _get_cache_path(ticker, cache_dir):
    safe_ticker = ticker.replace("/", "_").replace("\\", "_")
    return Path(cache_dir) / f"{safe_ticker}.csv"


def get_price_history(ticker, start, end, cache_dir="cache"):
    """Carica lo storico prezzi con cache su disco."""

    cache_path = _get_cache_path(ticker, cache_dir)
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    if cache_path.exists():
        cached = pd.read_csv(cache_path, parse_dates=["Date"], index_col="Date")
        if not cached.empty:
            last_date = cached.index.max().date()
            end_check = end - datetime.timedelta(days=1)
            if last_date >= end_check:
                return cached.loc[str(start):str(end)]

    data = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
    if data.empty:
        raise ValueError("Dati di mercato non disponibili")

    data.to_csv(cache_path)
    return data


def compute_market_metrics(close_prices):
    """Calcola metriche base del mercato.

    Output: dict con rendimento totale, CAGR, max drawdown e volatilita.
    """

    close = close_prices.dropna()
    if close.empty:
        raise ValueError("Serie prezzi vuota")

    daily_returns = close.pct_change().dropna()
    if daily_returns.empty:
        raise ValueError("Ritorni insufficienti per le metriche")

    total_return = (close.iloc[-1] / close.iloc[0]) - 1

    days = (close.index[-1] - close.index[0]).days
    years = max(days / 365.25, 1e-6)
    cagr = (close.iloc[-1] / close.iloc[0]) ** (1 / years) - 1

    cumulative = (1 + daily_returns).cumprod()
    running_max = cumulative.cummax()
    drawdown = (cumulative / running_max) - 1
    max_drawdown = float(drawdown.min())

    volatility = float(daily_returns.std() * (252 ** 0.5))

    return {
        "total_return": float(total_return),
        "cagr": float(cagr),
        "max_drawdown": max_drawdown,
        "volatility": volatility,
    }


def get_market_snapshot(ticker):
    """Restituisce uno snapshot del mercato per il ticker richiesto.

    Output: dict con ultimo prezzo, ritorni e volatilita annualizzata.
    """

    end = datetime.date.today()
    start = end - datetime.timedelta(days=365)

    data = get_price_history(ticker, start=start, end=end)
    close = data["Close"].dropna()
    last_close = float(close.iloc[-1])
    first_close = float(close.iloc[0])

    daily_returns = close.pct_change().dropna()
    if daily_returns.empty:
        raise ValueError("Ritorni insufficienti per le metriche")

    one_year_return = (last_close / first_close) - 1
    volatility = float(daily_returns.std() * (252 ** 0.5))

    return {
        "last_close": last_close,
        "one_year_return": one_year_return,
        "volatility": volatility,
        "last_update": end,
    }
