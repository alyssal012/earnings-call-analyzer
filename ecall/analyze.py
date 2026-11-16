"""Score a parsed call: tone, hedging, guidance, key figures, evasive answers,
and what changed from the previous quarter."""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from . import lexicon as L
from .parse import Turn

WORD = re.compile(r"[a-z][a-z'\-]*")
STOP = set("""a an the and or but if of to in on for with at by from as is are was were be been being this that
these those it its we our us you your they their i me my he she his her them there here what which who whom
whose when where why how all any both each few more most other some such no nor not only own same so than too
very can will just should now also about into over after before then once up down out off again further
during while because until against between through above below have has had having do does did doing
would could may might must shall let thank thanks operator question questions call today quarter year""".split())
NUMBER = re.compile(r"\$?\d[\d,.]*\s*(%|percent|basis points|million|billion)?")
FIGURE_WORDS = re.compile(r"revenue|sales|margin|earnings per share|eps|operating income|cash flow|inventory|"
                          r"guidance|members|stores|sell-through", re.I)


def words(text: str) -> list[str]:
    return WORD.findall(text.lower())


SOFTENERS = {"lower", "fewer", "less", "reduced", "no", "not"}


def count(text: str, vocab, negate: bool = False) -> int:
    """Count lexicon hits. With negate=True, skip hits right after 'lower', 'fewer', 'no'...
    so 'lower markdowns' isn't counted as bad news."""
    w = words(text)
    t = " " + " ".join(w) + " "
    n = 0
    for term in vocab:
        if " " in term:
            n += t.count(f" {term} ")
            continue
        for i, x in enumerate(w):
            if x == term and not (negate and i > 0 and w[i - 1] in SOFTENERS):
                n += 1
    return n


@dataclass
class Tone:
    words: int
    positive: int
    negative: int
    hedging: int

    @property
    def score(self) -> float:
        """-1 (all negative) to +1 (all positive)."""
        return (self.positive - self.negative) / max(1, self.positive + self.negative)

    @property
    def hedging_per_1k(self) -> float:
        return 1000 * self.hedging / max(1, self.words)


def tone(text: str) -> Tone:
    return Tone(len(words(text)), count(text, L.POSITIVE), count(text, L.NEGATIVE, negate=True), count(text, L.HEDGING))


@dataclass
class QA:
    question: Turn
    answers: list[Turn]
    deflections: list[str] = field(default_factory=list)
    asked_for_number: bool = False
    gave_number: bool = False
    relevance: float = 0.0

    @property
    def evasive(self) -> bool:
        score = 2 * len(self.deflections) + (self.asked_for_number and not self.gave_number) + (self.relevance < 0.08)
        return score >= 2


@dataclass
class Analysis:
    turns: list[Turn]
    tone_prepared: Tone
    tone_qa: Tone
    guidance: list[dict]
    figures: list[tuple[str, str]]
    qa: list[QA]
    positives: list[tuple[str, str, float]]
    concerns: list[tuple[str, str, float]]

    @property
    def guidance_direction(self) -> str:
        dirs = {g["direction"] for g in self.guidance}
        for d in ("lowered", "raised", "reaffirmed"):
            if d in dirs:
                return d
        return "not discussed"


def _exec_text(turns, section=None):
    return " ".join(t.text for t in turns if t.role == "executive" and (section is None or t.section == section))


def _guidance(turns) -> list[dict]:
    out = []
    for t in turns:
        if t.role != "executive":
            continue
        for s in t.sentences:
            low = s.lower()
            if not any(w in low for w in L.GUIDANCE_WORDS):
                continue
            direction = ("lowered" if any(w in low for w in L.LOWER) else
                         "raised" if any(w in low for w in L.RAISE) else
                         "reaffirmed" if any(w in low for w in L.REAFFIRM) else None)
            ranges = re.findall(r"\$?\d[\d.,]*%?\s+to\s+\$?\d[\d.,]*%?", s)
            if direction or ranges:
                out.append({"turn": t.id, "direction": direction or "stated", "ranges": ranges, "text": s})
    return out


def _figures(turns) -> list[tuple[str, str]]:
    out = []
    for t in turns:
        if t.role == "executive" and t.section == "prepared":
            for s in t.sentences:
                if NUMBER.search(s) and FIGURE_WORDS.search(s) and not any(w in s.lower() for w in L.GUIDANCE_WORDS):
                    out.append((t.id, s))
    return out


def _qa_pairs(turns) -> list[QA]:
    pairs, cur = [], None
    for t in turns:
        if t.section != "qa":
            continue
        if t.role == "analyst":
            cur = QA(t, [])
            pairs.append(cur)
        elif t.role == "executive" and cur is not None:
            cur.answers.append(t)
        elif t.role == "operator":
            cur = None if cur and cur.answers else cur
    for p in pairs:
        ans = " ".join(a.text for a in p.answers)
        low = ans.lower()
        p.deflections = [d for d in L.DEFLECTIONS if d in low]
        p.asked_for_number = bool(re.search(r"how much|how many|quantify|what was the|what rate|what percent|"
                                            r"how big|size of", p.question.text.lower()))
        p.gave_number = bool(re.search(r"\d", ans))
        if ans:
            m = TfidfVectorizer(stop_words=list(STOP)).fit_transform([p.question.text, ans])
            p.relevance = float(cosine_similarity(m[0], m[1])[0, 0])
    return pairs


def _rank_sentences(turns):
    scored = []
    for t in turns:
        if t.role != "executive":
            continue
        for s in t.sentences:
            if len(s) < 25 or "forward-looking" in s.lower():
                continue
            tn = tone(s)
            net = tn.positive - tn.negative
            if net == 0:
                continue  # mixed or neutral sentences ("grew 3%, below expectations") aren't clear signals
            weight = net + 0.5 * math.copysign(1, net) * bool(NUMBER.search(s))
            scored.append((t.id, s, weight))
    pos = sorted([x for x in scored if x[2] > 0], key=lambda x: -x[2])
    neg = sorted([x for x in scored if x[2] < 0], key=lambda x: x[2])
    return pos, neg


def analyze(turns: list[Turn]) -> Analysis:
    pos, neg = _rank_sentences(turns)
    return Analysis(turns=turns,
                    tone_prepared=tone(_exec_text(turns, "prepared")),
                    tone_qa=tone(_exec_text(turns, "qa")),
                    guidance=_guidance(turns), figures=_figures(turns), qa=_qa_pairs(turns),
                    positives=pos, concerns=neg)


def term_shifts(cur: list[Turn], prior: list[Turn], top: int = 6) -> tuple[list, list]:
    """Words executives used much more (or less) than last quarter, per 1,000 words."""
    def freq(turns):
        w = [x for x in words(_exec_text(turns)) if x not in STOP and len(x) > 3 and "'" not in x]
        return Counter(w), max(1, len(w))
    (c1, n1), (c0, n0) = freq(cur), freq(prior)
    shifts = []
    for term in set(c1) | set(c0):
        if max(c1[term], c0[term]) < 3 or abs(c1[term] - c0[term]) < 2:
            continue
        r1, r0 = 1000 * c1[term] / n1, 1000 * c0[term] / n0
        shifts.append((term, c0[term], c1[term], math.log((r1 + 1) / (r0 + 1))))
    up = sorted([s for s in shifts if s[3] > 0.3], key=lambda s: -s[3])[:top]
    down = sorted([s for s in shifts if s[3] < -0.3], key=lambda s: s[3])[:top]
    return up, down
