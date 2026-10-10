import base64
import html
import json
import os
from pathlib import Path
import numpy as np
import pandas as pd
import streamlit as st
import importlib.util
from config import DISTRICT_PROVINCE, ModelConfig, WINDOWS
from sowing_model import calibrate_gdd_total, recommend

st.set_page_config(
    page_title="Wheat Sowing Advisor",
    layout="wide",
)

URDU_DISTRICTS = {
    "Faisalabad": "فیصل آباد",
    "Multan": "ملتان",
    "Bahawalpur": "بہاولپور",
    "Rahim Yar Khan": "رحیم یار خان",
    "Sargodha": "سرگودھا",
    "Sahiwal": "ساہیوال",
    "Larkana": "لاڑکانہ",
    "Hyderabad": "حیدرآباد",
}

def bilingual_label(english, urdu):
    return f"{english} | {urdu}"


def district_label(name):
    return bilingual_label(name, URDU_DISTRICTS.get(name, name))


def show_bilingual(english, urdu, container=st, style="markdown"):
    english_column, urdu_column = container.columns(2)
    getattr(english_column, style)(english)
    urdu_column.markdown(
        f"<div class='urdu'>{html.escape(urdu).replace(chr(10), '<br>')}</div>",
        unsafe_allow_html=True,
    )


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
        "یہ فرضی ڈیٹا ہے۔ اعداد صرف ایپ بنانے کے لیے ہیں، انہیں پیش نہ کریں۔",
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
            f"اس سوال کا جواب نہیں دے سکے۔ تفصیل: {error}",
            style="error",
        )
    answer = st.session_state.get("urdu_answer")
    if not answer:
        return
    calls = st.session_state.get("urdu_calls", [])
    safe_answer = html.escape(answer).replace("\n", "<br>")
    st.markdown(
        f"<div class='urdu'>{safe_answer}</div>",
        unsafe_allow_html=True,
    )
    if st.button(bilingual_label("Read answer aloud", "جواب بلند آواز میں سنیں")):
        if advisor is None or not hasattr(advisor, "synthesize_speech"):
            show_bilingual(
                "Gemini speech generation is unavailable because the advisor module is not connected.",
                "ایڈوائزر ماڈیول منسلک نہیں، اس لیے Gemini سے آواز بنانا دستیاب نہیں۔",
                style="error",
            )
        else:
            try:
                with st.spinner(bilingual_label("Generating Urdu speech...", "اردو آواز تیار ہو رہی ہے...")):
                    st.session_state["urdu_speech_audio"] = advisor.synthesize_speech(answer)
                    st.session_state["urdu_speech_text"] = answer
            except Exception as exc:
                show_bilingual(
                    f"Could not generate speech: {exc}",
                    f"آواز تیار نہیں ہو سکی۔ تفصیل: {exc}",
                    style="error",
                )
    if (
        st.session_state.get("urdu_speech_text") == answer
        and st.session_state.get("urdu_speech_audio")
    ):
        st.audio(st.session_state["urdu_speech_audio"], format="audio/wav")
    if calls:
        with st.expander(bilingual_label("How the helper got its numbers (tool calls)", "مددگار نے اعداد کیسے حاصل کیے؟")):
            st.json(calls)
    show_bilingual(
        "The helper only uses numbers from this tool. It does not give advice on seed, "
        "fertilizer, irrigation or pesticides.",
        "مددگار صرف اس آلے کے اعداد استعمال کرتا ہے۔ یہ بیج، کھاد، آبپاشی یا کیڑے مار ادویات کے بارے میں مشورہ نہیں دیتا۔",
        style="caption",
    )
    if not calls:
        show_bilingual(
            "The helper returned a plain fallback answer without tool-call metadata.",
            "مددگار نے ٹول کی تفصیل کے بغیر ایک سادہ متبادل جواب دیا ہے۔",
            style="caption",
        )


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
       font-size: 16px; line-height: 1.8; color: #202820;}
.brand-name {color: #285d36; font-size: 2.5rem; font-weight: 700; line-height: 1.15;}
.brand-subtitle {color: #202820; font-size: 1rem; margin-top: 0.25rem;}
.brand-header {display: flex; align-items: center; gap: 1.25rem; margin: 0.5rem 0 1rem;}
.brand-logo {width: 120px; height: 120px; object-fit: contain; flex: 0 0 auto;}
</style>
""",
    unsafe_allow_html=True,
)

# ---------------- sidebar: limits always visible ----------------
with st.sidebar:
    st.header(bilingual_label("Read this first", "پہلے یہ پڑھیں"))
    show_bilingual(
        "Prototype. Estimates simulated heat exposure by sowing date from 25 years of "
        "weather (Open-Meteo / ERA5). NOT a yield prediction. NOT a forecast for this season. "
        "District-center weather, not farm-level. No irrigation, canal water, variety or "
        "rotation effects.",
        "یہ ایک ابتدائی نمونہ ہے۔ بوائی کی تاریخ کے مطابق گزشتہ 25 برس کے موسم (Open-Meteo / ERA5) سے "
        "گرمی کا تخمینہ لگایا گیا ہے۔ یہ پیداوار کی پیش گوئی یا موجودہ موسم کا اندازہ نہیں۔ ڈیٹا ضلع کے مرکز "
        "کا ہے، کھیت کا نہیں؛ آبپاشی، نہری پانی، قسم یا فصلوں کی گردش شامل نہیں۔",
        container=st.sidebar,
        style="warning",
    )
    show_bilingual(
        "Wheat often follows cotton or sugarcane, so earlier sowing is not always possible.",
        "گندم اکثر کپاس یا گنے کے بعد کاشت ہوتی ہے، اس لیے جلد بوائی ہمیشہ ممکن نہیں ہوتی۔",
        container=st.sidebar,
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
        coloraxis_colorbar_title=bilingual_label("Median date (day of year)", "بہترین دن"),
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
sow = c2.selectbox(bilingual_label("Your sowing date (month-day)", "آپ کی بوائی کی تاریخ (مہینہ-دن)"), d["labels"], index=default_i)

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

tab_names = ["Latest model",  bilingual_label("Advisor", "رہنما"),  bilingual_label("25-year drift", "25 سالہ رجحان"), bilingual_label("Ask in Urdu", "اردو میں پوچھیں"), bilingual_label("Limits", "حدود")]
if ml is not None:
    tab_names.insert(4, bilingual_label("Satellite check", "سیٹلائٹ کا جائزہ"))
tabs = dict(zip(tab_names, st.tabs(tab_names)))


# ---------------- Latest model tab ----------------
with tabs["Latest model"]:
    st.header("Latest wheat model")
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
        "District for latest model",
        districts,
        format_func=lambda name: name.replace("_", " "),
        key="latest_model_district",
    )

    district_result = latest_results[latest_district]
    summary = district_result["summary"]

    col1, col2, col3 = st.columns(3)
    col1.metric("Median model-selected date", summary["median"])
    col2.metric(
        "Historical date range (P10–P90)",
        f'{summary["p10"]} to {summary["p90"]}',
    )
    col3.metric(
        "Median latest acceptable date",
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

    st.subheader("Warming scenarios")
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

    st.subheader("Year-by-year model results")

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
with tabs[bilingual_label("Advisor", "رہنما")]:
    st.header("Sowing-date advisor")
    st.caption(
        "The selected date is simulated with the newer model across historical "
        "weather. It is not a forecast for the current season."
    )

    advisor_district = st.selectbox(
        "District",
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
        "Date to simulate (month-day)",
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
    col1.metric("Date being simulated", sow_mmdd)
    col2.metric("Median model-selected date", summary["median"])
    col3.metric(
        "Median extra stress vs. each year's selected date",
        f'{comparison["extra_stress_vs_best"].median():+.2f}',
    )

    st.caption(
        f'Historical model-selected dates range from {summary["p10"]} to '
        f'{summary["p90"]} for the middle 80% of years. '
        "This is a historical date distribution, not a guaranteed safe window."
    )

    st.subheader("Stress score by historical year")
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
with tabs[bilingual_label("25-year drift", "25 سالہ رجحان")]:
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
with tabs[bilingual_label("Ask in Urdu", "اردو میں پوچھیں")]:
    st.write("Ask in Urdu or Roman Urdu, for example: Multan mein 28 November ko gandum bona kaisa rahega?")
    q = st.text_input("Your question")
    if st.button("Ask") and q.strip():
        context = (
            f"The user selected district={district} and sowing date={sow} in the app. "
            f"Use these only if the question does not name a district or date."
        )
        answer, calls = get_answer(q, context)
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
    with tabs[bilingual_label("Satellite check", "سیٹلائٹ کا جائزہ")]:
        if ml.get("passed"):
            show_bilingual(
                "The satellite-trained model beat both simple baselines in leave-one-year-out testing.",
                "سال چھوڑ کر جانچنے میں سیٹلائٹ سے تربیت یافتہ ماڈل دونوں سادہ بنیادی ماڈلز سے بہتر رہا۔",
                style="success",
            )
        else:
            show_bilingual(
                "The satellite-trained model did NOT beat the simple baselines. Reported honestly.",
                "سیٹلائٹ سے تربیت یافتہ ماڈل سادہ بنیادی ماڈلز سے بہتر نہیں رہا۔ نتیجہ اسی طرح پیش کیا گیا ہے۔",
                style="warning",
            )
        st.table(
            pd.DataFrame(
                {
                    bilingual_label("Error (lower is better)", "غلطی (کم بہتر ہے)"): {
                        bilingual_label("Model", "ماڈل"): ml["cv_rmse_model"],
                        bilingual_label("Baseline: district average", "بنیاد: ضلع کی اوسط"): ml["cv_rmse_baseline_mean"],
                        bilingual_label("Baseline: district trend", "بنیاد: ضلع کا رجحان"): ml["cv_rmse_baseline_trend"],
                    }
                }
            )
        )
        if ml.get("notes"):
            show_bilingual(ml["notes"], "ماڈل کی اضافی تفصیل بائیں جانب انگریزی میں دی گئی ہے۔")
        if ml.get("season_2022"):
            show_bilingual("2022 held-out season: predicted vs actual late-season greenness",
                           "2022 کا الگ رکھا گیا موسم: موسم کے آخر کی سبزی، اندازہ بمقابلہ حقیقت", style="subheader")
            st.dataframe(pd.DataFrame(ml["season_2022"]).T)
        show_bilingual(
            "Greenness (NDVI) is a stand-in, not yield. 250 m satellite pixels mix crops.",
            "سبزی (NDVI) فصل کی پیداوار کا متبادل پیمانہ ہے، اصل پیداوار نہیں۔ 250 میٹر کے سیٹلائٹ پکسلز میں مختلف فصلیں شامل ہو سکتی ہیں۔",
            style="caption",
        )

# ---------------- Limits tab ----------------
with tabs[bilingual_label("Limits", "حدود")]:
    show_bilingual(
        "- Estimates **simulated heat exposure**, not yield or income.\n"
        "- District-center weather at roughly 10 km resolution, not farm-level.\n"
        "- Simulator settings are **tuned** against official calendars. That is tuning, not independent proof.\n"
        "- Advice reflects the **last 25 years**. It is not a forecast for this season.\n"
        "- No irrigation, canal water, seed variety, fertilizer or crop-rotation effects.\n"
        "- Eight irrigated-plains districts do not represent rainfed or mountain areas.\n"
        '- "Share of past years" is not a true probability.',
        "- یہ **تخمینی گرمی کے دباؤ** کو دکھاتا ہے، پیداوار یا آمدنی کو نہیں۔\n"
        "- موسم کا ڈیٹا تقریباً 10 کلومیٹر ریزولوشن پر ضلع کے مرکز کا ہے، کھیت کی سطح کا نہیں۔\n"
        "- سیمولیٹر کی ترتیبات کو سرکاری کیلنڈروں کے مطابق **ایڈجسٹ** کیا گیا ہے؛ یہ آزادانہ ثبوت نہیں۔\n"
        "- رہنمائی گزشتہ **25 برسوں** کے ڈیٹا پر مبنی ہے، موجودہ موسم کی پیش گوئی نہیں۔\n"
        "- آبپاشی، نہری پانی، بیج کی قسم، کھاد یا فصلوں کی گردش کے اثرات شامل نہیں۔\n"
        "- میدانی علاقوں کے آٹھ آبپاش اضلاع بارانی یا پہاڑی علاقوں کی نمائندگی نہیں کرتے۔\n"
        '- "گزشتہ برسوں کا حصہ" حقیقی احتمال نہیں ہے۔',
    )
