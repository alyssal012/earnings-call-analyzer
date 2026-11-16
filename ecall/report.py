"""Write the one-page report: key points, positives vs. concerns, Q&A check, and
what changed since last quarter. Every point cites the speaker turn it came from."""
from __future__ import annotations

from .analyze import Analysis, term_shifts


def _tone_word(x: float) -> str:
    return ("very positive" if x >= 0.6 else "positive" if x >= 0.2 else "mixed" if x > -0.2
            else "negative" if x > -0.6 else "very negative")


def _quote(s: str, n: int = 160) -> str:
    return s if len(s) <= n else s[: n - 1].rsplit(" ", 1)[0] + "…"


def build(a: Analysis, title: str, prior: Analysis | None = None) -> dict:
    speakers = {t.id: t.speaker for t in a.turns}
    evasive = [q for q in a.qa if q.evasive]
    g = a.guidance_direction

    # ---------- positives and concerns ----------
    positives, concerns = [], []
    if g == "raised":
        positives.append(("Raised full-year guidance.", a.guidance[0]["turn"]))
    if g == "lowered":
        lowered = [x for x in a.guidance if x["direction"] == "lowered"]
        gl = max(lowered, key=lambda x: len(x["ranges"]))
        rng = f" (now {gl['ranges'][0]}, was {gl['ranges'][1]})" if len(gl["ranges"]) >= 2 else ""
        concerns.append((f"Lowered full-year guidance{rng}.", gl["turn"]))
    for q in evasive:
        why = "gave no number when asked for one" if q.asked_for_number and not q.gave_number else "deflected"
        concerns.append((f"Didn't directly answer {q.question.speaker}'s question ({why}): "
                         f"\"{_quote(q.question.text, 110)}\"", q.question.id))
    direct = [q for q in a.qa if q.asked_for_number and q.gave_number and not q.evasive]
    numeric = sum(q.asked_for_number for q in a.qa)
    if direct and len(direct) * 2 >= numeric:
        positives.append((f"Gave specific numbers when analysts asked ({len(direct)} of "
                          f"{numeric} numeric questions).", direct[0].answers[0].id))
    used = set()
    for tid, s, _ in a.positives[:4]:
        positives.append((f"\"{_quote(s)}\"", tid))
        used.add(s)
    for tid, s, _ in a.concerns[:4]:
        if s not in used:
            concerns.append((f"\"{_quote(s)}\"", tid))

    # ---------- comparison ----------
    comp = []
    first_exec = next((t.id for t in a.turns if t.role == "executive"), a.turns[0].id)
    if prior:
        d_tone = a.tone_prepared.score - prior.tone_prepared.score
        d_hedge = a.tone_prepared.hedging_per_1k - prior.tone_prepared.hedging_per_1k
        comp.append(f"Tone of prepared remarks went from **{_tone_word(prior.tone_prepared.score)}** "
                    f"({prior.tone_prepared.score:+.2f}) to **{_tone_word(a.tone_prepared.score)}** ({a.tone_prepared.score:+.2f}).")
        comp.append(f"Hedging language: {prior.tone_prepared.hedging_per_1k:.1f} → {a.tone_prepared.hedging_per_1k:.1f} per 1,000 words"
                    + (" (more cautious)." if d_hedge > 3 else " (less cautious)." if d_hedge < -3 else "."))
        comp.append(f"Guidance: {prior.guidance_direction} last quarter → **{g}** this quarter.")
        comp.append(f"Evasive answers in Q&A: {sum(q.evasive for q in prior.qa)} → **{len(evasive)}**.")
        up, down = term_shifts(a.turns, prior.turns)
        if up:
            comp.append("Talked about more: " + ", ".join(f"*{t}* ({c0}→{c1})" for t, c0, c1, _ in up))
        if down:
            comp.append("Talked about less: " + ", ".join(f"*{t}* ({c0}→{c1})" for t, c0, c1, _ in down))
        if d_tone < -0.4:
            concerns.insert(0, (f"Management's tone dropped sharply since last quarter ({prior.tone_prepared.score:+.2f} → "
                                f"{a.tone_prepared.score:+.2f}).", first_exec))
        elif d_tone > 0.4:
            positives.insert(0, ("Management's tone improved sharply since last quarter.", first_exec))

    # ---------- key points ----------
    overall = _tone_word(a.tone_prepared.score)
    key = [f"**Overall tone: {overall}** ({a.tone_prepared.score:+.2f} on a −1 to +1 scale) in prepared remarks; "
           f"{_tone_word(a.tone_qa.score)} in Q&A answers."]
    key.append(f"**Guidance: {g}.**" + (f" {_quote(a.guidance[0]['text'], 200)}" if a.guidance else ""))
    if a.figures:
        key.append("**Headline numbers:** " + " ".join(_quote(s, 140) for _, s in a.figures[:3]))
    key.append(f"**Q&A:** {len(a.qa)} analyst questions, **{len(evasive)} not directly answered**.")
    if prior:
        key.append(comp[0])

    # ---------- markdown ----------
    cite = lambda tid: f" `[{tid} · {speakers.get(tid, '?')}]`"
    md = [f"# {title}", "", "## Key points", *[f"- {k}" for k in key], "",
          "## Positives vs. concerns", "", "**Positives**", *([f"- {t}{cite(tid)}" for t, tid in positives[:6]] or ["- none found"]),
          "", "**Concerns**", *([f"- {t}{cite(tid)}" for t, tid in concerns[:6]] or ["- none found"]), ""]
    if prior:
        md += ["## What changed since last quarter", *[f"- {c}" for c in comp], ""]
    md += ["## Q&A check", "", "| Analyst | Asked for a number? | Got one? | Deflection phrases | Verdict |", "|---|---|---|---|---|"]
    for q in a.qa:
        md.append(f"| {q.question.speaker} | {'yes' if q.asked_for_number else 'no'} | "
                  f"{'yes' if q.gave_number else 'no'} | {', '.join(f'“{d}”' for d in q.deflections[:2]) or '-'} | "
                  f"{'**evasive**' if q.evasive else 'answered'} |")
    md += ["", "## Key figures mentioned", *[f"- {_quote(s, 200)}{cite(tid)}" for tid, s in a.figures], "",
           "*Automated analysis for research, not investment advice. Tone scores are word-based and can miss context.*"]
    return {"markdown": "\n".join(md) + "\n", "positives": positives, "concerns": concerns,
            "evasive": len(evasive), "guidance": g, "tone": a.tone_prepared.score}
