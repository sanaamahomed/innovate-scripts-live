"""Innovate-branded PDF report (reportlab, no system libraries needed)."""
import io
import os
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (BaseDocTemplate, Frame, KeepTogether, PageBreak, PageTemplate, Paragraph,
                                Spacer, Table, TableStyle)

from engine import clock
from scorecards import PRODUCTS

NAVY, YELLOW, TEAL = colors.HexColor("#18305E"), colors.HexColor("#FFC709"), colors.HexColor("#2CCCC4")
INK, MUTED, LINE, BG = colors.HexColor("#111111"), colors.HexColor("#5b6678"), colors.HexColor("#E0E5EB"), colors.HexColor("#F5F7FA")
GREEN, RED, AMBER = colors.HexColor("#16805A"), colors.HexColor("#B3261E"), colors.HexColor("#B58900")
LOGO = os.path.join(os.path.dirname(__file__), "static", "logo.svg")
W, H = A4


def _p(txt, **kw):
    base = dict(fontName="Helvetica", fontSize=9.5, leading=13, textColor=INK, alignment=TA_LEFT)
    base.update(kw)
    return ParagraphStyle("x", **base)


S = {
    "body": _p(""), "muted": _p("", fontSize=8.5, leading=11, textColor=MUTED),
    "h": _p("", fontName="Helvetica-Bold", fontSize=13, leading=16, textColor=NAVY, spaceBefore=10, spaceAfter=4),
    "q": _p("", fontName="Helvetica-Oblique", fontSize=8.5, leading=11, textColor=INK, leftIndent=6),
    "tr": _p("", fontSize=8.8, leading=12),
}


def _logo():
    try:
        from svglib.svglib import svg2rlg
        d = svg2rlg(LOGO)
        sc = (11 * mm) / d.height
        d.scale(sc, sc)
        d.width, d.height = d.width * sc, d.height * sc
        return d
    except Exception:
        return None


def _header(c, doc):
    c.saveState()
    c.setFillColor(NAVY)
    c.rect(0, H - 24 * mm, W, 24 * mm, stroke=0, fill=1)
    c.setFillColor(YELLOW)
    c.rect(0, H - 25.5 * mm, W, 1.5 * mm, stroke=0, fill=1)
    logo = _logo()
    if logo:
        from reportlab.graphics import renderPDF
        renderPDF.draw(logo, c, 14 * mm, H - 18 * mm)
    else:
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(14 * mm, H - 15 * mm, "INNOVATE")
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 15)
    c.drawRightString(W - 14 * mm, H - 13 * mm, "Assure: Call Assessment")
    c.setFillColor(YELLOW)
    c.setFont("Helvetica", 9)
    c.drawRightString(W - 14 * mm, H - 19 * mm, doc.subtitle)
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 7.5)
    c.drawString(14 * mm, 8 * mm, "Innovate Assure · Where Strategy Meets People And Growth.")
    c.drawRightString(W - 14 * mm, 8 * mm, f"Page {doc.page}")
    c.restoreState()


def _bullets(title, items, color):
    if not items:
        return None
    rows = [[Paragraph(f"<b>{escape(title)}</b>", _p("", fontName="Helvetica-Bold", textColor=NAVY))]]
    rows += [[Paragraph("• " + escape(i), S["body"])] for i in items]
    t = Table(rows, colWidths=[(W - 36 * mm) / 2 - 3 * mm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), BG), ("LINEBEFORE", (0, 0), (0, -1), 2.5, color),
                           ("LEFTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 2),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
    return t


def build(rec, sc):
    """rec: stored assessment dict; sc: score dict from engine.score."""
    meta, res, product = rec["meta"], rec.get("result") or {}, rec["product"]
    over, notes = rec.get("overrides", {}), rec.get("notes", {})
    turns = rec.get("turns", [])
    buf = io.BytesIO()
    doc = BaseDocTemplate(buf, pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=31 * mm,
                          bottomMargin=16 * mm, title=f"QA Assessment - {meta.get('agent') or 'agent'} - {meta.get('date')}",
                          author="Innovate")
    doc.subtitle = PRODUCTS[product]["title"]
    doc.addPageTemplates([PageTemplate(id="p", frames=[Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height,
                                                             id="f", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)],
                                       onPage=_header)])
    st = []
    m = Table([[Paragraph(f"<font size=7 color='#5b6678'>{k.upper()}</font><br/>{escape(meta.get(v) or '–')}", S["body"])
                for k, v in (("Agent", "agent"), ("Client", "client"), ("Call date", "date"), ("Reference", "ref"))]],
              colWidths=[doc.width / 4] * 4)
    m.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), BG), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    st += [m, Spacer(1, 8)]

    col = GREEN if sc["verdict"] == "Pass" else AMBER if sc["verdict"] == "Needs coaching" else RED
    pct = "–" if sc["pct"] is None else f"{sc['pct']}%"
    verdict = sc["verdict"] + (" (provisional)" if sc["provisional"] and sc["pct"] is not None else "")
    c = sc["counts"]
    sub = f"{sc['points']}/{sc['of']} points · {c['pass']} pass · {c['fail']} fail · {c['review']} to review · {c['na']} N/A"
    if sc["critical_fails"]:
        sub += "<br/><b>Critical items failed:</b> " + escape("; ".join(sc["critical_fails"]))
    score = Table([[Paragraph(f"<font size=34 color='{col.hexval()}'><b>{pct}</b></font>", _p("", fontSize=34, leading=42)),
                    [Paragraph(f"<font color='{col.hexval()}'><b>{escape(verdict)}</b></font>", _p("", fontSize=13, leading=16)),
                     Paragraph(sub, S["muted"])]]], colWidths=[40 * mm, doc.width - 40 * mm])
    score.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    st += [score]

    if res.get("summary"):
        st += [Paragraph("Summary", S["h"]), Paragraph(escape(res["summary"]), S["body"])]
        tags = " · ".join(escape(x) for x in (f"Outcome: {res['outcome']}" if res.get("outcome") else "",
                                             f"Client: {res['client_sentiment']}" if res.get("client_sentiment") else "",
                                             f"Agent: {res['agent_tone']}" if res.get("agent_tone") else "") if x)
        if tags:
            st += [Spacer(1, 3), Paragraph(tags, S["muted"])]
        ins = res.get("insights", {})
        for a, b in ((("Strengths", ins.get("strengths"), GREEN), ("Areas to improve", ins.get("improvements"), YELLOW)),
                     (("Coaching actions", ins.get("coaching"), TEAL), ("Risk and compliance flags", ins.get("risks"), RED))):
            cells = [_bullets(*a), _bullets(*b)]
            if any(cells):
                t = Table([[x or "" for x in cells]], colWidths=[doc.width / 2, doc.width / 2])
                t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
                st += [Spacer(1, 6), t]

    groups = list(dict.fromkeys(i["group"] for i in PRODUCTS[product]["items"]))
    for g in groups:
        st.append(Paragraph(g + ("" if g.endswith("scorecard") else " items"), S["h"]))
        rows = []
        for it in (i for i in PRODUCTS[product]["items"] if i["group"] == g):
            r = (res.get("items") or {}).get(it["id"], {})
            s_ = over.get(it["id"]) or r.get("status", "review")
            sc_col = {"pass": GREEN, "fail": RED, "review": AMBER}.get(s_, MUTED)
            label = escape(it["label"]) + (" <font size=7 color='#B3261E'><b>CRITICAL</b></font>" if it["critical"] else "")
            cell = [Paragraph(f"<b>{label}</b>", S["body"])]
            why = (r.get("reason") or "") + (" (set by reviewer)" if over.get(it["id"]) else "")
            if why:
                cell.append(Paragraph(escape(why), S["muted"]))
            for e in r.get("evidence", [])[:1]:
                cell.append(Paragraph("“" + escape(e["quote"][:220]) + "”", S["q"]))
            if notes.get(it["id"]):
                cell.append(Paragraph("Note: " + escape(notes[it["id"]]), S["muted"]))
            rows.append([Paragraph(f"<font color='{sc_col.hexval()}'><b>{'N/A' if s_ == 'na' else s_.upper()}</b></font>", _p("", fontSize=8)), cell])
        t = Table(rows, colWidths=[16 * mm, doc.width - 16 * mm], repeatRows=0)
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.5, LINE),
                               ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4), ("LEFTPADDING", (0, 0), (-1, -1), 2)]))
        st.append(t)

    if turns:
        st += [PageBreak(), Paragraph("Transcript", S["h"])]
        for tr in turns:
            who = {"agent": "AGENT", "client": "CLIENT"}.get(tr["spk"], "?")
            colr = NAVY.hexval() if who == "AGENT" else "#0c7d77" if who == "CLIENT" else MUTED.hexval()
            t0 = f" <font color='#5b6678' size=7>{clock(tr['t'])}</font>" if tr.get("t") is not None else ""
            st.append(Paragraph(f"<font color='{colr}' size=7><b>{who}</b></font>{t0}  {escape(tr['text'])}", S["tr"]))
    doc.build(st)
    return buf.getvalue()
