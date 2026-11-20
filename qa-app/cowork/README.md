# No API key: let a Cowork scheduled task do Claude's analysis

This is the same design as your current call-analysis tool. The app does the upload, queue, Whisper
transcription, masking and reports. A **Claude Cowork scheduled task** does the analysis (step 5), so no
Anthropic API key is needed: it runs under your Claude login.

```
upload MP3s -> queue -> Whisper (this PC) -> mask + quick scan -> queue/<id>.json
                                                                      |  (Cowork task, every 15 min)
reports (dashboard, PDF, Excel) <- app picks up <- results/<id>.json <-+
```

## Set up
1. Run the app on the PC that stays on, with `ANALYSIS_MODE=cowork` (see `.env.example`) and a **real folder**
   as the data directory (`docker compose` does this: `./data`; without Docker set `DATA_DIR`).
2. In Claude Cowork, **connect that folder** (the one that contains `queue/` and `results/`).
3. In Cowork create a **scheduled task**, every 15 minutes, with the prompt below. The Claude desktop app must be
   open and the PC awake when it runs.
4. Optional: upload `qa-call-assessment-skill.zip` as a skill too, so the task and manual chats share the same rules.

## Scheduled task prompt (copy this)
```
In the connected QA data folder, look in queue/ for every *.json file whose matching file does NOT exist in
results/ (for queue/abc123.json the result is results/abc123.json; ignore *.done.json and *.bad.json).
Process at most 5 per run, oldest first. For each one:
1. Read the file. Its "prompt" field contains the full instructions, the scorecard, the call facts and the masked
   transcript. Follow the prompt exactly.
2. Work only from the transcript text. Never invent call content. Quotes must be word-for-word from the transcript
   (including masked tags such as [PHONE]).
3. Write ONLY the JSON object the prompt asks for (no markdown fences, no commentary) to results/<same id>.json.
Do not edit or delete anything else. If nothing is waiting, do nothing and say so in one line.
When finished, list the ids you processed.
```
The app notices the new file within seconds of the next page refresh and shows the assessment. If Claude writes
something unreadable the call shows an error with a **Re-run** button that puts it back in the queue.

## Notes
- Calls waiting for Claude show as "waiting for Claude" in History. A short call is typically done 15-25 minutes after upload.
- Only masked text is read by Claude. Audio never leaves the PC.
- You can run both modes: `ANALYSIS_MODE=api` (with a key) answers immediately; `cowork` waits for the scheduled task.
