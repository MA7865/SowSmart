# Guide for Person B: The App

Read `00_team_overview_and_contract.md` first. This guide is only about your part.

## Your mission

Build the web app that the judges will actually see: a map, a district selector, a sowing-date selector, charts, the 2022 check, and a box to ask the Urdu helper. You can start **immediately** on fake data, and the real data will slot in later without code changes.

## What "done" looks like

- `streamlit run app.py` opens a clean page with a map, a district dropdown and a sowing-date dropdown.
- It shows the safest window, the best day, and "extra stress" for the chosen date.
- Tabs: Advisor, 2022 check, 25-year drift, Ask in Urdu, Limits (and Satellite check only if D delivers one).
- The limits panel is always visible.
- A red banner appears whenever fake data is in use, so fake numbers never get presented.
- The app **never crashes** if the Claude API fails, a file is missing, or Wi-Fi drops.
- It runs from a clean copy of the repo.

## Files you own

`app.py`, `requirements.txt`

## What you depend on (and what to do if it is late)

| You need | From | Due | If late |
|---|---|---|---|
| `results_mock.json` | D | H0:20 | Run `make_mock.py` from the contract file yourself |
| `advisor.py` (`ask`, `fallback_answer`) | C | H1:45 | The app already handles `advisor` being missing |
| Real `results.json` | A | v1 at H2:15, final at H5:30 | Keep using the mock. The banner tells you which one you are on |
| `ml_results.json` | D | H6:00 | The ML tab is hidden automatically |

## Your timeline at a glance

| Time (H) | Phase | Your task | Deliverable |
|---|---|---|---|
| 0:00-0:45 | 0. Setup | Install, run a hello-world Streamlit page | App window opens |
| 0:45-2:30 | 1. Build | Full app on fake data | `app.py` v1 pushed by 2:30 |
| 2:30-4:00 | 2. Connect | Switch to real data, add 2022 and drift tabs, connect the Urdu helper | App works on real `results.json` |
| 4:00-4:45 | Break | Eat and rest | |
| 4:45-7:00 | 3. Polish | Tool-call display, ML tab, map colours, screenshots | Final app by 6:30 |
| 7:00+ | 4-5. Demo and submit | Clean-clone test, bug fixes, rehearse | |

---

## PHASE 0: Setup (H0:00 to H0:45)

**Objective:** a working Streamlit on your computer.

1. Install Python 3.10 or newer. Check: `python --version`.
2. Install the tools:
   ```
   pip install streamlit pandas numpy plotly anthropic
   ```
3. Make a file `hello.py` with:
   ```python
   import streamlit as st
   st.title("It works")
   ```
4. Run `streamlit run hello.py`. A browser tab should open showing "It works". (Delete `hello.py` afterwards.)
5. Get the repo from D (about H0:20) and pull the files.

**If stuck:** if `streamlit` is not found, use `python -m streamlit run hello.py`. If the browser does not open, copy the link (like http://localhost:8501) from the terminal into the browser.

---

## PHASE 1: Build the app on fake data (H0:45 to H2:30)

**Objective:** the complete page working with `results_mock.json`.

### What Streamlit is (plain English)

Streamlit turns a Python script into a web page. Every time someone changes a dropdown, it reruns the script from the top. That is normal. You write the page from top to bottom like a document.

### The full `app.py`

Copy this and run it. Read the comments, because you will change things in Phase 3.

```python
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
            return advisor.ask_agent(question, context=context)
        except Exception:
            pass
    try:
        return advisor.ask(facts, question), []
    except Exception:
        pass
    try:
        return advisor.fallback_answer(facts), []
    except Exception:
        return "The helper is unavailable right now.", []


# ---------------- styles ----------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu&display=swap');
.urdu {direction: rtl; text-align: right; font-family: 'Noto Nastaliq Urdu', serif;
       font-size: 22px; line-height: 2.2;}
</style>
""", unsafe_allow_html=True)

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
map_df = pd.DataFrame([{"district": k, "lat": v["lat"], "lon": v["lon"]} for k, v in res.items()])
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
    st.write(f"Sowing on **{d['labels'][k]}**: stress {d['mean_curve'][k]:.1f} "
             f"(your chosen date: {your:.1f}, change {d['mean_curve'][k] - your:+.1f}).")
    st.caption(f"Share of past years in which the best day was within tolerance of that year's best: "
               f"{d['share_of_years_ok']:.0%}. This is not a forecast probability.")

# ---------------- 2022 tab ----------------
with tabs["2022 check"]:
    b = d["backtest_2022"]
    st.write(f"At the standard sowing date (15 Nov), the 2022 season had "
             f"**{b['heat_days_std_sowing']} heat days** in grain filling in {district}. "
             f"That is hotter than about **{b['percentile_hot_year']}%** of seasons from 2001 to 2021.")
    st.subheader("Heat days in 2022 by sowing date (simulation)")
    hd = b["heat_days_by_sowing_date"]
    st.bar_chart(pd.DataFrame({"heat days": list(hd.values())}, index=list(hd.keys())))
    st.caption("A simulation check, not proof of crop losses.")
    st.subheader("All districts")
    st.dataframe(pd.DataFrame({
        k: {"Heat days at 15 Nov sowing (2022)": v["backtest_2022"]["heat_days_std_sowing"],
            "Hotter than % of earlier years": v["backtest_2022"]["percentile_hot_year"]}
        for k, v in res.items()}).T)

# ---------------- drift tab ----------------
with tabs["25-year drift"]:
    st.write("Has the best sowing date moved over 25 years? Positive numbers mean later.")
    rows = {}
    for k_, v in res.items():
        clear = v["drift_p_value"] < 0.05
        rows[k_] = {"Days per decade": v["drift_days_per_decade"],
                    "p-value": v["drift_p_value"],
                    "Verdict": "clear shift" if clear else "no clear shift"}
    st.dataframe(pd.DataFrame(rows).T)
    st.caption("A p-value above 0.05 means we cannot say the date moved. That is a valid result.")

# ---------------- Urdu tab ----------------
with tabs["Ask in Urdu"]:
    st.write("Ask in Urdu or Roman Urdu, for example: Multan mein 28 November ko gandum bona kaisa rahega?")
    q = st.text_input("Your question")
    if st.button("Ask") and q.strip():
        context = f"The user selected district={district} and sowing date={sow} in the app. " \
                  f"Use these only if the question does not name a district or date."
        answer, calls = get_answer(facts, q, context)
        st.markdown(f"<div class='urdu'>{answer.replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)
        if calls:
            with st.expander("How the helper got its numbers (tool calls)"):
                st.json(calls)
        st.caption("The helper only uses numbers from this tool. It does not give advice on seed, "
                   "fertilizer, irrigation or pesticides.")

# ---------------- Satellite tab (only if D delivered ml_results.json) ----------------
if ml is not None:
    with tabs["Satellite check"]:
        if ml.get("passed"):
            st.success("The satellite-trained model beat both simple baselines in leave-one-year-out testing.")
        else:
            st.warning("The satellite-trained model did NOT beat the simple baselines. Reported honestly.")
        st.table(pd.DataFrame({
            "Error (lower is better)": {
                "Model": ml["cv_rmse_model"],
                "Baseline: district average": ml["cv_rmse_baseline_mean"],
                "Baseline: district trend": ml["cv_rmse_baseline_trend"]}}))
        st.write(ml.get("notes", ""))
        if ml.get("season_2022"):
            st.subheader("2022 held-out season: predicted vs actual late-season greenness")
            st.dataframe(pd.DataFrame(ml["season_2022"]).T)
        st.caption("Greenness (NDVI) is a stand-in, not yield. 250 m satellite pixels mix crops.")

# ---------------- Limits tab ----------------
with tabs["Limits"]:
    st.markdown("""
- Estimates **simulated heat exposure**, not yield or income.
- District-center weather at roughly 10 km resolution, not farm-level.
- Simulator settings are **tuned** against official calendars. That is tuning, not independent proof.
- Advice reflects the **last 25 years**. It is not a forecast for this season.
- No irrigation, canal water, seed variety, fertilizer or crop-rotation effects.
- Eight irrigated-plains districts do not represent rainfed or mountain areas.
- "Share of past years" is not a true probability.
    """)
```

Run: `streamlit run app.py`. Because there is no `results.json` yet, the **red fake-data banner** appears. That is correct.

### Step-by-step checks

1. The page shows a red banner, a map, two dropdowns, three numbers and a line chart.
2. Change the district. The numbers change.
3. Move the slider. The text under it changes.
4. Click each tab. None should show a red error box (an error box means a bug in your code or a missing key in the data).
5. The "Ask in Urdu" tab shows "not connected yet" until C's `advisor.py` exists. That is expected.

Push `app.py` (v1) by H2:30. Then create `requirements.txt`:

```
streamlit>=1.30
pandas
numpy
plotly
anthropic
scipy
requests
```

**If stuck:**

| Problem | What to do |
|---|---|
| `KeyError: 'labels'` (or another key) | The data file does not match the contract. Open the JSON and check the field names against `00_team_overview_and_contract.md` |
| `st.map` does nothing | Check the column names are `lat` and `lon`, and the values are numbers |
| `ModuleNotFoundError` | Install the missing package with `pip install name` |
| Page reloads and loses my selection | Normal in Streamlit. Selections persist when widgets have the same label |
| Port busy | Run `streamlit run app.py --server.port 8502` |

---

## PHASE 2: Connect the real parts (H2:30 to H4:00)

**Objective:** real numbers and the Urdu helper working in the app.

1. **Pull A's `results.json`.** The red banner should disappear, because the app uses `results.json` automatically when it exists. If you still see the banner, check you pulled the real file and not the mock.
2. **Go through all 8 districts** and look for anything strange: empty charts, `nan`, windows at the very edge. Report oddities to A immediately (message the district and the field).
3. **Connect C's `advisor.py`.** Pull it. The app already tries `ask_agent`, then `ask`, then `fallback_answer`. Test in the Urdu tab:
   - Ask a normal question. You should see Urdu text, right-to-left.
   - **Unset the API key** (or turn Wi-Fi off) and ask again. You should still get a Urdu fallback answer, **not an error**. If you see an error, fix the `get_answer` function.
4. **Check the Urdu rendering.** Text should be right-to-left. If you see boxes, your browser lacks the font, or you are offline (the font loads from Google Fonts). Test once with Wi-Fi on, and know the app still works without it.
5. **Test the "all districts" 2022 table** and the drift table. They should list all 8 districts.

**Done when:** you can click through every tab on real data without an error, with and without the API key.

---

## BREAK (H4:00 to H4:45)

Eat, pray, rest.

---

## CHECKPOINT 1 (H4:45)

Report: real data in the app? Urdu helper connected? Any fields missing? Fix any crash first.

---

## PHASE 3: Polish (H4:45 to H7:00)

**Objective:** make it look clean and credible, without adding risky features.

### Step 1: nicer map (optional, 20 minutes, with a safe fallback)

Replace the `st.map` line with this. It colours districts by the recommended sowing day. If plotly misbehaves, it falls back to the plain map.

```python
try:
    import plotly.express as px
    mdf = pd.DataFrame([{"district": k, "lat": v["lat"], "lon": v["lon"],
                         "best_day_number": v["labels"].index(v["best"]), "best": v["best"]}
                        for k, v in res.items()])
    fig = px.scatter_mapbox(mdf, lat="lat", lon="lon", color="best_day_number",
                            hover_name="district", hover_data={"best": True, "best_day_number": False},
                            zoom=4.5, height=380, mapbox_style="open-street-map",
                            color_continuous_scale="YlOrRd")
    fig.update_traces(marker={"size": 16})
    fig.update_layout(margin={"l": 0, "r": 0, "t": 0, "b": 0}, coloraxis_colorbar_title="Best day")
    st.plotly_chart(fig, use_container_width=True)
except Exception:
    st.map(map_df, latitude="lat", longitude="lon")
```

### Step 2: show the AI working

The Urdu tab already shows an expander called "How the helper got its numbers (tool calls)". Check it works when C delivers `ask_agent`. This is the most convincing thing you can show a judge: the AI picks a tool, the tool returns numbers, and the AI explains them. Make sure the expander looks neat in the demo.

### Step 3: satellite tab

When D delivers `ml_results.json`, the tab appears automatically. Check it shows the honest result (pass or fail) and that the wording matches what D says in the slides.

### Step 4: quality checks (do all)

- [ ] Every number on screen has a clear label and no unexplained abbreviation.
- [ ] Source labels visible (the caption under the title).
- [ ] Limits sidebar visible on every tab.
- [ ] No red error boxes in any tab for all 8 districts.
- [ ] App works with the API key removed.
- [ ] App works with Wi-Fi off (Claude calls will fail, so the fallback must show).
- [ ] The page is readable on a projector: test by zooming the browser to 125%.

### Step 5: screenshots for D (H5:30 and H7:00)

Take clean screenshots: Advisor tab for a Punjab district, 2022 tab, Urdu answer with the tool-call expander open, the Limits tab. Save in `slides/screens/` and tell D.

---

## FEATURE FREEZE (H7:00)

No new features after this. Only bugs.

## PHASES 4 and 5: Demo prep and submit (H7:00 onward)

1. **Clean-clone test (with D).** Copy the repo into a new empty folder. Create a fresh virtual environment or use another computer. Run `pip install -r requirements.txt` and `streamlit run app.py`. It must work without anything from your computer that is not in the repo (no secret files, no missing CSVs). Fix `requirements.txt` if a package is missing.
2. **Demo rehearsal.** You drive the app while D presents. Practise: pick Multan → set 11-28 → show the extra stress → open the 2022 tab → ask the Urdu question → open the tool-call expander.
3. **Backup:** record a screen video of the full flow (D coordinates).
4. **Prepare for a crash:** know how to restart the app in 10 seconds, and keep the screenshots ready.

## Questions you should be able to answer

- **What is the stress number?** "Heat days in the grain-filling weeks plus double-weighted frost days and late maturity. Lower is safer."
- **Where do the numbers come from?** "25 years of ERA5-based weather from Open-Meteo, run through our wheat simulator."
- **What happens if the Claude API fails?** "The app falls back to a template answer with the same numbers."

## Your final checklist

- [ ] App runs on real `results.json`, with no fake-data banner
- [ ] All tabs work for all districts
- [ ] Works without API key and without Wi-Fi (with fallback)
- [ ] Limits sidebar and tab present
- [ ] `requirements.txt` complete and tested from a clean copy
- [ ] Screenshots delivered to D
- [ ] I can restart the app quickly if it crashes during the demo
- [ ] I ate, rested and told the team about any known problems
