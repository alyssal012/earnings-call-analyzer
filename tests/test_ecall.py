import json
import pathlib
from types import SimpleNamespace

from ecall.analyze import analyze, count, term_shifts, tone
import pytest

from ecall.llm import summarize
from ecall.llm_client import LLM
from ecall.parse import parse
from ecall.report import build

EX = pathlib.Path(__file__).resolve().parents[1] / "examples"
Q2 = parse((EX / "harborline_q2_fy2026.txt").read_text())
Q3 = parse((EX / "harborline_q3_fy2026.txt").read_text())


def test_parser_finds_roles_and_sections():
    roles = {(t.speaker, t.role) for t in Q3}
    assert ("Priya Raman", "executive") in roles and ("Owen Pak", "analyst") in roles
    assert ("Dana Whitcomb", "other") in roles  # investor relations host isn't scored as management
    assert all(t.section == "prepared" for t in Q3 if t.speaker == "Priya Raman" and "Gross margin" in t.text)
    assert all(t.section == "qa" for t in Q3 if t.role == "analyst")


def test_parser_without_section_headers():
    text = ("Operator\nWelcome.\nJane Roe -- Chief Executive Officer\nRevenue grew 5%.\n"
            "Sam Lee -- Big Bank -- Analyst\nHow much was pricing?\nJane Roe -- Chief Executive Officer\nAbout 2%.\n")
    t = parse(text)
    assert [x.section for x in t] == ["prepared", "prepared", "qa", "qa"]


def test_softeners_flip_negative_words():
    assert count("fewer markdowns and lower promotional activity", {"markdowns", "promotional"}, negate=True) == 0
    assert count("higher markdowns", {"markdowns"}, negate=True) == 1


def test_tone_moves_the_right_way():
    a2, a3 = analyze(Q2), analyze(Q3)
    assert a2.tone_prepared.score > 0.5 > a3.tone_prepared.score
    assert a3.tone_prepared.hedging_per_1k > a2.tone_prepared.hedging_per_1k


def test_guidance_direction():
    assert analyze(Q2).guidance_direction == "raised"
    assert analyze(Q3).guidance_direction == "lowered"


def test_evasive_answers_are_caught_and_direct_ones_are_not():
    qa = {q.question.speaker: q for q in analyze(Q3).qa}
    assert qa["Leah Castro"].evasive and qa["Owen Pak"].evasive
    assert not qa["Ravi Menon"].evasive  # asked for a rate, got "6%"
    assert not any(q.evasive for q in analyze(Q2).qa)


def test_term_shifts_spot_new_themes():
    up, down = term_shifts(Q3, Q2)
    assert "wholesale" in [u[0] for u in up] and "freight" in [d[0] for d in down]


def test_report_has_summary_and_pros_cons_with_citations():
    r = build(analyze(Q3), "Q3", prior=analyze(Q2))
    md = r["markdown"]
    for section in ("## Key points", "**Positives**", "**Concerns**", "## What changed since last quarter", "## Q&A check"):
        assert section in md
    assert r["guidance"] == "lowered" and r["evasive"] == 2
    assert any("Lowered full-year guidance (now 5% to 6%, was 9% to 10%)" in c for c, _ in r["concerns"])
    ids = {t.id for t in Q3}
    assert all(tid in ids for _, tid in r["positives"] + r["concerns"])


def test_mixed_sentences_are_not_called_positive():
    assert all("below our expectations" not in s for _, s, _ in analyze(Q3).positives)


PAYLOAD = json.dumps({"key_points": [{"point": "Guidance was lowered.", "turns": ["T04"]},
                                      {"point": "Made-up claim.", "turns": ["T99"]}],
                       "positives": [{"point": "DTC grew 9%.", "turns": ["T03"]}], "concerns": []})


def fake_anthropic():
    return SimpleNamespace(messages=SimpleNamespace(
        create=lambda **kw: SimpleNamespace(content=[SimpleNamespace(text=PAYLOAD)])))


def fake_openai():
    resp = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=PAYLOAD))])
    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kw: resp)))


@pytest.mark.parametrize("provider,make", [("anthropic", fake_anthropic), ("openai", fake_openai),
                                           ("compatible", fake_openai)])
def test_llm_summary_drops_uncited_points_for_every_provider(provider, make):
    md = summarize(Q3, LLM(provider=provider, model="any-model", client=make()))
    assert "Guidance was lowered." in md and "Made-up claim." not in md
    assert "1 point(s) removed" in md and f"{provider}:any-model" in md
