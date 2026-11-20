---
name: qa-call-assessment
description: Assess a recorded sales call (Netstar or Cartrack) against the Innovate QA scorecard. Use when the user gives a call recording (mp3, wav, m4a...), a transcript, or a Quo call and asks for a QA assessment, call score, scorecard marking, call insights or coaching feedback. Transcribes audio if needed, marks every scorecard item with quoted evidence, writes insights, and produces an Innovate-branded PDF.
---

# QA call assessment

Goal: from a call (audio or transcript) produce a scored scorecard, specific insights and coaching, and a PDF.

## 1. Get the basics
Work out from the user's message or the call itself: **which scorecard** (Netstar sales call, or Cartrack verification call), the **agent name**, **client name**, **call date** and an optional **reference**. Only ask for what you cannot work out.

## 2. Get a transcript
- **Transcript supplied** (text, .srt, .vtt, .json): use it.
- **Quo call:** fetch the call transcript with the Quo tools.
- **Audio file:** transcribe it. Use any transcription tool or connector available in this session. If none, run `python scripts/transcribe.py <file> > transcript.json` (needs `pip install faster-whisper numpy` and ffmpeg; first run downloads a model, so it needs internet). Set `WHISPER_MODEL=medium` for heavy accents or Zulu/Afrikaans mixing if the machine can cope. Recordings with agent and client on separate channels are separated automatically ("Speaker 1"/"Speaker 2"); work out which is the agent.
- If you can't transcribe it, say so plainly and ask for a transcript. Never invent or guess call content.

Number the turns 1..n (with timestamps if known) and label each Agent or Client. Speech-to-text can mishear, so don't fail an item on one garbled word when the meaning is clear.

## 3. Mark the scorecard
Read `references/scorecards.md` for the items, points, critical flags and background facts of the chosen scorecard. For EVERY item give:
- `status`: `pass`, `fail`, `review` or `na`. Pass only with clear evidence. A wrong price, term or fee is a fail. Missing is a fail unless clearly not applicable (`na`, e.g. objection handling when the client raised no objection).
- Tone, pace, language switching and interruptions can't be judged from words: use `review` and say why. Say honestly that you worked from a transcript, not by hearing the audio.
- `reason`: one sentence. `evidence`: up to 2 short verbatim quotes with their turn number.

Then write insights specific to THIS call (what was actually said, not generic advice): a 3-4 sentence `summary`, `outcome`, `client_sentiment`, `agent_tone`, `strengths`, `improvements`, `coaching` (concrete actions for the next call), `risks` (compliance or customer risks, empty if none) and `key_moments` (turn + note).

## 4. Build the PDF
Write the assessment JSON, then run the script:

```json
{"product":"ns","meta":{"agent":"","client":"","date":"YYYY-MM-DD","ref":""},
 "turns":[{"spk":"agent","text":"...","t":12.5}],
 "result":{"summary":"","outcome":"","client_sentiment":"","agent_tone":"",
   "items":{"n_intro":{"status":"pass","reason":"","evidence":[{"turn":1,"quote":"..."}]}},
   "insights":{"strengths":[],"improvements":[],"coaching":[],"risks":[]},
   "key_moments":[{"turn":0,"note":""}]}}
```
`turn` in `evidence` is 1-based; in `key_moments` it is 0-based. Use `spk` of `agent`, `client` or `unknown`; `t` is seconds or null. Every item id in the scorecard must appear in `items`.

```
pip install reportlab svglib
python scripts/report.py assessment.json "QA - <agent> - <date>.pdf"
```
The script prints the score (weighted points, percentage, verdict). Verdict rules: any failed critical item = **Critical fail**; otherwise 85%+ **Pass**, 70-84% **Needs coaching**, below 70% **Fail**. Items marked `review` are left out of the score, so it is **provisional** until a person decides them.

## 5. Reply
Give the user, in chat: the score and verdict, the 3-5 most important findings, the items needing a human listen, and the PDF file. Keep it short; the detail is in the PDF.
