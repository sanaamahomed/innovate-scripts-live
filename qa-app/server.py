"""Innovate QA Assessment app.

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

import engine
import parsing
import pdf_report
import transcribe as stt
from scorecards import PRODUCTS

DATA = Path(os.environ.get("DATA_DIR", Path(__file__).parent / "data"))
AUDIO = DATA / "audio"
RECS = DATA / "assessments"
for d in (AUDIO, RECS):
    d.mkdir(parents=True, exist_ok=True)
MAX_BYTES = int(os.environ.get("MAX_UPLOAD_MB", "200")) * 1024 * 1024
RETAIN_AUDIO = os.environ.get("RETAIN_AUDIO", "true").lower() != "false"
AUDIO_EXT = {".mp3", ".wav", ".m4a", ".ogg", ".oga", ".webm", ".aac", ".flac", ".mp4", ".amr", ".opus"}

basic = HTTPBasic(auto_error=False)
pool = ThreadPoolExecutor(max_workers=1)  # transcription is CPU heavy: one call at a time
lock = threading.Lock()


@asynccontextmanager
async def lifespan(_):
    recover()
    yield


app = FastAPI(title="Innovate QA Assessment", lifespan=lifespan)


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
    return json.loads(p.read_text())


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


@app.get("/api/health")
def health(_=Depends(auth)):
    return {"ok": True, "claude_key": bool(os.environ.get("ANTHROPIC_API_KEY")), "model": engine.MODEL,
            "whisper_model": stt.MODEL_NAME, "password_protected": bool(os.environ.get("APP_PASSWORD"))}


@app.get("/api/scorecards")
def scorecards(_=Depends(auth)):
    return {k: {"name": v["name"], "title": v["title"], "items": v["items"]} for k, v in PRODUCTS.items()}


@app.post("/api/assessments", status_code=202)
async def create(product: str = Form("ct"), agent: str = Form(""), client: str = Form(""), call_date: str = Form(""),
                 ref: str = Form(""), transcript: str = Form(""), audio: UploadFile | None = File(None), _=Depends(auth)):
    if product not in PRODUCTS:
        raise HTTPException(400, "Unknown scorecard")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise HTTPException(503, "The server has no ANTHROPIC_API_KEY set.")
    rid = uuid.uuid4().hex[:12]
    rec = {"id": rid, "created": time.time(), "status": "queued", "progress": 0.0, "product": product, "error": None,
           "meta": {"agent": agent.strip(), "client": client.strip(), "date": call_date or date.today().isoformat(), "ref": ref.strip()},
           "turns": [], "result": None, "overrides": {}, "notes": {}, "audio": None, "filename": ""}
    if audio is not None and audio.filename:
        ext = Path(audio.filename).suffix.lower()
        if ext not in AUDIO_EXT:
            raise HTTPException(400, "Unsupported audio type. Use mp3, wav, m4a, ogg, webm, aac or flac.")
        dest, size = AUDIO / f"{rid}{ext}", 0
        with open(dest, "wb") as f:
            while chunk := await audio.read(1 << 20):
                size += len(chunk)
                if size > MAX_BYTES:
                    f.close()
                    dest.unlink(missing_ok=True)
                    raise HTTPException(413, f"File is larger than {MAX_BYTES >> 20} MB.")
                f.write(chunk)
        rec["audio"], rec["filename"] = str(dest), audio.filename
    if transcript.strip():
        rec["turns"] = parsing.parse(transcript)
        if not rec["turns"]:
            raise HTTPException(400, "No text found in that transcript.")
    if not rec["turns"] and not rec["audio"]:
        raise HTTPException(400, "Add a call recording or a transcript.")
    save(rec)
    pool.submit(run, rid)
    return {"id": rid}


@app.get("/api/assessments")
def list_all(_=Depends(auth)):
    out = []
    for p in RECS.glob("*.json"):
        r = json.loads(p.read_text())
        s = engine.score(r["product"], r["result"]["items"], r.get("overrides")) if r.get("result") else None
        out.append({"id": r["id"], "created": r["created"], "status": r["status"], "product": r["product"],
                    "meta": r["meta"], "score": s})
    return sorted(out, key=lambda x: -x["created"])


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
