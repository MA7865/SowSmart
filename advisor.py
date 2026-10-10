"""Root entry point for Person C's advisor module.

The working project lives in ./wheat-advisor, where results.json is stored.
This wrapper loads that implementation so imports from the repo root also work.
"""

from __future__ import annotations
from sowing_model import (
    calibrate_gdd_total,
    recommend,
    scenario_table,
    score_all_dates,
    sensitivity,
    summarize,
)

import importlib.util
import os
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from config import DISTRICT_PROVINCE, ModelConfig, WINDOWS
from sowing_model import (
    calibrate_gdd_total,
    recommend,
    scenario_table,
    sensitivity,
    summarize,
)

WHEAT_ADVISOR_DIR = Path(__file__).resolve().parent / "wheat-advisor"
sys.path.insert(0, str(WHEAT_ADVISOR_DIR))
import sim_core as sc


YEARS = range(2000, 2025)
RESULTS_DIR = WHEAT_ADVISOR_DIR / "results"
PROVINCE_TARGET_DAYS = {
    "punjab": 140,
    "sindh": 128,
}
# Punjab ~140 d from Rehman et al. 2021 (Faisalabad), Sindh ~128 d from
# Sial et al. 2005 (Tando Jam).


def _json_value(value):
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, dict):
        return {str(k): _json_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_value(v) for v in value]
    return value


def _make_chart(name, rec, scenarios):
    chart_rec = rec.copy()
    for column in ("best_date", "ok_from", "ok_to"):
        chart_rec[column] = pd.to_datetime(chart_rec[column])

    fig, ax = plt.subplots(figsize=(10, 5.5))
    years = chart_rec["year"].to_numpy()
    ax.fill_between(
        years,
        chart_rec["ok_from"].dt.dayofyear,
        chart_rec["ok_to"].dt.dayofyear,
        color="#9ecae1",
        alpha=0.55,
        label="acceptable range",
    )
    ax.plot(
        years,
        chart_rec["best_date"].dt.dayofyear,
        "o-",
        color="#2171b5",
        label="best date",
    )
    for scenario, color in (
        ("+1.0C", "#e6550d"),
        ("+2.0C", "#a63603"),
        ("+3.0C", "#7f0000"),
    ):
        row = scenarios.loc[scenarios["scenario"] == scenario]
        if not row.empty:
            day = pd.to_datetime(
                row.iloc[0]["median"], format="%d %b"
            ).dayofyear
            ax.axhline(
                day,
                color=color,
                linestyle="--",
                linewidth=1.5,
                label=f"{scenario} median",
            )

    ax.set_title(f"{name}: wheat sowing recommendations by year")
    ax.set_xlabel("Sowing year")
    ax.set_ylabel("Calendar day of year")
    ax.set_xticks(years[::2])
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / f"{name}_sowing_dates.png", dpi=150)
    plt.close(fig)


def main():
    RESULTS_DIR.mkdir(exist_ok=True)
    results = {}
    summary_rows = []

    for name in DISTRICT_PROVINCE:
        print(f"\nProcessing {name}...")

        weather = sc.load(name)
        cfg = ModelConfig()
        province = DISTRICT_PROVINCE[name]
        cfg.gdd_total = calibrate_gdd_total(
            weather,
            sow_mmdd="11-18",
            target_days=PROVINCE_TARGET_DAYS[province],
            cfg=cfg,
        )
        window = WINDOWS[province]

        rec = recommend(weather, window, cfg, years=YEARS)
        if rec.empty:
            raise ValueError(f"{name}: no usable season results were produced.")

        summary = summarize(rec, window, cfg)
        scenarios = scenario_table(weather, window, cfg)
        fixed_sensitivity = sensitivity(
            weather,
            window,
            cfg,
            heat_thresholds=(33, 34, 35),
            window_starts=("11-01",),
            warm_weights=(0.1, 0.5, 1.0),
        )
        fixed_sensitivity.to_csv(
            RESULTS_DIR / f"{name}_sensitivity_fixedwindow.csv",
            index=False,
        )
        _make_chart(name, rec, scenarios)

        rec.to_csv(RESULTS_DIR / f"{name}_per_year.csv", index=False)
        date_scores = score_all_dates(
            weather,
            window,
            cfg,
            years=YEARS,
        )
        date_scores.to_csv(
            RESULTS_DIR / f"{name}_date_scores.csv",
            index=False,
        )
        scenarios.to_csv(RESULTS_DIR / f"{name}_scenarios.csv", index=False)

        results[name] = {
            "province": DISTRICT_PROVINCE[name],
            "gdd_total": round(cfg.gdd_total, 2),
            "summary": _json_value(summary),
            "scenarios": _json_value(scenarios.to_dict(orient="records")),
        }
        summary_rows.append(
            {
                "district": name,
                "province": province,
                "gdd_total": cfg.gdd_total,
                "median_days_to_maturity": summary[
                    "median_days_to_maturity"
                ],
                "median_best_date": summary["median"],
                "median_latest_ok_date": summary["median_latest_ok"],
                "pct_edge": summary["pct_edge"],
                "pct_ties": summary["pct_ties"],
                "phenology_ok": summary["phenology_ok"],
            }
        )

        print(f"{name}: calibrated gdd_total = {cfg.gdd_total:.0f}")
        median_dates = pd.to_datetime(
            fixed_sensitivity["median"], format="%d %b"
        )
        movement = int((median_dates.max() - median_dates.min()).days)
        print(
            f"  fixed-window sensitivity movement: {movement} days "
            f"({median_dates.min():%d %b} to {median_dates.max():%d %b})"
        )

    output_path = WHEAT_ADVISOR_DIR / "results.json"
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    summary_table = pd.DataFrame(summary_rows)
    summary_table.to_csv(RESULTS_DIR / "eight_district_summary.csv", index=False)
    print("\nDistrict summary")
    print(summary_table.to_string(index=False, float_format="%.1f"))
    flagged = summary_table.loc[
        (summary_table["pct_edge"] > 30) | ~summary_table["phenology_ok"]
    ]
    print("\nFlags (pct_edge > 30% or phenology_ok is False)")
    print("none" if flagged.empty else flagged.to_string(index=False, float_format="%.1f"))
    print(f"\nSaved results to {output_path}")
    print(f"Saved per-year and scenario CSV files to {RESULTS_DIR}")


if __name__ == "__main__":
    main()
