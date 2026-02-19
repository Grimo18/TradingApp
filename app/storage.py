"""Salvataggio metriche su JSON/CSV."""

import csv
import datetime
import json
from pathlib import Path


def save_metrics(details, benchmark_metrics, strategy_metrics, output_dir="reports"):
    """Salva metriche su JSON e CSV e ritorna i path creati."""

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
