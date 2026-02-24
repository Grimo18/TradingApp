"""
Market data acquisition and caching module using Yahoo Finance.

Implements a disk-based caching strategy to minimize API calls and
disk I/O while computing institutional-grade market metrics including
CAGR, max drawdown, and annualized volatility.

Cache Strategy:
- First call: Download from Yahoo Finance, persist to disk
- Subsequent calls: Check cache freshness (end_date >= requested_end)
- If cache extends to requested period, return cached data (0 API calls)
- Otherwise: Download fresh data and update cache
"""

import datetime
from pathlib import Path

import pandas as pd
import yfinance as yf


def _get_cache_path(ticker, cache_dir):
    """
    Generate a sanitized cache file path for a given ticker symbol.
    
    Removes illegal characters (/, \) from ticker names to ensure
    filesystem compatibility across Windows and Unix systems.
    
    Args:
        ticker (str): Raw ticker symbol (e.g., "EURUSD", "BTC/USD").
        cache_dir (str): Root directory for cached data files.
    
    Returns:
        Path: Pathlib Path object pointing to the cached CSV file.
    """
    safe_ticker = ticker.replace("/", "_").replace("\\", "_")
    return Path(cache_dir) / f"{safe_ticker}.csv"


def get_price_history(ticker, start, end, cache_dir="cache"):
    """
    Retrieve historical price data with intelligent disk caching.
    
    Strategy:
    1. Check if valid cached data exists on disk
    2. If cache is complete (end_date >= requested_end), return cached data
    3. Otherwise, download fresh data from Yahoo Finance and update cache
    
    This minimizes API calls and disk I/O while maintaining data freshness.
    
    Args:
        ticker (str): Asset symbol (e.g., "SPY", "EURUSD").
        start (datetime.date or datetime.datetime): Period start date.
        end (datetime.date or datetime.datetime): Period end date.
        cache_dir (str): Directory for storing cached price data.
    
    Returns:
        pd.DataFrame: OHLCV data with DatetimeIndex, from start to end.
    
    Raises:
        ValueError: If no market data is available for the given ticker/period.
    """

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
        raise ValueError("Market data not available")

    data.to_csv(cache_path)
    return data


def compute_market_metrics(close_prices):
    """
    Compute institutional-grade market metrics from a price series.
    
    Calculates key performance indicators used in fund prospectuses and
    regulatory filings:
    - Total Return: Cumulative price appreciation over period
    - CAGR: Compound Annual Growth Rate (annualized return)
    - Max Drawdown: Largest peak-to-trough decline (risk metric)
    - Volatility: Annualized standard deviation of daily returns
    
    Args:
        close_prices (pd.Series): Daily closing prices indexed by date.
    
    Returns:
        dict: Metrics dictionary with keys:
            - total_return (float): Percentage return over full period
            - cagr (float): Annualized compound growth rate
            - max_drawdown (float): Maximum cumulative drawdown (negative)
            - volatility (float): Annualized volatility (252 trading days)
    
    Raises:
        ValueError: If less than 2 price points or no valid returns data.
    """

    close = close_prices.dropna()
    if close.empty:
        raise ValueError("Empty price series")

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
    """
    Generate a point-in-time market snapshot for the given ticker.
    
    Useful for real-time UI updates and decision-making context.
    Covers the trailing 365-day window to provide annual performance context.
    
    Args:
        ticker (str): Asset symbol.
    
    Returns:
        dict: Snapshot data with keys:
            - last_close (float): Most recent closing price
            - one_year_return (float): Annual return percentage
            - volatility (float): Annualized volatility
            - last_update (datetime.date): Data freshness timestamp
    
    Raises:
        ValueError: If insufficient historical data (< 2 data points).
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
