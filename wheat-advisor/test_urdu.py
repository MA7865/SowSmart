"""Offline-friendly checks for Person C's Urdu helper.

Run:
    python test_urdu.py
    python test_urdu.py simple
    python test_urdu.py agent

The agent mode needs GEMINI_API_KEY, GROQ_API_KEY, or ANTHROPIC_API_KEY.
Without a key, the default uses the simple helper and tool functions so the
project can still be checked offline.
"""

from __future__ import annotations

import io
import json
import os
import re
import sys
import wave
from unittest.mock import patch

import advisor


def has_live_key() -> bool:
    return any(os.environ.get(k) for k in ("GEMINI_API_KEY", "GROQ_API_KEY", "ANTHROPIC_API_KEY"))


def has_urdu(text: str) -> bool:
    return bool(re.search(r"[\u0600-\u06ff]", text))


def no_yield_claim(text: str) -> bool:
    bad = ["پیداوار ہوگی", "آمدنی ہوگی", "loss", "yield will"]
    return not any(x.lower() in text.lower() for x in bad)


def check(name: str, ok: bool, detail: str = "") -> bool:
    mark = "PASS" if ok else "FAIL"
    print(f"{mark}: {name}" + (f" - {detail}" if detail else ""))
    return ok


def mock_groq_transcription() -> bool:
    advisor_globals = advisor.transcribe_audio.__globals__
    captured: dict[str, object] = {}
    sample = io.BytesIO()
    with wave.open(sample, "wb") as recording:
        recording.setnchannels(1)
        recording.setsampwidth(2)
        recording.setframerate(16000)
        recording.writeframes(b"\x00\x00" * 8000)

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["body"] = request.data
        captured["content_type"] = request.get_header("Content-type")
        captured["authorization"] = request.get_header("Authorization")
        captured["timeout"] = timeout
        return io.BytesIO(json.dumps({"text": "ملتان میں بوائی کا سوال"}).encode("utf-8"))

    with patch.dict(
        os.environ,
        {
            "GROQ_API_KEY": "test-groq-key",
            "GROQ_MODEL": "whisper-large-v3-turbo",
            "GROQ_TRANSCRIPTION_MODEL": "",
        },
    ):
        with patch.object(advisor_globals["urllib"].request, "urlopen", fake_urlopen):
            transcript = advisor.transcribe_audio(sample.getvalue())

    body = captured["body"]
    return (
        transcript == "ملتان میں بوائی کا سوال"
        and captured["url"] == "https://api.groq.com/openai/v1/audio/transcriptions"
        and captured["authorization"] == "Bearer test-groq-key"
        and "multipart/form-data" in captured["content_type"]
        and b"whisper-large-v3-turbo" in body
        and b"audio/wav" in body
        and captured["timeout"] == 30.0
    )


def run_simple() -> int:
    facts = advisor.facts_for("Multan", "11-28")

    def gemini_answer(question: str):
        advisor_globals = advisor.ask_agent.__globals__

        def unexpected_model_call(*args, **kwargs):
            raise AssertionError("Gemini question answering should use the local result")

        with patch.dict(
            advisor_globals,
            {
                "_selected_provider": lambda: "gemini",
                "_call_llm": unexpected_model_call,
            },
        ):
            return advisor.ask_agent(
                question,
                context=advisor.app_context("Faisalabad", "11-15"),
            )

    multan_answer, multan_calls = gemini_answer(
        "Multan mein 28 November ko gandum bona kaisa rahega?"
    )
    urdu_multan_answer, urdu_multan_calls = gemini_answer(
        "ملتان میں ۲۸ نومبر کو گندم کی بوائی کیسی رہے گی؟"
    )
    cases = [
        ("Urdu script answer", lambda: has_urdu(advisor.ask(facts, "ملتان میں 28 نومبر کو گندم بونا کیسا رہے گا؟"))),
        ("Roman Urdu answered in Urdu", lambda: has_urdu(advisor.ask(facts, "Multan mein 28 November ko gandum bona kaisa rahega?"))),
        ("Fallback has selected date", lambda: "28 نومبر" in advisor.fallback_answer(facts)),
        ("Fallback has safest window", lambda: "سے" in advisor.fallback_answer(facts) and "تک" in advisor.fallback_answer(facts)),
        ("Fertilizer refusal", lambda: "کھاد" in advisor.ask(facts, "Gandum mein kitni khad dalni chahiye?")),
        ("Forecast refusal", lambda: "پیش گوئی" in advisor.ask(facts, "Is saal garmi zyada paregi? Kitni paidawar milegi?")),
        ("Urdu fertilizer refusal", lambda: "کھاد" in advisor._precheck_question("گندم میں کتنی کھاد ڈالنی چاہیے؟", facts)),
        ("Urdu district and date parsed", lambda: advisor._district_from_question("ملتان میں ۲۸ نومبر کو بوائی؟") == "Multan" and advisor._dates_from_question("ملتان میں ۲۸ نومبر کو بوائی؟") == ["11-28"]),
        ("Groq voice transcription request uses configured model", mock_groq_transcription),
        ("Roman Urdu district overrides selected district", lambda: multan_calls[0]["input"] == {"district": "Multan", "date": "11-28"} and "ملتان" in multan_answer and "فیصل آباد" not in multan_answer),
        ("Urdu-script question uses its district and date", lambda: urdu_multan_calls[0]["input"] == {"district": "Multan", "date": "11-28"} and "ملتان" in urdu_multan_answer),
        ("Desi month asks for date", lambda: "انگریزی تاریخ" in advisor.ask(facts, "Maghar mein Sahiwal mein bijai theek rahegi?")),
        ("Wrong spelling district tool", lambda: advisor.run_tool("get_stress_for_date", {"district": "Faislabad", "date": "11-28"}).get("district") == "Faisalabad"),
        ("Unknown district handled", lambda: "districts" in advisor.run_tool("get_stress_for_date", {"district": "Lahore", "date": "11-28"})),
        ("2022 tool has no loss claim", lambda: no_yield_claim(str(advisor.run_tool("get_2022_check", {"district": "Bahawalpur"})))),
    ]
    passed = sum(check(name, fn()) for name, fn in cases)
    print(f"\n{passed}/{len(cases)} checks passed")
    return 0 if passed >= 9 else 1


def run_agent() -> int:
    if not has_live_key():
        print("SKIP: set GEMINI_API_KEY, GROQ_API_KEY, or ANTHROPIC_API_KEY to run agent mode.")
        return 1
    os.makedirs(os.path.join(advisor.HERE, "advice"), exist_ok=True)
    questions = [
        ("Multan mein 28 November ko gandum bona kaisa rahega?", "Multan", "11-28"),
        ("Faislabad mein 15 November ko bijai karun to kya hoga?", "Faisalabad", "11-15"),
        ("2022 ki garmi ki lehar Bahawalpur mein kitni shadeed thi?", "Bahawalpur", "11-15"),
        ("Larkana mein 5 November aur 1 December mein kitna farq hai?", "Larkana", "11-05"),
        ("Gandum mein kitni khad dalni chahiye?", "Multan", "11-15"),
    ]
    passed = 0
    rows = []
    for question, district, sow in questions:
        try:
            answer, calls = advisor.ask_agent(question, context=advisor.app_context(district, sow))
            ok = has_urdu(answer) and no_yield_claim(answer)
            if "khad" not in question.lower():
                ok = ok and bool(calls)
            passed += check(question[:44], ok, answer[:80].replace("\n", " "))
            rows.append((question, answer, calls, ok, ""))
        except Exception as exc:
            check(question[:44], False, str(exc))
            rows.append((question, f"ERROR: {exc}", [], False, str(exc)))
    print(f"\n{passed}/{len(questions)} agent checks passed")
    path = os.path.join(advisor.HERE, "advice", "test_run_agent.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# Urdu agent test run\n\nPassed: {passed}/{len(questions)}\n\n")
        for i, (question, answer, calls, ok, error) in enumerate(rows, 1):
            f.write(f"## {i}. {'PASS' if ok else 'FAIL'}\n\n")
            f.write(f"**Question:** {question}\n\n")
            f.write(f"**Answer:**\n\n{answer}\n\n")
            if error:
                f.write(f"**Error:** {error}\n\n")
            f.write(f"**Tool calls:** `{calls}`\n\n---\n\n")
    print(f"saved {path}")
    return 0 if passed >= 4 else 1


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ("agent" if has_live_key() else "simple")
    if mode == "agent":
        raise SystemExit(run_agent())
    raise SystemExit(run_simple())
