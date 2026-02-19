"""Motore di backtest e integrazione con Lumibot."""

import datetime
import logging

from lumibot.backtesting import YahooDataBacktesting

from app.analytics import extract_strategy_metrics
from app.market_data import compute_market_metrics, get_market_snapshot, get_price_history
from app.report import generate_html_report
from app.storage import save_metrics
from app.strategy import ATHDipStrategy

logger = logging.getLogger(__name__)


def _safe_call(callbacks, name, *args):
    callback = callbacks.get(name)
    if callback:
        callback(*args)


def esegui_backtest(ticker, capitale, callbacks):
    """Esegue il backtest e notifica la UI tramite callback.

    callbacks: dict con chiavi "status", "progress_start", "progress_stop",
    "market", "running", "details", "metrics", "report", "chart",
    "strategy_metrics", "metrics_files".
    """

    start = datetime.date(2020, 1, 1)
    end = datetime.date.today()

    _safe_call(callbacks, "running", True)
    details = {"ticker": ticker, "capital": capitale, "start": start, "end": end}
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
        history = get_price_history(ticker, start=start, end=end)
        metrics = compute_market_metrics(history["Close"])
        _safe_call(callbacks, "metrics", metrics)
    except Exception as exc:
        logger.warning("Metriche mercato non disponibili: %s", exc)

    if history is not None:
        close_series = history["Close"].dropna().tail(220)
        _safe_call(callbacks, "chart", close_series.tolist())

    try:
        result = ATHDipStrategy.backtest(
            YahooDataBacktesting,
            start,
            end,
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
