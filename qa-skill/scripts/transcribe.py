"""Speech-to-text with faster-whisper (runs locally on the server, no extra API key).

Stereo recordings where each side of the call is on its own channel are transcribed per channel,
which gives near-perfect speaker separation. Mono recordings return unlabelled turns and Claude
works out who is the agent.
"""
import os
import subprocess

import numpy as np

MODEL_NAME = os.environ.get("WHISPER_MODEL", "large-v3-turbo")  # tiny, base, small, medium, large-v3, large-v3-turbo ...
BEAM = int(os.environ.get("WHISPER_BEAM", "5"))  # 1 = fast, 5 = slower and more accurate
PROMPT = os.environ.get("STT_PROMPT", "South African call centre sales call between an agent and a client. Netstar, Cartrack, StarTag, DebiCheck, Innovate, Early Warning, Repair Assist.")
SR = 16000
_model = None


def _load():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        _model = WhisperModel(MODEL_NAME, device=os.environ.get("WHISPER_DEVICE", "cpu"),
                              compute_type=os.environ.get("WHISPER_COMPUTE", "int8"))
    return _model


def decode(path):
    """Return a float32 array shaped (channels, samples) at 16 kHz, max 2 channels."""
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries",
                            "stream=channels", "-of", "csv=p=0", path], capture_output=True, text=True)
    try:
        ch = 2 if int(probe.stdout.strip() or "1") >= 2 else 1
    except ValueError:
        ch = 1
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", str(ch), "-ar", str(SR),
                          "-f", "f32le", "-"], capture_output=True)
    if raw.returncode != 0 or not raw.stdout:
        raise ValueError("Could not read that audio file. Try mp3, wav, m4a or ogg.")
    a = np.frombuffer(raw.stdout, dtype=np.float32)
    return a.reshape(-1, ch).T.copy()


def is_true_stereo(a):
    """True when the two channels carry different speech (not a mono file duplicated)."""
    if a.shape[0] < 2:
        return False
    x, y = a[0], a[1]
    if x.std() < 1e-4 or y.std() < 1e-4:
        return False  # one channel silent: treat as mono
    return abs(float(np.corrcoef(x[::10], y[::10])[0, 1])) < 0.9


def _segments(samples, label, progress):
    model = _load()
    segs, info = model.transcribe(samples, vad_filter=True, beam_size=BEAM, condition_on_previous_text=False,
                                  initial_prompt=PROMPT or None)
    dur = max(len(samples) / SR, 1)
    out = []
    for s in segs:
        text = s.text.strip()
        if text:
            out.append({"spk": label, "text": text, "t": float(s.start), "e": float(s.end)})
        progress(min(0.99, s.end / dur))
    return out


def merge(turns, gap):
    """Join consecutive segments from the same speaker when they are within `gap` seconds. gap<=0 disables."""
    out = []
    for t in sorted(turns, key=lambda x: x["t"]):
        if gap > 0 and out and out[-1]["spk"] == t["spk"] and t["t"] - out[-1]["e"] < gap:
            out[-1]["text"] += " " + t["text"]
            out[-1]["e"] = t["e"]
        else:
            out.append(dict(t))
    return [{"spk": t["spk"], "text": t["text"], "t": t["t"]} for t in out]


def transcribe(path, progress=lambda f: None):
    """Dispatch on TRANSCRIBER: whisper (default, local), deepgram or assemblyai (cloud)."""
    engine = os.environ.get("TRANSCRIBER", "whisper").lower()
    if engine in ("deepgram", "assemblyai", "elevenlabs"):
        import providers
        turns = getattr(providers, engine)(path, progress)
        if not turns:
            raise ValueError("No speech was found in that recording.")
        return turns
    a = decode(path)
    if is_true_stereo(a):
        turns = []
        for idx, label in enumerate(("Speaker 1", "Speaker 2")):
            turns += _segments(a[idx], label, lambda f, i=idx: progress((i + f) / 2))
    else:
        mono = a.mean(axis=0) if a.shape[0] > 1 else a[0]
        turns = _segments(mono, "unknown", progress)
    turns = merge(turns, gap=1.5 if len({t["spk"] for t in turns}) > 1 else 0.0)
    if not turns:
        raise ValueError("No speech was found in that recording.")
    return turns


if __name__ == "__main__":
    # usage: python transcribe.py call.mp3 > transcript.json   (needs ffmpeg + faster-whisper; runs locally)
    import json
    import sys
    json.dump(transcribe(sys.argv[1], lambda f: print(f"{f:.0%}", file=sys.stderr)), sys.stdout)
