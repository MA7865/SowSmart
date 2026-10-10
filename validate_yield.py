"""Validate fixed-date sowing-model stress against Punjab district yields."""

from pathlib import Path
import sys

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
WHEAT_ADVISOR_DIR = ROOT / "wheat-advisor"
DATA_PATH = (
    WHEAT_ADVISOR_DIR
    / "data"
    / "area-sown-production-and-yield-per-hectare-of-wheat-by-districts-punjab-yield-per-hectare-in-kg-.csv"
)
RESULTS_DIR = WHEAT_ADVISOR_DIR / "results"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(WHEAT_ADVISOR_DIR))

import sim_core as sc
from config import DISTRICT_PROVINCE, ModelConfig
from sowing_model import _season_slice, calibrate_gdd_total, simulate


DISTRICTS = (
    "Bahawalpur",
    "Faisalabad",
    "Hyderabad",
    "Larkana",
    "Multan",
    "Rahim_Yar_Khan",
    "Sahiwal",
    "Sargodha",
)
CSV_LABELS = {"Rahim_Yar_Khan": "Rahim Yar Khan"}
FIXED_SOWINGS = ("11-10", "11-20", "12-01")
MEASURES = ("score", "heat", "warm", "frost", "late_days")
TARGET_DAYS = {"punjab": 140, "sindh": 128}


def load_yields():
    parsed = pd.read_csv(DATA_PATH, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    label_column = parsed.columns[0]
    year_columns = parsed.columns[1:]
    by_district = {}
    print("Yield CSV district-name check (labels shown as stored):")
    for district in DISTRICTS:
        label = CSV_LABELS.get(district, district)
        matches = parsed.loc[parsed[label_column].str.strip().eq(label)]
        if len(matches) == 1:
            print(f"  {district}: {matches.iloc[0, 0]!r} (matched)")
            row = matches.iloc[0]
            values = {}
            for season, raw in row[year_columns].items():
                value = raw.strip().replace(",", "")
                if value in {"", "**", "NA", "N/A", "null", "None"}:
                    values[int(str(season).split("-", 1)[0])] = np.nan
                else:
                    try:
                        values[int(str(season).split("-", 1)[0])] = float(value)
                    except ValueError:
                        values[int(str(season).split("-", 1)[0])] = np.nan
            series = pd.Series(values, dtype="float64").sort_index()
            series.index.name = "sowing_year"
            by_district[district] = series
        else:
            exact = parsed.loc[parsed[label_column].str.strip().eq(district)]
            shown = [repr(v) for v in exact[label_column].tolist()]
            if district in CSV_LABELS:
                shown = [repr(v) for v in matches[label_column].tolist()]
            print(f"  {district}: no match; CSV label found: {', '.join(shown) if shown else 'none'}")
    return by_district


def detrend(values):
    values = values.dropna()
    if len(values) < 2:
        return pd.Series(dtype="float64", name="detrended_yield")
    x = values.index.to_numpy(dtype=float)
    residual = values.to_numpy(dtype=float) - np.polyval(np.polyfit(x, values.to_numpy(dtype=float), 1), x)
    return pd.Series(residual, index=values.index, name="detrended_yield")


def correlate(frame, measure):
    usable = frame[["detrended_yield", measure]].dropna()
    output = {"n": len(usable), "correlation": np.nan, "p_value": np.nan}
    if len(usable) < 2 or usable["detrended_yield"].nunique() < 2 or usable[measure].nunique() < 2:
        return output
    from scipy.stats import spearmanr

    result = spearmanr(usable[measure], usable["detrended_yield"])
    output["correlation"] = float(result.statistic)
    output["p_value"] = float(result.pvalue)
    return output


def write_validation_chart(district, frame):
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), sharey=True)
    for ax, sowing in zip(axes, FIXED_SOWINGS):
        subset = frame.loc[
            frame["sowing_date"].str.endswith(sowing)
            & frame["validation_status"].eq("ok")
        ]
        ax.scatter(
            subset["score"], subset["detrended_yield"],
            color="#2171b5", edgecolor="white",
        )
        ax.axhline(0, color="black", linewidth=0.8, alpha=0.5)
        ax.axvline(0, color="black", linewidth=0.8, alpha=0.5)
        ax.set_title(f"Sowing {sowing}")
        ax.set_xlabel("Model stress score")
        ax.grid(alpha=0.25)
    axes[0].set_ylabel("Detrended yield (kg/hectare)")
    fig.suptitle(f"{district} wheat yield versus model stress")
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / f"{district}_yield_validation.png", dpi=150)
    plt.close(fig)


def validate_district(district, yields):
    weather = sc.load(district)
    province = DISTRICT_PROVINCE[district]
    cfg = ModelConfig()
    cfg.gdd_total = calibrate_gdd_total(
        weather,
        sow_mmdd="11-18",
        target_days=TARGET_DAYS[province],
        cfg=cfg,
    )
    residual = detrend(yields)
    rows = []
    for year, yield_value in yields.items():
        season = _season_slice(weather, year)
        for sowing in FIXED_SOWINGS:
            result = None
            status = "ok"
            if pd.isna(yield_value):
                status = "missing_yield"
            elif season is None:
                status = "missing_weather"
            else:
                result = simulate(season, pd.Timestamp(f"{year}-{sowing}"), cfg)
                if result is None:
                    status = "no_maturity"
            row = {
                "district": district,
                "sowing_year": year,
                "sowing_date": f"{year}-{sowing}",
                "yield_kg_per_hectare": yield_value,
                "detrended_yield": residual.get(year, np.nan),
                "validation_status": status,
            }
            row.update({measure: result[measure] if result else np.nan for measure in MEASURES})
            rows.append(row)

    frame = pd.DataFrame(rows)
    frame.to_csv(RESULTS_DIR / f"{district}_yield_validation.csv", index=False)
    write_validation_chart(district, frame)
    stats = []
    for sowing in FIXED_SOWINGS:
        subset = frame.loc[
            frame["sowing_date"].str.endswith(sowing)
            & frame["validation_status"].eq("ok")
        ]
        for measure in MEASURES:
            result = correlate(subset, measure)
            stats.append({
                "district": district,
                "n": result["n"],
                "date": sowing,
                "measure": measure,
                "correlation": result["correlation"],
                "p_value": result["p_value"],
            })
    return frame, stats


def main():
    RESULTS_DIR.mkdir(exist_ok=True)
    yields = load_yields()
    all_frames = []
    stats = []
    for district, series in yields.items():
        frame, district_stats = validate_district(district, series)
        all_frames.append(frame)
        stats.extend(district_stats)

    pooled = pd.concat(all_frames, ignore_index=True)
    for sowing in FIXED_SOWINGS:
        subset = pooled.loc[
            pooled["sowing_date"].str.endswith(sowing)
            & pooled["validation_status"].eq("ok")
        ]
        result = correlate(subset, "score")
        stats.append({
            "district": "Pooled",
            "n": result["n"],
            "date": sowing,
            "measure": "score",
            "correlation": result["correlation"],
            "p_value": result["p_value"],
        })

    stats_table = pd.DataFrame(stats)
    output = RESULTS_DIR / "yield_validation_statistics.csv"
    stats_table.to_csv(output, index=False)
    stats_table[stats_table["district"].eq("Multan")].to_csv(
        RESULTS_DIR / "Multan_yield_validation_statistics.csv", index=False
    )
    pooled.to_csv(RESULTS_DIR / "yield_validation_by_year.csv", index=False)

    print("\nSpearman validation results (negative is the expected direction):")
    print(stats_table.to_string(index=False, float_format=lambda value: f"{value:.4g}"))
    print(f"\nSaved combined statistics: {output}")
    print(f"Saved per-year validation rows: {RESULTS_DIR / 'yield_validation_by_year.csv'}")
    print("Hyderabad and Larkana remain unvalidated: no yield rows were present.")
    print(
        "Pooled p-values are optimistic: districts in the same year share weather, "
        "so district-year observations are not independent."
    )
    print(
        f"Tests run: {len(yields)} matched districts x {len(FIXED_SOWINGS)} dates "
        f"x {len(MEASURES)} measures = {len(yields) * len(FIXED_SOWINGS) * len(MEASURES)} "
        f"district-specific tests, plus {len(FIXED_SOWINGS)} pooled total-stress tests."
    )


if __name__ == "__main__":
    main()
