"""Parse Wisconsin Essential Elements for Social Studies (2022 PDF) into one record per standard.

Usage: python3 -I parse_wi_ee_ss.py <ee_text_from_pdftotext_layout> <out.json>
"""
import json
import re
import sys

txt = open(sys.argv[1], encoding="utf-8").read()
start = txt.index("Section III")
body = txt[start:]
# drop footers and content-area headings
body = re.sub(r"Wisconsin Essential Elements for Social Studies\s+\d+\s*\n", "\n", body)
body = re.sub(r"\n\s*Content Area:[^\n]*", "\n", body)
flat = re.sub(r"\s+", " ", body)
flat = flat.replace("reasonin g", "reasoning").replace("SS:.Econ1:", "SS.Econ1:")  # typo in source PDF

pat = re.compile(r"Wisconsin Standards for Social Studies:? (SS\.\w+\d): (.*?) Essential Element:? (SS\.EE\.\w+\d): (.*?) "
                 r"Target Level: (.*?) Precursor Level: (.*?) Initial Level: (.*?)(?= Wisconsin Standards for Social Studies| Content Area|$)")
out = []
for m in pat.finditer(flat):
    out.append({"standard": m.group(1), "standard_text": m.group(2).strip(), "ee_code": m.group(3),
                "ee_text": m.group(4).strip(), "target": m.group(5).strip(), "precursor": m.group(6).strip(),
                "initial": m.group(7).strip()})
json.dump(out, open(sys.argv[2], "w"), indent=1, ensure_ascii=False)
print(len(out), "EE records")
for r in out:
    print(r["ee_code"], "|", r["ee_text"], "|", r["initial"][-60:])
