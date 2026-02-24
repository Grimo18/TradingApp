"""
Backtesting engine integrating Lumibot with market data and metrics extraction.

Orchestrates the complete backtest lifecycle:
1. Data retrieval via yfinance
2. Strategy execution via Lumibot
3. Metrics computation and reporting
4. HTML/JSON export for analysis
"""

import datetime
import logging

from lumibot.backtesting import YahooDataBacktesting

from app.analytics import extract_strategy_metrics
from app.market_data import compute_market_metrics, get_market_snapshot, get_price_history
from app.report import generate_html_report
from app.storage import save_metrics
from app.strategy import STRATEGIES

logger = logging.getLogger(__name__)


def _safe_call(callbacks, name, *args):
    """
    Safely invoke a callback function if it exists in the callback dictionary.
    
    Defensive pattern: Silently ignores missing callbacks instead of raising errors.
    This allows graceful degradation if the UI fails to register callbacks.
    
    Args:
        callbacks (dict): Dictionary of callback functions.
        name (str): Callback name (key).
        *args: Arguments to pass to the callback.
    """
    callback = callbacks.get(name)
    if callback:
        callback(*args)


def esegui_backtest(ticker, capitale, start, end, nome_strategia, callbacks):
    """
    Execute a complete strategy backtest with market context and reporting.
    
    Workflow:
    1. Validate strategy selection
    2. Retrieve market data for the period
    3. Execute Lumibot backtest
    4. Extract performance metrics
    5. Generate HTML report and metric files
    6. Notify UI via callbacks
    
    Args:
        ticker (str): Asset symbol to backtest.
        capitale (float): Initial capital in USD.
        start (datetime.datetime): Backtest start date/time.
        end (datetime.datetime): Backtest end date/time.
        nome_strategia (str): Strategy name from STRATEGIES registry.
        callbacks (dict): UI callback functions:
            - status: Logging messages
            - progress_start/stop: Progress bar control
            - market: Market snapshot data
            - running: Execution state
            - details: Test metadata
            - metrics: Benchmark metrics
            - report: HTML report path
            - chart: Price chart data
            - strategy_metrics: Performance metrics
            - metrics_files: Generated file paths
    
    Returns:
        None: Communication via callbacks only.
    """
        nome_strategia: nome della strategia da usare (chiave del dizionario STRATEGIES)
        callbacks: dict con chiavi "status", "progress_start", "progress_stop",
                   "market", "running", "details", "metrics", "report", "chart",
                   "strategy_metrics", "metrics_files".
    """

    # Seleziona la classe strategia dal dizionario
    if nome_strategia not in STRATEGIES:
        _safe_call(callbacks, "status", f"Strategia '{nome_strategia}' non trovata")
        _safe_call(callbacks, "running", False)
        return

    StrategyClass = STRATEGIES[nome_strategia]

    _safe_call(callbacks, "running", True)
    details = {"ticker": ticker, "capital": capitale, "start": str(start.date()), "end": str(end.date())}
    _safe_call(callbacks, "details", details)
    _safe_call(callbacks, "status", "Simulazione in corso...")
    _safe_call(callbacks, "progress_start")

    try:
        snapshot = get_market_snapshot(ticker)
        _safe_call(callbacks, "market", snapshot)
    except Exception as exc:
        logger.warning("Snapshot mercato non disponibile: %s", exc)

    metrics = None
    history = None
    try:
        history = get_price_history(ticker, start=start.date(), end=end.date())
        metrics = compute_market_metrics(history["Close"])
        _safe_call(callbacks, "metrics", metrics)
    except Exception as exc:
        logger.warning("Metriche mercato non disponibili: %s", exc)

    if history is not None:
        close_series = history["Close"].dropna().tail(220)
        _safe_call(callbacks, "chart", close_series.tolist())

    try:
        # Lumibot richiede datetime.datetime per backtesting_start e backtesting_end
        result = StrategyClass.backtest(
            YahooDataBacktesting,
            start,  # ora è datetime.datetime
            end,    # ora è datetime.datetime
            parameters={"symbol": ticker},
            show_tearsheet=True,
            initial_cash=capitale,
        )
        strategy_metrics = extract_strategy_metrics(result)
        if strategy_metrics:
            _safe_call(callbacks, "strategy_metrics", strategy_metrics)

        if metrics or strategy_metrics:
            report_path = generate_html_report(details, metrics or {}, strategy_metrics)
            _safe_call(callbacks, "report", report_path)

            metrics_files = save_metrics(details, metrics or {}, strategy_metrics)
            _safe_call(callbacks, "metrics_files", metrics_files)
        _safe_call(callbacks, "status", "Completato!")
    except Exception as exc:
        logger.exception("Errore nel backtest")
        _safe_call(callbacks, "status", f"Errore: {exc}")
    finally:
        _safe_call(callbacks, "progress_stop")
        _safe_call(callbacks, "running", False)
