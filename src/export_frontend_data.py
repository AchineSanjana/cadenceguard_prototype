"""
Export all model predictions, metrics, and comparison stats into a consolidated
JSON file for the AquaGuard Component C frontend.
"""

import json
from pathlib import Path
import pandas as pd
import numpy as np

from src import config, data_loader, figures

def export_all():
    output_path = config.PROJECT_ROOT / "frontend" / "data" / "app_data.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    full_df = data_loader.load_variant("full")
    pump_ids = data_loader.list_pumps(full_df)

    pumps_data = {}
    for pid in pump_ids:
        scored = figures.score_full_timeline("variant3", pid)
        if scored.empty:
            continue
        
        # Subsample or take full timeline (every 2nd or 3rd hour for snappy charts, or full)
        # Let's take every point or round values for clean JSON
        records = []
        for _, row in scored.iterrows():
            records.append({
                "t": str(row["timestamp"])[:16],
                "h": round(float(row["health_score"]), 4),
                "al": str(row["alert_level"]),
                "ra": round(float(row["RUL_days"]), 2),
                "rp": round(float(row["RUL_days_predicted"]), 2),
                "fm_true": str(row["failure_mode_label"]),
                "fm_pred": str(row["failure_mode_predicted"])
            })
        
        latest = scored.iloc[-1]
        pumps_data[pid] = {
            "id": pid,
            "display_name": f"Engine {pid.split('_')[-1]} ({pid})",
            "timeline": records,
            "latest": {
                "health_score": round(float(latest["health_score"]), 4),
                "alert_level": str(latest["alert_level"]),
                "rul_actual": round(float(latest["RUL_days"]), 1),
                "rul_predicted": round(float(latest["RUL_days_predicted"]), 1),
                "failure_mode_predicted": str(latest["failure_mode_predicted"]),
                "failure_mode_true": str(latest["failure_mode_label"]),
                "timestamp": str(latest["timestamp"])[:16]
            }
        }

    # Load metrics
    metrics = {}
    for v in ["variant1", "variant2", "variant3"]:
        m_file = config.RESULTS_DIR / f"{v}_metrics.json"
        if m_file.exists():
            with open(m_file) as f:
                metrics[v] = json.load(f)

    # Load comparison
    comp_file = config.RESULTS_DIR / "variant_comparison.csv"
    comparison = []
    if comp_file.exists():
        comp_df = pd.read_csv(comp_file)
        comparison = comp_df.to_dict(orient="records")

    # Load significance
    sig_file = config.RESULTS_DIR / "significance_tests.json"
    significance = {}
    if sig_file.exists():
        with open(sig_file) as f:
            significance = json.load(f)

    full_payload = {
        "pumps": pumps_data,
        "metrics": metrics,
        "comparison": comparison,
        "significance": significance,
        "meta": {
            "dataset_name": "Synthetic Rehearsal (Phase A / NASA C-MAPSS Schema)",
            "active_variant": "variant3",
            "variant_label": config.VARIANT_LABELS["variant3"]
        }
    }

    with open(output_path, "w") as f:
        json.dump(full_payload, f, indent=2)

    print(f"Successfully exported data payload to {output_path} ({output_path.stat().st_size} bytes)")

if __name__ == "__main__":
    export_all()
