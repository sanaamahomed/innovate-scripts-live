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

## Run it

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
| `WHISPER_MODEL` | `small` | `tiny`/`base` faster, `medium`/`large-v3` more accurate (needs more RAM and time). |
| `RETAIN_AUDIO` | `true` | `false` deletes the recording once transcribed. |
| `MAX_UPLOAD_MB` | `200` | Upload limit. |
| `DATA_DIR` | `./data` | Where assessments and audio are stored. |

## Getting the best accuracy
- **Stereo recordings** (agent on one channel, client on the other) are transcribed per channel, so
  speakers are separated almost perfectly. Ask your dialler/phone system for dual-channel recordings.
- Use `WHISPER_MODEL=medium` if calls contain heavy accents or Zulu/Afrikaans code-switching and the
  server has the memory (about 5 GB). If you have a better transcript source, paste it in: it is used
  instead of the audio.
- Mono recordings work too; Claude works out who is the agent. If it gets a speaker wrong, click the
  tag in the transcript and press *Re-run assessment*.

## Changing the scorecards
Edit `scorecards.py` (wording, points, critical flags, pass marks), then restart. Add a new product by
adding an entry to `PRODUCTS`.

## Tests
`pip install pytest httpx && python -m pytest qa-app/tests` (speech-to-text and Claude are faked).
`python -m tests.mock_server` (from `qa-app/`) runs the UI with fakes so you can try it without keys.
