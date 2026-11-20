"""Build the Innovate-branded QA PDF from an assessment JSON.

usage: python report.py assessment.json out.pdf
Prints the score as JSON. Needs: pip install reportlab svglib
"""
import json
import sys

import engine
import pdf_report

rec = json.load(open(sys.argv[1]))
rec.setdefault("overrides", {})
rec.setdefault("notes", {})
rec.setdefault("turns", [])
sc = engine.score(rec["product"], rec["result"]["items"], rec["overrides"])
open(sys.argv[2], "wb").write(pdf_report.build(rec, sc))
print(json.dumps(sc))
