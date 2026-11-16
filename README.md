# Earnings Call Analyzer

Reads an earnings call transcript and produces a one-page brief: **key points, positives vs. concerns, which analyst questions management dodged, and what changed since last quarter.** Every point cites the part of the call it came from.

Each quarter, public companies hold a call where executives present results and then take questions from analysts. Analysts, investors and competitors listen closely for *how* management talks as well as the numbers: whether they sound confident or nervous, raise or cut their forecast, or sidestep hard questions. This tool reads the call for those signals.

```bash
python -m ecall examples/harborline_q3_fy2026.txt --prior examples/harborline_q2_fy2026.txt
```

```markdown
## Key points
- Overall tone: negative (-0.52 on a −1 to +1 scale) in prepared remarks; mixed in Q&A answers.
- Guidance: lowered. Given the softer demand and wholesale headwinds, we are lowering our full-year guidance.
- Q&A: 4 analyst questions, 2 not directly answered.
- Tone of prepared remarks went from very positive (+1.00) to negative (-0.52).

## Positives vs. concerns
Positives
- "That said, our direct-to-consumer business grew 9%, and our loyalty program reached 6.5 million members."  [T03 · Marcus Feld]
Concerns
- Lowered full-year guidance (now 5% to 6%, was 9% to 10%).  [T04 · Priya Raman]
- Didn't directly answer Owen Pak's question (gave no number when asked for one):
  "Can you quantify how much of the guidance cut is from wholesale order cancellations…"  [T09 · Owen Pak]

## What changed since last quarter
- Hedging language: 0.0 → 19.9 per 1,000 words (more cautious).
- Guidance: raised last quarter → lowered this quarter.
- Evasive answers in Q&A: 0 → 2.
- Talked about more: wholesale (1→4), partners (1→3), inventory (2→4)
- Talked about less: freight (3→0)
```

Full reports: [`reports/harborline_q3_report.md`](reports/harborline_q3_report.md) and [`reports/harborline_q2_report.md`](reports/harborline_q2_report.md).

> **The sample calls are fictional.** Harborline Outfitters and everyone on its calls are invented, written to show a strong quarter followed by a weak one. Real transcripts are copyrighted and often paywalled, so none are included. Point the tool at any transcript you have access to.

## What it checks

| Signal | How |
|---|---|
| **Tone**, scored separately for scripted remarks and live Q&A | Word lists written for earnings language. General sentiment tools misread finance: "liability" isn't bad news, but "challenging" is a strong warning. Handles "*lower* markdowns" and "*fewer* promotions" so good news isn't counted as bad. |
| **Hedging** (per 1,000 words) | "dynamic", "prudent", "too early", "reviewing", "visibility"... |
| **Guidance** raised / lowered / reaffirmed | Finds forecast sentences and pulls out the new and old ranges ("now 5% to 6%, was 9% to 10%"). |
| **Evasive answers** | For each analyst question: did the answer include deflection phrases ("we don't break that out", "too early to say")? If the analyst asked for a number, did the answer contain one? How related is the answer to the question (TF-IDF similarity)? |
| **Quarter-over-quarter changes** | Tone, hedging, guidance and evasiveness vs. last call, plus the words management started or stopped using. In the sample, *wholesale* and *inventory* surge while *freight* (last quarter's tailwind) disappears. |
| **Positives vs. concerns** | Combines the structural signals above with the most clearly positive and negative sentences. Mixed sentences like "grew 3%, below our expectations" are left out of both lists. |

## Optional: AI summary with checked citations (bring your own model)

Add an AI-written summary using **whichever model you choose**: OpenAI, Anthropic, or any OpenAI-compatible service, including free local models through Ollama. It's set with two settings, with no code changes:

```bash
export LLM_PROVIDER=openai     LLM_MODEL=<model>   # + OPENAI_API_KEY,    pip install openai
export LLM_PROVIDER=anthropic  LLM_MODEL=<model>   # + ANTHROPIC_API_KEY, pip install anthropic
export LLM_PROVIDER=compatible LLM_MODEL=<model> LLM_BASE_URL=http://localhost:11434/v1   # local Ollama

python -m ecall call.txt --prior last_call.txt --llm
```

The model gets the transcript with every speaker turn labeled (`T01`, `T02`...) and must cite the turns behind each point. **Any point that cites a turn that doesn't exist is removed**, and the report says how many were dropped, so the AI can't slip in unsupported claims. The report also records which provider and model wrote the summary. Tests check every provider path with fake clients.

## Run it

```bash
pip install -r requirements.txt
python -m ecall examples/harborline_q3_fy2026.txt --prior examples/harborline_q2_fy2026.txt --out reports/q3.md
pytest -q
```

Transcripts should use the common public format: a `Prepared Remarks:` section, a `Questions and Answers:` section, and speaker lines like `Jane Doe -- Chief Financial Officer` or `John Smith -- Some Bank -- Analyst`. If the section headers are missing, the parser starts Q&A at the first analyst.

## Limitations and next steps

- Word-based tone misses sarcasm, context and negations beyond simple cases. The optional AI summary helps here.
- **Does tone predict the stock?** The natural next step is to run this across many companies' calls and test whether a tone drop or a jump in evasive answers predicts the next day's stock move, compared against what the reported numbers alone would predict.
- Compare a company's call against its competitors' calls from the same quarter.

*For research, not investment advice.*

## Stack

Python, scikit-learn (TF-IDF), regex, pytest, optional LLM layer (OpenAI, Anthropic, or OpenAI-compatible/local models)
