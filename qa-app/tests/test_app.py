import os
import subprocess
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["ANTHROPIC_API_KEY"] = "test"

import engine  # noqa: E402
import parsing  # noqa: E402
import transcribe as stt  # noqa: E402
from scorecards import PRODUCTS  # noqa: E402


def fake_claude(prompt, client=None):
    ids = [i["id"] for i in PRODUCTS["ns"]["items"]]
    items = [{"id": i, "status": "fail" if i == "n_kyc" else "pass", "reason": "r " + i,
              "evidence": [{"turn": 1, "quote": "calling on behalf of Netstar"}]} for i in ids]
    return {"summary": "S", "outcome": "Sale", "client_sentiment": "ok", "agent_tone": "pro", "items": items,
            "strengths": ["a"], "improvements": ["b"], "coaching": ["c"], "risks": [], "key_moments": [{"turn": 2, "note": "n"}],
            "speakers": ["A", "C", "A", "C"], "agent_speaker": ""}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    import importlib
    import server
    importlib.reload(server)
    monkeypatch.setattr(server.engine, "call_claude", fake_claude)
    monkeypatch.setattr(server.stt, "transcribe", lambda p, prog=lambda f: None: [
        {"spk": "unknown", "text": "calling on behalf of Netstar", "t": 1.0}, {"spk": "unknown", "text": "yes", "t": 5.0},
        {"spk": "unknown", "text": "it is R259", "t": 8.0}, {"spk": "unknown", "text": "ok", "t": 12.0}])
    from fastapi.testclient import TestClient
    with TestClient(server.app) as c:
        yield c, server


def wait(c, rid):
    for _ in range(100):
        r = c.get(f"/api/assessments/{rid}").json()
        if r["status"] in ("done", "error"):
            return r
        time.sleep(0.05)
    raise AssertionError("timeout")


def test_audio_flow_scores_overrides_and_pdf(client):
    c, _ = client
    r = c.post("/api/assessments", data={"product": "ns", "agent": "Sam", "client": "Dlamini"},
               files={"audio": ("call.mp3", b"fake", "audio/mpeg")})
    assert r.status_code == 202
    rec = wait(c, r.json()["id"])
    assert rec["status"] == "done", rec.get("error")
    assert [t["spk"] for t in rec["turns"]] == ["agent", "client", "agent", "client"]  # speakers applied from Claude
    assert rec["score"]["points"] == 220 - 10 and rec["score"]["pct"] == 95 and rec["score"]["verdict"] == "Pass"
    assert rec["audio_url"]
    # reviewer override of the failed KYC to pass -> 100%
    rec = c.patch(f"/api/assessments/{rec['id']}", json={"overrides": {"n_kyc": "pass"}, "notes": {"n_kyc": "ok on call"}}).json()
    assert rec["score"]["pct"] == 100
    pdf = c.get(f"/api/assessments/{rec['id']}/pdf")
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF" and len(pdf.content) > 4000
    assert len(c.get("/api/assessments").json()) == 1
    assert c.delete(f"/api/assessments/{rec['id']}").status_code == 200


def test_transcript_only_and_critical_fail(client, monkeypatch):
    c, server = client
    def bad(prompt, client=None):
        d = fake_claude(prompt)
        for i in d["items"]:
            if i["id"] == "n_intro":
                i["status"] = "fail"
        return d
    monkeypatch.setattr(server.engine, "call_claude", bad)
    r = c.post("/api/assessments", data={"product": "ns", "transcript": "Agent: Hi\nClient: Hello\nAgent: Bye\nClient: Bye"})
    rec = wait(c, r.json()["id"])
    assert rec["score"]["verdict"] == "Critical fail" and rec["score"]["critical_fails"]


def test_validation(client):
    c, _ = client
    assert c.post("/api/assessments", data={"product": "ns"}).status_code == 400
    assert c.post("/api/assessments", data={"product": "zz", "transcript": "x"}).status_code == 400
    assert c.post("/api/assessments", data={"product": "ct", "transcript": "x"}).status_code == 400  # Cartrack is switched off
    cards = c.get("/api/scorecards").json()
    assert cards["ns"]["enabled"] and not cards["ct"]["enabled"]
    assert c.post("/api/assessments", data={"product": "ns"}, files={"audio": ("a.exe", b"x")}).status_code == 400


def test_error_is_recorded(client, monkeypatch):
    c, server = client
    monkeypatch.setattr(server.engine, "call_claude", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    rec = wait(c, c.post("/api/assessments", data={"transcript": "Agent: Hi\nClient: Yo"}).json()["id"])
    assert rec["status"] == "error" and "boom" in rec["error"]


def test_password(client, monkeypatch):
    c, _ = client
    monkeypatch.setenv("APP_PASSWORD", "pw")
    assert c.get("/api/scorecards").status_code == 401
    assert c.get("/api/scorecards", auth=("x", "pw")).status_code == 200


def test_parsing():
    t = parsing.parse("Agent: Hello there\nClient: Hi\ncontinued line\nAgent: Bye")
    assert [x["spk"] for x in t] == ["agent", "client", "agent"] and "continued" in t[1]["text"]
    t = parsing.parse("00:05 Sam: hi\n00:09 Mr D: hello")  # two unknown labels -> first is agent
    assert [x["spk"] for x in t] == ["agent", "client"] and t[1]["t"] == 9
    t = parsing.parse('[{"speaker":"Agent","text":"a","start":1.5},{"speaker":"Customer","text":"b"}]')
    assert [x["spk"] for x in t] == ["agent", "client"] and t[0]["t"] == 1.5
    t = parsing.parse("WEBVTT\n\n00:00:01.000 --> 00:00:03.000\nAgent: Hello\n")
    assert t[0]["t"] == 1 and t[0]["spk"] == "agent"


def test_engine_helpers():
    assert engine.extract_json('Sure! {"a": 1} done') == {"a": 1}
    turns = [{"spk": "Speaker 1", "text": "a", "t": 0}, {"spk": "Speaker 2", "text": "b", "t": 1}]
    assert engine.apply_speakers(turns, {"agent_speaker": "Speaker 2"}) == ""
    assert [t["spk"] for t in turns] == ["client", "agent"]
    assert "Speaker 1" in engine.build_prompt("ns", {}, [{"spk": "Speaker 1", "text": "a", "t": 0}, {"spk": "Speaker 2", "text": "b", "t": 1}])


def _tone(path, freqs):
    args = ["ffmpeg", "-v", "error", "-y"]
    for f in freqs:
        args += ["-f", "lavfi", "-i", f"sine=frequency={f}:duration=2"]
    if len(freqs) == 2:
        args += ["-filter_complex", "[0][1]amerge=inputs=2"]
    subprocess.run(args + [path], check=True)


def test_audio_decode_and_stereo_detection(tmp_path):
    mono, stereo, dup = (str(tmp_path / n) for n in ("m.wav", "s.wav", "d.wav"))
    _tone(mono, [440]); _tone(stereo, [440, 1330])
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", mono, "-ac", "2", dup], check=True)
    assert stt.decode(mono).shape[0] == 1 and not stt.is_true_stereo(stt.decode(mono))
    assert stt.is_true_stereo(stt.decode(stereo))
    assert not stt.is_true_stereo(stt.decode(dup))  # mono duplicated to 2 channels
    with pytest.raises(ValueError):
        open(tmp_path / "x.mp3", "wb").write(b"junk"); stt.decode(str(tmp_path / "x.mp3"))


def test_merge():
    segs = [{"spk": "a", "text": "x", "t": 0, "e": 1}, {"spk": "a", "text": "y", "t": 1.5, "e": 2}, {"spk": "b", "text": "z", "t": 2, "e": 3}]
    assert [t["text"] for t in stt.merge(segs, 1.5)] == ["x y", "z"]
    assert len(stt.merge(segs, 0)) == 3


def test_unverified_quote_downgrades_pass():
    turns = [{"spk": "agent", "text": "Hello, calling on behalf of Netstar.", "t": 0}]
    raw = {"items": [{"id": "n_intro", "status": "pass", "reason": "r", "evidence": [{"turn": 1, "quote": "I am from Netstar Cubix"}]},
                     {"id": "n_disc", "status": "pass", "reason": "r", "evidence": [{"turn": 5, "quote": "calling on behalf of netstar"}]}]}
    res = engine.normalise(raw, "ns", turns)
    assert res["items"]["n_intro"]["status"] == "review" and "no quote" in res["items"]["n_intro"]["reason"]
    d = res["items"]["n_disc"]  # wrong turn number but quote is real: turn corrected, stays pass
    assert d["status"] == "pass" and d["evidence"][0]["turn"] == 0 and d["evidence"][0]["verified"]


def _wav(tmp_path, stereo):
    p = str(tmp_path / "c.wav")
    _tone(p, [440, 1330] if stereo else [440])
    return p


def test_deepgram_provider(tmp_path, monkeypatch):
    import httpx, providers
    monkeypatch.setenv("DEEPGRAM_API_KEY", "k")
    seen = {}
    def handler(req):
        seen["q"] = dict(req.url.params.multi_items()) if False else str(req.url)
        return httpx.Response(200, json={"results": {"utterances": [
            {"channel": 0, "transcript": "Hello", "start": 0.5}, {"channel": 1, "transcript": "Hi", "start": 2.0}, {"channel": 1, "transcript": "there", "start": 3.0}]}})
    c = httpx.Client(transport=httpx.MockTransport(handler))
    turns = providers.deepgram(_wav(tmp_path, True), client=c)
    assert "multichannel=true" in seen["q"] and "keyterm=Netstar" in seen["q"]
    assert [(t["spk"], t["text"]) for t in turns] == [("Speaker 1", "Hello"), ("Speaker 2", "Hi there")]


def test_assemblyai_provider(tmp_path, monkeypatch):
    import httpx, providers
    monkeypatch.setenv("ASSEMBLYAI_API_KEY", "k")
    def handler(req):
        if req.url.path == "/v2/upload":
            return httpx.Response(200, json={"upload_url": "u"})
        if req.method == "POST":
            import json as j
            assert j.loads(req.content)["speaker_labels"] is True  # mono -> diarization
            return httpx.Response(200, json={"id": "t1"})
        return httpx.Response(200, json={"status": "completed", "utterances": [
            {"speaker": "A", "text": "Hello", "start": 500}, {"speaker": "B", "text": "Hi", "start": 2500}]})
    turns = providers.assemblyai(_wav(tmp_path, False), client=httpx.Client(transport=httpx.MockTransport(handler)), poll=0)
    assert [(t["spk"], t["t"]) for t in turns] == [("Speaker 1", 0.5), ("Speaker 2", 2.5)]


def test_wer_and_terms():
    from tools.compare_engines import wer, term_recall
    assert wer("the price is R 239 a month", "the price is r239 a month")[0] == 0
    rate, errs, n = wer("the price is 239 a month", "the prize is 239 month")
    assert errs == 2 and n == 6
    assert term_recall("it is r239 for netstar", "it is r239 for net star")[0] == 0.5


def test_elevenlabs_provider(tmp_path, monkeypatch):
    import httpx, providers
    monkeypatch.setenv("ELEVENLABS_API_KEY", "k")
    def handler(req):
        assert b"use_multi_channel" in req.content
        w = lambda t, s, e, ty="word": {"text": t, "start": s, "end": e, "type": ty}
        return httpx.Response(200, json={"transcripts": [
            {"words": [w("Hello", 0.5, 0.9), w(" ", 0.9, 1.0, "spacing"), w("there", 1.0, 1.4)]},
            {"words": [w("Hi", 2.0, 2.2)]}]})
    turns = providers.elevenlabs(_wav(tmp_path, True), client=httpx.Client(transport=httpx.MockTransport(handler)))
    assert [(t["spk"], t["text"]) for t in turns] == [("Speaker 1", "Hello there"), ("Speaker 2", "Hi")]


def test_healthz_is_public(client, monkeypatch):
    c, _ = client
    monkeypatch.setenv("APP_PASSWORD", "pw")
    assert c.get("/healthz").json() == {"ok": True}
    assert c.get("/api/health").status_code == 401


def test_pii_masking_keeps_prices():
    m = engine.mask_pii("Email me at sam.d@gmail.com, ID 900101 5009 087, cell 082 123 4567, account 1234 5678 90, it is R239 and R2,650.")
    assert "gmail" not in m and "5009" not in m and "123 4567" not in m and "1234 5678" not in m
    assert "[EMAIL]" in m and "[ID NUMBER]" in m and "[PHONE]" in m and "[NUMBER]" in m
    assert "R239" in m and "R2,650" in m


def test_prompt_is_masked_and_quotes_check_masked_text():
    turns = [{"spk": "agent", "text": "Is your cell 082 123 4567?", "t": 0}]
    assert "123 4567" not in engine.build_prompt("ns", {}, turns)
    raw = {"items": [{"id": "n_kyc", "status": "pass", "reason": "r", "evidence": [{"turn": 1, "quote": "Is your cell [PHONE]?"}]}]}
    assert engine.normalise(raw, "ns", turns)["items"]["n_kyc"]["status"] == "pass"


def test_cowork_mode_queue_and_ingest(client, monkeypatch):
    c, server = client
    monkeypatch.setenv("ANALYSIS_MODE", "cowork")
    monkeypatch.delenv("ANTHROPIC_API_KEY")
    monkeypatch.setattr(server.engine, "call_claude", lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not call the API")))
    r = c.post("/api/assessments", data={"product": "ns", "agent": "Sam"}, files={"audio": ("call.mp3", b"x", "audio/mpeg")})
    assert r.status_code == 202
    rid = r.json()["id"]
    for _ in range(100):
        rec = c.get(f"/api/assessments/{rid}").json()
        if rec["status"] == "awaiting_claude":
            break
        time.sleep(0.05)
    assert rec["status"] == "awaiting_claude" and rec["flags"]
    q = server.QUEUE / f"{rid}.json"
    job = __import__("json").loads(q.read_text())
    assert "TRANSCRIPT" in job["prompt"] and job["id"] == rid
    # Cowork (Claude) writes the result file
    (server.RESULTS / f"{rid}.json").write_text("```json\n" + __import__("json").dumps(fake_claude("")) + "\n```")
    rec = c.get(f"/api/assessments/{rid}").json()
    assert rec["status"] == "done" and rec["score"]["pct"] == 95
    assert not q.exists() and (server.RESULTS / f"{rid}.done.json").exists()


def test_cowork_bad_result_then_rerun(client, monkeypatch):
    c, server = client
    monkeypatch.setenv("ANALYSIS_MODE", "cowork")
    rid = c.post("/api/assessments", data={"product": "ns", "transcript": "Agent: Hi\nClient: Yo"}).json()["id"]
    for _ in range(100):
        if c.get(f"/api/assessments/{rid}").json()["status"] == "awaiting_claude":
            break
        time.sleep(0.05)
    (server.RESULTS / f"{rid}.json").write_text("not json at all")
    rec = c.get(f"/api/assessments/{rid}").json()
    assert rec["status"] == "error" and "Re-run" in rec["error"]
    assert c.post(f"/api/assessments/{rid}/reassess").status_code == 202


def test_batch_upload_and_excel(client):
    c, _ = client
    r = c.post("/api/assessments", data={"product": "ns", "agent": "Sam"},
               files=[("audio", ("a.mp3", b"x", "audio/mpeg")), ("audio", ("b.mp3", b"y", "audio/mpeg"))])
    ids = r.json()["ids"]
    assert len(ids) == 2
    for i in ids:
        assert wait(c, i)["status"] == "done"
    x = c.get("/api/export.xlsx")
    assert x.status_code == 200 and x.content[:2] == b"PK"
    import io, openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(x.content))
    assert wb["Calls"].max_row == 3 and wb["Items"].max_row == 1 + 2 * 14
    assert {wb["Calls"].cell(r, 4).value for r in (2, 3)} == {"a", "b"}  # refs default to the file names


def test_quick_scan():
    f = engine.quick_scan("ns", [{"spk": "agent", "text": "Howzit bro", "t": 0}])
    assert any("recording" in x for x in f) and any("slang" in x for x in f) and any("short" in x.lower() for x in f)


def test_env_file_loader(tmp_path, monkeypatch):
    import envload
    f = tmp_path / ".env"
    f.write_text('# c\nAPP_X=1\nQUOTED="two words"\nEMPTY=\nKEEP=fromfile\n', encoding="utf-8-sig")
    monkeypatch.setenv("KEEP", "fromenv")
    for k in ("APP_X", "QUOTED", "EMPTY"):
        monkeypatch.delenv(k, raising=False)
    envload.load_env(f)
    assert os.environ["APP_X"] == "1" and os.environ["QUOTED"] == "two words"
    assert "EMPTY" not in os.environ and os.environ["KEEP"] == "fromenv"
    for k in ("APP_X", "QUOTED"):
        monkeypatch.delenv(k)
