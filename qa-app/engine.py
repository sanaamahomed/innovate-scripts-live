"""Claude-based assessment: build the prompt, call Claude, parse and score the answer."""
import json
import os
import re

from scorecards import COACH_MARK, PASS_MARK, PRODUCTS

MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5-5")
STATUSES = {"pass", "fail", "review", "na"}


MASK_PII = os.environ.get("MASK_PII", "true").lower() != "false"
_PII = [
    (re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"), "[EMAIL]"),
    (re.compile(r"\b\d{6}\s?\d{4}\s?\d{3}\b"), "[ID NUMBER]"),                       # SA ID: 13 digits
    (re.compile(r"(?<!\d)(?:\+27|0)[\s-]?\d{2}[\s-]?\d{3}[\s-]?\d{4}(?!\d)"), "[PHONE]"),  # SA phone numbers
    (re.compile(r"\b\d(?:[\s-]?\d){7,}\b"), "[NUMBER]"),                              # account / policy numbers (8+ digits)
]


def mask_pii(text):
    """Hide emails, ID, phone and account numbers before the text goes to Claude. Prices (R239, R2,650) are untouched.
    Digits spoken as words ("zero eight two...") are not caught."""
    if not MASK_PII:
        return text
    for rx, tag in _PII:
        text = rx.sub(tag, text)
    return text


def masked_turns(turns):
    return [dict(t, text=mask_pii(t["text"])) for t in turns]


QUICK_SLANG = re.compile(r"\b(lekker|bru|boet|my china|ja nee|howzit|yoh|eish|sharp sharp|dude|bro|gonna|wanna|gotta|kinda|nope|yup|no worries|guys)\b", re.I)


def quick_scan(product, turns):
    """Cheap keyword flags that need no AI (step 'mask and quick scan'). Shown to the reviewer; they never change the score."""
    agent = " ".join(t["text"] for t in turns if t["spk"] != "client") or " ".join(t["text"] for t in turns)
    allt = " ".join(t["text"] for t in turns)
    flags = []
    if not re.search(r"(call is|calls are|call will be|being) recorded|recorded for", agent, re.I):
        flags.append("No recording statement heard")
    if not re.search(r"\br\s?\d{2,4}\b", allt, re.I):
        flags.append("No rand amount mentioned (price/premium)")
    brand = r"netstar" if product == "ns" else r"cartrack"
    if not re.search(brand, agent, re.I):
        flags.append(f"Brand name ({PRODUCTS[product]['name']}) not heard from the agent")
    s = sorted({m.group(0).lower() for m in QUICK_SLANG.finditer(agent)})
    if s:
        flags.append("Possible slang: " + ", ".join(s))
    if len(turns) < 6:
        flags.append("Very short call or transcript")
    return flags


def clock(s):
    if s is None:
        return ""
    s = max(0, int(round(s)))
    return f"{s // 60}:{s % 60:02d}"


def _label(t):
    return {"agent": "Agent", "client": "Client", "unknown": "Speaker?"}.get(t["spk"], t["spk"])


def build_prompt(product, meta, turns):
    p = PRODUCTS[product]
    items = "\n".join(
        f"- {i['id']} [{i['group']}{', CRITICAL' if i['critical'] else ''}]: {i['label']}" for i in p["items"]
    )
    tr = "\n".join(
        f"[{n + 1}]{' (' + clock(t['t']) + ')' if t.get('t') is not None else ''} {_label(t)}: {mask_pii(t['text'])}"
        for n, t in enumerate(turns)
    )
    named = sorted({t["spk"] for t in turns if t["spk"] not in ("agent", "client", "unknown")})
    if any(t["spk"] in ("agent", "client") for t in turns):
        spk_rule = "Speakers are already labelled; return speakers as an empty array and agent_speaker as an empty string."
    elif len(named) == 2:
        spk_rule = (
            f"The transcript has two separate audio channels labelled {named[0]!r} and {named[1]!r}. "
            "Work out which one is the Agent (the Innovate sales rep) and return it as agent_speaker. "
            "Return speakers as an empty array."
        )
    else:
        spk_rule = (
            "The transcript has no speaker labels. Infer who is Agent and who is Client and return speakers: "
            f'an array with one entry per turn, "A" or "C" (exactly {len(turns)} entries). agent_speaker is an empty string.'
        )
    meta_line = " ".join(
        x for x in (f"Agent name: {meta.get('agent')}." if meta.get("agent") else "",
                    f"Client name: {meta.get('client')}." if meta.get("client") else "") if x
    )
    return f"""You are a strict, fair call-centre QA analyst. Assess this sales call transcript against the scorecard.

SCORECARD: {p['title']}
BACKGROUND FACTS
{p['facts']}
{meta_line}

SCORECARD ITEMS (use these ids exactly)
{items}

RULES
- status is "pass", "fail", "review" or "na". Pass only with clear evidence in the transcript. A wrong price, term or fee is a fail. Missing is a fail, except items that were clearly not applicable, which are "na".
- You only have text, not audio. For tone, pace, language switching, interruptions or anything the words cannot show, use "review" and say why.
- The transcript was produced by speech-to-text and may contain mishearings. Do not fail an item on a single garbled word if the meaning is clear; note it in the reason.
- evidence: up to 2 short VERBATIM quotes with their turn number. Give a one-sentence reason for every item.
- {spk_rule}
- Insights must be specific to THIS call, referencing what was actually said. No generic advice.

Return ONLY one JSON object, no markdown, in this shape:
{{"summary":"3-4 sentence summary of the call","outcome":"e.g. Sale completed / Declined / Incomplete","client_sentiment":"short phrase","agent_tone":"short phrase",
"items":[{{"id":"{p['items'][0]['id']}","status":"pass","reason":"...","evidence":[{{"turn":1,"quote":"..."}}]}}],
"strengths":["..."],"improvements":["..."],"coaching":["concrete action the agent can take next call"],"risks":["compliance or customer risks, empty if none"],
"key_moments":[{{"turn":12,"note":"..."}}],"speakers":[],"agent_speaker":""}}

TRANSCRIPT
{tr}"""


def extract_json(text):
    a, b = text.find("{"), text.rfind("}")
    if a < 0 or b < a:
        raise ValueError("Claude did not return JSON")
    return json.loads(text[a:b + 1])


def call_claude(prompt, client=None):
    if client is None:
        import anthropic
        client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
    msg = client.messages.create(model=MODEL, max_tokens=12000, messages=[{"role": "user", "content": prompt}])
    return extract_json("".join(b.text for b in msg.content if getattr(b, "type", "") == "text"))


def apply_speakers(turns, raw):
    """Relabel turns from Claude's speaker answer. Returns a warning string or ''."""
    if any(t["spk"] in ("agent", "client") for t in turns):
        return ""
    ag = (raw.get("agent_speaker") or "").strip()
    if ag:
        for t in turns:
            t["spk"] = "agent" if t["spk"] == ag else "client"
        return ""
    sp = raw.get("speakers") or []
    if len(sp) == len(turns):
        for t, s in zip(turns, sp):
            t["spk"] = "client" if str(s).upper().startswith("C") else "agent"
        return ""
    if sp:
        return "Claude's speaker labels did not line up with the transcript, so they were not applied."
    return ""


def _norm(t):
    return " ".join("".join(c.lower() if c.isalnum() else " " for c in t).split())


def quote_in_transcript(quote, turns):
    """Return the 0-based turn holding the quote (whitespace/punctuation/case-insensitive), or -1."""
    q = _norm(quote)
    if len(q) < 4:
        return -1
    for i, t in enumerate(turns):
        if q in _norm(t["text"]):
            return i
    # allow a quote that spans two adjacent turns
    for i in range(len(turns) - 1):
        if q in _norm(turns[i]["text"] + " " + turns[i + 1]["text"]):
            return i
    return -1


def normalise(raw, product, turns):
    """Turn Claude's JSON into the stored result: per-item status/reason/evidence plus insights."""
    items = {}
    turns = masked_turns(turns)  # quotes are checked against what Claude actually saw
    by_id = {x.get("id"): x for x in raw.get("items", []) if isinstance(x, dict)}
    for it in PRODUCTS[product]["items"]:
        x = by_id.get(it["id"])
        if not x:
            items[it["id"]] = {"status": "review", "reason": "Claude did not return a result for this item.", "evidence": []}
            continue
        st = x.get("status") if x.get("status") in STATUSES else "review"
        ev = []
        for e in x.get("evidence") or []:
            try:
                n = int(e.get("turn", 0)) - 1
            except (TypeError, ValueError):
                n = -1
            q = str(e.get("quote", "")).strip()
            if q:
                found = quote_in_transcript(q, turns)
                ev.append({"turn": found if found >= 0 else (n if 0 <= n < len(turns) else -1), "quote": q, "verified": found >= 0})
        reason = str(x.get("reason", ""))
        # Hallucination control: a PASS must be backed by at least one quote that really is in the transcript.
        if st == "pass" and not any(e["verified"] for e in ev):
            st, reason = "review", "Claude marked this Pass but gave no quote that appears in the transcript, so a person needs to check. " + reason
        elif st == "pass" and any(not e["verified"] for e in ev):
            reason += " (One quoted line was not found word-for-word in the transcript.)"
        items[it["id"]] = {"status": st, "reason": reason, "evidence": ev[:2]}
    ins = {k: [str(v) for v in raw.get(k, []) if v] for k in ("strengths", "improvements", "coaching", "risks")}
    moments = []
    for k in raw.get("key_moments") or []:
        try:
            moments.append({"turn": int(k.get("turn")) - 1, "note": str(k.get("note", ""))})
        except (TypeError, ValueError):
            pass
    return {
        "summary": str(raw.get("summary", "")),
        "outcome": str(raw.get("outcome", "")),
        "client_sentiment": str(raw.get("client_sentiment", "")),
        "agent_tone": str(raw.get("agent_tone", "")),
        "items": items,
        "insights": ins,
        "key_moments": moments,
    }


def score(product, items, overrides=None):
    """Weighted score. Reviewer overrides win over Claude. Unresolved 'review' items are left out and flagged."""
    overrides = overrides or {}
    got = tot = 0
    n = {"pass": 0, "fail": 0, "review": 0, "na": 0}
    crit = []
    for it in PRODUCTS[product]["items"]:
        st = overrides.get(it["id"]) or items.get(it["id"], {}).get("status", "review")
        n[st] += 1
        if st in ("review", "na"):
            continue
        tot += it["weight"]
        if st == "pass":
            got += it["weight"]
        elif it["critical"]:
            crit.append(it["label"])
    pct = round(got / tot * 100) if tot else None
    if pct is None:
        verdict = "Not assessed"
    elif crit:
        verdict = "Critical fail"
    elif pct >= PASS_MARK:
        verdict = "Pass"
    elif pct >= COACH_MARK:
        verdict = "Needs coaching"
    else:
        verdict = "Fail"
    return {"pct": pct, "points": got, "of": tot, "verdict": verdict, "provisional": n["review"] > 0,
            "counts": n, "critical_fails": crit}
