"""
HTML report generation for backtest results and live trading performance.

Produces institutional-grade PDF-ready HTML reports with embedded styling,
suitable for fund presentations and regulatory documentation.
"""

import datetime
from pathlib import Path


def _format_percent(value):
    """
    Format a decimal value as a percentage string.
    
    Args:
        value: Numeric value or None.
    
    Returns:
        str: Formatted percentage (e.g., "12.34%") or "-" if invalid.
    """
    if isinstance(value, (int, float)):
        return f"{value:.2%}"
    return "-"


def _format_number(value):
    """
    Format a numeric value with thousands separators and 2 decimal places.
    
    Args:
        value: Numeric value or None.
    
    Returns:
        str: Formatted number (e.g., "1,234.56") or "-" if invalid.
    """
    if isinstance(value, (int, float)):
        return f"{value:,.2f}"
    return "-"


def generate_html_report(details, benchmark_metrics, strategy_metrics=None, output_dir="reports"):
    """
    Generate a minimalist HTML report of backtest/trading results.
    
    Creates a self-contained HTML file with inline CSS suitable for
    email distribution and regulatory submission (no external dependencies).
    
    Args:
        details (dict): Test metadata (ticker, capital, period dates).
        benchmark_metrics (dict): Market benchmarks for comparison.
        strategy_metrics (dict, optional): Trading strategy results.
        output_dir (str): Directory for report output.
    
    Returns:
        str: Absolute path to generated HTML file.
    """

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = Path(output_dir) / f"report_{timestamp}.html"

    strategy_metrics = strategy_metrics or {}

    html = f"""<!DOCTYPE html>
<html lang=\"it\">
<head>
  <meta charset=\"UTF-8\" />
  <title>Trading Algo Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; background: #0b0f14; color: #e2e8f0; margin: 0; }}
    .wrap {{ max-width: 860px; margin: 24px auto; padding: 24px; }}
    .card {{ background: #111827; border: 1px solid #1f2a3a; border-radius: 14px; padding: 18px 20px; margin-bottom: 14px; }}
    h1 {{ margin: 0 0 6px 0; font-size: 24px; }}
    h2 {{ margin: 0 0 8px 0; font-size: 16px; color: #9fb3c8; }}
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
    .item span {{ color: #9fb3c8; }}
  </style>
</head>
<body>
  <div class=\"wrap\">
    <div class=\"card\">
      <h1>Trading Algo Dashboard</h1>
      <h2>Report simulazione</h2>
      <div class=\"grid\">
        <div class=\"item\"><span>Ticker</span>: {details.get("ticker", "-")}</div>
        <div class="item"><span>Capital</span>: {details.get("capital", "-")}</div>
        <div class="item"><span>Period</span>: {details.get("start", "-")} -> {details.get("end", "-")}</div>
        <div class="item"><span>Generated</span>: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}</div>
      </div>
    </div>
    <div class=\"card\">
      <h2>Market Metrics (Benchmark)</h2>
      <div class=\"grid\">
        <div class="item"><span>Total Return</span>: {_format_percent(benchmark_metrics.get("total_return"))}</div>
        <div class="item"><span>CAGR</span>: {_format_percent(benchmark_metrics.get("cagr"))}</div>
        <div class="item"><span>Max Drawdown</span>: {_format_percent(benchmark_metrics.get("max_drawdown"))}</div>
        <div class="item"><span>Volatility</span>: {_format_percent(benchmark_metrics.get("volatility"))}</div>
      </div>
    </div>
    <div class=\"card\">
      <h2>Strategy Metrics</h2>
      <div class=\"grid\">
        <div class="item"><span>Total Return</span>: {_format_percent(strategy_metrics.get("total_return"))}</div>
        <div class=\"item\"><span>CAGR</span>: {_format_percent(strategy_metrics.get("cagr"))}</div>
        <div class=\"item\"><span>Max Drawdown</span>: {_format_percent(strategy_metrics.get("max_drawdown"))}</div>
        <div class=\"item\"><span>Sharpe</span>: {_format_number(strategy_metrics.get("sharpe"))}</div>
        <div class=\"item\"><span>Win Rate</span>: {_format_percent(strategy_metrics.get("win_rate"))}</div>
        <div class=\"item\"><span>Trades</span>: {_format_number(strategy_metrics.get("trades"))}</div>
      </div>
    </div>
  </div>
</body>
</html>
"""

    file_path.write_text(html, encoding="utf-8")
    return str(file_path)
