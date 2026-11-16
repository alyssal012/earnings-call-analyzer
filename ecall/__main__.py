"""
python -m ecall CALL.txt [--prior LAST_QUARTER.txt] [--out report.md] [--llm]
"""
from __future__ import annotations

import argparse
import pathlib

from .analyze import analyze
from .parse import parse
from .report import build


def main() -> None:
    ap = argparse.ArgumentParser(prog="ecall", description="Analyze an earnings call transcript.")
    ap.add_argument("transcript", type=pathlib.Path)
    ap.add_argument("--prior", type=pathlib.Path, help="last quarter's transcript, for comparison")
    ap.add_argument("--out", type=pathlib.Path)
    ap.add_argument("--llm", action="store_true", help="add an AI-written summary using the model set in LLM_PROVIDER / LLM_MODEL")
    args = ap.parse_args()

    text = args.transcript.read_text()
    turns = parse(text)
    a = analyze(turns)
    prior = analyze(parse(args.prior.read_text())) if args.prior else None
    title = text.strip().splitlines()[0][:100]
    report = build(a, title, prior)
    md = report["markdown"]
    if args.llm:
        from .llm import summarize
        md += "\n" + summarize(turns)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(md)
    print(md)


if __name__ == "__main__":
    main()
