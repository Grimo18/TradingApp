"""
Metrics persistence layer for strategy backtests and live trading results.

Exports performance data in multiple formats (JSON, CSV) for compatibility
with external analytics platforms, risk management systems, and compliance audits.
"""

import csv
import datetime
import json
from pathlib import Path


def save_metrics(details, benchmark_metrics, strategy_metrics, output_dir="reports"):
    """
    Persist trading metrics to both JSON (structured) and CSV (tabular) formats.
    
    Creates timestamped output files for easy historical comparison and archival.
    Useful for regression testing strategies across market regimes.
    
    Args:
        details (dict): Metadata about the backtest/trade session
            (ticker, capital, start_date, end_date, etc.)
        benchmark_metrics (dict): Market benchmark metrics
            (total_return, CAGR, max_drawdown, volatility)
        strategy_metrics (dict): Trading strategy performance metrics
            (Sharpe ratio, win_rate, max_drawdown, etc.)
        output_dir (str): Directory for report output.
    
    Returns:
        dict: Paths to generated files
            - json (str): Path to JSON file
            - csv (str): Path to CSV file
    """

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    json_path = Path(output_dir) / f"metrics_{timestamp}.json"
    csv_path = Path(output_dir) / f"metrics_{timestamp}.csv"

    payload = {
        "details": details,
        "benchmark": benchmark_metrics or {},
        "strategy": strategy_metrics or {},
    }

    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["category", "metric", "value"])
        for category, metrics in ("benchmark", benchmark_metrics), ("strategy", strategy_metrics):
            if not metrics:
                continue
            for name, value in metrics.items():
                writer.writerow([category, name, value])

    return {"json": str(json_path), "csv": str(csv_path)}
