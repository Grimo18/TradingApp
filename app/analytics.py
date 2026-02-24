"""
Strategy performance metric extraction from Lumibot backtest results.

Provides robust parsing of heterogeneous result structures returned by
different strategy engines and backtesting frameworks.
"""


def _is_number(value):
    """
    Type guard to identify valid numeric values (excluding booleans).
    
    Args:
        value: Value to test.
    
    Returns:
        bool: True if value is int or float (not bool), False otherwise.
    """
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _get_first(stats, keys):
    """
    Extract the first available numeric value from a list of candidate keys.
    
    Resilience pattern: Different backtesting engines use different metric names.
    This function tries multiple naming conventions and returns the first match.
    
    Args:
        stats (dict): Statistics dictionary from backtest result.
        keys (list): Ordered list of candidate key names to try.
    
    Returns:
        float or None: First numeric value found, or None if no matches.
    """
    for key in keys:
        if key in stats and _is_number(stats[key]):
            return float(stats[key])
    return None


def extract_strategy_metrics(result):
    """
    Robustly extract strategy performance metrics from Lumibot results.
    
    Handles multiple result structure formats:
    1. result.stats (attribute access)
    2. result['stats'] (dict access)
    3. Fallback to analyzing the result dict directly
    
    This is a defensive parsing approach for compatibility across framework versions.
    
    Args:
        result: Backtest result object or dict from Lumibot.
    
    Returns:
        dict: Performance metrics with standardized keys:
            - total_return: Cumulative return as decimal
            - cagr: Compound Annual Growth Rate
            - max_drawdown: Peak-to-trough decline
            - sharpe: Risk-adjusted return ratio
            - win_rate: Percentage of winning trades
            - trades: Total number of trades executed
    """

    if result is None:
        return {}

    stats = None
    if hasattr(result, "stats") and isinstance(result.stats, dict):
        stats = result.stats
    elif isinstance(result, dict):
        for key in ("stats", "metrics", "analysis", "summary"):
            value = result.get(key)
            if isinstance(value, dict):
                stats = value
                break
        if stats is None:
            stats = result

    if not isinstance(stats, dict):
        return {}

    metrics = {
        "total_return": _get_first(stats, ["Total Return", "total_return", "return", "Cumulative Return"]),
        "cagr": _get_first(stats, ["CAGR", "cagr", "annual_return"]),
        "max_drawdown": _get_first(stats, ["Max Drawdown", "max_drawdown", "max_dd"]),
        "sharpe": _get_first(stats, ["Sharpe", "Sharpe Ratio", "sharpe"]),
        "win_rate": _get_first(stats, ["Win Rate", "win_rate"]),
        "trades": _get_first(stats, ["Trades", "Total Trades", "trades"]),
    }

    return {key: value for key, value in metrics.items() if value is not None}
