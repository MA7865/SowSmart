"""Save five real Urdu demo answers from the agent.

Run after final results.json is ready:
    python make_demo_answers.py

Check whether saved answers still match current results.json:
    python make_demo_answers.py --check
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time

import advisor

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

QUESTIONS = [
    ("ملتان میں 28 نومبر کو گندم بونا کیسا رہے گا؟", "Multan", "11-28"),
    ("Faisalabad mein gandum kab bona chahiye?", "Faisalabad", "11-15"),
    ("2022 ki garmi ki lehar Bahawalpur mein kitni shadeed thi?", "Bahawalpur", "11-15"),
    ("Larkana mein 5 November aur 1 December mein kitna farq hai?", "Larkana", "11-05"),
    ("Gandum mein kitni khad dalni chahiye?", "Multan", "11-15"),
]

RESULTS = os.path.join(advisor.HERE, "results.json")
OUT_JSON = os.path.join(advisor.HERE, "advice", "demo_answers.json")
OUT_MD = os.path.join(advisor.HERE, "advice", "demo_answers.md")


def has_live_key() -> bool:
    return any(os.environ.get(k) for k in ("GEMINI_API_KEY", "GROQ_API_KEY", "ANTHROPIC_API_KEY"))


def sha(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha1(f.read()).hexdigest()[:10]


def main() -> int:
    if "--check" in sys.argv:
        if not os.path.exists(OUT_JSON):
            print("OUT OF DATE: advice/demo_answers.json does not exist")
            return 1
        saved = json.load(open(OUT_JSON, encoding="utf-8"))
        same = os.path.exists(RESULTS) and saved.get("results_sha1") == sha(RESULTS)
        print("OK, answers match the current results.json" if same else "OUT OF DATE: run make_demo_answers.py again")
        return 0 if same else 1

    if not os.path.exists(RESULTS) or any(v.get("FAKE") for v in advisor._load_results().values()):
        print("Refusing to save demo answers: results.json is missing or fake.")
        return 1
    if not has_live_key():
        print("Refusing to save demo answers: set GEMINI_API_KEY, GROQ_API_KEY, or ANTHROPIC_API_KEY first.")
        return 1

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    items = []
    for question, district, sow in QUESTIONS:
        answer, calls = advisor.ask_agent(question, context=advisor.app_context(district, sow))
        items.append({"question": question, "answer": answer, "tool_calls": calls})
        print("\nQ:", question, "\nA:", answer)
        time.sleep(1)

    out = {
        "model": advisor.MODEL,
        "results_sha1": sha(RESULTS),
        "created": time.strftime("%Y-%m-%d %H:%M"),
        "items": items,
    }
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(f"# Saved demo answers (real outputs, {out['created']}, results {out['results_sha1']})\n\n")
        for item in items:
            f.write(f"**Q:** {item['question']}\n\n{item['answer']}\n\n---\n\n")
    print("\nsaved advice/demo_answers.json and advice/demo_answers.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
