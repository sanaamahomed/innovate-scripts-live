"""Innovate Assure: call quality assurance app.

Upload a call recording (or paste a transcript) -> speech-to-text -> Claude marks it against the
scorecard and writes insights -> review/override -> download a branded PDF.

Run:  uvicorn server:app --host 0.0.0.0 --port 8000
Config (environment): ANTHROPIC_API_KEY (required), APP_PASSWORD (strongly recommended),
CLAUDE_MODEL, WHISPER_MODEL, DATA_DIR, MAX_UPLOAD_MB, RETAIN_AUDIO.
"""
import json
import os
import secrets
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles

import envload  # noqa: F401  (loads qa-app/.env before the other modules read settings)
import engine
import parsing
import pdf_report
import transcribe as stt
import scorecards as sc_cfg
from scorecards import PRODUCTS

DATA = Path(os.environ.get("DATA_DIR", Path(__file__).parent / "data"))
AUDIO = DATA / "audio"
RECS = DATA / "assessments"
for d in (AUDIO, RECS):
    d.mkdir(parents=True, exist_ok=True)
MAX_BYTES = int(os.environ.get("MAX_UPLOAD_MB", "200")) * 1024 * 1024
RETAIN_AUDIO = os.environ.get("RETAIN_AUDIO", "true").lower() != "false"
# api    : the app calls Claude itself (needs ANTHROPIC_API_KEY).
# cowork : no API key. The app writes masked calls to DATA_DIR/queue and a Claude Cowork scheduled task
#          (see cowork/README.md) writes the analysis to DATA_DIR/results; the app picks it up.
QUEUE, RESULTS = DATA / "queue", DATA / "results"
for d in (QUEUE, RESULTS):
    d.mkdir(parents=True, exist_ok=True)


def mode():
    return os.environ.get("ANALYSIS_MODE", "api").lower()
AUDIO_EXT = {".mp3", ".wav", ".m4a", ".ogg", ".oga", ".webm", ".aac", ".flac", ".mp4", ".amr", ".opus"}

basic = HTTPBasic(auto_error=False)
pool = ThreadPoolExecutor(max_workers=1)  # transcription is CPU heavy: one call at a time
lock = threading.Lock()


@asynccontextmanager
async def lifespan(_):
    recover()
    yield


app = FastAPI(title="Innovate Assure", lifespan=lifespan)


def auth(creds: HTTPBasicCredentials = Depends(basic)):
    pw = os.environ.get("APP_PASSWORD")
    if not pw:
        return
    if not creds or not secrets.compare_digest(creds.password.encode(), pw.encode()):
        raise HTTPException(401, "Password required", headers={"WWW-Authenticate": 'Basic realm="Innovate QA"'})


def path_of(rid):
    if not rid.isalnum():
        raise HTTPException(404)
    return RECS / f"{rid}.json"


def load(rid):
    p = path_of(rid)
    if not p.exists():
        raise HTTPException(404, "Assessment not found")
    return maybe_ingest(json.loads(p.read_text()))


def maybe_ingest(rec):
    """Cowork mode: when Claude has written results/<id>.json, turn it into the stored result."""
    if rec["status"] != "awaiting_claude":
        return rec
    rf = RESULTS / f"{rec['id']}.json"
    if not rf.exists():
        return rec
    try:
        raw = engine.extract_json(rf.read_text())
        rec["warning"] = engine.apply_speakers(rec["turns"], raw)
        rec["result"] = engine.normalise(raw, rec["product"], rec["turns"])
        rec.update(status="done", error=None)
        rf.rename(RESULTS / f"{rec['id']}.done.json")
        (QUEUE / f"{rec['id']}.json").unlink(missing_ok=True)
    except Exception as e:
        rec.update(status="error", error=f"Claude's result file could not be read ({type(e).__name__}: {e}). Click Re-run to queue it again.")
        rf.rename(RESULTS / f"{rec['id']}.bad.json")
    save(rec)
    return rec


def enqueue(rec):
    """Write the masked call + full instructions where the Cowork scheduled task will find them."""
    (QUEUE / f"{rec['id']}.json").write_text(json.dumps({
        "id": rec["id"], "product": rec["product"], "meta": rec["meta"],
        "instructions": f"Follow 'prompt' exactly. Write ONLY the JSON object it asks for to results/{rec['id']}.json (no markdown, no other text).",
        "prompt": engine.build_prompt(rec["product"], rec["meta"], rec["turns"])}, indent=1))
    rec.update(status="awaiting_claude", error=None)


def save(rec):
    with lock:
        tmp = path_of(rec["id"]).with_suffix(".tmp")
        tmp.write_text(json.dumps(rec))
        tmp.replace(path_of(rec["id"]))


def view(rec):
    out = dict(rec)
    out["audio_url"] = f"/api/assessments/{rec['id']}/audio" if rec.get("audio") and Path(rec["audio"]).exists() else None
    out.pop("audio", None)
    if rec.get("result"):
        out["score"] = engine.score(rec["product"], rec["result"]["items"], rec.get("overrides"))
    return out


def run(rid):
    """Background pipeline: transcribe (if audio), assess with Claude, store."""
    rec = load(rid)
    try:
        if not rec.get("turns"):
            rec.update(status="transcribing", progress=0.0)
            save(rec)

            def prog(f):
                rec["progress"] = round(f, 3)
                save(rec)
            rec["turns"] = stt.transcribe(rec["audio"], prog)
        rec["flags"] = engine.quick_scan(rec["product"], rec["turns"])
        if mode() == "cowork":
            enqueue(rec)
            return
        rec.update(status="assessing", progress=1.0)
        save(rec)
        raw = engine.call_claude(engine.build_prompt(rec["product"], rec["meta"], rec["turns"]))
        rec["warning"] = engine.apply_speakers(rec["turns"], raw)
        rec["result"] = engine.normalise(raw, rec["product"], rec["turns"])
        rec.update(status="done", error=None)
    except Exception as e:  # keep the record so the user sees what went wrong
        rec.update(status="error", error=f"{type(e).__name__}: {e}")
    finally:
        if rec.get("audio") and not RETAIN_AUDIO:
            Path(rec["audio"]).unlink(missing_ok=True)
            rec["audio"] = None
        save(rec)


@app.get("/healthz")
def healthz():
    """Unauthenticated liveness probe for hosting platforms. Reveals nothing."""
    return {"ok": True}


@app.get("/api/health")
def health(_=Depends(auth)):
    return {"ok": True, "mode": mode(), "claude_key": mode() == "cowork" or bool(os.environ.get("ANTHROPIC_API_KEY")), "model": engine.MODEL,
            "transcriber": os.environ.get("TRANSCRIBER", "whisper"), "whisper_model": stt.MODEL_NAME, "password_protected": bool(os.environ.get("APP_PASSWORD"))}


@app.get("/api/scorecards")
def scorecards(_=Depends(auth)):
    return {k: {"name": v["name"], "title": v["title"], "items": v["items"], "enabled": k in sc_cfg.ENABLED} for k, v in PRODUCTS.items()}


async def save_audio(rid, up):
    ext = Path(up.filename).suffix.lower()
    if ext not in AUDIO_EXT:
        raise HTTPException(400, "Unsupported audio type. Use mp3, wav, m4a, ogg, webm, aac or flac.")
    dest, size = AUDIO / f"{rid}{ext}", 0
    with open(dest, "wb") as f:
        while chunk := await up.read(1 << 20):
            size += len(chunk)
            if size > MAX_BYTES:
                f.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(413, f"File is larger than {MAX_BYTES >> 20} MB.")
            f.write(chunk)
    return str(dest)


@app.post("/api/assessments", status_code=202)
async def create(product: str = Form("ns"), agent: str = Form(""), client: str = Form(""), call_date: str = Form(""),
                 ref: str = Form(""), transcript: str = Form(""), audio: list[UploadFile] = File(default=[]), _=Depends(auth)):
    """One call per audio file (batch upload), or one call from a pasted transcript."""
    if product not in PRODUCTS or product not in sc_cfg.ENABLED:
        raise HTTPException(400, "That scorecard is not switched on")
    if mode() == "api" and not os.environ.get("ANTHROPIC_API_KEY"):
        raise HTTPException(503, "The server has no ANTHROPIC_API_KEY set (or set ANALYSIS_MODE=cowork).")
    files = [a for a in audio if a.filename]
    if files and transcript.strip() and len(files) > 1:
        raise HTTPException(400, "A pasted transcript can only go with one recording.")
    if not files and not transcript.strip():
        raise HTTPException(400, "Add a call recording or a transcript.")
    turns = []
    if transcript.strip():
        turns = parsing.parse(transcript)
        if not turns:
            raise HTTPException(400, "No text found in that transcript.")
    ids = []
    for up in (files or [None]):
        rid = uuid.uuid4().hex[:12]
        rec = {"id": rid, "created": time.time(), "status": "queued", "progress": 0.0, "product": product, "error": None,
               "meta": {"agent": agent.strip(), "client": client.strip(), "date": call_date or date.today().isoformat(),
                        "ref": ref.strip() or (Path(up.filename).stem[:40] if up is not None and len(files) > 1 else "")},
               "turns": [dict(t) for t in turns], "result": None, "overrides": {}, "notes": {}, "audio": None, "filename": ""}
        if up is not None:
            rec["audio"], rec["filename"] = await save_audio(rid, up), up.filename
        save(rec)
        pool.submit(run, rid)
        ids.append(rid)
    return {"id": ids[0], "ids": ids}


@app.get("/api/assessments")
def list_all(_=Depends(auth)):
    out = []
    for p in RECS.glob("*.json"):
        r = maybe_ingest(json.loads(p.read_text()))
        s = engine.score(r["product"], r["result"]["items"], r.get("overrides")) if r.get("result") else None
        out.append({"id": r["id"], "created": r["created"], "status": r["status"], "product": r["product"],
                    "meta": r["meta"], "score": s})
    return sorted(out, key=lambda x: -x["created"])


def stats_for(agent="", dfrom="", dto=""):
    """Dashboard numbers over finished assessments (reviewer overrides included)."""
    recs = []
    for p in RECS.glob("*.json"):
        r = maybe_ingest(json.loads(p.read_text()))
        if r["status"] != "done" or not r.get("result"):
            continue
        d = r["meta"].get("date", "")
        if (dfrom and d < dfrom) or (dto and d > dto) or (agent and (r["meta"].get("agent") or "(no agent)") != agent):
            continue
        recs.append(r)
    pcts, verd, per_q, by_day, by_agent = [], {}, {}, {}, {}
    for r in recs:
        sc = engine.score(r["product"], r["result"]["items"], r.get("overrides"))
        a = r["meta"].get("agent") or "(no agent)"
        ag = by_agent.setdefault(a, {"agent": a, "calls": 0, "pcts": [], "critical_fails": 0, "q": {}, "coaching": []})
        ag["calls"] += 1
        verd[sc["verdict"]] = verd.get(sc["verdict"], 0) + 1
        if sc["pct"] is not None:
            pcts.append(sc["pct"])
            ag["pcts"].append(sc["pct"])
            by_day.setdefault(r["meta"].get("date", ""), []).append(sc["pct"])
        if sc["verdict"] == "Critical fail":
            ag["critical_fails"] += 1
        for it in PRODUCTS[r["product"]]["items"]:
            st = (r.get("overrides") or {}).get(it["id"]) or r["result"]["items"][it["id"]]["status"]
            for bucket in (per_q.setdefault(it["id"], {"id": it["id"], "label": it["label"], "weight": it["weight"], "critical": it["critical"], "pass": 0, "fail": 0, "review": 0, "na": 0}),
                           ag["q"].setdefault(it["id"], {"id": it["id"], "label": it["label"], "pass": 0, "fail": 0, "review": 0, "na": 0})):
                bucket[st] += 1
        for line in (r["result"].get("insights", {}).get("coaching") or [])[:3]:
            ag["coaching"].append({"date": r["meta"].get("date", ""), "ref": r["meta"].get("ref", ""), "text": line})

    def rate(b):
        done = b["pass"] + b["fail"]
        return round(b["pass"] / done * 100) if done else None
    questions = sorted(({**b, "pass_rate": rate(b)} for b in per_q.values()), key=lambda b: (-b["fail"], b["pass_rate"] if b["pass_rate"] is not None else 101))
    agents = []
    for ag in by_agent.values():
        weak = sorted((b for b in ag["q"].values() if b["fail"]), key=lambda b: -b["fail"])[:3]
        agents.append({"agent": ag["agent"], "calls": ag["calls"], "avg": round(sum(ag["pcts"]) / len(ag["pcts"])) if ag["pcts"] else None,
                       "lowest": min(ag["pcts"]) if ag["pcts"] else None, "highest": max(ag["pcts"]) if ag["pcts"] else None,
                       "critical_fails": ag["critical_fails"], "weakest": [{"label": b["label"], "fail": b["fail"]} for b in weak],
                       "questions": sorted(({**b, "pass_rate": rate(b)} for b in ag["q"].values()), key=lambda b: (-b["fail"], b["id"])),
                       "coaching": sorted(ag["coaching"], key=lambda c: c["date"], reverse=True)[:8]})
    agents.sort(key=lambda a: (a["avg"] is None, -(a["avg"] or 0)))
    return {"calls": len(recs), "avg": round(sum(pcts) / len(pcts)) if pcts else None,
            "pass_rate": round(verd.get("Pass", 0) / len(recs) * 100) if recs else None,
            "critical_fails": verd.get("Critical fail", 0), "verdicts": verd, "questions": questions, "agents": agents,
            "trend": [{"date": d, "avg": round(sum(v) / len(v)), "calls": len(v)} for d, v in sorted(by_day.items()) if d]}


@app.get("/api/stats")
def stats(agent: str = "", date_from: str = "", date_to: str = "", _=Depends(auth)):
    return stats_for(agent, date_from, date_to)


@app.get("/api/export.xlsx")
def export_xlsx(_=Depends(auth)):
    from io import BytesIO

    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    wb = Workbook()
    ws, wi = wb.active, wb.create_sheet("Items")
    ws.title = "Calls"
    ws.append(["Date", "Agent", "Client", "Reference", "Scorecard", "Status", "Score %", "Points", "Out of", "Verdict", "Provisional", "Critical fails", "Quick-scan flags", "Summary"])
    wi.append(["Date", "Agent", "Reference", "Scorecard", "Group", "Item", "Points", "Critical", "Result", "Reason", "Reviewer note"])
    for p in sorted(RECS.glob("*.json"), key=lambda x: x.stat().st_mtime):
        r = maybe_ingest(json.loads(p.read_text()))
        m, sc = r["meta"], (engine.score(r["product"], r["result"]["items"], r.get("overrides")) if r.get("result") else None)
        ws.append([m["date"], m["agent"], m["client"], m["ref"], PRODUCTS[r["product"]]["name"], r["status"],
                   sc and sc["pct"], sc and sc["points"], sc and sc["of"], sc and sc["verdict"], sc and ("yes" if sc["provisional"] else "no"),
                   sc and "; ".join(sc["critical_fails"]), "; ".join(r.get("flags", [])), (r.get("result") or {}).get("summary", "")])
        if r.get("result"):
            for it in PRODUCTS[r["product"]]["items"]:
                x = r["result"]["items"][it["id"]]
                wi.append([m["date"], m["agent"], m["ref"], PRODUCTS[r["product"]]["name"], it["group"], it["label"], it["weight"],
                           "yes" if it["critical"] else "", r["overrides"].get(it["id"]) or x["status"], x["reason"], r["notes"].get(it["id"], "")])
    for sheet in (ws, wi):
        for c in sheet[1]:
            c.font, c.fill = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="18305E")
        sheet.freeze_panes = "A2"
        for col in sheet.columns:
            sheet.column_dimensions[col[0].column_letter].width = min(60, max(12, max(len(str(c.value or "")) for c in col[:50]) + 2))
    buf = BytesIO()
    wb.save(buf)
    return Response(buf.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": 'attachment; filename="qa-assessments.xlsx"'})


@app.get("/api/assessments/{rid}")
def get_one(rid: str, _=Depends(auth)):
    return view(load(rid))


@app.patch("/api/assessments/{rid}")
async def patch(rid: str, request: Request, _=Depends(auth)):
    body = await request.json()
    rec = load(rid)
    valid = {i["id"] for i in PRODUCTS[rec["product"]]["items"]}
    if "overrides" in body:  # {item_id: "pass"|"fail"|"na"|null}
        for k, v in body["overrides"].items():
            if k in valid:
                if v in ("pass", "fail", "na"):
                    rec["overrides"][k] = v
                else:
                    rec["overrides"].pop(k, None)
    if "notes" in body:
        for k, v in body["notes"].items():
            if k in valid:
                rec["notes"][k] = str(v)[:2000]
    if "meta" in body:
        for k in ("agent", "client", "date", "ref"):
            if k in body["meta"]:
                rec["meta"][k] = str(body["meta"][k])[:200]
    if "speakers" in body:  # {turn_index: "agent"|"client"|"unknown"}
        for k, v in body["speakers"].items():
            if v in ("agent", "client", "unknown") and k.isdigit() and int(k) < len(rec["turns"]):
                rec["turns"][int(k)]["spk"] = v
    save(rec)
    return view(rec)


@app.post("/api/assessments/{rid}/reassess", status_code=202)
def reassess(rid: str, _=Depends(auth)):
    rec = load(rid)
    if rec["status"] in ("queued", "transcribing", "assessing"):
        raise HTTPException(409, "Already running")
    rec.update(status="queued", error=None)
    for f in (RESULTS / f"{rid}.json", RESULTS / f"{rid}.bad.json"):
        f.unlink(missing_ok=True)
    save(rec)
    pool.submit(run, rid)
    return {"id": rid}


@app.delete("/api/assessments/{rid}")
def delete(rid: str, _=Depends(auth)):
    rec = load(rid)
    if rec.get("audio"):
        Path(rec["audio"]).unlink(missing_ok=True)
    path_of(rid).unlink(missing_ok=True)
    return {"deleted": rid}


@app.get("/api/assessments/{rid}/audio")
def get_audio(rid: str, _=Depends(auth)):
    rec = load(rid)
    if not rec.get("audio") or not Path(rec["audio"]).exists():
        raise HTTPException(404, "No audio stored")
    return FileResponse(rec["audio"], filename=rec.get("filename") or None)


@app.get("/api/assessments/{rid}/pdf")
def get_pdf(rid: str, _=Depends(auth)):
    rec = load(rid)
    if not rec.get("result"):
        raise HTTPException(409, "Not assessed yet")
    sc = engine.score(rec["product"], rec["result"]["items"], rec.get("overrides"))
    pdf = pdf_report.build(rec, sc)
    name = f"QA-{rec['meta'].get('agent') or 'agent'}-{rec['meta'].get('date')}.pdf".replace(" ", "_").replace("/", "-")
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{name}"'})


def recover():
    """Jobs interrupted by a restart are marked as errors so they can be re-run."""
    for p in RECS.glob("*.json"):
        r = json.loads(p.read_text())
        if r["status"] in ("queued", "transcribing", "assessing"):
            r.update(status="error", error="Interrupted by a server restart. Click Re-run.")
            save(r)




app.mount("/", StaticFiles(directory=Path(__file__).parent / "static", html=True), name="static")
