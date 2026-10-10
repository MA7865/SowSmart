"""
sowing_model.py - season-specific wheat sowing-date recommendations.

Differences from the old static model:
  1. Best date is chosen PER YEAR (no averaging across years first).
  2. Search is limited to an agronomic window (config.WINDOWS), not Oct 1 - Dec 31.
  3. Heat/frost/warmth are continuous (degrees of exceedance), not day counts.
  4. The 30 C cap is applied to GDD only, never to heat stress.
  5. Warming scenarios (delta method) and a yield-validation helper are built in.

Weather input per district: DataFrame indexed by daily DatetimeIndex with
columns 'tmax' and 'tmin' (C). A sowing year Y needs data from 15 Oct Y to
15 Jul Y+1.
"""
import argparse
import os
import numpy as np
import pandas as pd

from config import ModelConfig, WINDOWS, DISTRICT_PROVINCE


# ------------------------------------------------------------------ helpers
def _season_slice(w, year):
    start, end = pd.Timestamp(year, 10, 15), pd.Timestamp(year + 1, 7, 15)
    s = w.loc[start:end]
    if len(s) < (end - start).days + 1:
        s = s.reindex(pd.date_range(start, end)).interpolate(limit=3)
    return None if s[["tmax", "tmin"]].isna().any().any() else s


def _gdd(tmax, tmin, cfg):
    tx = np.minimum(tmax, cfg.gdd_ceiling)          # cap ONLY here
    tn = np.maximum(tmin, cfg.gdd_base)
    return np.maximum((tx + tn) / 2.0 - cfg.gdd_base, 0.0)


def simulate(season, sow, cfg):
    """Stress components for one sowing date inside one season frame."""
    tmax, tmin = season["tmax"].to_numpy(), season["tmin"].to_numpy()
    cs = np.cumsum(_gdd(tmax, tmin, cfg))
    i = season.index.get_loc(sow)
    base = cs[i - 1] if i > 0 else 0.0
    m = np.searchsorted(cs, base + cfg.gdd_total)
    if m >= len(cs):
        return None                                   # crop would not mature within data
    idx = np.arange(i, m + 1)
    p = (cs[idx] - base) / cfg.gdd_total
    tmean = (tmax[idx] + tmin[idx]) / 2.0

    heat = np.maximum(tmax[idx] - cfg.heat_threshold, 0)[p >= cfg.heat_from_frac].sum()
    warm = np.maximum(tmean - cfg.warm_optimum_max, 0)[p < cfg.anthesis_frac].sum()
    frost = np.maximum(cfg.frost_threshold - tmin[idx], 0)[p >= cfg.frost_from_frac].sum()
    mat_date = season.index[m]
    deadline = pd.Timestamp(f"{mat_date.year}-{cfg.maturity_deadline}")
    if mat_date.month < 6 and mat_date.year == sow.year:   # safety for odd calendars
        deadline = pd.Timestamp(f"{sow.year + 1}-{cfg.maturity_deadline}")
    late = max((mat_date - deadline).days, 0)

    score = cfg.w_heat * heat + cfg.w_warm * warm + cfg.w_frost * frost + cfg.w_late * late
    return dict(score=score, heat=heat, warm=warm, frost=frost, late_days=late,
                maturity=mat_date, days_to_maturity=int(m - i))


def _window_dates(year, window):
    return pd.date_range(f"{year}-{window[0]}", f"{year}-{window[1]}")


# ------------------------------------------------------------ core routines
def recommend(weather, window, cfg=None, years=None):
    """Best sowing date for EACH year. Returns one row per year."""
    cfg = cfg or ModelConfig()
    years = years or sorted(set(weather.index.year))
    rows = []
    for y in years:
        season = _season_slice(weather, y)
        if season is None:
            continue
        dates = _window_dates(y, window)[:: cfg.step_days]
        res = [(d, simulate(season, d, cfg)) for d in dates]
        res = [(d, r) for d, r in res if r is not None]
        if not res:
            continue
        d_best, r_best = min(res, key=lambda t: (t[1]["score"], t[0]))   # ties -> earliest
        edge = (min((d_best - dates[0]).days, (dates[-1] - d_best).days) <= cfg.edge_tolerance_days)
        ok = [d for d, r in res if r["score"] <= r_best["score"] + cfg.score_tolerance]
        n_tied = sum(abs(r["score"] - r_best["score"]) < 1e-9 for _, r in res)
        rows.append(dict(year=y, best_date=d_best, ok_from=min(ok), ok_to=max(ok), **r_best,
                         edge_flag=edge, n_tied_dates=n_tied))
    return pd.DataFrame(rows)


def summarize(rec, window, cfg=None):
    """Distribution of recommendations across years."""
    cfg = cfg or ModelConfig()
    if rec.empty:
        return {}
    ref = pd.to_datetime(rec["best_date"].dt.year.astype(str) + "-" + window[0])
    off = (rec["best_date"] - ref).dt.days
    mmdd = lambda o: (pd.Timestamp(2001, int(window[0][:2]), int(window[0][3:])) + pd.Timedelta(days=float(o))).strftime("%d %b")
    freq = rec["best_date"].dt.strftime("%d %b").value_counts(normalize=True).head(3)
    ok_to = (rec["ok_to"] - pd.to_datetime(rec["ok_to"].dt.year.astype(str) + "-" + window[0])).dt.days
    med_days = float(rec["days_to_maturity"].median())
    lo, hi = cfg.ref_days_to_maturity
    return dict(n_years=len(rec), median=mmdd(off.median()), median_latest_ok=mmdd(ok_to.median()),
                median_days_to_maturity=med_days,
                phenology_ok=bool(lo <= med_days <= hi),
                p10=mmdd(off.quantile(.1)),
                p90=mmdd(off.quantile(.9)), earliest=mmdd(off.min()), latest=mmdd(off.max()),
                pct_edge=100 * rec["edge_flag"].mean(), pct_ties=100 * (rec["n_tied_dates"] > 1).mean(),
                median_heat=rec["heat"].median(), top_dates=freq.round(2).to_dict())


def warm_weather(weather, d_tmax, d_tmin=None):
    """Delta method: shift observed weather by a warming offset (C)."""
    w = weather.copy()
    w["tmax"] += d_tmax
    w["tmin"] += d_tmax if d_tmin is None else d_tmin
    return w


def scenario_table(weather, window, cfg=None, ref_sow="11-15"):
    """Re-run the model under each warming offset; also report heat at a fixed reference sowing date."""
    cfg = cfg or ModelConfig()
    out = []
    for name, (dx, dn) in cfg.scenario_offsets.items():
        w = warm_weather(weather, dx, dn)
        rec = recommend(w, window, cfg)
        s = summarize(rec, window, cfg)
        ref = [simulate(_season_slice(w, y), pd.Timestamp(f"{y}-{ref_sow}"), cfg) for y in rec["year"]]
        ref_heat = np.nanmedian([r["heat"] if r else np.nan for r in ref])
        out.append(dict(scenario=name, **{k: s[k] for k in ("median", "p10", "p90", "pct_edge", "median_heat")},
                        heat_at_ref_sowing=ref_heat))
    return pd.DataFrame(out)


def sensitivity(weather, window, cfg=None, heat_thresholds=(33, 34, 35), window_starts=("11-01", "11-15"),
                warm_weights=(0.1, 0.5, 1.0)):
    """How stable is the median recommendation to the least certain inputs?"""
    cfg = cfg or ModelConfig()
    rows = []
    for ht in heat_thresholds:
        for ws in window_starts:
            for ww in warm_weights:
                c = ModelConfig(**{**cfg.__dict__, "heat_threshold": float(ht), "w_warm": float(ww)})
                rec = recommend(weather, (ws, window[1]), c)
                s = summarize(rec, (ws, window[1]), c)
                rows.append(dict(heat_threshold=ht, window_start=ws, w_warm=ww, median=s["median"],
                                 median_latest_ok=s["median_latest_ok"], p10=s["p10"], p90=s["p90"],
                                 pct_edge=s["pct_edge"]))
    return pd.DataFrame(rows)


def calibrate_gdd_total(weather, sow_mmdd="11-18", target_days=128, cfg=None):
    """Pick gdd_total so median days-to-maturity matches an observed value (e.g. 128 d, Tando Jam)."""
    cfg = cfg or ModelConfig()
    vals = []
    for y in sorted(set(weather.index.year)):
        s = _season_slice(weather, y)
        if s is None:
            continue
        g = np.cumsum(_gdd(s["tmax"].to_numpy(), s["tmin"].to_numpy(), cfg))
        i = s.index.get_loc(pd.Timestamp(f"{y}-{sow_mmdd}"))
        if i + target_days < len(g):
            vals.append(g[i + target_days] - (g[i - 1] if i else 0))
    return float(np.median(vals))


def validate_against_yield(weather, yield_by_year, window, cfg=None, sow_mmdd="11-15"):
    """Spearman correlation: stress at a fixed sowing date vs detrended district yield (expect NEGATIVE)."""
    cfg = cfg or ModelConfig()
    yrs = [y for y in yield_by_year.index if _season_slice(weather, y) is not None]
    stress = pd.Series({y: (simulate(_season_slice(weather, y), pd.Timestamp(f"{y}-{sow_mmdd}"), cfg) or {}).get("score", np.nan)
                        for y in yrs})
    yv = yield_by_year.loc[yrs]
    resid = yv - np.polyval(np.polyfit(yv.index.astype(float), yv.values, 1), yv.index.astype(float))
    df = pd.concat([stress.rename("stress"), resid.rename("yield_resid")], axis=1).dropna()
    return dict(n=len(df), spearman=df["stress"].corr(df["yield_resid"], method="spearman"))


# --------------------------------------------------------------------- CLI
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data", help="folder with <District>.csv (date,tmax,tmin)")
    ap.add_argument("--out-dir", default="results")
    ap.add_argument("--target-days", type=float, default=None,
                    help="calibrate gdd_total per district so a 18-Nov sowing matures in this many days "
                         "(sourced observations: ~128 d Tando Jam, ~139-142 d Faisalabad)")
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    for f in sorted(os.listdir(a.data_dir)):
        if not f.endswith(".csv"):
            continue
        name = f[:-4]
        if name not in DISTRICT_PROVINCE:
            print(f"skip {name}: add it to config.DISTRICT_PROVINCE"); continue
        w = pd.read_csv(os.path.join(a.data_dir, f), parse_dates=["date"], index_col="date").sort_index()
        win = WINDOWS[DISTRICT_PROVINCE[name]]
        cfg = ModelConfig()
        if a.target_days:
            cfg.gdd_total = calibrate_gdd_total(w, "11-18", int(a.target_days), cfg)
            print(f"{name}: calibrated gdd_total = {cfg.gdd_total:.0f}")
        rec = recommend(w, win, cfg)
        rec.to_csv(os.path.join(a.out_dir, f"{name}_per_year.csv"), index=False)
        scenario_table(w, win, cfg).to_csv(os.path.join(a.out_dir, f"{name}_scenarios.csv"), index=False)
        sensitivity(w, win, cfg).to_csv(os.path.join(a.out_dir, f"{name}_sensitivity.csv"), index=False)
        s = summarize(rec, win, cfg)
        print(name, s)
        if not s["phenology_ok"]:
            print(f"  WARNING {name}: median days-to-maturity {s['median_days_to_maturity']:.0f} is outside the sourced "
                  f"{cfg.ref_days_to_maturity} range; run calibrate_gdd_total() and set cfg.gdd_total.")


if __name__ == "__main__":
    main()