"""Split a transcript into speaker turns and tag each as prepared remarks or Q&A.

Expected layout (the common public transcript format):

    Prepared Remarks:
    Operator
    ...
    Jane Doe -- Chief Financial Officer
    ...
    Questions and Answers:
    John Smith -- Some Bank -- Analyst
    ...

Speaker lines are "Name -- Title" (or "Name -- Firm -- Analyst"), or just "Operator".
"""
from __future__ import annotations

import re
from dataclasses import dataclass

SPEAKER = re.compile(r"^(?P<name>[A-Z][\w.'\- ]{1,60}?)\s+(?:--|—|–)\s+(?P<title>.+)$")
QA_MARK = re.compile(r"^\s*(questions?\s*(and|&)\s*answers?|q\s*&\s*a)\s*:?\s*$", re.I)
PREP_MARK = re.compile(r"^\s*(prepared remarks|presentation)\s*:?\s*$", re.I)


@dataclass
class Turn:
    id: str
    speaker: str
    title: str
    role: str        # "executive", "analyst", "operator", "other"
    section: str     # "prepared" or "qa"
    text: str

    @property
    def sentences(self) -> list[str]:
        return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z\"$])", self.text) if s.strip()]


def _role(name: str, title: str) -> str:
    t = title.lower()
    if name.lower() == "operator":
        return "operator"
    if "analyst" in t:
        return "analyst"
    if re.search(r"chief|ceo|cfo|coo|president|officer|chair|head of|director", t) and "investor relations" not in t:
        return "executive"
    return "other"


def parse(text: str) -> list[Turn]:
    turns: list[Turn] = []
    section = "prepared"
    cur: dict | None = None

    def flush():
        if cur and cur["lines"]:
            body = " ".join(cur["lines"]).strip()
            turns.append(Turn(f"T{len(turns) + 1:02d}", cur["name"], cur["title"],
                              _role(cur["name"], cur["title"]), cur["section"], body))

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if QA_MARK.match(line):
            flush()
            cur, section = None, "qa"
            continue
        if PREP_MARK.match(line):
            flush()
            cur, section = None, "prepared"
            continue
        m = SPEAKER.match(line)
        if line == "Operator" or (m and len(line) < 120 and not line.endswith(".")):
            flush()
            name, title = ("Operator", "") if line == "Operator" else (m["name"].strip(), m["title"].strip())
            if section == "prepared" and _role(name, title) == "analyst":
                section = "qa"  # no Q&A marker, but an analyst is speaking
            cur = {"name": name, "title": title, "section": section, "lines": []}
            continue
        if cur is not None:
            cur["lines"].append(line)
    flush()
    if not turns:
        raise ValueError("couldn't find any speaker turns; expected lines like 'Jane Doe -- Chief Financial Officer'")
    return turns
