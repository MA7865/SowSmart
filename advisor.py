import json
import sys
from pathlib import Path

import pandas as pd

from config import DISTRICT_PROVINCE, ModelConfig, WINDOWS
from sowing_model import (
    calibrate_gdd_total,
    recommend,
    scenario_table,
    summarize,
)

WHEAT_ADVISOR_DIR = Path(__file__).resolve().parent / "wheat-advisor"
sys.path.insert(0, str(WHEAT_ADVISOR_DIR))
import sim_core as sc


YEARS = range(2000, 2025)
RESULTS_DIR = WHEAT_ADVISOR_DIR / "results"


def _json_value(value):
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, dict):
        return {str(k): _json_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_value(v) for v in value]
    return value


def main():
    RESULTS_DIR.mkdir(exist_ok=True)
    results = {}

    for name in DISTRICT_PROVINCE:
        print(f"\nProcessing {name}...")

        weather = sc.load(name)
        cfg = ModelConfig()
        cfg.gdd_total = calibrate_gdd_total(weather, cfg=cfg)
        window = WINDOWS[DISTRICT_PROVINCE[name]]

        rec = recommend(weather, window, cfg, years=YEARS)
        if rec.empty:
            raise ValueError(f"{name}: no usable season results were produced.")

        summary = summarize(rec, window, cfg)
        scenarios = scenario_table(weather, window, cfg)

        rec.to_csv(RESULTS_DIR / f"{name}_per_year.csv", index=False)
        scenarios.to_csv(RESULTS_DIR / f"{name}_scenarios.csv", index=False)

        results[name] = {
            "province": DISTRICT_PROVINCE[name],
            "gdd_total": round(cfg.gdd_total, 2),
            "summary": _json_value(summary),
            "scenarios": _json_value(scenarios.to_dict(orient="records")),
        }

        print(f"{name}: calibrated gdd_total = {cfg.gdd_total:.0f}")
        print(
            f"  median days to maturity: "
            f"{summary['median_days_to_maturity']:.1f} "
            f"(target {cfg.ref_days_to_maturity[0]}-{cfg.ref_days_to_maturity[1]})"
        )
        print(
            f"  median recommendation: {summary['median']} "
            f"(acceptable through {summary['median_latest_ok']})"
        )
        print(f"  yearly rows: {len(rec)}")
        print(rec[["year", "best_date", "ok_from", "ok_to"]].to_string(index=False))

    output_path = WHEAT_ADVISOR_DIR / "results.json"
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\nSaved results to {output_path}")
    print(f"Saved per-year and scenario CSV files to {RESULTS_DIR}")


if __name__ == "__main__":
    main()
