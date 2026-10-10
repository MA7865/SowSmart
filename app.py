import json
import os

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Wheat Sowing Advisor", layout="wide")

# ---------------- load data (real if present, otherwise fake) ----------------
USING_MOCK = not os.path.exists("results.json")
DATA_FILE = "results_mock.json" if USING_MOCK else "results.json"


@st.cache_data
def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


res = load_json(DATA_FILE)
if USING_MOCK or any(v.get("FAKE") for v in res.values()):
    st.error("USING FAKE DATA. Numbers are for building only. Do not present this.")

ml = load_json("ml_results.json") if os.path.exists("ml_results.json") else None

suspicious_best_dates = []
for district, values in res.items():
    labels = values.get("labels", [])
    best = values.get("best")
    if best and labels and best == labels[0]:
        suspicious_best_dates.append(district)
if suspicious_best_dates:
    st.warning(
        "Data check: several districts show the best sowing date at the very start of the tested window. "
        "Please confirm with the data team before presenting these numbers."
    )

# ---------------- Urdu helper (optional, never crashes the app) ----------------
try:
    import advisor
except Exception:
    advisor = None


def get_answer(facts, question, context):
    """Try the agent, then the simple helper, then the template. Returns (text, tool_calls)."""
    if advisor is None:
        return "The Urdu helper is not connected yet.", []
    if hasattr(advisor, "ask_agent"):
        try:
            result = advisor.ask_agent(question, context=context, facts=facts)
            if isinstance(result, tuple) and len(result) == 2:
                return result
            if isinstance(result, str):
                return result, []
        except Exception:
            pass
    try:
        result = advisor.ask(facts, question)
        return result, []
    except Exception:
        pass
    try:
        return advisor.fallback_answer(facts), []
    except Exception:
        return "The helper is unavailable right now.", []


# ---------------- styles ----------------
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu&display=swap');
html, body, [data-testid="stAppViewContainer"] {
    background: linear-gradient(180deg, #07131f 0%, #0d1d2b 100%);
    color: #f3f6fb;
}
.stApp {
    background: transparent;
}
.urdu {direction: rtl; text-align: right; font-family: 'Noto Nastaliq Urdu', serif;
       font-size: 22px; line-height: 2.2;}
</style>
""",
    unsafe_allow_html=True,
)

# ---------------- sidebar: limits always visible ----------------
with st.sidebar:
    st.header("Read this first")
    st.warning(
        "Prototype. Estimates simulated heat exposure by sowing date from 25 years of "
        "weather (Open-Meteo / ERA5). NOT a yield prediction. NOT a forecast for this season. "
        "District-center weather, not farm-level. No irrigation, canal water, variety or "
        "rotation effects."
    )
    st.caption("Wheat often follows cotton or sugarcane, so earlier sowing is not always possible.")

st.title("Wheat Sowing Advisor (prototype)")
st.caption("Source of numbers: Open-Meteo / ERA5 weather, 2000 to 2025, run through a simple wheat simulator.")

# ---------------- map ----------------
map_df = pd.DataFrame([
    {"district": k, "lat": v["lat"], "lon": v["lon"]} for k, v in res.items()
])
try:
    import plotly.express as px

    mdf = pd.DataFrame(
        [
            {
                "district": k,
                "lat": v["lat"],
                "lon": v["lon"],
                "best_day_number": v["labels"].index(v["best"]),
                "best": v["best"],
            }
            for k, v in res.items()
        ]
    )
    fig = px.scatter_mapbox(
        mdf,
        lat="lat",
        lon="lon",
        color="best_day_number",
        hover_name="district",
        hover_data={"best": True, "best_day_number": False},
        zoom=4.5,
        height=380,
        mapbox_style="open-street-map",
        color_continuous_scale="YlOrRd",
    )
    fig.update_traces(marker={"size": 16})
    fig.update_layout(
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        coloraxis_colorbar_title="Best day",
    )
    st.plotly_chart(fig, use_container_width=True)
except Exception:
    st.map(map_df, latitude="lat", longitude="lon")

# ---------------- selectors ----------------
c1, c2 = st.columns(2)
district = c1.selectbox("District", list(res.keys()))
d = res[district]
default_i = d["labels"].index("11-15") if "11-15" in d["labels"] else 0
sow = c2.selectbox("Your sowing date (month-day)", d["labels"], index=default_i)

i = d["labels"].index(sow)
j = d["labels"].index(d["best"])
your, best = d["mean_curve"][i], d["mean_curve"][j]

facts = {
    "district": district,
    "chosen_sowing_date": sow,
    "safest_window": [d["window_start"], d["window_end"]],
    "best_day": d["best"],
    "extra_stress_vs_best": round(your - best, 1),
    "share_of_past_years_best_day_was_ok": d["share_of_years_ok"],
    "backtest_2022": d["backtest_2022"],
}

tab_names = ["Advisor", "2022 check", "25-year drift", "Ask in Urdu", "Limits"]
if ml is not None:
    tab_names.insert(4, "Satellite check")
tabs = dict(zip(tab_names, st.tabs(tab_names)))

# ---------------- Advisor tab ----------------
with tabs["Advisor"]:
    m1, m2, m3 = st.columns(3)
    m1.metric("Safest window", f"{d['window_start']} to {d['window_end']}")
    m2.metric("Best day", d["best"])
    m3.metric("Your date: extra stress vs best", f"{your - best:+.1f}")
    st.caption("Stress = heat days in grain filling + 2 x frost days + 2 x days of late maturity. Lower is safer.")
    if d.get("edge_warning"):
        st.warning("The best date is at the edge of the tested range for this district. Treat with care.")

    st.subheader("Stress by sowing date (average of 25 years)")
    st.line_chart(pd.DataFrame({"stress": d["mean_curve"]}, index=d["labels"]))

    st.subheader("What if I sow earlier or later?")
    shift = st.slider("Move my sowing date by (days)", -30, 30, 0)
    k = max(0, min(len(d["labels"]) - 1, i + shift))
    st.write(
        f"Sowing on **{d['labels'][k]}**: stress {d['mean_curve'][k]:.1f} "
        f"(your chosen date: {your:.1f}, change {d['mean_curve'][k] - your:+.1f})."
    )
    st.caption(
        f"Share of past years in which the best day was within tolerance of that year's best: "
        f"{d['share_of_years_ok']:.0%}. This is not a forecast probability."
    )

# ---------------- 2022 tab ----------------
with tabs["2022 check"]:
    b = d["backtest_2022"]
    st.write(
        f"At the standard sowing date (15 Nov), the 2022 season had "
        f"**{b['heat_days_std_sowing']} heat days** in grain filling in {district}. "
        f"That is hotter than about **{b['percentile_hot_year']}%** of seasons from 2001 to 2021."
    )
    st.subheader("Heat days in 2022 by sowing date (simulation)")
    hd = b["heat_days_by_sowing_date"]
    st.bar_chart(pd.DataFrame({"heat days": list(hd.values())}, index=list(hd.keys())))
    st.caption("A simulation check, not proof of crop losses.")
    st.subheader("All districts")
    st.dataframe(
        pd.DataFrame(
            {
                k: {
                    "Heat days at 15 Nov sowing (2022)": v["backtest_2022"]["heat_days_std_sowing"],
                    "Hotter than % of earlier years": v["backtest_2022"]["percentile_hot_year"],
                }
                for k, v in res.items()
            }
        ).T
    )

# ---------------- drift tab ----------------
with tabs["25-year drift"]:
    st.write("Has the best sowing date moved over 25 years? Positive numbers mean later.")
    rows = {}
    for k_, v in res.items():
        p_value = v.get("drift_p_value")
        if p_value is None:
            verdict = "not enough information"
        else:
            verdict = "clear shift" if p_value < 0.05 else "no clear shift"
        rows[k_] = {
            "Days per decade": v["drift_days_per_decade"],
            "p-value": p_value if p_value is not None else "n/a",
            "Verdict": verdict,
        }
    st.dataframe(pd.DataFrame(rows).T)
    st.caption("A p-value above 0.05 means we cannot say the date moved. A null p-value means the trend could not be tested in this dataset.")

# ---------------- Urdu tab ----------------
with tabs["Ask in Urdu"]:
    st.write("Ask in Urdu or Roman Urdu, for example: Multan mein 28 November ko gandum bona kaisa rahega?")
    q = st.text_input("Your question")
    if st.button("Ask") and q.strip():
        context = (
            f"The user selected district={district} and sowing date={sow} in the app. "
            f"Use these only if the question does not name a district or date."
        )
        answer, calls = get_answer(facts, q, context)
        st.markdown(f"<div class='urdu'>{answer.replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)
        if calls:
            with st.expander("How the helper got its numbers (tool calls)"):
                st.json(calls)
        st.caption(
            "The helper only uses numbers from this tool. It does not give advice on seed, "
            "fertilizer, irrigation or pesticides."
        )
        if not calls:
            st.caption("The helper returned a plain fallback answer without tool-call metadata.")

# ---------------- Satellite tab (only if D delivered ml_results.json) ----------------
if ml is not None:
    with tabs["Satellite check"]:
        if ml.get("passed"):
            st.success("The satellite-trained model beat both simple baselines in leave-one-year-out testing.")
        else:
            st.warning("The satellite-trained model did NOT beat the simple baselines. Reported honestly.")
        st.table(
            pd.DataFrame(
                {
                    "Error (lower is better)": {
                        "Model": ml["cv_rmse_model"],
                        "Baseline: district average": ml["cv_rmse_baseline_mean"],
                        "Baseline: district trend": ml["cv_rmse_baseline_trend"],
                    }
                }
            )
        )
        st.write(ml.get("notes", ""))
        if ml.get("season_2022"):
            st.subheader("2022 held-out season: predicted vs actual late-season greenness")
            st.dataframe(pd.DataFrame(ml["season_2022"]).T)
        st.caption("Greenness (NDVI) is a stand-in, not yield. 250 m satellite pixels mix crops.")

# ---------------- Limits tab ----------------
with tabs["Limits"]:
    st.markdown(
        """
- Estimates **simulated heat exposure**, not yield or income.
- District-center weather at roughly 10 km resolution, not farm-level.
- Simulator settings are **tuned** against official calendars. That is tuning, not independent proof.
- Advice reflects the **last 25 years**. It is not a forecast for this season.
- No irrigation, canal water, seed variety, fertilizer or crop-rotation effects.
- Eight irrigated-plains districts do not represent rainfed or mountain areas.
- "Share of past years" is not a true probability.
    """
    )
