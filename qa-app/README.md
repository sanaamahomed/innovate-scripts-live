# Innovate QA Assessment app

Upload a call recording (or paste a transcript) and get it marked against the Cartrack or Netstar
scorecard, with insights, coaching points and a branded PDF.

```
recording -> speech-to-text (faster-whisper, runs on this server)
          -> Claude marks every scorecard item, quotes evidence, writes insights
          -> reviewer can override any item / add notes -> Download PDF
```

**Claude does not hear audio** (the API reads text only), so the server turns speech into text first.
Claude then does the marking and insights from that transcript. Tone, pace and interruptions can't
be judged from words, so those items come back as *Review* for a human to decide.

## Run it on your own laptop/PC (same as the Cowork setup)
Your Cowork setup transcribes on the laptop with faster-whisper large-v3-turbo, so audio never leaves the machine.
This app can do the same: `docker compose up -d --build` on a PC with about 4 GB free RAM (8 cores is comfortable),
then open http://localhost:8000. Only the masked transcript text goes to Claude.

## Put it live (easiest)
**Render (recommended, no server skills needed):** render.com > New > Blueprint > connect this GitHub repo and
branch > it reads `render.yaml` at the repo root. Fill in `ANTHROPIC_API_KEY` and `APP_PASSWORD` (and a speech
engine key if you use one) when asked. When it finishes you get a `https://....onrender.com` address; share it
with the QA team with the password. Works the same on Railway, Fly.io or any host that runs Docker.

**Office/local server:** `cp .env.example .env`, fill it in, then `docker compose up -d --build` and open
http://localhost:8000.

## Run it manually

```bash
docker build -t innovate-qa ./qa-app
docker run -d -p 8000:8000 -v qa-data:/data \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  -e APP_PASSWORD=choose-a-password \
  innovate-qa
```
Open http://localhost:8000 (username anything, password = `APP_PASSWORD`).
Put it behind HTTPS (e.g. Caddy, nginx, or your host's TLS) before exposing it to the internet.

Without Docker: install `ffmpeg`, then `pip install -r requirements.txt` and
`uvicorn server:app --host 0.0.0.0 --port 8000`.

| Variable | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | required | Claude access. Stays on the server. |
| `APP_PASSWORD` | none | Shared password. **Set this**: the app holds call recordings and spends API credit. |
| `CLAUDE_MODEL` | `claude-sonnet-5-5` | Model used for marking. |
| `TRANSCRIBER` | `whisper` | `whisper` (built in, free, private), `deepgram`, `assemblyai` or `elevenlabs` (cloud, usually more accurate; needs `DEEPGRAM_API_KEY`, `ASSEMBLYAI_API_KEY` or `ELEVENLABS_API_KEY`). Audio is sent to that vendor. |
| `STT_KEYTERMS` | product names | Comma-separated words the speech engine should expect (Netstar, StarTag, DebiCheck...). Cloud engines only. |
| `WHISPER_MODEL` | `large-v3-turbo` | Same model your Cowork setup uses. `small`/`medium` need less RAM; `large-v3` is slowest and most accurate. About 4 GB RAM for turbo. |
| `WHISPER_BEAM` | `5` | `1` = fast, higher = slower and more accurate (the "slower more accurate setting"). |
| `STT_PROMPT` | call-centre hint | Hint given to Whisper: "South African call centre sales call between an agent and a client" plus product names. |
| `MASK_PII` | `true` | Hides emails, ID, phone and account numbers (8+ digits) before Claude reads the call. Prices are kept. Digits spoken as words are not caught. |
| `RETAIN_AUDIO` | `true` | `false` deletes the recording once transcribed. |
| `MAX_UPLOAD_MB` | `200` | Upload limit. |
| `DATA_DIR` | `./data` | Where assessments and audio are stored. |

## Getting the best accuracy
- **Stereo recordings** (agent on one channel, client on the other) are transcribed per channel, so
  speakers are separated almost perfectly. Ask your dialler/phone system for dual-channel recordings.
- Use `WHISPER_BEAM=5` (default) rather than 1 for phone audio. Use `WHISPER_MODEL=large-v3` if calls contain heavy accents or Zulu/Afrikaans code-switching and the
  server has the memory (about 5 GB). If you have a better transcript source, paste it in: it is used
  instead of the audio.
- Mono recordings work too; Claude works out who is the agent. If it gets a speaker wrong, click the
  tag in the transcript and press *Re-run assessment*.

## Finding the most accurate engine for your calls
No vendor publishes accuracy for South African English with Zulu/Afrikaans on phone audio, so measure it:
1. Pick 20-30 typical calls (stereo if you can). For a few, correct the transcript by hand and save as text.
2. Set the API keys for the engines you want to try, then run
   `python tools/compare_engines.py call.mp3 corrected.txt` (from `qa-app/`).
3. It prints each engine's word error rate and how many key terms (R239, StarTag, DebiCheck...) it got right,
   and saves every transcript in `compare_out/`. Use the engine with the lowest error, then set `TRANSCRIBER` to it.
Published (vendor-run, unverified) hint: ElevenLabs Scribe reports far better Zulu than Whisper; Deepgram added
Afrikaans in Aug 2026. Treat both as claims to test, not facts.

## How accuracy is protected
- Claude must give word-for-word quotes for every item. The app checks each quote really appears in the
  transcript; a **Pass with no verifiable quote is automatically downgraded to Review**.
- Tone, pace and interruptions can't be judged from text, so they always come back as Review.
- Speech-to-text engines mishear numbers most. Check prices, IDs and the customer's verbal YES against
  the audio (click a quote or timestamp to jump there) before a score affects an agent.
- The Deepgram and AssemblyAI connectors follow the vendors' public documentation but have only been
  tested against simulated responses. Try each on a few real calls first. No vendor publishes accuracy
  for South African English with Zulu/Afrikaans on phone audio, so compare engines on your own calls.

## Changing the scorecards
Edit `scorecards.py` (wording, points, critical flags, pass marks), then restart. Add a new product by
adding an entry to `PRODUCTS`.

## Tests
`pip install pytest httpx && python -m pytest qa-app/tests` (speech-to-text and Claude are faked).
`python -m tests.mock_server` (from `qa-app/`) runs the UI with fakes so you can try it without keys.
