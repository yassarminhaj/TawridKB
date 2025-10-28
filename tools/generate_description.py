"""
Generate short, professional video descriptions from transcript text.

Two modes:
- Online (if OPENAI_API_KEY is set): Uses OpenAI Chat Completions
- Offline fallback: TextRank summarization via `summa`
"""

import os

SYSTEM_PROMPT = (
    "You are a product documentation writer for Tawrid, "
    "a supply chain financing platform. Based on the transcript, "
    "write a concise, professional video description (max 4 sentences) "
    "summarizing the tutorial’s purpose and the key user actions."
)

def _online_generate(transcript: str) -> str:
    from openai import OpenAI
    client = OpenAI()
    model = os.getenv("GENERATOR_MODEL", "gpt-4o-mini")
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role":"system","content": SYSTEM_PROMPT},
            {"role":"user","content": transcript},
        ],
        temperature=0.2,
    )
    return resp.choices[0].message.content.strip()

def _offline_generate(transcript: str) -> str:
    # TextRank summarization as a fallback
    try:
        from summa.summarizer import summarize
        summary = summarize(transcript, ratio=0.15) or summarize(transcript, words=80)
        if not summary:
            return transcript.strip()[:600]
        parts = [s.strip() for s in summary.split(".") if s.strip()]
        return (". ".join(parts[:4]) + ".") if parts else transcript.strip()[:600]
    except Exception:
        return transcript.strip()[:600]

def generate_description(transcript: str) -> str:
    if os.getenv("OPENAI_API_KEY"):
        try:
            return _online_generate(transcript)
        except Exception:
            pass
    return _offline_generate(transcript)
