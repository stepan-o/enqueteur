from __future__ import annotations

from typing import Any, Dict, Iterable, List
import csv
import json

from .engine import DayResult
from .runner import AggregateMetrics


def print_day_summary(result: DayResult) -> None:
    ledger = result.ledger
    print("Day Summary")
    print(f"  Money delta: {ledger.money_delta:.2f}")
    print(f"  Brains produced: {ledger.brains_produced:.2f}")
    print(f"  Brains sold: {ledger.brains_sold:.2f}")
    print(f"  New workers: {ledger.new_workers}")
    print(f"  Workers lost: {ledger.workers_lost}")
    print(f"  Chaos: {ledger.chaos:.2f}")
    print("  Worker stat deltas:")
    for stat, delta in ledger.worker_stat_deltas.items():
        print(f"    {stat}: {delta:+.2f}")


def print_metrics(metrics: AggregateMetrics, label: str = "Metrics") -> None:
    print(label)
    for name, summary in metrics.metrics.items():
        print(
            f"  {name}: mean={summary.mean:.2f} std={summary.std:.2f} "
            f"p10={summary.p10:.2f} p50={summary.p50:.2f} p90={summary.p90:.2f}"
        )


def write_metrics_csv(path: str, metrics: AggregateMetrics) -> None:
    rows = metrics.to_rows()
    if not rows:
        return
    with open(path, "w", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_metrics_json(path: str, metrics: AggregateMetrics) -> None:
    with open(path, "w") as json_file:
        json.dump({"n": metrics.n, "metrics": metrics.to_rows()}, json_file, indent=2)


def write_table_csv(path: str, rows: Iterable[Dict[str, Any]]) -> None:
    rows_list = list(rows)
    if not rows_list:
        return
    with open(path, "w", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=list(rows_list[0].keys()))
        writer.writeheader()
        writer.writerows(rows_list)
