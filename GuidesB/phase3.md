> Part of Guide B. See [`guide_B_app.md`](../guide_B_app.md) for the mission, dependencies and timeline.

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
