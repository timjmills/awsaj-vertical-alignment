"""Parse the Wisconsin Standards for ELA (2020) Word version (DPI media 54346) into JSON rows for grades 6-12.

Each lettered sub-item (Word numbered-list paragraph) becomes its own row "<code>.a", matching the school
sheets' style (e.g. W.9-10.2.a). The row text is the stem followed by "a. <sub text>".
Usage: python3 -I parse_wi_ela.py <docx> <out.json> [band regex, default grades 6-12]
"""
import json, re, sys
import docx

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
BANDS = sys.argv[3] if len(sys.argv) > 3 else "6|7|8|9-10|9\\.10|11-12"   # e.g. "K|1|2|3|4|5"
CODE = re.compile(r"^\s*((RF|R|W|SL|L)\.(" + BANDS + r"))\.(\d+)\s*\t?\s*(.*)$", re.S)
STRAND = {"R": "Reading", "RF": "Reading Foundational Skills", "W": "Writing", "SL": "Speaking and Listening",
          "L": "Language"}

d = docx.Document(sys.argv[1])
stds = {}   # code -> dict(stem, extra[], subs[], cluster)
order = []
last_in_col = {}   # (ncols, col) -> last code, so "(cont.)" tables attach sub-items to the right standard
typos = {}

def band_of(code):
    return code.split(".")[1]

def clean(s):
    s = s.replace(" ", " ").replace("\t", " ")
    s = s.replace("—", ", ").replace("–", "-")
    return re.sub(r"\s+", " ", s).strip()

for t in d.tables:
    hdr = []
    for c in t.rows[0].cells:
        hdr.append(clean(c.text))
    for ri, row in enumerate(t.rows[1:], 1):
        seen = set()
        for ci, cell in enumerate(row.cells):
            if id(cell._tc) in seen:
                continue
            seen.add(id(cell._tc))
            carried = ri == 1 and ci < len(hdr) and "cont" in hdr[ci]
            hb = re.search(r"Grades?\s*([\dK]+(?:\s*-\s*\d+)?)", hdr[ci]) if ci < len(hdr) else None
            hb = hb.group(1).replace(" ", "") if hb else None
            cur = last_in_col.get(hb) if carried else None
            for p in cell.paragraphs:
                txt = clean(p.text)
                if not txt:
                    continue
                m = CODE.match(p.text.replace(" ", " "))
                if m:
                    code = f"{m.group(1)}.{m.group(4)}"
                    if "9.10" in code:
                        fixed = code.replace("9.10", "9-10"); typos[fixed] = code; code = fixed
                    cluster = hdr[ci] if ci < len(hdr) else ""
                    cluster = re.sub(r"\s*-\s*Grades?.*$", "", cluster, flags=re.S).strip()
                    if m.group(2) == "SL" and int(m.group(4)) >= 4:
                        cluster = "Presentation of Knowledge & Ideas"
                    if code not in stds:
                        stds[code] = {"stem": clean(m.group(5)), "extra": [], "subs": [], "cluster": cluster}
                        order.append(code)
                    cur = code
                    carried = False
                    last_in_col[band_of(code)] = code
                    continue
                if cur is None:
                    continue
                numbered = p._p.find(f".//{W}numPr") is not None
                if numbered:
                    stds[cur]["subs"].append(txt)
                elif not carried:
                    if txt not in stds[cur]["extra"] and txt != stds[cur]["stem"]:
                        stds[cur]["extra"].append(txt)

rows = []
for code in order:
    s = stds[code]
    pre, band, num = code.split(".")[0], code.split(".")[1], code.split(".")[2]
    stem = " ".join([s["stem"]] + s["extra"]).strip()
    base = dict(prefix=pre, band=band, strand=STRAND[pre], cluster=s["cluster"], code_original=typos.get(code, ""))
    if s["subs"]:
        for i, sub in enumerate(s["subs"]):
            if i >= 10: print("MANY", code, len(s["subs"]), s["subs"][:3]); break
            L = "abcdefghij"[i]
            rows.append(dict(base, code=f"{code}.{L}", parent=code, stem=stem, sub=sub,
                             text=f"{stem} {L}. {sub}"))
    else:
        rows.append(dict(base, code=code, parent=code, stem=stem, sub="", text=stem))

json.dump(rows, open(sys.argv[2], "w"), indent=1, ensure_ascii=False)
from collections import Counter
print(Counter(r["band"] for r in rows))
print(Counter((r["band"], r["prefix"]) for r in rows))
