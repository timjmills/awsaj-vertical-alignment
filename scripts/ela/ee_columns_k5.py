"""K-5 variant: split the Wisconsin Essential Elements for ELA (2022) PDF (grades K-5 pages) into one text stream per grade
column, so each grade's standards and EEs read top to bottom across page breaks.
Usage: python3 -I ee_columns.py <pdf> <out_dir>
Writes <out_dir>/ee_stream_<band>.txt
"""
import re, sys, os
import pdfplumber

CODE = re.compile(r"(EE\.)?(R|W|SL|L|RF)\.(K|[1-5])\.")
SKIP = re.compile(r"^(Wisconsin Essential Elements for English Language Arts\b.*|Strand:.*|Overarching Statement:.*|"
                  r"RI = Reading Information.*|\d+)$")

pdf = pdfplumber.open(sys.argv[1])
streams = {b: [] for b in ["K", "1", "2", "3", "4", "5"]}
ncols = None
overarching = False
for pno, pg in enumerate(pdf.pages, 1):
    if pno < 20:
        continue
    words = pg.extract_words(keep_blank_chars=False, use_text_flow=False, extra_attrs=["size"])
    xs = [w["x0"] for w in words if CODE.match(w["text"])]
    bands_on_page = set(CODE.match(w["text"]).group(3) for w in words if CODE.match(w["text"]))
    k5 = any(re.match(r"(EE\.)?(R|W|SL|L|RF)\.(6|7|8|9-10|11-12)\.", w["text"]) for w in words)
    first = next((l for l in (pg.extract_text() or "").split("\n") if l.strip()), "")
    if first.startswith("Endnotes"):
        break
    if not bands_on_page and re.search(r"Introduction|^Anchor Standards", first):
        continue
    if k5 and not bands_on_page:
        ncols = None
        continue
    if bands_on_page and bands_on_page <= {"K", "1", "2"}:
        ncols = "K2"
    elif bands_on_page and bands_on_page <= {"3", "4", "5"}:
        ncols = "35"
    if ncols is None:
        continue
    bounds = [265, 468]
    names = ["K", "1", "2"] if ncols == "K2" else ["3", "4", "5"]
    cols = {n: [] for n in names}
    for w in words:
        if w["top"] > pg.height - 40:
            continue
        ci = sum(1 for b in bounds if w["x0"] >= b)
        cols[names[ci]].append(w)
    # full-width lines (headers/footers) span columns; drop by text pattern after line assembly
    for n in names:
        ws = sorted(cols[n], key=lambda w: (round(w["top"]), w["x0"]))
        lines, cur, top = [], [], None
        for w in ws:
            if top is None or abs(w["top"] - top) > 3:
                if cur:
                    lines.append(" ".join(cur))
                cur, top = [w["text"]], w["top"]
            else:
                cur.append(w["text"])
        if cur:
            lines.append(" ".join(cur))
        for ln in lines:
            if SKIP.match(ln.strip()):
                continue
            streams[n].append(ln)
    for n in names:
        streams[n].append(f"<<page {pno}>>")

os.makedirs(sys.argv[2], exist_ok=True)
for b, ls in streams.items():
    open(os.path.join(sys.argv[2], f"ee_stream_{b}.txt"), "w").write("\n".join(ls))
    print(b, len(ls))
