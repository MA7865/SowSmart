"""Validate Multan wheat yield against fixed-date model stress."""

import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

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
from config import ModelConfig, WINDOWS
from sowing_model import _season_slice, calibrate_gdd_total, simulate


FIXED_SOWINGS = ("11-10", "11-20", "12-01")
DISTRICT = "Multan"


def inspect_yield_file():
    with DATA_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        raw_rows = list(csv.reader(handle))

    header = raw_rows[0]
    rows = raw_rows[1:]
    first_column = header[0]
    year_columns = header[1:]
    print("Yield file inspection")
    print(f"  columns: {header}")
    print(f"  year columns: {year_columns}")
    print(f"  district column: {first_column!r}")
    print(f"  data rows: {len(rows)}")

    parsed = pd.read_csv(DATA_PATH, dtype=str, keep_default_na=False)
    label_column = parsed.columns[0]
    multan_rows = parsed.loc[parsed[label_column].str.strip() == DISTRICT]
    if len(multan_rows) != 1:
        raise ValueError(
            f"Expected exactly one {DISTRICT!r} row, found {len(multan_rows)}."
        )

    print(f"  Multan spelling: {multan_rows.iloc[0, 0]!r}")
    problems = []
    for row_number, row in enumerate(rows, start=2):
        if len(row) != len(header):
            problems.append(
                f"row {row_number} has {len(row)} fields; expected {len(header)}"
            )
    if problems:
        print("  CSV structure problems:")
        for problem in problems:
            print(f"    - {problem}")
    else:
        print("  CSV structure problems: none")
    return parsed, label_column, year_columns


def clean_multan_yield(parsed, label_column, year_columns):
    multan = parsed.loc[parsed[label_column].str.strip() == DISTRICT].iloc[0]
    cleaned = {}
    changes = []
    missing = []
    non_numeric = []

    for season, raw_value in multan[year_columns].items():
        value = raw_value.strip()
        if value in {"", "**", "NA", "N/A", "null", "None"}:
            cleaned[season] = np.nan
            missing.append(season)
            continue
        normalized = value.replace(",", "")
        try:
            cleaned[season] = float(normalized)
        except ValueError:
            cleaned[season] = np.nan
            non_numeric.append((season, value))
            continue
        if normalized != value:
            changes.append(f"{season}: removed comma separators from {value!r}")

    print("Cleaning changes")
    print("  - Removed thousands separators from quoted values.")
    print("  - Converted yield values to numeric kg/hectare.")
    print("  - Kept all Multan season columns; no rows were dropped.")
    if changes:
        print(f"  - Values reformatted: {len(changes)}")
    if missing:
        print(f"  - Missing values: {missing}")
    else:
        print("  - Missing values in Multan row: none")
    if non_numeric:
        print(f"  - Non-numeric values: {non_numeric}")
    else:
        print("  - Non-numeric values in Multan row: none")

    yields = pd.Series(cleaned, dtype="float64")
    yields.index = [
        int(str(season).split("-", 1)[0]) for season in yields.index
    ]
    yields.index.name = "sowing_year"
    return yields.sort_index()


def detrend(values):
    x = values.index.to_numpy(dtype=float)
    coefficients = np.polyfit(x, values.to_numpy(dtype=float), 1)
    trend = np.polyval(coefficients, x)
    return values - trend


def spearman_result(frame, measure):
    usable = frame[["detrended_yield", measure]].dropna()
    result = {
        "measure": measure,
        "n": len(usable),
        "spearman": np.nan,
        "p_value": np.nan,
    }
    if usable["detrended_yield"].nunique() < 2 or usable[measure].nunique() < 2:
        return result, "Correlation is undefined because one series is constant."

    try:
        from scipy.stats import spearmanr
    except ImportError:
        return result, "SciPy could not load; p-values were skipped."

    result["spearman"], result["p_value"] = spearmanr(
        usable[measure], usable["detrended_yield"]
    )
    return result, None


def main():
    parsed, label_column, year_columns = inspect_yield_file()
    yields = clean_multan_yield(parsed, label_column, year_columns)
    detrended = detrend(yields.dropna())

    weather = sc.load(DISTRICT)
    cfg = ModelConfig()
    cfg.gdd_total = calibrate_gdd_total(
        weather,
        sow_mmdd="11-18",
        target_days=140,
        cfg=cfg,
    )
    print(f"\nMultan province calibration: gdd_total={cfg.gdd_total:.1f}")

    rows = []
    for year, yield_value in yields.items():
        season = _season_slice(weather, year)
        for sow_mmdd in FIXED_SOWINGS:
            result = None
            status = "ok"
            if pd.isna(yield_value):
                status = "missing_yield"
            elif season is None:
                status = "missing_weather"
            else:
                result = simulate(
                    season,
                    pd.Timestamp(f"{year}-{sow_mmdd}"),
                    cfg,
                )
                if result is None:
                    status = "no_maturity"

            row = {
                "sowing_year": year,
                "sowing_date": f"{year}-{sow_mmdd}",
                "yield_kg_per_hectare": yield_value,
                "detrended_yield": detrended.get(year, np.nan),
                "validation_status": status,
            }
            for field in ("score", "heat", "warm", "frost", "late_days"):
                row[field] = result[field] if result else np.nan
            rows.append(row)

    table = pd.DataFrame(rows)
    output_csv = RESULTS_DIR / "Multan_yield_validation.csv"
    table.to_csv(output_csv, index=False)

    print("\nValidation results")
    print("Expected correlation sign: negative (more stress should mean lower yield).")
    result_rows = []
    plot_data = {}
    for sow_mmdd in FIXED_SOWINGS:
        subset = table.loc[
            (table["sowing_date"].str.endswith(sow_mmdd))
            & (table["validation_status"] == "ok")
        ].copy()
        print(f"\nFixed sowing date: {sow_mmdd}")
        plot_data[sow_mmdd] = subset
        for measure in ("score", "heat", "warm", "frost", "late_days"):
            result, note = spearman_result(subset, measure)
            result["sowing_date"] = sow_mmdd
            result_rows.append(result)
            p_value = (
                "not available"
                if pd.isna(result["p_value"])
                else f"{result['p_value']:.4g}"
            )
            print(
                f"  {measure}: n={result['n']}, "
                f"Spearman={result['spearman']:.3f}, p-value={p_value}"
            )
            if note:
                print(f"  Note: {note}")

    stats = pd.DataFrame(result_rows)
    stats_path = RESULTS_DIR / "Multan_yield_validation_statistics.csv"
    stats.to_csv(stats_path, index=False)

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), sharey=True)
    for ax, sow_mmdd in zip(axes, FIXED_SOWINGS):
        subset = plot_data[sow_mmdd]
        ax.scatter(
            subset["score"],
            subset["detrended_yield"],
            color="#2171b5",
            edgecolor="white",
        )
        ax.axhline(0, color="black", linewidth=0.8, alpha=0.5)
        ax.axvline(0, color="black", linewidth=0.8, alpha=0.5)
        ax.set_title(f"Nov/Dec {sow_mmdd[3:]}")
        ax.set_xlabel("Model stress score")
        ax.grid(alpha=0.25)
    axes[0].set_ylabel("Detrended yield (kg/hectare)")
    fig.suptitle("Multan wheat yield versus model stress")
    fig.tight_layout()
    output_png = RESULTS_DIR / "Multan_yield_validation.png"
    fig.savefig(output_png, dpi=150)
    plt.close(fig)

    print(f"\nSaved validation table to {output_csv}")
    print(f"Saved correlation statistics to {stats_path}")
    print(f"Saved scatter plot to {output_png}")
    print(
        "\nDistricts not validated: Hyderabad and Larkana. "
        "The project contains no district wheat-yield rows for them."
    )


if __name__ == "__main__":
    main()
