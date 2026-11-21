# Handoff: Innovate Assure (call QA app)

Read this first. It summarises a long session so a new session can continue without the history.

## The user and how to talk to them
- Works at Innovate (a South African sales brokerage). Non-technical, easily frustrated by long instructions.
- **Give ONE short plain-language step at a time.** No jargon, no option menus, no long lists. If they are stuck, ask for a photo of the screen.
- Never ask them to paste API keys in chat. Keys go into the `.env` file themselves.
- Do not suggest Claude Cowork any more: they are on their personal PC and said repeatedly they are not using Cowork there.
- Their repo: GitHub `sanaamahomed/innovate-scripts-live`, branch `ccr-84693f23-6p9m3f` (all work is pushed there).

## What they want
"Upload calls and it marks them and gives accurate insights", as in their existing work tool (built in Claude Cowork): upload MP3s -> queue -> Whisper on the laptop -> mask numbers + quick scan -> Claude analyses (Cowork scheduled task every 15 min, no API key) -> dashboard, call reports, agent scorecards, PDF, Excel. **Netstar only for now** (agents only dial Netstar). No call comparison for now.

## Key facts established
- **Claude cannot hear audio.** Anthropic API/apps take text, images, documents only. Audio must be transcribed first (faster-whisper large-v3-turbo, beam 5, call-centre prompt, ffmpeg). The user's work Cowork does exactly this on their laptop. Research report: `reports/Claude call QA audio options.md`.
- Netstar scorecard: 14 questions, 220 points (from their spreadsheet photo). INTRO is the only critical item (the sheet shows "Compliance Critical Result" on that row only). Pass >=85%, coaching 70-84%, else fail; any failed critical item = Critical fail. (Pass bands and the critical flag are assumptions, easy to change in `qa-app/scorecards.py`.)

## What is built (all in this repo)
- `qa-app/` = **Innovate Assure** (FastAPI + web UI, Innovate navy/yellow/teal theme, logo). Features: batch MP3 upload, Whisper transcription (or Deepgram/AssemblyAI/ElevenLabs via `TRANSCRIBER`), PII masking, quick-scan flags, Claude marking with quote verification (a Pass without a quote that appears in the transcript is downgraded to Review), reviewer overrides + notes, PDF per call (reportlab), Excel export, Dashboard, Agent scorecards, History. `ANALYSIS_MODE=api` (needs `ANTHROPIC_API_KEY`) or `cowork` (queue/results folders + a Cowork scheduled task, see `qa-app/cowork/README.md`). 23 automated tests pass (`cd qa-app && python -m pytest -q tests`); Whisper/Claude/Deepgram etc. are faked in tests.
- `qa-app/START_HERE.bat` = one-click Windows setup/start (installs Python/ffmpeg via winget, venv, pip, asks for password + Claude key, starts on port 8501). `qa-app/windows/` has older step scripts.
- `qa-skill/` + `qa-call-assessment-skill.zip` = a Claude skill version (scorecards, marking rules, PDF script).
- A published artifact (transcript-only, uses Claude via the page, no keys): https://claude.ai/artifact/G1TY4DXV6aVZAUfD79EoKv
- Old single-page Script Assistant (`index.html`) has an earlier browser-only QA tab; unrelated to Assure.

## Where it stands (not verified on the user's machine)
- User extracted `innovate-assure.zip` to `C:\Users\info\OneDrive\Desktop\innovate-assure` (Windows, personal PC, OneDrive Desktop). `START_HERE.bat` ran and installed ffmpeg successfully; they were told to rerun it. **Unknown whether the Assure page ever opened** at http://localhost:8501 or whether the password/key questions were answered.
- Not yet run for real anywhere: Whisper (model download ~1.6 GB), Claude marking with a real key, Cowork-mode scheduled task, Deepgram/AssemblyAI/ElevenLabs providers (only simulated).
- **Privacy problem to fix:** the folder is inside OneDrive, so real customer call recordings would sync to cloud. Move it to e.g. `C:\Assure` before real calls (set `DATA_DIR` or move the folder). Also remind them about company policy for customer calls on a personal PC.
- The user's PC (computer name "Junaid") is connected via Remote Control but offers no folders to cloud sessions (needs the Claude desktop app updated and the folder added under Settings > Claude Code > Remote Control). A local session in the Claude desktop app (Code tab, Local, folder = the extracted innovate-assure) is the way to run things on their PC.
- Needed for marking when not using Cowork: an Anthropic API key (console.anthropic.com) in `.env` (`ANALYSIS_MODE=api`). Without it, uploads transcribe but marking waits.

## Suggested next steps
1. Get Assure actually running on the user's PC (see the local-session prompt in the suggested task), then test with ONE short call; fix whatever breaks (the Windows scripts and real transcription are the likeliest failure points).
2. Move data out of OneDrive.
3. Tune marking against a real Netstar call + the user's expectations.
4. Optional later: Cartrack (`ENABLED_PRODUCTS=ns,ct`), campaigns/briefs and comparison pages (their tool has them; user said not now), hosting (`render.yaml`).
