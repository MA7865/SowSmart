> Part of Guide B. See [`guide_B_app.md`](../guide_B_app.md) for the mission, dependencies and timeline.

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
