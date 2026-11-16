"""Optional LLM summary that must cite the transcript.

Works with whichever model the user configures: OpenAI, Anthropic, or any
OpenAI-compatible endpoint such as a local Ollama model (see llm_client.py).
The model gets the transcript with every turn labeled (T01, T02...) and returns
key points, positives and concerns as JSON, each citing the turns it relies on.
Any point citing a turn that doesn't exist is dropped, so the summary can't
quietly invent support.
"""
from __future__ import annotations

import json
import re

from .llm_client import LLM
from .parse import Turn

PROMPT = """You are summarizing an earnings call for an analyst. Use ONLY the transcript.
Return JSON with keys "key_points", "positives", "concerns". Each is a list of
objects {{"point": str, "turns": [turn ids]}} with 3-5 items. Cite the turn ids
that support each point. Do not give investment advice.

Transcript:
{transcript}"""


def summarize(turns: list[Turn], llm: LLM | None = None) -> str:
    llm = llm or LLM()
    transcript = "\n".join(f"[{t.id}] {t.speaker} ({t.role}, {t.section}): {t.text}" for t in turns)
    text = llm.complete(PROMPT.format(transcript=transcript))
    m = re.search(r"\{.*\}", text, re.S)
    data = json.loads(m.group(0)) if m else {}
    valid = {t.id: t.speaker for t in turns}
    out = [f"## AI summary ({llm.label}, citations checked)"]
    dropped = 0
    for key, heading in (("key_points", "Key points"), ("positives", "Positives"), ("concerns", "Concerns")):
        out.append(f"\n**{heading}**")
        for item in data.get(key, []):
            cited = [t for t in item.get("turns", []) if t in valid]
            if not cited:
                dropped += 1
                continue
            out.append(f"- {item['point']} " + " ".join(f"`[{t} · {valid[t]}]`" for t in cited))
    if dropped:
        out.append(f"\n*{dropped} point(s) removed because they didn't cite a real part of the transcript.*")
    return "\n".join(out) + "\n"
