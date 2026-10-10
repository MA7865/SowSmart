"""Compare saved SEAS5 seasonal forecasts with observed district history.

This is a diagnostic only. Forecast values are never passed to the sowing
recommendation model.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
FORECAST_DIR = ROOT / "forecasts"
RESULTS_PATH = FORECAST_DIR / "forecast_vs_history.csv"
MONTHS = pd.period_range("2026-11", "2027-04", freq="M")
DISTRICTS = ("Multan", "Hyderabad", "Larkana")

sys.path.insert(0, str(ROOT / "wheat-advisor"))
import sim_core as sc


def latest_file(district: str, kind: str) -> Path:
    files = sorted(
        (FORECAST_DIR / district).glob(f"{kind}_*.json"),
        key=lambda path: path.name,
    )
    if not files:
        raise FileNotFoundError(f"No {kind} snapshot found for {district}")
    return files[-1]


def read_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def member_monthly_values(
    payload: dict, variable: str, total: bool = False
) -> pd.DataFrame:
    """Return one row per member and one column per forecast month."""
    daily = payload["daily"]
    dates = pd.to_datetime(daily["time"])
    names = [
        name
        for name in daily
        if re.fullmatch(rf"{re.escape(variable)}_member\d+", name)
    ]
    if len(names) != 50:
        raise ValueError(
            f"Expected 50 {variable} members, found {len(names)}"
        )

    rows = []
    for name in names:
        series = pd.Series(daily[name], index=dates, dtype="float64")
        rows.append({
            str(month): (
                series[series.index.to_period("M") == month].sum()
                if total
                else series[series.index.to_period("M") == month].mean()
            )
            for month in MONTHS
        })
    return pd.DataFrame(rows, index=names)


def ensemble_monthly_values(
    payload: dict, variable: str, total: bool = False
) -> pd.Series:
    dates = pd.to_datetime(payload["daily"]["time"])
    series = pd.Series(payload["daily"][variable], index=dates, dtype="float64")
    operation = series.groupby(series.index.to_period("M")).sum if total else (
        series.groupby(series.index.to_period("M")).mean
    )
    return operation().reindex(MONTHS)


def observed_monthly(district: str, variable: str, total: bool = False):
    weather = sc.load(district)
    if variable in {"tmax", "tmin"}:
        series = weather[variable].copy()
    else:
        cache_path = sc.CACHE_DIR / (district.replace(" ", "_") + ".csv")
        raw = pd.read_csv(cache_path, parse_dates=["time"])
        if "precipitation_sum" not in raw:
            return None
        series = raw.set_index("time")["precipitation_sum"]

    series = series[series.index.month.isin([11, 12, 1, 2, 3, 4])]
    rows = []
    for year in range(2000, 2025):
        values = []
        for month in range(11, 13):
            values.append(
                series[
                    (series.index.year == year)
                    & (series.index.month == month)
                ]
            )
        for month in range(1, 5):
            values.append(
                series[
                    (series.index.year == year + 1)
                    & (series.index.month == month)
                ]
            )
        rows.append(
            [
                (value.sum() if total else value.mean())
                for value in values
            ]
        )
    return pd.DataFrame(rows, columns=[str(month) for month in MONTHS])


def percentile_of_history(value: float, history: pd.Series) -> float:
    return float((history <= value).mean() * 100)


def make_chart(district: str, table: pd.DataFrame) -> None:
    labels = [period.strftime("%b %Y") for period in MONTHS]
    x = np.arange(len(labels))
    fig, axes = plt.subplots(2, 1, figsize=(11, 8), sharex=True)

    for axis, variable in zip(axes, ("tmax", "tmin")):
        rows = table[table["variable"] == variable].reset_index(drop=True)
        axis.fill_between(
            x,
            rows["history_min"],
            rows["history_max"],
            color="#d9d9d9",
            alpha=0.8,
            label="2000-2024 historical range",
        )
        axis.fill_between(
            x,
            rows["forecast_p10"],
            rows["forecast_p90"],
            color="#9ecae1",
            alpha=0.8,
            label="SEAS5 p10-p90",
        )
        axis.plot(x, rows["forecast_median"], "o-", label="SEAS5 median")
        axis.plot(x, rows["ensemble_mean"], "x--", label="ensemble mean")
        axis.set_ylabel(f"{variable} (°C)")
        axis.grid(axis="y", alpha=0.25)
        axis.legend(loc="best")

    axes[-1].set_xticks(x, labels, rotation=30, ha="right")
    fig.suptitle(f"{district}: SEAS5 forecast compared with history")
    fig.tight_layout()
    fig.savefig(FORECAST_DIR / f"{district}_forecast_vs_history.png", dpi=150)
    plt.close(fig)


def main() -> None:
    output_rows = []

    for district in DISTRICTS:
        member_path = latest_file(district, "seasonal_seas5_members")
        mean_path = latest_file(district, "seasonal_seas5_mean")
        member_payload = read_json(member_path)
        mean_payload = read_json(mean_path)
        district_rows = []

        print(f"\n{district}")
        print(f"  Members: {member_path.name}")
        print(f"  Mean:    {mean_path.name}")

        for variable, api_variable in (
            ("tmax", "temperature_2m_max"),
            ("tmin", "temperature_2m_min"),
        ):
            members = member_monthly_values(member_payload, api_variable)
            mean = ensemble_monthly_values(mean_payload, api_variable)
            history = observed_monthly(district, variable)
            for month in MONTHS:
                values = members[str(month)].dropna()
                historical = history[str(month)].dropna()
                forecast_median = float(values.median())
                row = {
                    "district": district,
                    "month": str(month),
                    "variable": variable,
                    "forecast_median": forecast_median,
                    "forecast_p10": float(values.quantile(0.10)),
                    "forecast_p90": float(values.quantile(0.90)),
                    "ensemble_mean": float(mean.loc[month]),
                    "history_mean": float(historical.mean()),
                    "history_min": float(historical.min()),
                    "history_max": float(historical.max()),
                    "history_percentile": percentile_of_history(
                        forecast_median, historical
                    ),
                    "member_spread": float(
                        values.quantile(0.90) - values.quantile(0.10)
                    ),
                    "history_spread": float(
                        historical.max() - historical.min()
                    ),
                    "spread_smaller_than_history": bool(
                        values.quantile(0.90) - values.quantile(0.10)
                        < historical.max() - historical.min()
                    ),
                }
                output_rows.append(row)
                district_rows.append(row)

        precipitation = observed_monthly(district, "precipitation_sum", True)
        precip_members = member_monthly_values(
            member_payload, "precipitation_sum", total=True
        )
        precip_mean = ensemble_monthly_values(
            mean_payload, "precipitation_sum", total=True
        )
        if precipitation is None:
            print("  Rainfall: not available in cached weather; skipped.")
        else:
            print("  Rainfall: cached weather contains precipitation_sum.")
            for month in MONTHS:
                values = precip_members[str(month)].dropna()
                forecast_median = float(values.median())
                plausible = bool(
                    np.isfinite(values).all()
                    and (values >= 0).all()
                    and (values <= 1000).all()
                )
                history = precipitation[str(month)].dropna()
                output_rows.append(
                    {
                        "district": district,
                        "month": str(month),
                        "variable": "precipitation_sum",
                        "forecast_median": forecast_median,
                        "forecast_p10": float(values.quantile(0.10)),
                        "forecast_p90": float(values.quantile(0.90)),
                        "ensemble_mean": float(precip_mean.loc[month]),
                        "history_mean": float(history.mean()),
                        "history_min": float(history.min()),
                        "history_max": float(history.max()),
                        "history_percentile": percentile_of_history(
                            forecast_median, history
                        ),
                        "member_spread": float(
                            values.quantile(0.90) - values.quantile(0.10)
                        ),
                        "history_spread": float(
                            history.max() - history.min()
                        ),
                        "spread_smaller_than_history": bool(
                            values.quantile(0.90) - values.quantile(0.10)
                            < history.max() - history.min()
                        ),
                    }
                )
                print(
                    f"    {month}: median {forecast_median:.1f} mm, "
                    f"history {history.mean():.1f} mm "
                    f"({history.min():.1f}-{history.max():.1f}), "
                    f"non-zero={forecast_median > 0}, plausible={plausible}, "
                    f"ensemble mean={float(precip_mean.loc[month]):.1f} mm"
                )

        table = pd.DataFrame(district_rows)
        make_chart(district, table)
        for variable in ("tmax", "tmin"):
            print(f"  {variable}:")
            for _, row in table[table["variable"] == variable].iterrows():
                direction = (
                    "above"
                    if row["forecast_median"] > row["history_mean"]
                    else "below"
                )
                print(
                    f"    {row['month']}: median {row['forecast_median']:.1f}°C, "
                    f"{row['history_percentile']:.0f}th historical percentile, "
                    f"{direction} history mean by "
                    f"{abs(row['forecast_median'] - row['history_mean']):.1f}°C; "
                    f"spread {row['member_spread']:.1f}°C vs history "
                    f"{row['history_spread']:.1f}°C"
                )
            offsets = (
                table[table["variable"] == variable]["forecast_median"]
                - table[table["variable"] == variable]["history_mean"]
            ).abs()
            largest = offsets.idxmax()
            print(
                f"    Largest absolute forecast offset: "
                f"{table.loc[largest, 'month']} "
                f"({offsets.loc[largest]:.1f}°C)"
            )

    pd.DataFrame(output_rows).to_csv(RESULTS_PATH, index=False)
    print(
        "\nCaveat: raw seasonal forecasts can have model bias. "
        "Offsets from history are reported, not corrected, and forecasts "
        "were not used for recommendations."
    )
    print(f"Saved table to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
