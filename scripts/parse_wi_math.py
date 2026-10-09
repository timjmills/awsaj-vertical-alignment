"""Parse Wisconsin Standards for Mathematics (pdftotext -layout output) into rows.

Usage: python3 parse_wi_math.py <WI_Math_Standards.txt> <out.json>
Extracts Grades 6-8 and High School content standards (K-5 come from the school's CCEE sheet).

Method: inside each standards table, rows are separated by blank lines. Each block of lines
belongs to the one code it contains (text can wrap above the code line). Blocks with no code
continue the previous standard (e.g. sub-items or text carried over a page break).
"""
import json, re, sys
from collections import Counter

src, out = sys.argv[1], sys.argv[2]
lines = open(src, encoding="utf-8").read().replace("\x0c", "").split("\n")

CODE = re.compile(r"(?<!2010\.)(?<!2010\. )\bM\s?\.\s?((?:6|7|8)\.[A-Z]{1,3}\.[A-D]\.?\d+|(?:N|A|F|G|SP)\.[A-Z]{1,4}\.[A-D]\.?\d+)(?![\]a-z0-9])")
DOMAIN = re.compile(r"^\s*([A-Z][A-Za-z ,\-—’'&]+?)\s+\(((?:\d\.)?[A-Z]{1,3}(?:-[A-Z]{1,4})?)\)(\s*\(\s*cont’d\))?\s*$")
FOOTER = re.compile(r"^\s*Wisconsin Standards for Mathematics\s+\d+\s*$")
HEADER = re.compile(r"^\s*(Cluster Statement|Notation|NOTE: This)")
TAG = re.compile(r"\((F2Y|\+|M)\)")


def norm_code(raw):
    return re.sub(r"\.([A-D])(\d)", r".\1.\2", "M." + raw.replace(" ", ""))


start = next(i for i, l in enumerate(lines) if l.strip().startswith("Grade 6 Content Standards"))
end = next(i for i, l in enumerate(lines) if i > start and re.match(r"^\s*(References|Appendix|Bibliography)", l))

# 1. walk lines -> blocks (lists of lines) with section/domain context
blocks, block, section, domain, in_table = [], [], "6", ("", ""), False


def close():
    global block
    if block:
        blocks.append({"lines": block, "section": section, "domain": domain})
    block = []


for i in range(start, end):
    l = lines[i].rstrip()
    l = re.sub(r"\[WI\.2010\.?", lambda m: " " * len(m.group(0)), l)
    l = re.sub(r"M\.[A-Z]{1,2}\.[A-Z]{1,4}\.[A-D]\.\d+\]", lambda m: " " * len(m.group(0)), l)
    if FOOTER.match(l):
        continue
    s = l.strip()
    m = re.match(r"^Grade (\d) Content Standards", s)
    if m:
        close(); section = m.group(1); in_table = False; continue
    if s.startswith("High School"):
        close(); section = "HS"; in_table = False; continue
    dm = DOMAIN.match(l)
    if dm and not CODE.search(l):
        close(); domain = (dm.group(1).strip(), dm.group(2)); continue
    if HEADER.match(l):
        close(); in_table = True; continue
    if not s:
        close(); continue
    # narrative prose (not in a table row): starts at margin and is a long sentence
    if (s.startswith("Introduction") or (len(l) - len(l.lstrip()) == 0 and len(s.split()) > 9)) and not CODE.search(l):
        close(); in_table = False; continue
    if in_table:
        block.append(l)
close()

# 2. turn blocks into standards
rows, last = [], None
for b in blocks:
    code_lines = [(j, CODE.search(l)) for j, l in enumerate(b["lines"]) if CODE.search(l)]
    if not code_lines:
        if last is not None:
            for l in b["lines"]:
                last["_parts"].append(l[max(last["_tcol"] - 2, 0):].strip())
                last["_clus"].append(l[:last["_ccol"]].strip())
        continue
    bounds = [j for j, _ in code_lines] + [len(b["lines"])]
    for k, (j, m) in enumerate(code_lines):
        ccol, after = m.start(), m.end()
        rest = b["lines"][j][after:]
        tcol = after + (len(rest) - len(rest.lstrip()))
        lo = 0 if k == 0 else j
        if k > 0 and not rest.strip():
            # text starts above the code line: go back to just after the previous sentence end
            prev = rows[-1]
            tcol = prev["_tcol"]
            t = j
            while t - 1 > bounds[k - 1] and not b["lines"][t - 1][tcol - 2:].strip().endswith("."):
                t -= 1
            lo = t
            cut = j - t  # remove those lines from the previous standard
            if cut:
                del prev["_parts"][-cut:]
        seg = b["lines"][lo:bounds[k + 1]]
        r = {"code": norm_code(m.group(1)), "section": b["section"], "domain": b["domain"][0],
             "domain_code": b["domain"][1], "_parts": [], "_clus": [], "_mid": [], "_tcol": tcol, "_ccol": ccol}
        for idx, l in enumerate(seg):
            r["_clus"].append(l[:ccol].strip())
            if lo + idx == j:
                r["_parts"].append(rest.strip())
            else:
                r["_mid"].append(l[ccol:max(tcol - 2, ccol)].strip())
                r["_parts"].append(l[max(tcol - 2, 0):].strip())
        rows.append(r); last = r

# 3. tidy fields (cluster text runs down the left column across several rows of one cluster)
clus_by_prefix = {}
for r in rows:
    clus = " ".join(r.pop("_clus"))
    mid = " ".join(r.pop("_mid"))
    pre = r["code"].rsplit(".", 1)[0]
    clus_by_prefix.setdefault(pre, []).append(clus)
    tags = set(t for t in TAG.findall(clus + " " + mid) if t != "M")
    text = re.sub(r"\s+", " ", " ".join(p for p in r.pop("_parts") if p)).strip()
    if "(+)" in text: tags.add("+")
    text = TAG.sub("", text).strip()
    r.pop("_tcol"); r.pop("_ccol")
    r["text"], r["tags"] = text, sorted(tags)
cluster_of, major = {}, {}
for pre, parts in clus_by_prefix.items():
    c = " ".join(parts)
    major[pre] = "(M)" in c
    c = re.sub(r"\s+", " ", TAG.sub(" ", c)).strip()
    c = re.sub(r"(\w)- (\w)", r"\1\2", c)  # re-join hyphenated line breaks (multiplica- tion)
    letter = pre.rsplit(".", 1)[1]
    m = re.search(letter + r"\.\s.*?[a-z)]\.(?=\s|$)", c)
    cluster_of[pre] = m.group(0) if m else c
for r in rows:
    pre = r["code"].rsplit(".", 1)[0]
    r["cluster"], r["major_cluster"] = cluster_of[pre], major[pre]

seen, final = set(), []
for r in rows:
    if r["code"] in seen:
        continue
    seen.add(r["code"]); final.append(r)
json.dump(final, open(out, "w"), indent=1, ensure_ascii=False)
print(len(final), Counter(r["section"] for r in final))
