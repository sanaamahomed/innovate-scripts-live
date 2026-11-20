"""Find the most accurate speech-to-text engine for YOUR calls.

usage: python tools/compare_engines.py call.mp3 [corrected_transcript.txt] [--engines whisper,deepgram,assemblyai,elevenlabs]

Runs every engine that is configured (API key set) on the recording and writes each transcript to
compare_out/<engine>.txt. If you give a transcript you have corrected by hand, it also reports each
engine's word error rate (lower is better) overall and on key terms/numbers (prices, product names).
Do this on 20-30 representative calls (stereo if possible) and pick the winner on the total.
"""
import os
import re
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

KEY_ENV = {"deepgram": "DEEPGRAM_API_KEY", "assemblyai": "ASSEMBLYAI_API_KEY", "elevenlabs": "ELEVENLABS_API_KEY", "whisper": None}
KEY_TERMS = ["netstar", "cartrack", "startag", "debicheck", "innovate", "motordrive", "r239", "r259", "r149", "r19", "36 months"]


def words(text):
    text = text.lower().replace("’", "'")
    text = re.sub(r"\br\s*(\d)", r"r\1", text)       # "R 239" -> "r239"
    text = re.sub(r"(?<=\d),(?=\d)", "", text)        # "2,650" -> "2650"
    return re.sub(r"[^a-z0-9']+", " ", text).split()


def wer(ref, hyp):
    """Word error rate via edit distance. Returns (rate, errors, ref_len)."""
    r, h = words(ref), words(hyp)
    if not r:
        return 0.0, 0, 0
    prev = list(range(len(h) + 1))
    for i, rw in enumerate(r, 1):
        cur = [i]
        for j, hw in enumerate(h, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (rw != hw)))
        prev = cur
    return prev[-1] / len(r), prev[-1], len(r)


def term_recall(ref, hyp):
    """Share of the key terms in the reference that the engine also got right."""
    rt, ht = " ".join(words(ref)), " ".join(words(hyp))
    want = [t for t in KEY_TERMS if t in rt]
    return (sum(t in ht for t in want) / len(want), len(want)) if want else (None, 0)


def to_text(turns):
    return "\n".join(f"{t['spk']}: {t['text']}" for t in turns)


def run(path, ref_path=None, engines=None):
    import transcribe
    ref = open(ref_path).read() if ref_path else None
    os.makedirs("compare_out", exist_ok=True)
    rows = []
    for e in engines or list(KEY_ENV):
        if KEY_ENV[e] and not os.environ.get(KEY_ENV[e]):
            print(f"- {e}: skipped ({KEY_ENV[e]} not set)")
            continue
        os.environ["TRANSCRIBER"] = e
        t0 = time.time()
        try:
            turns = transcribe.transcribe(path)
        except Exception as ex:
            print(f"- {e}: FAILED {type(ex).__name__}: {ex}")
            continue
        txt = to_text(turns)
        open(f"compare_out/{e}.txt", "w").write(txt)
        row = {"engine": e, "secs": round(time.time() - t0), "turns": len(turns)}
        if ref:
            # strip "Agent:" style labels from the reference so only spoken words are compared
            ref_words = re.sub(r"(?m)^\s*[A-Za-z][A-Za-z0-9 ]{0,20}:\s*", "", ref)
            hyp_words = re.sub(r"(?m)^Speaker \d+:\s*|^unknown:\s*", "", txt)
            rate, errs, n = wer(ref_words, hyp_words)
            rec, nt = term_recall(ref_words, hyp_words)
            row.update(wer=round(rate * 100, 1), key_terms=None if rec is None else round(rec * 100))
        rows.append(row)
    print("\nengine        secs  turns  WER%   key-terms-right%")
    for r in sorted(rows, key=lambda r: r.get("wer", 999)):
        print(f"{r['engine']:<13} {r['secs']:>4}  {r['turns']:>5}  {r.get('wer', '-'):>5}  {r.get('key_terms', '-')}")
    print("\nTranscripts saved in compare_out/. Lower WER is better; key terms should be near 100%.")
    return rows


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    eng = next((x.split("=", 1)[1].split(",") for x in sys.argv if x.startswith("--engines=")), None)
    if not a:
        sys.exit(__doc__)
    run(a[0], a[1] if len(a) > 1 else None, eng)
