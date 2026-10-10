import base64
import html
import json
import os

import pandas as pd
import streamlit as st

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
if USING_MOCK or any(v.get("FAKE") for v in res.values()):
    show_bilingual(
        "USING FAKE DATA. Numbers are for building only. Do not present this.",
        "یہ فرضی ڈیٹا ہے۔ اعداد صرف ایپ بنانے کے لیے ہیں، انہیں پیش نہ کریں۔",
        style="error",
    )

ml = load_json("ml_results.json") if os.path.exists("ml_results.json") else None

# ---------------- Urdu helper (optional, never crashes the app) ----------------
try:
    import advisor
except Exception:
    advisor = None


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
    background: linear-gradient(180deg, #f7faf4 0%, #edf3e9 100%);
    color: #202820;
}
.stApp {
    background: transparent;
    color: #202820;
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
map_df = pd.DataFrame([
    {"district": district_label(k), "lat": v["lat"], "lon": v["lon"]} for k, v in res.items()
])
try:
    import plotly.express as px

    mdf = pd.DataFrame(
        [
            {
                "district": district_label(k),
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
        coloraxis_colorbar_title=bilingual_label("Best day", "بہترین دن"),
    )
    st.plotly_chart(fig, use_container_width=True)
except Exception:
    st.map(map_df, latitude="lat", longitude="lon")

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

tab_names = [
    bilingual_label("Advisor", "رہنما"),
    bilingual_label("2022 check", "2022 کا جائزہ"),
    bilingual_label("25-year drift", "25 سالہ رجحان"),
    bilingual_label("Ask in Urdu", "اردو میں پوچھیں"),
    bilingual_label("Limits", "حدود"),
]
if ml is not None:
    tab_names.insert(4, bilingual_label("Satellite check", "سیٹلائٹ کا جائزہ"))
tabs = dict(zip(tab_names, st.tabs(tab_names)))

# ---------------- Advisor tab ----------------
with tabs[bilingual_label("Advisor", "رہنما")]:
    m1, m2, m3 = st.columns(3)
    m1.metric(bilingual_label("Safest window", "محفوظ ترین مدت"), f"{d['window_start']} to {d['window_end']} | {d['window_start']} تا {d['window_end']}")
    m2.metric(bilingual_label("Best day", "بہترین دن"), d["best"])
    m3.metric(bilingual_label("Your date: extra stress vs best", "آپ کی تاریخ: بہترین تاریخ سے اضافی دباؤ"), f"{your - best:+.1f}")
    show_bilingual(
        "Stress = heat days in grain filling + 2 x frost days + 2 x days of late maturity. Lower is safer.",
        "دباؤ = دانہ بننے کے دوران گرم دن + کہر کے دنوں کے 2 گنا + دیر سے پکنے کے دنوں کے 2 گنا۔ کم دباؤ زیادہ محفوظ ہے۔",
        style="caption",
    )
    if d.get("edge_warning"):
        show_bilingual(
            "The best date is at the edge of the tested range for this district. Treat with care.",
            "اس ضلع میں بہترین تاریخ آزمائی گئی حد کے کنارے پر ہے۔ اس نتیجے کو احتیاط سے دیکھیں۔",
            style="warning",
        )

    show_bilingual("Stress by sowing date (average of 25 years)", "بوائی کی تاریخ کے لحاظ سے دباؤ (25 سالہ اوسط)", style="subheader")
    st.line_chart(pd.DataFrame({bilingual_label("Stress", "دباؤ"): d["mean_curve"]}, index=d["labels"]))

    show_bilingual("What if I sow earlier or later?", "اگر میں پہلے یا بعد میں بوائی کروں تو؟", style="subheader")
    shift = st.slider(bilingual_label("Move my sowing date by (days)", "میری بوائی کی تاریخ اتنے دن بدلیں"), -30, 30, 0)
    k = max(0, min(len(d["labels"]) - 1, i + shift))
    show_bilingual(
        f"Sowing on **{d['labels'][k]}**: stress {d['mean_curve'][k]:.1f} "
        f"(your chosen date: {your:.1f}, change {d['mean_curve'][k] - your:+.1f}).",
        f"**{d['labels'][k]}** کو بوائی: دباؤ {d['mean_curve'][k]:.1f} "
        f"(آپ کی منتخب تاریخ کا دباؤ: {your:.1f}، تبدیلی {d['mean_curve'][k] - your:+.1f})۔",
    )
    show_bilingual(
        f"Share of past years in which the best day was within tolerance of that year's best: "
        f"{d['share_of_years_ok']:.0%}. This is not a forecast probability.",
        f"گزشتہ برسوں میں {d['share_of_years_ok']:.0%} برسوں میں بہترین دن، اس سال کے بہترین دن کی قابلِ قبول حد میں تھا۔ "
        "یہ موجودہ موسم کی پیش گوئی کا امکان نہیں ہے۔",
        style="caption",
    )

# ---------------- 2022 tab ----------------
with tabs[bilingual_label("2022 check", "2022 کا جائزہ")]:
    b = d["backtest_2022"]
    show_bilingual(
        f"At the standard sowing date (15 Nov), the 2022 season had "
        f"**{b['heat_days_std_sowing']} heat days** in grain filling in {district_label(district)}. "
        f"That is hotter than about **{b['percentile_hot_year']}%** of seasons from 2001 to 2021.",
        f"معیاری بوائی کی تاریخ (15 نومبر) پر 2022 کے موسم میں {URDU_DISTRICTS.get(district, district)} کے اندر دانہ بننے کے دوران "
        f"**{b['heat_days_std_sowing']} گرم دن** تھے۔ یہ 2001 سے 2021 کے تقریباً **{b['percentile_hot_year']}%** "
        "موسموں سے زیادہ گرم تھا۔",
    )
    show_bilingual("Heat days in 2022 by sowing date (simulation)", "2022 میں بوائی کی تاریخ کے لحاظ سے گرم دن (سیمولیشن)", style="subheader")
    hd = b["heat_days_by_sowing_date"]
    st.bar_chart(pd.DataFrame({bilingual_label("Heat days", "گرم دن"): list(hd.values())}, index=list(hd.keys())))
    show_bilingual("A simulation check, not proof of crop losses.", "یہ سیمولیشن کی جانچ ہے، فصل کے نقصان کا ثبوت نہیں۔", style="caption")
    show_bilingual("All districts", "تمام اضلاع", style="subheader")
    st.dataframe(
        pd.DataFrame(
            {
                district_label(k): {
                    bilingual_label("Heat days at 15 Nov sowing (2022)", "15 نومبر کی بوائی پر گرم دن (2022)"): v["backtest_2022"]["heat_days_std_sowing"],
                    bilingual_label("Hotter than % of earlier years", "گزشتہ برسوں میں اتنے فیصد سے زیادہ گرم"): v["backtest_2022"]["percentile_hot_year"],
                }
                for k, v in res.items()
            }
        ).T
    )

# ---------------- drift tab ----------------
with tabs[bilingual_label("25-year drift", "25 سالہ رجحان")]:
    show_bilingual("Has the best sowing date moved over 25 years? Positive numbers mean later.",
                   "کیا 25 برسوں میں بہترین بوائی کی تاریخ بدلی ہے؟ مثبت عدد کا مطلب ہے کہ تاریخ بعد میں ہوئی۔")
    rows = {}
    for k_, v in res.items():
        p_value = v.get("drift_p_value")
        if p_value is None:
            verdict = bilingual_label("not enough information", "معلومات ناکافی ہیں")
        else:
            verdict = (
                bilingual_label("clear shift", "واضح تبدیلی")
                if p_value < 0.05
                else bilingual_label("no clear shift", "واضح تبدیلی نہیں")
            )
        rows[k_] = {
            bilingual_label("Days per decade", "فی دہائی دن"): v["drift_days_per_decade"],
            bilingual_label("p-value", "پی ویلیو"): p_value if p_value is not None else bilingual_label("n/a", "دستیاب نہیں"),
            bilingual_label("Verdict", "نتیجہ"): verdict,
        }
    st.dataframe(pd.DataFrame(rows).T)
    show_bilingual(
        "A p-value above 0.05 means we cannot say the date moved. A null p-value means the trend could not be tested in this dataset.",
        "0.05 سے بڑا p-value ہونے کا مطلب ہے کہ تاریخ کی تبدیلی کا نتیجہ واضح نہیں۔ خالی p-value کا مطلب ہے کہ اس ڈیٹا سے رجحان کی جانچ نہیں ہو سکی۔",
        style="caption",
    )

# ---------------- Urdu tab ----------------
with tabs[bilingual_label("Ask in Urdu", "اردو میں پوچھیں")]:
    show_bilingual(
        "Ask in Urdu or Roman Urdu, for example: Multan mein 28 November ko gandum bona kaisa rahega?",
        "اردو یا رومن اردو میں سوال پوچھیں، مثلاً: ملتان میں 28 نومبر کو گندم بونا کیسا رہے گا؟",
    )
    q = st.text_input(bilingual_label("Your question", "آپ کا سوال"))
    if st.button(bilingual_label("Ask", "پوچھیں")) and q.strip():
        save_urdu_answer(q)

    show_saved_urdu_answer()

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
