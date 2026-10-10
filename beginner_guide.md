# Wheat Sowing Advisor: Beginner's Step-by-Step Guide

Read **Part 1 and Part 2 first** (10 minutes). Then follow the steps in order. Every step says what to do, what you should see when it works, and what to do if it doesn't.

---

## PART 1: What are we building? (plain English)

**The problem.** Wheat in Pakistan is sown around November. In March-April, when the wheat grain is filling, a hot spell can damage the crop. If a farmer sows late (for example, because cotton is still in the field), the grain filling slides later into hotter weeks.

**What we build.** A small web app. You pick a district and a sowing date. It tells you:
1. "In the last 25 years, sowing on this date usually meant X hot days during grain filling."
2. "The best date was around Y. Your date is Z days later, which means about N more hot days."
3. "What happened in 2022 (a famous heatwave), and what sowing earlier would have changed, **in our simulation**."
4. A Gemini helper explains this in **Urdu**, and you can ask questions in Urdu or Roman Urdu.

**How it works, in four boxes:**

```
[1. Weather data]  ->  [2. Simulator]  ->  [3. Results file]  ->  [4. App + Gemini in Urdu]
 (25 years, 8        (pretend to sow       (results.json:         (map, chart, Urdu
  districts)          on every date)        the numbers)           explanation)
```

**An analogy.** Imagine you could replay the last 25 winters in a computer and "sow" wheat on every possible date in each one, then count the hot days it would have faced. Averaging those 25 replays tells you which dates are usually safest. That is all the simulator does.

---

## PART 2: Words you will see

| Word | Meaning |
|---|---|
| **Sowing** | Planting the seeds. |
| **Grain filling** | The weeks when the wheat grain gets its size. Heat here hurts most. |
| **Heat day** | A day when the maximum temperature is 34 °C or higher during grain filling. |
| **Simulator** | A small program with simple rules that imitates how wheat grows with temperature. Not an AI model. |
| **GDD (growing degree days)** | A way to measure crop "progress" using temperature. Warm days add more. When the total reaches a target, the crop is mature. |
| **Backtest** | Using the past to check an idea. Example: "what would our advice have said in 2022?" |
| **API** | A way for your program to ask another service for something (weather, or Gemini's answer). |
| **API key** | A secret password for an API. Never put it in code you share. |
| **CSV** | A table saved as a text file. |
| **JSON** | A way to store data as text, like a labeled list. `results.json` is our results file. |
| **Cache** | A saved copy so we don't download the same data twice. |
| **Streamlit** | A Python tool that turns a script into a web page. |
| **NDVI** | A number from satellites that says how green the land is. Optional part of this project (Level 2). |
| **Baseline** | A simple comparison method. A model is only useful if it beats the baseline. |
| **Proxy** | A stand-in measurement. Example: greenness is a proxy for crop health, not an exact measure. |

---

## PART 3: What is AI in this project? (honest answer)

Be clear about this with yourselves and with the judges.

- **Level 1 (the main plan, doable today):** a simulator plus an AI helper. Gemini reads the supplied results, understands Urdu and Roman Urdu questions, and explains them in Urdu. The core calculation is the simulator, not AI. That is fine, as long as you describe it truthfully.
- **Level 2 (optional, only if Level 1 is finished and working):** a small machine learning model trained on satellite greenness (NDVI) to check whether the simulator's heat-risk idea matches what satellites actually saw. This adds real "trained AI", but it is harder and may not work in one day.

Say to judges: **"We built a heat-risk checker for sowing dates. Gemini lets farmers and extension officers ask about it in Urdu. We also tested our assumptions against satellite data."** (Only say the last sentence if you finished Level 2.)

---

## PART 4: Common confusions, answered

**"Isn't this just a crop calendar?"**
A crop calendar gives one fixed window. Ours prices *any* date: "if you can only sow on Nov 28, here is your extra risk." It also shows how the safe window has moved over 25 years. That second use is what a calendar cannot do.

**"Do we need to train a model?"**
Not for Level 1. The simulator uses rules, not training. Training only appears in Level 2.

**"Will it predict yield?"**
No. Never say yield. We estimate **heat exposure**, not how much wheat is harvested.

**"Is the recommended window a guarantee?"**
No. It reflects the last 25 years. It is not a weather forecast for this year.

**"The farmer speaks Urdu. How does that work?"**
The farmer (or an extension officer) can type in Urdu or Roman Urdu, or record a spoken question. Groq transcribes voice questions; Gemini answers using the app's supplied results. Answers are displayed in Urdu, and Gemini can generate Urdu audio when the user selects **Read answer aloud**. The simulator never sees Urdu.

**"Can a farmer ask by voice?"**
Yes. Set `GROQ_API_KEY` and `GROQ_MODEL=whisper-large-v3-turbo` in the project `.env` file. The app sends the recording to Groq only after the user selects **Transcribe and ask**, then displays the transcript and uses Gemini to answer it in Urdu. Recordings are not saved by the app. Typed questions do not need Groq. **Read answer aloud** remains on Gemini.

**"What does 'calibration' mean?"**
Adjusting the simulator's settings so that its harvest date roughly matches the official harvest time. Compare with the Punjab Agriculture Department or FAO crop calendar. It is *tuning*, not proof.

---

## PART 5: Who does what (4 people)

| Person | Job |
|---|---|
| **A** | Data and simulator (Steps 2 to 4) |
| **B** | App (Step 5) |
| **C** | Gemini helper and Urdu (Step 6) |
| **D** | Setup, Earth Engine signup, slides, README, testing, backup video |

If only one or two of you can code, **A and B** are the coders. C can write the Gemini prompt and test Urdu with no coding. D can prepare slides and the checklist.

---

## PART 6: Step by step

Times are relative to your start (Hour 0). Add breaks for food, prayer and commute. Do not skip the checkpoints.

### STEP 0: Setup (Hour 0 to 0:45) — everyone

1. **Install Python 3.10 or newer** from python.org if you don't have it. Check it with `python --version`.
2. **Create a project folder** called `wheat-advisor`. Inside it, create folders `cache` and `advice`.
3. **Install the tools** (in a terminal, inside the folder):
   ```
   pip install pandas numpy scipy requests streamlit anthropic
   ```
   If `pip` is not found, try `python -m pip install ...`.
4. **Get a Gemini API key** (person C) from Google AI Studio. Add it as `GEMINI_API_KEY=your-key` in the project `.env` file; do not paste the key into code or commit `.env`.
5. **Person D: sign up for Google Earth Engine** at https://console.cloud.google.com/earth-engine. Do this now even if you plan to skip Level 2. It can take time to approve.
6. **Make a free GitHub repo** and share the folder, so all four of you work from the same files. Add `.gitignore` with a line `*.key` and never commit keys.

**You'll know it worked when:** `python -c "import pandas, streamlit, anthropic"` prints nothing (no error).

---

### STEP 1: Pick districts (Hour 0:45) — everyone, 10 minutes

We use 8 districts in the irrigated plains: Faisalabad, Multan, Bahawalpur, Rahim Yar Khan, Sargodha, Sahiwal (Punjab), and Larkana, Hyderabad (Sindh). The coordinates are district centers, so say "district center" on your slides, not "farm-level".

---

### STEP 2: Download weather data (Hour 0:45 to 1:30) — Person A

Create `fetch_weather.py` and run it with `python fetch_weather.py`.

```python
import requests, pandas as pd, time, os

DISTRICTS = {
    "Faisalabad": (31.42, 73.08), "Multan": (30.20, 71.47),
    "Bahawalpur": (29.40, 71.68), "Rahim Yar Khan": (28.42, 70.30),
    "Sargodha": (32.08, 72.67), "Sahiwal": (30.67, 73.11),
    "Larkana": (27.56, 68.21), "Hyderabad": (25.39, 68.37),
}
os.makedirs("cache", exist_ok=True)

for name, (lat, lon) in DISTRICTS.items():
    path = f"cache/{name.replace(' ', '_')}.csv"
    if os.path.exists(path):
        print("already have", name)
        continue
    for attempt in range(5):
        r = requests.get("https://archive-api.open-meteo.com/v1/archive", params={
            "latitude": lat, "longitude": lon,
            "start_date": "2000-01-01", "end_date": "2025-12-31",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
            "timezone": "Asia/Karachi"})
        if r.status_code == 200:
            pd.DataFrame(r.json()["daily"]).to_csv(path, index=False)
            print("saved", name)
            break
        print("problem", r.status_code, "waiting...")
        time.sleep(30 * (attempt + 1))
    time.sleep(5)
```

**You'll know it worked when:** the `cache` folder has 8 `.csv` files. Open one. You should see columns `time`, `temperature_2m_max`, `temperature_2m_min`, `precipitation_sum`, with about 9,500 rows.

**If it fails:**
- Error 429 or "too many requests": the script waits and retries. Leave it running. If it still fails after 20 minutes, use the NASA POWER weather service (https://power.larc.nasa.gov/) for the remaining districts, or reduce the number of districts.
- No internet: use mobile data. Do not wait.

**Commit the CSVs to GitHub** so you never have to download them again.

---

### STEP 3: The simulator and the results file (Hour 1:30 to 4:00) — Person A

Create `simulate.py`. It "sows" wheat on every date from Oct 1 to Dec 31 in each year from 2000 to 2024, counts heat days, and saves the averages.

**What the settings mean (these are starting guesses, not facts):**
- Crop is "mature" after 2200 growing degree days. **This is a placeholder.** You will adjust it in Step 3b.
- Heat day: max temperature ≥ 34 °C while the crop is 60 to 95 percent of the way to maturity.
- Frost day: min temperature ≤ 0 °C while the crop is 50 to 65 percent of the way.
- Extra penalty if the crop would mature after May 15.

```python
import json
import numpy as np
import pandas as pd
from scipy.stats import theilslopes, kendalltau

DISTRICTS = {
    "Faisalabad": (31.42, 73.08, "Punjab"), "Multan": (30.20, 71.47, "Punjab"),
    "Bahawalpur": (29.40, 71.68, "Punjab"), "Rahim Yar Khan": (28.42, 70.30, "Punjab"),
    "Sargodha": (32.08, 72.67, "Punjab"), "Sahiwal": (30.67, 73.11, "Punjab"),
    "Larkana": (27.56, 68.21, "Sindh"), "Hyderabad": (25.39, 68.37, "Sindh"),
}
TBASE, TCAP = 0.0, 30.0
GDD_TOTAL = 2200.0     # placeholder: calibrate in Step 3b
HEAT_C = 34.0
STD_SOW = "11-15"

def load(name):
    path = f"cache/{name.replace(' ', '_')}.csv"
    return pd.read_csv(path, parse_dates=["time"]).set_index("time")

def simulate(df, sow_date):
    """Pretend to sow on sow_date. Returns a dict of results, or None if data ran out."""
    i = df.index.get_loc(sow_date)
    tx = df["temperature_2m_max"].values[i:]
    tn = df["temperature_2m_min"].values[i:]
    g = np.maximum(0, (np.minimum(tx, TCAP) + np.maximum(tn, TBASE)) / 2 - TBASE).cumsum()
    if g[-1] < GDD_TOTAL:
        return None
    m = int(np.argmax(g >= GDD_TOTAL))          # day index when mature
    frac = g[:m + 1] / GDD_TOTAL                 # how far along the crop is each day
    heat = int(((tx[:m + 1] >= HEAT_C) & (frac >= 0.60) & (frac <= 0.95)).sum())
    frost = int(((tn[:m + 1] <= 0) & (frac >= 0.50) & (frac <= 0.65)).sum())
    mat = df.index[i + m]
    late = max(0, (mat - pd.Timestamp(sow_date.year + 1, 5, 15)).days)
    return {"stress": heat + 2 * frost + 2 * late, "heat": heat,
            "frost": frost, "maturity": mat}

def moving_avg(x, w=5):
    return pd.Series(x).rolling(w, center=True, min_periods=1).mean().values

results = {}
for name, (lat, lon, prov) in DISTRICTS.items():
    df = load(name)
    years = list(range(2000, 2025))              # sowing years
    days = pd.date_range("2001-10-01", "2001-12-31")
    labels = [d.strftime("%m-%d") for d in days]

    # matrix: rows = years, columns = sowing dates
    mat = np.full((len(years), len(labels)), np.nan)
    for a, y in enumerate(years):
        for b, d in enumerate(pd.date_range(f"{y}-10-01", f"{y}-12-31")):
            r = simulate(df, d)
            if r is not None:
                mat[a, b] = r["stress"]

    mean_curve = moving_avg(np.nanmean(mat, axis=0))
    best = int(np.argmin(mean_curve))
    tol = max(2.0, 0.10 * (mean_curve.max() - mean_curve.min()))
    lo, hi = best, best
    while lo > 0 and mean_curve[lo - 1] <= mean_curve[best] + tol: lo -= 1
    while hi < len(labels) - 1 and mean_curve[hi + 1] <= mean_curve[best] + tol: hi += 1

    year_min = np.nanmin(mat, axis=1)
    share_ok = float(np.mean(mat[:, best] <= year_min + tol))

    # has the best date moved over the years?
    best_each_year = np.nanargmin(mat, axis=1)
    slope = theilslopes(best_each_year, years)[0] * 10      # days per decade
    p_val = float(kendalltau(years, best_each_year)[1])

    # 2022 backtest (the 2022 season was sown in autumn 2021)
    heat_std = {y: simulate(df, pd.Timestamp(f"{y}-{STD_SOW}"))["heat"]
                for y in range(2000, 2022)}
    h2022 = heat_std[2021]
    percentile = 100 * float(np.mean([v <= h2022 for v in heat_std.values()]))
    alt = {s: simulate(df, pd.Timestamp(f"2021-{s}"))["heat"]
           for s in ["10-25", "11-01", "11-15", "12-01"]}

    results[name] = {
        "lat": lat, "lon": lon, "province": prov,
        "labels": labels,
        "mean_curve": [round(float(v), 2) for v in mean_curve],
        "best": labels[best], "window_start": labels[lo], "window_end": labels[hi],
        "share_of_years_ok": round(share_ok, 2),
        "drift_days_per_decade": round(float(slope), 2),
        "drift_p_value": round(p_val, 3),
        "backtest_2022": {"heat_days_std_sowing": h2022,
                          "percentile_hot_year": round(percentile),
                          "heat_days_by_sowing_date": alt},
        "edge_warning": best in (0, len(labels) - 1),
    }
    print(name, "best", labels[best], "window", labels[lo], "to", labels[hi])

with open("results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=1)
print("saved results.json")
```

**You'll know it worked when:** it prints one line per district with a best date and a window, then "saved results.json".

**Sanity check (important):** for Punjab districts, the best window should usually fall somewhere in **late October to late November**. If many districts say `10-01` or `12-31`, something is off (see the table below).

#### STEP 3b: Calibrate (Person A with D, 30 minutes)

1. Find the official wheat sowing and harvest times for Punjab from the FAO crop calendar (https://cropcalendar.apps.fao.org/, I haven't verified this link, so check it opens) or the Punjab Agriculture Department. Write the source in a note.
2. Run `simulate` for one district with sowing on Nov 15 and print `maturity`.
3. If the maturity date is much earlier or later than the official harvest period (roughly April, check your source), change `GDD_TOTAL` (try 2300, 2400) and rerun.
4. Keep a screenshot of this: **"we tuned the simulator to match the official harvest time."** Say the word *tuned*. Do not say *validated*.

#### If something looks wrong

| Problem | What to do |
|---|---|
| `KeyError` or "get_loc" error | A date is missing in the CSV. Check the CSV has all dates from 2000 to 2025. Re-download that district |
| Best date is `10-01` or `12-31` for many districts | The candidate range may be too narrow, or `GDD_TOTAL` is off. Re-calibrate (Step 3b) |
| All stress values are 0 | `HEAT_C` is never reached in your data, or `GDD_TOTAL` is too high so no crop matures. Print one `simulate(...)` result and check |
| `nanargmin` error "All-NaN slice" | That year ran out of data. Make sure the weather file goes to 2025-12-31 |
| Windows are huge (30+ days) | The curve is flat. That's a real result. Report "this district is not very sensitive to sowing date" |
| Drift p-value is large (above 0.05) | That means no clear shift. Report it honestly. Don't hunt for significance |

---

### STEP 4: Check 2022 (Hour 4:00 to 4:30) — Person A

Open `results.json` and look at `backtest_2022` for each district. Write down:
- Percentile: "2022 was hotter than X percent of the previous years at standard sowing."
- Heat days by sowing date: "in our simulation, sowing on Oct 25 instead of Nov 15 would have meant A fewer heat days."

**If 2022 does not look extreme in some districts:** show that. That is an honest result. Do not change numbers to make it look dramatic. Also do not quote losses (like "yields fell by X percent") unless you find and cite a published source.

---

### STEP 5: The app (Hour 1 onward, in parallel) — Person B

Person B can start as soon as `results.json` exists. Until then, B can make a copy of the file with fake numbers to build the layout.

Create `app.py`:

```python
import json
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Wheat Sowing Advisor", layout="wide")
res = json.load(open("results.json", encoding="utf-8"))

st.title("Wheat Sowing Advisor (prototype)")
st.caption("Based on 25 years of ERA5 weather (Open-Meteo) and a simple wheat simulator. "
           "This estimates heat exposure. It is NOT a yield prediction or a weather forecast.")

# Map
df = pd.DataFrame([{"district": k, "lat": v["lat"], "lon": v["lon"]} for k, v in res.items()])
st.map(df, latitude="lat", longitude="lon")

# Pick district and date
district = st.selectbox("District", list(res.keys()))
d = res[district]
sow = st.selectbox("Your sowing date (month-day)", d["labels"],
                   index=d["labels"].index("11-15") if "11-15" in d["labels"] else 0)

i = d["labels"].index(sow)
j = d["labels"].index(d["best"])
your, best = d["mean_curve"][i], d["mean_curve"][j]

c1, c2, c3 = st.columns(3)
c1.metric("Safest window", f"{d['window_start']} to {d['window_end']}")
c2.metric("Best day", d["best"])
c3.metric("Your date: extra stress vs best", f"{your - best:+.1f}")

st.subheader("Heat-and-cold stress by sowing date (lower is safer)")
st.line_chart(pd.DataFrame({"stress": d["mean_curve"]}, index=d["labels"]))

st.subheader("2022 heatwave check (simulation)")
b = d["backtest_2022"]
st.write(f"At the standard sowing date, 2022 had {b['heat_days_std_sowing']} heat days, "
         f"hotter than {b['percentile_hot_year']}% of 2000 to 2021.")
st.write("Heat days by sowing date in 2022:", b["heat_days_by_sowing_date"])

st.subheader("Drift over 25 years")
st.write(f"Best date moved about {d['drift_days_per_decade']} days per decade "
         f"(p-value {d['drift_p_value']}). A p-value above 0.05 means no clear shift.")
st.info("Limits: district-center weather, simulation only, no yield, no irrigation or "
        "rotation constraints. Wheat often follows cotton or sugarcane, so earlier sowing "
        "is not always possible.")
```

Run it with `streamlit run app.py`. A browser tab opens.

**You'll know it worked when:** you see a map, a district dropdown, three numbers, and a line chart.

**If it fails:** `ModuleNotFoundError` means a package is missing (`pip install <name>`). If `results.json` is not found, run the app from the same folder where it lives.

---

### STEP 6: Gemini helper, voice, and read-aloud (Hour 1:30 onward) — Person C

The current app already connects the Gemini helper in `wheat-advisor/advisor.py`; do not replace it with the older Anthropic example. Keep `GEMINI_API_KEY` active in the project `.env`. The configured model is `gemini-3.8-flash`.

In the app's **Ask in Urdu** tab, users can:
- Type a question in Urdu script or Roman Urdu and receive an Urdu answer based on the app's results.
- Record a spoken Urdu or Roman Urdu question and select **Transcribe and ask**. Groq Whisper transcribes the recording; Gemini then answers the transcript.
- Select **Read answer aloud** to hear the displayed answer. Gemini generates and returns a WAV audio player.

The app sends a recording to Groq only after **Transcribe and ask** is selected, and it does not save recordings. Answers are heat-risk explanations based on historical simulation data, not forecasts or advice about seed, fertilizer, irrigation, pesticides, yield, or income.

**Test it with questions** in Urdu script and Roman Urdu, including a district and sowing date. Confirm that the answer is Urdu and its dates and numbers match the app. Also try an out-of-scope question such as fertilizer and confirm the helper politely refuses it.

**If it fails:**
- Authentication error: check that `GEMINI_API_KEY` is active in `.env`, then restart Streamlit.
- Model not found: check the configured model name in the Gemini API docs.
- Voice control disabled: confirm the key is active and the browser has microphone permission.
- Audio generation is unavailable: check Gemini API access and quota for the configured TTS model.

---

### CHECKPOINT (about Hour 5): decide, don't argue

| Question | If YES | If NO |
|---|---|---|
| Does the app run with real results for at least 6 districts? | Continue to polish | Cut districts to 6. Do not add features |
| Does the Urdu helper pass your 10 test questions? | Continue | Fix the prompt before anything else |
| Do the windows look sensible (Step 3 sanity check)? | Continue | Recalibrate first |

**Level 2 (satellite model) starts only if all three are YES and you still have 4 or more hours.**

---

### LEVEL 2 (optional): satellite check — Persons A and D

Skip this unless Level 1 is finished. The idea in plain words: satellites record how green each district's wheat was every winter since 2000. If hot Marches really reduce late-season greenness in the past, that supports the simulator's heat-risk idea. We train a small model to learn that link and test it on years it has not seen.

1. **Earth Engine must be approved.** If it is not, skip Level 2 and say "satellite check is future work".
2. **Download greenness (NDVI) per district per date** using the Earth Engine script in the earlier file `buildathon_plan.md` (Phase 2, Step A). Datasets: MODIS NDVI `MODIS/061/MOD13Q1`, ESA WorldCover (cropland mask) `ESA/WorldCover/v200`, FAO GAUL districts `FAO/GAUL/2015/level2`. Pages are linked there. Always print the district names first, since the spelling may differ.
3. **Avoid the three classic mistakes:**
   - **Mistake 1, cheating by accident ("leakage").** Do not predict greenness using something computed from the same greenness curve. Use only weather and the simulator's numbers as inputs, and use greenness in **February to April** as the answer to predict.
   - **Mistake 2, trend.** Greenness may rise over the years for reasons unrelated to weather. Compare your model with a baseline that includes each district's trend, not just its average.
   - **Mistake 3, picking the test after seeing results.** Fix the test now: train on all years except one, predict the left-out year, repeat for every year (this is "leave-one-year-out"). Keep 2022 as a special case study.
4. **Success means:** the model's error is **lower than the baseline's**. If it is not, say so honestly: "with only about 200 data points, a model did not beat a simple baseline." That is an acceptable result. Judges respect honesty more than a made-up win.
5. Note: the earlier file `buildathon_plan.md` has a model-checking script that has the leakage problem from Mistake 1. If you use it, change the features and the target as described above.

---

## PART 7: Suggested timeline (adjust to your real start time)

| When | What |
|---|---|
| Hour 0 to 0:45 | Step 0 setup (everyone) |
| 0:45 to 1:30 | Step 2: download weather (A). B builds the app layout with fake numbers. C writes the Claude prompt and 10 test questions. D works on the slides skeleton |
| 1:30 to 4:00 | Step 3: simulator and calibration (A). B and C keep building |
| 4:00 to 5:00 | Step 4 (2022 check) and plug real numbers into the app |
| **~5:00** | **Checkpoint** |
| 5:00 to 7:00 | Polish app, test Urdu, optional Level 2 |
| Lunch/dinner and prayer | Take real breaks. Tired teams make mistakes |
| **~2 hours before deadline** | **Feature freeze.** No new features. Test from a clean copy of the project |
| Last 90 minutes | 3 rehearsals, backup video, README, submit |
| Last 30 minutes | Buffer. Only fix a failed upload |

---

## PART 8: 5-minute demo script

1. **Problem (30 s):** Farmers sow by tradition, but March-April heat is rising. Late sowing is often forced by cotton or sugarcane.
2. **Map and district (60 s):** Pick a district, show the safest window.
3. **Late sowing (60 s):** Change the date to a late one. Show the extra stress. "A calendar can't tell you this."
4. **2022 check (60 s):** Show how hot 2022 was and what sowing earlier would have changed, **in our simulation**.
5. **Urdu helper (45 s):** Ask a question in Urdu. Show the answer (use the saved backup if the internet is bad).
6. **Limits (30 s):** Read the limits honestly (Part 9).

---

## PART 9: Limits to say out loud (judges like honesty)

- We estimate **heat exposure**, not yield or income.
- Weather is for the district center, not each farm.
- The simulator's settings are tuned to match official calendars. That is tuning, not independent proof.
- The advice reflects the **last 25 years**. It is not a forecast for this season.
- We do not model irrigation, canal water, seed variety, or fertilizer.
- Eight irrigated-plains districts do not represent rainfed or mountain areas.
- "Share of past years" is not a true probability.
- If Level 2 was done: satellite greenness is a proxy, and 250 m satellite pixels mix crops, so wheat is not isolated.

**Likely judge questions and short answers:**
- *Why not a neural network?* "There are no labeled records of sowing outcomes. A simulation is explainable. We used satellite data to test our assumptions where we could."
- *How accurate is it?* Show the numbers you have, plus the limits above. Do not give one flattering number.
- *Who uses it?* Extension officers first, who then advise farmers.
- *Why Claude?* "It lets people ask in Urdu and gives plain explanations that only use our numbers."

---

## PART 10: Final checklist

- [ ] `results.json` has all 8 districts, and windows pass the sanity check
- [ ] Calibration note with your source (official calendar) saved
- [ ] 2022 check shown with wording "simulation, not proof"
- [ ] Limits slide ready
- [ ] Urdu helper passed 10 test questions, native speaker reviewed
- [ ] `advice/demo_answers.json` saved as a backup
- [ ] App runs on a fresh copy: `pip install -r requirements.txt`, then `streamlit run app.py`
- [ ] API key is NOT in the code or GitHub
- [ ] README explains setup, data sources and licences (Open-Meteo is free for non-commercial use)
- [ ] Demo rehearsed 3 times under 5 minutes; backup video recorded
- [ ] Submission uploaded and checked
- [ ] Everyone ate and rested

---

## If you are completely stuck

Send the exact error message (copy and paste it) to Claude with: what step you are on, and the last command you ran. Do not retype the error, as small details matter. If you are still stuck after 30 minutes on one step, use the cut list: **drop extra districts first, then Level 2, then the 2022 slide's extras. Never drop the map, the Urdu helper, the limits slide, or the working app.**
