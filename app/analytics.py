"""Estrazione metriche strategia da risultati Lumibot."""


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _get_first(stats, keys):
    for key in keys:
        if key in stats and _is_number(stats[key]):
            return float(stats[key])
    return None


def extract_strategy_metrics(result):
    """Estrae metriche della strategia in modo robusto.

    Ritorna un dict con chiavi standard se disponibili.
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
