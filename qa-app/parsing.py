"""Parse pasted/uploaded transcripts (.txt, .srt, .vtt, .json) into turns: {spk, text, t}."""
import json
import re

AGENT = re.compile(r"^(agent|rep|representative|consultant|advisor|adviser|sales|operator|innovate|me|outbound|user)", re.I)
CLIENT = re.compile(r"^(client|customer|caller|cust|lead|prospect|contact|inbound|participant)", re.I)
LABEL = re.compile(r"^\s*(?:[\[(]?(\d{1,2}:\d{2}(?::\d{2})?(?:[.,]\d+)?)[\])]?\s*[-–]?\s*)?([A-Za-z][A-Za-z0-9 _.'-]{0,28}?)\s*[:\-–]\s+(\S.*)$")
NOT_LABEL = re.compile(r"^(note|time|date|call|duration|ref|reference)$", re.I)


def secs(s):
    try:
        p = [float(x) for x in s.replace(",", ".").split(":")]
    except ValueError:
        return None
    return p[0] * 3600 + p[1] * 60 + p[2] if len(p) == 3 else p[0] * 60 + p[1]


def role(label):
    l = (label or "").strip()
    if not l:
        return ""
    if AGENT.match(l):
        return "agent"
    if CLIENT.match(l):
        return "client"
    return "?" + l.lower()


def finish(raw):
    unk = list(dict.fromkeys(t["spk"] for t in raw if t["spk"].startswith("?")))
    known = any(t["spk"] in ("agent", "client") for t in raw)
    for t in raw:
        if t["spk"].startswith("?"):
            t["spk"] = ("agent" if t["spk"] == unk[0] else "client") if (not known and len(unk) == 2) else "unknown"
        elif not t["spk"]:
            t["spk"] = "unknown"
    return raw


def parse(text):
    text = text.lstrip("﻿").strip()
    raw = []
    if text[:1] in "[{":
        try:
            j = json.loads(text)
            if isinstance(j, dict):
                for k in ("dialogue", "transcript", "segments", "utterances", "data"):
                    if isinstance(j.get(k), list):
                        j = j[k]
                        break
            if isinstance(j, list):
                for o in j:
                    if isinstance(o, str):
                        raw.append({"spk": "", "text": o, "t": None})
                        continue
                    tx = o.get("content") or o.get("text") or o.get("transcript") or o.get("message")
                    if not tx:
                        continue
                    st = o.get("start", o.get("startTime", o.get("start_time", o.get("timestamp"))))
                    if isinstance(st, str):
                        st = secs(st) if ":" in st else None
                    raw.append({"spk": role(o.get("identifier") or o.get("speaker") or o.get("role") or ""),
                                "text": str(tx).strip(), "t": st if isinstance(st, (int, float)) else None})
                if raw:
                    return finish(raw)
        except json.JSONDecodeError:
            pass
    cur, cue_t = None, None
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln:
            cue_t = None
            continue
        if re.match(r"^(WEBVTT|NOTE\b|\d+$)", ln, re.I):
            continue
        if "-->" in ln:
            m = re.search(r"(\d{1,2}:\d{2}(?::\d{2})?[.,]?\d*)\s*-->", ln)
            cue_t = secs(m.group(1)) if m else None
            cur = None
            continue
        m = LABEL.match(ln)
        if m and len(m.group(2).split()) <= 3 and not NOT_LABEL.match(m.group(2).strip()):
            cur = {"spk": role(m.group(2)), "text": m.group(3).strip(), "t": secs(m.group(1)) if m.group(1) else cue_t}
            raw.append(cur)
        elif cur and cue_t is None:
            cur["text"] += " " + ln
        else:
            cur = {"spk": "", "text": ln, "t": cue_t}
            raw.append(cur)
    return finish(raw)
