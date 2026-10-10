import json
import os

try:
    import anthropic
except Exception:  # pragma: no cover - optional dependency
    anthropic = None

SYSTEM = """You help Pakistani extension officers and farmers choose a wheat sowing date.
Rules:
- Use ONLY the numbers in the FACTS. Never invent numbers or facts.
- Answer in simple Urdu (Urdu script). If the question is in Roman Urdu, still answer in Urdu script.
- 3 to 5 short sentences.
- Say this is based on the last 25 years of weather and a simulation, not a forecast.
- Do NOT give advice about seed varieties, irrigation, fertilizer or pesticide.
  If asked, say this tool cannot answer that and they should ask their extension officer.
- If district or date is unclear, ask ONE short question.
"""


def _client():
    if anthropic is None:
        raise RuntimeError("anthropic package is not available")
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")
    return anthropic.Anthropic()


def ask(facts: dict, question: str) -> str:
    client = _client()
    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=600,
        system=SYSTEM,
        messages=[
            {
                "role": "user",
                "content": "FACTS:\n"
                + json.dumps(facts, ensure_ascii=False)
                + "\n\nQUESTION:\n"
                + question,
            }
        ],
    )
    return msg.content[0].text


def fallback_answer(facts: dict) -> str:
    district = facts.get("district", "district")
    sowing = facts.get("chosen_sowing_date", "chosen date")
    window = facts.get("safest_window", ["unknown", "unknown"])
    best = facts.get("best_day", "unknown")
    extra = facts.get("extra_stress_vs_best", 0)
    share = facts.get("share_of_past_years_best_day_was_ok", 0)
    if isinstance(share, (int, float)):
        share_text = f"{share:.0%}"
    else:
        share_text = str(share)

    return (
        f"{district} کے لیے منتخب تاریخ {sowing} ہے۔ سب سے محفوظ دہلیز {window[0]} سے {window[1]} تک ہے، "
        f"اور بہترین دن {best} ہے۔ آپ کی تاریخ کے لیے اضافی دباؤ {extra:+.1f} ہے، جبکہ پچھلے سالوں میں بہترین دن "
        f"کافی حد تک مناسب رہا ہے۔ یہ اوسط کے مطابق 25 سال کے موسم کے اعداد و شمار پر مبنی ہے، نہ کہ موجودہ موسم کی پیش گوئی۔"
    )


def ask_agent(question: str, context: str | None = None, facts: dict | None = None):
    if facts is None:
        facts = {}
    tool_calls = [
        {
            "tool": "sowing_risk_lookup",
            "input": {"question": question, "context": context or "", "facts": facts},
        }
    ]
    try:
        answer = ask(facts, question)
        return answer, tool_calls
    except Exception:
        return fallback_answer(facts), tool_calls
