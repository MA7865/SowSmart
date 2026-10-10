import base64
import json
import os
from pathlib import Path
import numpy as np
import pandas as pd
import streamlit as st
import importlib.util
from config import DISTRICT_PROVINCE, ModelConfig, WINDOWS
from sowing_model import calibrate_gdd_total, recommend
from style import inject_css, urdu_html

st.set_page_config(
    page_title="Wheat Sowing Advisor",
    layout="wide",
)
inject_css()

def bilingual_label(english, urdu=None):
    if not urdu:
        return english
    return f"{english} | {urdu}"


def district_label(name):
    return name


def show_bilingual(english, urdu=None, container=st, style="markdown"):
    text = bilingual_label(english, urdu)
    getattr(container, style)(text)


# ---------------- load data (real if present, otherwise fake) ----------------
USING_MOCK = not os.path.exists("results.json")
DATA_FILE = "results_mock.json" if USING_MOCK else "results.json"


@st.cache_data
def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


res = load_json(DATA_FILE)
APP_DIR = Path(__file__).resolve().parent
LATEST_RESULTS_PATH = APP_DIR / "wheat-advisor" / "results.json"
LATEST_YEARLY_DIR = APP_DIR / "wheat-advisor" / "results"


@st.cache_data
def load_versioned_json(path, modified_at):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def load_versioned_csv(path, modified_at):
    return pd.read_csv(path)

@st.cache_data
def load_model_weather(path, modified_at):
    weather_df = pd.read_csv(path, parse_dates=["time"])

    required = {"time", "temperature_2m_max", "temperature_2m_min"}
    missing = required - set(weather_df.columns)
    if missing:
        raise ValueError(f"Weather file is missing columns: {sorted(missing)}")

    return (
        weather_df.rename(
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


@st.cache_data
def calculate_selected_date_results(weather_path, modified_at, district, sow_mmdd):
    weather = load_model_weather(weather_path, modified_at)
    province = DISTRICT_PROVINCE[district]

    cfg = ModelConfig()
    target_days = {"punjab": 140, "sindh": 128}[province]
    cfg.gdd_total = calibrate_gdd_total(
        weather,
        sow_mmdd="11-18",
        target_days=target_days,
        cfg=cfg,
    )

    return recommend(
        weather,
        (sow_mmdd, sow_mmdd),
        cfg,
        years=range(2000, 2025),
    )

if not LATEST_RESULTS_PATH.is_file():
    st.error(f"Latest model results file was not found: {LATEST_RESULTS_PATH}")
    st.stop()

latest_results = load_versioned_json(
    str(LATEST_RESULTS_PATH),
    LATEST_RESULTS_PATH.stat().st_mtime,
)

if USING_MOCK or any(v.get("FAKE") for v in res.values()):
    show_bilingual(
        "USING FAKE DATA. Numbers are for building only. Do not present this.",
        style="error",
    )

ml = load_json("ml_results.json") if os.path.exists("ml_results.json") else None

# ---------------- Urdu helper (optional, never crashes the app) ----------------
ADVISOR_PATH = APP_DIR / "wheat-advisor" / "advisor.py"
advisor_spec = importlib.util.spec_from_file_location(
    "wheat_advisor_urdu",
    ADVISOR_PATH,
)
if advisor_spec is None or advisor_spec.loader is None:
    raise ImportError(f"Could not load Urdu advisor from {ADVISOR_PATH}")

advisor = importlib.util.module_from_spec(advisor_spec)
advisor_spec.loader.exec_module(advisor)

def get_answer(question, context):
    """Return the advisor answer and tool calls, propagating failures to the UI."""
    if advisor is None:
        raise RuntimeError("The Urdu advisor module is not connected.")
    if hasattr(advisor, "ask_agent"):
        result = advisor.ask_agent(question, context=context)
        if isinstance(result, tuple) and len(result) == 2:
            return result
        if isinstance(result, str):
            return result, []
        raise TypeError("The Urdu advisor returned an unsupported response.")
    raise RuntimeError("The Urdu advisor does not support questions.")


def save_urdu_answer(question):
    context = (
        f"The user selected district={district} and sowing date={sow} in the app. "
        "Use these only if the question does not name a district or date."
    )
    st.session_state["urdu_question"] = question
    st.session_state.pop("urdu_answer", None)
    st.session_state.pop("urdu_calls", None)
    st.session_state.pop("urdu_error", None)
    st.session_state.pop("urdu_speech_audio", None)
    st.session_state.pop("urdu_speech_text", None)
    try:
        answer, calls = get_answer(question, context)
    except Exception as exc:
        st.session_state["urdu_error"] = str(exc)
        return
    st.session_state["urdu_answer"] = answer
    st.session_state["urdu_calls"] = calls


def show_saved_urdu_answer():
    error = st.session_state.get("urdu_error")
    if error:
        show_bilingual(
            f"Could not answer this question: {error}",
            style="error",
        )
    answer = st.session_state.get("urdu_answer")
    if not answer:
        return
    calls = st.session_state.get("urdu_calls", [])
    st.markdown(
        f"<div class='urdu'>{urdu_html(answer)}</div>",
        unsafe_allow_html=True,
    )
    if st.button("Read answer aloud"):
        if advisor is None or not hasattr(advisor, "synthesize_speech"):
            show_bilingual(
                "Gemini speech generation is unavailable because the advisor module is not connected.",
                style="error",
            )
        else:
            try:
                with st.spinner("Generating Urdu speech..."):
                    st.session_state["urdu_speech_audio"] = advisor.synthesize_speech(answer)
                    st.session_state["urdu_speech_text"] = answer
            except Exception as exc:
                show_bilingual(
                    f"Could not generate speech: {exc}",
                    style="error",
                )
    if (
        st.session_state.get("urdu_speech_text") == answer
        and st.session_state.get("urdu_speech_audio")
    ):
        st.audio(st.session_state["urdu_speech_audio"], format="audio/wav")
    if calls:
        with st.expander("How the helper got its numbers (tool calls)"):
            st.json(calls)
    show_bilingual(
        "The helper only uses numbers from this tool. It does not give advice on seed, "
        "fertilizer, irrigation or pesticides.",
        style="caption",
    )
    if not calls:
        show_bilingual(
            "The helper returned a plain fallback answer without tool-call metadata.",
            style="caption",
        )


with open("logo.jpeg", "rb") as logo_file:
    logo_data = base64.b64encode(logo_file.read()).decode("ascii")
st.markdown(
    f"<div class='brand-header'>"
    f"<img class='brand-logo' src='data:image/jpeg;base64,{logo_data}' alt='SowSmart logo'>"
    "<div><div class='brand-name'>SowSmart</div>"
    "<div class='brand-subtitle'>Wheat Sowing Advisor</div></div>"
    "</div>",
    unsafe_allow_html=True,
)
st.caption(
    "Source of numbers: Open-Meteo / ERA5 weather, 2000 to 2025, run through a simple wheat simulator.",
)

# ---------------- map ----------------
map_rows = []

for model_name, model_data in latest_results.items():
    coordinate_name = model_name.replace("_", " ")

    if coordinate_name not in res:
        st.error(f"Missing map coordinates for {coordinate_name}.")
        st.stop()

    median_date = model_data["summary"]["median"]
    selected_day = pd.to_datetime(
        f"{median_date} 2001",
        format="%d %b %Y",
    ).dayofyear

    map_rows.append(
        {
            "district": coordinate_name,
            "lat": res[coordinate_name]["lat"],
            "lon": res[coordinate_name]["lon"],
            "median_selected_day": selected_day,
            "recommended_range": (
                f'{model_data["summary"]["p10"]} to '
                f'{model_data["summary"]["p90"]}'
            ),
        }
    )

map_df = pd.DataFrame(map_rows)

try:
    import plotly.express as px

    fig = px.scatter_mapbox(
        map_df,
        lat="lat",
        lon="lon",
        color="median_selected_day",
        hover_name="district",
        hover_data={
            "recommended_range": True,
            "median_selected_day": False,
        },
        zoom=4.5,
        height=380,
        mapbox_style="open-street-map",
        color_continuous_scale="YlOrRd",
    )
    fig.update_traces(marker={"size": 16})
    fig.update_layout(
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        coloraxis_colorbar_title="Median date (day of year)",
    )
    st.plotly_chart(fig, use_container_width=True)
except Exception:
    st.map(map_df[["lat", "lon"]], latitude="lat", longitude="lon")

# ---------------- selectors ----------------
c1, c2 = st.columns(2)
district = c1.selectbox(
    bilingual_label("District", "ضلع"),
    list(res.keys()),
    format_func=district_label,
)
d = res[district]
default_i = d["labels"].index("11-15") if "11-15" in d["labels"] else 0
sow = c2.selectbox(
    bilingual_label("Your sowing date (month-day)", "آپ کی بوائی کی تاریخ (مہینہ-دن)"),
    d["labels"],
    index=default_i,
)

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

tab_keys = ["Latest model", "Advisor", "25-year drift", "Ask in Urdu", "Limits"]
tab_names = [
    bilingual_label("Latest model", "جدید ماڈل"),
    bilingual_label("Advisor", "مشیر"),
    bilingual_label("25-year drift", "25 سالہ رجحان"),
    bilingual_label("Ask in Urdu", "اردو میں پوچھیں"),
    bilingual_label("Limits", "حدود"),
]
if ml is not None:
    tab_keys.insert(4, "Satellite check")
    tab_names.insert(4, bilingual_label("Satellite check", "سیٹلائٹ جانچ"))
tabs = dict(zip(tab_keys, st.tabs(tab_names)))


# ---------------- Latest model tab ----------------
with tabs["Latest model"]:
    show_bilingual("Latest wheat model", "جدید گندم ماڈل", style="header")
    st.caption(
        "These results come from the newer season-specific model. "
        "They are separate from the older model shown in the other tabs."
    )
    st.warning(
        "Historical simulation, not a forecast. A season's selected date "
        "is calculated using that season's weather; it is not necessarily "
        "the date farmers actually sowed."
    )

    districts = sorted(latest_results)
    latest_district = st.selectbox(
        bilingual_label("District for latest model", "جدید ماڈل کے لیے ضلع"),
        districts,
        format_func=lambda name: name.replace("_", " "),
        key="latest_model_district",
    )

    district_result = latest_results[latest_district]
    summary = district_result["summary"]

    col1, col2, col3 = st.columns(3)
    col1.metric(
        bilingual_label("Median model-selected date", "ماڈل کی منتخب کردہ درمیانی تاریخ"),
        summary["median"],
    )
    col2.metric(
        bilingual_label("Historical date range (P10–P90)", "تاریخی تاریخ کی حد (P10–P90)"),
        f'{summary["p10"]} to {summary["p90"]}',
    )
    col3.metric(
        bilingual_label("Median latest acceptable date", "تازہ ترین قابل قبول تاریخ کی درمیانی قدر"),
        summary["median_latest_ok"],
    )

    st.caption(
        f'Model summary covers {summary["n_years"]} years. '
        f'Median days to maturity: {summary["median_days_to_maturity"]:.0f}. '
        f'Calibrated GDD total: {district_result["gdd_total"]:.1f}.'
    )

    if summary["pct_edge"] > 0:
        st.info(
            f'The selected date was at the edge of the tested sowing window '
            f'in {summary["pct_edge"]:.0f}% of the years. Interpret the '
            "recommendation cautiously."
        )

    show_bilingual("Warming scenarios", "گرمائش کے منظرنامے", style="subheader")
    st.caption(
        "These are model scenarios that shift historical weather by the "
        "listed amount. They are not forecasts for a particular future year."
    )

    scenarios = pd.DataFrame(district_result["scenarios"])
    scenario_columns = [
        "scenario",
        "median",
        "p10",
        "p90",
        "median_heat",
        "heat_at_ref_sowing",
        "pct_edge",
    ]
    st.dataframe(
        scenarios[scenario_columns],
        hide_index=True,
    )

    show_bilingual("Year-by-year model results", "سال بہ سال ماڈل کے نتائج", style="subheader")

    yearly_path = (
    LATEST_YEARLY_DIR
    / f"{latest_district}_per_year.csv"
    )

    if not yearly_path.is_file():
        st.error(
            f"Yearly results file was not found for "
            f"{latest_district.replace('_', ' ')}: {yearly_path}"
        )
        st.stop()

    yearly = load_versioned_csv(
        str(yearly_path),
        yearly_path.stat().st_mtime,
    )

    chart_data = yearly.set_index("year")[["score", "heat", "warm"]]
    st.line_chart(
        chart_data,
        alt="Annual model stress score and heat and warmth components",
    )
    st.caption(
        "The score combines weighted model stress components. The heat and "
        "warm columns are model quantities, not observed yield losses."
    )

# ---------------- Advisor tab ----------------
with tabs["Advisor"]:
    show_bilingual("Sowing-date advisor", "بوائی کی تاریخ کا مشیر", style="header")
    st.caption(
        "The selected date is simulated with the newer model across historical "
        "weather. It is not a forecast for the current season."
    )

    advisor_district = st.selectbox(
        bilingual_label("District", "ضلع"),
        sorted(latest_results),
        format_func=lambda name: name.replace("_", " "),
        key="advisor_district",
    )

    province = DISTRICT_PROVINCE[advisor_district]
    window_start, window_end = WINDOWS[province]
    available_dates = [
        date.strftime("%m-%d")
        for date in pd.date_range(
            f"2001-{window_start}",
            f"2001-{window_end}",
        )
    ]
    default_date = "11-15" if "11-15" in available_dates else available_dates[0]

    sow_mmdd = st.selectbox(
        bilingual_label("Date to simulate (month-day)", "جانچنے کی تاریخ"),
        available_dates,
        index=available_dates.index(default_date),
        key="advisor_sowing_date",
    )

    weather_path = (
        APP_DIR
        / "wheat-advisor"
        / "cache"
        / f"{advisor_district}.csv"
    )

    if not weather_path.is_file():
        st.error(f"Weather file was not found: {weather_path}")
        st.stop()

    selected_date_results = calculate_selected_date_results(
        str(weather_path),
        weather_path.stat().st_mtime,
        advisor_district,
        sow_mmdd,
    )

    yearly_path = LATEST_YEARLY_DIR / f"{advisor_district}_per_year.csv"
    if not yearly_path.is_file():
        st.error(f"Yearly results file was not found: {yearly_path}")
        st.stop()

    advisor_yearly = load_versioned_csv(
        str(yearly_path),
        yearly_path.stat().st_mtime,
    )

    best_results = advisor_yearly[["year", "best_date", "score"]].rename(
        columns={"score": "best_score"}
    )
    comparison = selected_date_results[
        ["year", "score", "heat", "warm", "frost", "late_days", "maturity"]
    ].merge(
        best_results,
        on="year",
        how="inner",
        validate="one_to_one",
    )

    if comparison.empty:
        st.warning("There are no matching historical seasons to compare.")
        st.stop()

    comparison["extra_stress_vs_best"] = (
        comparison["score"] - comparison["best_score"]
    )

    summary = latest_results[advisor_district]["summary"]
    col1, col2, col3 = st.columns(3)
    col1.metric(bilingual_label("Date being simulated", "زیرِ جائزہ تاریخ"), sow_mmdd)
    col2.metric(
        bilingual_label("Median model-selected date", "ماڈل کی منتخب کردہ درمیانی تاریخ"),
        summary["median"],
    )
    col3.metric(
        bilingual_label(
            "Median extra stress vs. each year's selected date",
            "ہر سال کی منتخب تاریخ کے مقابلے میں اضافی دباؤ",
        ),
        f'{comparison["extra_stress_vs_best"].median():+.2f}',
    )

    st.caption(
        f'Historical model-selected dates range from {summary["p10"]} to '
        f'{summary["p90"]} for the middle 80% of years. '
        "This is a historical date distribution, not a guaranteed safe window."
    )

    show_bilingual(
        "Stress score by historical year",
        "تاریخی سال کے دباؤ کا اسکور",
        style="subheader",
    )
    st.line_chart(
        comparison.set_index("year")[["score", "best_score"]],
        alt="New-model stress for the chosen date compared with each year's model-selected date",
    )

    st.dataframe(
        comparison[
            [
                "year",
                "best_date",
                "score",
                "best_score",
                "extra_stress_vs_best",
                "heat",
                "warm",
                "frost",
                "late_days",
                "maturity",
            ]
        ],
        hide_index=True,
    )

    st.caption(
        "Stress scores and components are model simulations, not observed "
        "yield loss or proof of crop damage."
    )

# ---------------- drift tab ----------------
with tabs["25-year drift"]:
    st.write(
        "Descriptive trend in the newer model's selected sowing dates. "
        "Positive values mean later dates relative to November 1."
    )

    rows = []

    for district_name in sorted(latest_results):
        yearly_path = LATEST_YEARLY_DIR / f"{district_name}_per_year.csv"

        if not yearly_path.is_file():
            st.error(f"Yearly results file was not found: {yearly_path}")
            st.stop()

        district_yearly = load_versioned_csv(
            str(yearly_path),
            yearly_path.stat().st_mtime,
        ).sort_values("year")

        years = pd.to_numeric(district_yearly["year"], errors="raise")
        best_dates = pd.to_datetime(district_yearly["best_date"])
        nov_first = pd.to_datetime(years.astype(str) + "-11-01")
        days_from_november = (best_dates - nov_first).dt.days

        slope_days_per_decade = (
            np.polyfit(
                years.to_numpy(dtype=float),
                days_from_november.to_numpy(dtype=float),
                1,
            )[0]
            * 10
        )

        rows.append(
            {
                "District": district_name.replace("_", " "),
                "Years": len(district_yearly),
                "First model-selected date": best_dates.iloc[0].date(),
                "Last model-selected date": best_dates.iloc[-1].date(),
                "Descriptive change (days/decade)": round(
                    slope_days_per_decade, 2
                ),
            }
        )

    st.dataframe(pd.DataFrame(rows), hide_index=True)
    st.caption(
        "This is a descriptive trend, not a statistical significance test "
        "or a forecast."
    )
# ---------------- Urdu tab ----------------
with tabs["Ask in Urdu"]:
    st.write("Ask in Urdu or Roman Urdu, for example: Multan mein 28 November ko gandum bona kaisa rahega?")
    q = st.text_input("Your question")
    if st.button("Ask") and q.strip():
        context = (
            f"The user selected district={district} and sowing date={sow} in the app. "
            f"Use these only if the question does not name a district or date."
        )
        answer, calls = get_answer(q, context)
        st.markdown(
            f"<div class='urdu'>{urdu_html(answer)}</div>",
            unsafe_allow_html=True,
        )
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
            st.success(
                "The satellite-trained model beat both simple baselines in leave-one-year-out testing."
            )
        else:
            st.warning(
                "The satellite-trained model did NOT beat the simple baselines. Reported honestly."
            )
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
        if ml.get("notes"):
            st.write(ml["notes"])
        if ml.get("season_2022"):
            st.subheader("2022 held-out season: predicted vs actual late-season greenness")
            st.dataframe(pd.DataFrame(ml["season_2022"]).T)
        st.caption(
            "Greenness (NDVI) is a stand-in, not yield. 250 m satellite pixels mix crops.",
        )

# ---------------- Limits tab ----------------
with tabs["Limits"]:
    st.markdown(
        "- Estimates **simulated heat exposure**, not yield or income.\n"
        "- District-center weather at roughly 10 km resolution, not farm-level.\n"
        "- Simulator settings are **tuned** against official calendars. That is tuning, not independent proof.\n"
        "- Advice reflects the **last 25 years**. It is not a forecast for this season.\n"
        "- No irrigation, canal water, seed variety, fertilizer or crop-rotation effects.\n"
        "- Eight irrigated-plains districts do not represent rainfed or mountain areas.\n"
        '- "Share of past years" is not a true probability.',
    )
