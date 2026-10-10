
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from scipy.stats import theilslopes, kendalltau
except ImportError:
    theilslopes = None
    kendalltau = None


BASE_DIR = Path(__file__).resolve().parent
CACHE_DIR = BASE_DIR / "cache"

DISTRICTS = {
    "Faisalabad": (31.42, 73.08, "Punjab"),
    "Multan": (30.20, 71.47, "Punjab"),
    "Bahawalpur": (29.40, 71.68, "Punjab"),
    "Rahim Yar Khan": (28.42, 70.30, "Punjab"),
    "Sargodha": (32.08, 72.67, "Punjab"),
    "Sahiwal": (30.67, 73.11, "Punjab"),
    "Larkana": (27.56, 68.21, "Sindh"),
    "Hyderabad": (25.39, 68.37, "Sindh"),
}

TBASE = 0.0
TCAP = 30.0

# Starting assumption; tune with the calibration script.
GDD_TOTAL = 2200.0
HEAT_C = 34.0

STD_SOW = "11-15"
FIRST_SOW_YEAR = 2000
LAST_SOW_YEAR = 2024


def load(name):
    """Load one district's daily weather in the new model's schema."""
    path = CACHE_DIR / (name.replace(" ", "_") + ".csv")

    if not path.exists():
        raise FileNotFoundError(
            f"Missing weather file: {path}. "
            "Run fetch_weather.py first."
        )

    df = pd.read_csv(path, parse_dates=["time"])
    required = {"time", "temperature_2m_max", "temperature_2m_min"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{name}: missing columns {missing}")

    weather = (
        df.rename(
            columns={
                "time": "date",
                "temperature_2m_max": "tmax",
                "temperature_2m_min": "tmin",
            }
        )
        .sort_values("date")
        .drop_duplicates("date")
        .set_index("date")[["tmax", "tmin"]]
    )
    weather.index.name = "date"
    return weather


def simulate(df, sow_date):
    """
    Simulate one sowing date using daily weather.

    Returns a dictionary with stress, heat, frost, maturity,
    and late_days. Returns None if the crop cannot reach the
    maturity threshold with available, usable weather.
    """
    sow_date = pd.Timestamp(sow_date).normalize()

    if sow_date not in df.index:
        return None

    i = df.index.get_loc(sow_date)

    # Need a complete daily weather sequence after sowing.
    dates = df.index[i:i + 365]
    if len(dates) < 365:
        return None

    tx = df["tmax"].to_numpy(
        dtype=float
    )[i:i + 365]
    tn = df["tmin"].to_numpy(
        dtype=float
    )[i:i + 365]

    # Avoid silently treating missing weather as zero.
    if not np.isfinite(tx).all() or not np.isfinite(tn).all():
        return None

    # Simple daily GDD approximation:
    # mean temperature, capped at TCAP and floored at TBASE.
    tx_adj = np.minimum(tx, TCAP)
    tn_adj = np.clip(tn, TBASE, TCAP)

    daily_gdd = np.maximum(
        0.0,
        (tx_adj + tn_adj) / 2.0 - TBASE
    )
    gdd = np.cumsum(daily_gdd)

    reached = np.flatnonzero(gdd >= GDD_TOTAL)
    if len(reached) == 0:
        return None

    m = int(reached[0])
    progress = gdd[:m + 1] / GDD_TOTAL

    # Stage ranges are simplified assumptions, not
    # crop-specific phenology measurements.
    heat_mask = (
        (tx[:m + 1] >= HEAT_C)
        & (progress >= 0.60)
        & (progress <= 0.95)
    )

    frost_mask = (
        (tn[:m + 1] <= 0.0)
        & (progress >= 0.50)
        & (progress <= 0.65)
    )

    heat_days = int(heat_mask.sum())
    frost_days = int(frost_mask.sum())
    maturity = dates[m]

    # Compare with May 15 of the year after sowing.
    expected_deadline = pd.Timestamp(
        sow_date.year + 1, 5, 15
    )
    late_days = max(
        0, (maturity - expected_deadline).days
    )

    # Transparent illustrative score. It is not a
    # validated agronomic loss or yield score.
    stress = heat_days + 2 * frost_days + 2 * late_days

    return {
        "stress": int(stress),
        "heat": heat_days,
        "frost": frost_days,
        "late_days": late_days,
        "maturity": maturity,
    }


def moving_avg(values, window=5):
    """Smooth the average curve to reduce day-to-day noise."""
    return (
        pd.Series(values)
        .rolling(window, center=True, min_periods=1)
        .mean()
        .to_numpy()
        .copy()
    )


def district_summary(df):
    """Calculate all summary fields for one district."""
    if theilslopes is None or kendalltau is None:
        raise RuntimeError(
            "The legacy district_summary() requires SciPy, but SciPy could "
            "not load in this environment. Use sowing_model.recommend()."
        )

    years = list(range(FIRST_SOW_YEAR, LAST_SOW_YEAR + 1))

    sow_dates = list(
        pd.date_range("2001-10-01", "2001-12-31", freq="D")
    )
    labels = [d.strftime("%m-%d") for d in sow_dates]

    matrix = np.full(
        (len(years), len(labels)), np.nan
    )

    for a, year in enumerate(years):
        dates = pd.date_range(
            f"{year}-10-01",
            f"{year}-12-31",
            freq="D",
        )

        for b, date in enumerate(dates):
            result = simulate(df, date)
            if result is not None:
                matrix[a, b] = result["stress"]

    valid_years = np.isfinite(matrix).any(axis=1)
    if valid_years.sum() < 10:
        raise ValueError(
            "Too few valid historical seasons. "
            "Check weather coverage and missing values."
        )

    # Keep only candidate dates with at least one result.
    with np.errstate(invalid="ignore"):
        raw_curve = np.nanmean(matrix, axis=0)

    if not np.isfinite(raw_curve).any():
        raise ValueError("No valid sowing-date results.")

    curve = moving_avg(raw_curve)

    # Do not choose an all-NaN date.
    curve[~np.isfinite(raw_curve)] = np.inf

    best = int(np.argmin(curve))
    best_value = curve[best]

    # Window tolerance is a transparent heuristic.
    finite_curve = curve[np.isfinite(curve)]
    tol = max(
        2.0,
        0.10 * (
            float(finite_curve.max())
            - float(finite_curve.min())
        ),
    )

    lo = best
    hi = best

    while lo > 0 and curve[lo - 1] <= best_value + tol:
        lo -= 1

    while (
        hi < len(labels) - 1
        and curve[hi + 1] <= best_value + tol
    ):
        hi += 1

    # Share of usable seasons where this chosen date
    # is within tolerance of that season's minimum score.
    annual_min = np.full(len(years), np.nan)
    for i, row in enumerate(matrix):
        valid = row[np.isfinite(row)]
        if len(valid):
            annual_min[i] = valid.min()

    chosen_scores = matrix[:, best]
    valid = (
        np.isfinite(chosen_scores)
        & np.isfinite(annual_min)
    )

    if valid.any():
        share_ok = float(np.mean(
            chosen_scores[valid]
            <= annual_min[valid] + tol
        ))
    else:
        share_ok = float("nan")

    # Best date in each usable year, then trend in
    # its position within the Oct-Dec candidate range.
    usable_indices = []
    usable_years = []

    for i, row in enumerate(matrix):
        if np.isfinite(row).any():
            usable_indices.append(int(np.nanargmin(row)))
            usable_years.append(years[i])

    if len(usable_indices) >= 3:
        slope = (
            theilslopes(usable_indices, usable_years)[0]
            * 10.0
        )
        p_value = float(
            kendalltau(usable_years, usable_indices).pvalue
        )
    else:
        slope = float("nan")
        p_value = float("nan")

    # Backtest the 2021-22 season (sown in autumn 2021).
    # Use only the same sowing date for historical comparison.
    historical_heat = {}

    for year in range(FIRST_SOW_YEAR, 2022):
        r = simulate(
            df, pd.Timestamp(f"{year}-{STD_SOW}")
        )
        if r is not None:
            historical_heat[year] = r["heat"]

    if 2021 not in historical_heat:
        raise ValueError(
            "Cannot calculate 2022-season check for "
            "Nov 15, 2021. Check weather data."
        )

    h2022 = historical_heat[2021]
    percentile = 100.0 * np.mean([
        value <= h2022
        for value in historical_heat.values()
    ])

    alternative_heat = {}
    for date_label in ["10-25", "11-01", "11-15", "12-01"]:
        r = simulate(
            df, pd.Timestamp(f"2021-{date_label}")
        )
        alternative_heat[date_label] = (
            r["heat"] if r is not None else None
        )

    return {
        "labels": labels,
        "mean_curve": [
            round(float(v), 2) if np.isfinite(v) else None
            for v in curve
        ],
        "best": labels[best],
        "window_start": labels[lo],
        "window_end": labels[hi],
        "share_of_years_ok": (
            round(share_ok, 2)
            if np.isfinite(share_ok) else None
        ),
        "drift_days_per_decade": (
            round(float(slope), 2)
            if np.isfinite(slope) else None
        ),
        "drift_p_value": (
            round(float(p_value), 3)
            if np.isfinite(p_value) else None
        ),
        "backtest_2022": {
            "heat_days_std_sowing": h2022,
            "percentile_hot_year": round(float(percentile)),
            "heat_days_by_sowing_date": alternative_heat,
            "season": "2021-2022",
        },
        "edge_warning": best in (0, len(labels) - 1),
    }
