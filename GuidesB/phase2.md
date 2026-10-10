> Part of Guide B. See [`guide_B_app.md`](../guide_B_app.md) for the mission, dependencies and timeline.

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
