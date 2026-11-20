"""Cloud speech-to-text providers (optional). Pick one with TRANSCRIBER=deepgram|assemblyai.

Both return turns in the same shape as the local engine: {spk, text, t}. Recordings with the agent and
client on separate channels are sent with multichannel on, so each channel becomes one speaker.
NOTE: written to each vendor's public REST docs but NOT yet run against the live APIs. Test on a few
real calls before relying on it. Audio is sent to the vendor: check POPIA cross-border requirements.
"""
import os
import time

import httpx

GLOSSARY = [w.strip() for w in os.environ.get(
    "STT_KEYTERMS", "Netstar,Cartrack,StarTag,DebiCheck,Innovate,Motordrive,Early Warning,Repair Assist,Cubix"
).split(",") if w.strip()]


def _label(n):
    return f"Speaker {int(n) + 1}"


def _merge(turns):
    """Join consecutive utterances from the same speaker."""
    out = []
    for t in turns:
        if out and out[-1]["spk"] == t["spk"]:
            out[-1]["text"] += " " + t["text"]
        else:
            out.append(dict(t))
    return out


def deepgram(path, progress=lambda f: None, client=None):
    key = os.environ["DEEPGRAM_API_KEY"]
    from transcribe import decode, is_true_stereo  # reuse the stereo check
    stereo = is_true_stereo(decode(path))
    params = [("model", os.environ.get("DEEPGRAM_MODEL", "nova-3")), ("smart_format", "true"), ("utterances", "true"),
              ("punctuate", "true"), ("language", os.environ.get("STT_LANGUAGE", "multi"))]
    params += [("multichannel", "true")] if stereo else [("diarize", "true")]
    params += [("keyterm", k) for k in GLOSSARY]
    c = client or httpx.Client(timeout=900)
    progress(0.1)
    with open(path, "rb") as f:
        r = c.post("https://api.deepgram.com/v1/listen", params=params, content=f.read(),
                   headers={"Authorization": f"Token {key}", "Content-Type": "application/octet-stream"})
    r.raise_for_status()
    utts = r.json().get("results", {}).get("utterances") or []
    progress(1.0)
    spk = (lambda u: u.get("channel", 0)) if stereo else (lambda u: u.get("speaker", 0))
    turns = [{"spk": _label(spk(u)), "text": u["transcript"].strip(), "t": float(u["start"])} for u in utts if u.get("transcript", "").strip()]
    return _merge(sorted(turns, key=lambda x: x["t"]))


def assemblyai(path, progress=lambda f: None, client=None, poll=3.0):
    key = os.environ["ASSEMBLYAI_API_KEY"]
    from transcribe import decode, is_true_stereo
    stereo = is_true_stereo(decode(path))
    h = {"authorization": key}
    c = client or httpx.Client(timeout=900)
    with open(path, "rb") as f:
        up = c.post("https://api.assemblyai.com/v2/upload", content=f.read(), headers=h)
    up.raise_for_status()
    body = {"audio_url": up.json()["upload_url"], "language_detection": True, "punctuate": True, "format_text": True,
            "word_boost": GLOSSARY, **({"multichannel": True} if stereo else {"speaker_labels": True})}
    r = c.post("https://api.assemblyai.com/v2/transcript", json=body, headers=h)
    r.raise_for_status()
    tid = r.json()["id"]
    progress(0.2)
    for _ in range(int(3600 / max(poll, 0.01))):
        s = c.get(f"https://api.assemblyai.com/v2/transcript/{tid}", headers=h).json()
        if s["status"] == "completed":
            break
        if s["status"] == "error":
            raise RuntimeError("AssemblyAI: " + str(s.get("error")))
        progress(0.5)
        time.sleep(poll)
    else:
        raise RuntimeError("AssemblyAI timed out")
    progress(1.0)
    utts = s.get("utterances") or []
    def who(u):
        if stereo:
            return _label(int(u.get("channel", 1)) - 1)
        sp = str(u.get("speaker", "A"))
        return _label(ord(sp[0].upper()) - 65 if sp[:1].isalpha() else int(sp))
    return _merge([{"spk": who(u), "text": u["text"].strip(), "t": u["start"] / 1000.0} for u in utts if u.get("text", "").strip()])


def elevenlabs(path, progress=lambda f: None, client=None):
    """ElevenLabs Scribe. ELEVENLABS_MODEL defaults to scribe_v1; set it to a newer Scribe model id if you have one."""
    key = os.environ["ELEVENLABS_API_KEY"]
    from transcribe import decode, is_true_stereo
    stereo = is_true_stereo(decode(path))
    data = {"model_id": os.environ.get("ELEVENLABS_MODEL", "scribe_v1"), "tag_audio_events": "false",
            "timestamps_granularity": "word", "diarize": "false" if stereo else "true"}
    if stereo:
        data["use_multi_channel"] = "true"
    if os.environ.get("STT_LANGUAGE", "").strip() and os.environ["STT_LANGUAGE"] != "multi":
        data["language_code"] = os.environ["STT_LANGUAGE"]
    c = client or httpx.Client(timeout=1800)
    progress(0.1)
    with open(path, "rb") as f:
        r = c.post("https://api.elevenlabs.io/v1/speech-to-text", headers={"xi-api-key": key}, data=data,
                   files={"file": (os.path.basename(path), f)})
    r.raise_for_status()
    j = r.json()
    progress(1.0)
    blocks = j.get("transcripts") or [j]  # multichannel returns one transcript per channel
    turns = []
    for ch, b in enumerate(blocks):
        cur = None
        for w in b.get("words", []):
            if w.get("type") == "audio_event":
                continue
            spk = w.get("speaker_id") or (f"speaker_{ch}" if stereo else "speaker_0")
            if w.get("type") == "spacing":
                if cur:
                    cur["text"] += w["text"]
                continue
            if cur is None or cur["key"] != spk or w["start"] - cur["end"] > 1.5:
                if cur:
                    turns.append(cur)
                cur = {"key": spk, "spk": spk, "text": "", "t": float(w["start"]), "end": float(w["end"])}
            cur["text"] += ("" if not cur["text"] or cur["text"].endswith(" ") else " ") + w["text"].strip() if w.get("text") else ""
            cur["end"] = float(w.get("end", cur["end"]))
        if cur:
            turns.append(cur)
    names = {}
    for t in sorted(turns, key=lambda x: x["t"]):
        names.setdefault(t["spk"], _label(len(names)))
    return _merge([{"spk": names[t["spk"]], "text": t["text"].strip(), "t": t["t"]} for t in sorted(turns, key=lambda x: x["t"]) if t["text"].strip()])
