"""Offline-friendly checks for Person C's Urdu helper.

Run:
    python test_urdu.py
    python test_urdu.py simple
    python test_urdu.py agent

The agent mode needs ANTHROPIC_API_KEY. Without a key, the default uses the
simple helper and tool functions so the project can still be checked offline.
"""

from __future__ import annotations

import os
import re
import sys

import advisor


def has_urdu(text: str) -> bool:
    return bool(re.search(r"[\u0600-\u06ff]", text))


def no_yield_claim(text: str) -> bool:
    bad = ["پیداوار ہوگی", "آمدنی ہوگی", "loss", "yield will"]
    return not any(x.lower() in text.lower() for x in bad)


def check(name: str, ok: bool, detail: str = "") -> bool:
    mark = "PASS" if ok else "FAIL"
    print(f"{mark}: {name}" + (f" - {detail}" if detail else ""))
    return ok


def run_simple() -> int:
    facts = advisor.facts_for("Multan", "11-28")
    cases = [
        ("Urdu script answer", lambda: has_urdu(advisor.ask(facts, "ملتان میں 28 نومبر کو گندم بونا کیسا رہے گا؟"))),
        ("Roman Urdu answered in Urdu", lambda: has_urdu(advisor.ask(facts, "Multan mein 28 November ko gandum bona kaisa rahega?"))),
        ("Fallback has selected date", lambda: "28 نومبر" in advisor.fallback_answer(facts)),
        ("Fallback has safest window", lambda: "سے" in advisor.fallback_answer(facts) and "تک" in advisor.fallback_answer(facts)),
        ("Fertilizer refusal", lambda: "کھاد" in advisor.ask(facts, "Gandum mein kitni khad dalni chahiye?")),
        ("Forecast refusal", lambda: "پیش گوئی" in advisor.ask(facts, "Is saal garmi zyada paregi? Kitni paidawar milegi?")),
        ("Desi month asks for date", lambda: "انگریزی تاریخ" in advisor.ask(facts, "Maghar mein Sahiwal mein bijai theek rahegi?")),
        ("Wrong spelling district tool", lambda: advisor.run_tool("get_stress_for_date", {"district": "Faislabad", "date": "11-28"}).get("district") == "Faisalabad"),
        ("Unknown district handled", lambda: "districts" in advisor.run_tool("get_stress_for_date", {"district": "Lahore", "date": "11-28"})),
        ("2022 tool has no loss claim", lambda: no_yield_claim(str(advisor.run_tool("get_2022_check", {"district": "Bahawalpur"})))),
    ]
    passed = sum(check(name, fn()) for name, fn in cases)
    print(f"\n{passed}/{len(cases)} checks passed")
    return 0 if passed >= 9 else 1


def run_agent() -> int:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("SKIP: ANTHROPIC_API_KEY is not set, so agent mode cannot call Claude.")
        return 1
    questions = [
        ("Multan mein 28 November ko gandum bona kaisa rahega?", "Multan", "11-28"),
        ("Faislabad mein 15 November ko bijai karun to kya hoga?", "Faisalabad", "11-15"),
        ("2022 ki garmi ki lehar Bahawalpur mein kitni shadeed thi?", "Bahawalpur", "11-15"),
        ("Larkana mein 5 November aur 1 December mein kitna farq hai?", "Larkana", "11-05"),
        ("Gandum mein kitni khad dalni chahiye?", "Multan", "11-15"),
    ]
    passed = 0
    for question, district, sow in questions:
        try:
            answer, calls = advisor.ask_agent(question, context=advisor.app_context(district, sow))
            ok = has_urdu(answer) and no_yield_claim(answer)
            if "khad" not in question.lower():
                ok = ok and bool(calls)
            passed += check(question[:44], ok, answer[:80].replace("\n", " "))
        except Exception as exc:
            check(question[:44], False, str(exc))
    print(f"\n{passed}/{len(questions)} agent checks passed")
    return 0 if passed >= 4 else 1


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ("agent" if os.environ.get("ANTHROPIC_API_KEY") else "simple")
    if mode == "agent":
        raise SystemExit(run_agent())
    raise SystemExit(run_simple())
