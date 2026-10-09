"""Parse Wisconsin Essential Elements for Mathematics (2022) crosswalk into CC -> EE rows.

Usage: python3 parse_wi_ee_math.py <WI_EE_Math_2022.txt> <out.json>
Each row: cc_code, ee_code (or ""), ee_text (or "Not applicable. See ...").

Method: column positions come from each table header ("... DLM  Notation  Alternate Academic").
Within a block (lines between blank lines), each EE entry starts either with an EE code in the
EE notation column or with "Not applicable" in the right column. Entries are paired in order
with the CC codes found in the block.
"""
import json, re, sys

src, out = sys.argv[1], sys.argv[2]
lines = open(src, encoding="utf-8").read().replace("\x0c", "").split("\n")
CC = re.compile(r"\bM\s?\.\s?((?:K|[1-8])\.[A-Z]{1,3}\.[A-D]\.?\d+|(?:N|A|F|G|SP)\.[A-Z]{1,4}\.[A-D]\.?\d+)(?![a-z0-9\]])")
EE = re.compile(r"M\.EE\.[A-Z0-9]+(?:\.[A-Z]{1,4})?\.\d+(?:[a-z](?:-[a-z])?)?(?:-\d+)?")
FOOT = re.compile(r"^\s*Wisconsin Essential Elements for Mathematics\s+\d+\s*$")


def norm(raw):
    return re.sub(r"\.([A-D])(\d)", r".\1.\2", "M." + raw.replace(" ", ""))


cols = None  # (dlm_col, ee_code_col, alt_col)
blocks, block = [], []


def close():
    global block
    if block and cols:
        blocks.append((list(block), cols))
    block = []


for l in lines:
    if FOOT.match(l):
        continue
    if re.search(r"Alternate Academic|\bDLM\b|Conceptual|Notation", l) and not CC.search(l) and not EE.search(l):
        close()
        c = list(cols) if cols else [96, 112, 128]
        if "DLM" in l: c[0] = l.index("DLM")
        elif "Conceptual" in l: c[0] = l.index("Conceptual")
        for m in re.finditer("Notation", l):
            if m.start() > 70: c[1] = m.start()
        if "Alternate" in l: c[2] = l.index("Alternate")
        cols = tuple(c)
        continue
    if re.match(r"^\s*(Area|Statement|Standard|Cluster|Achievement( Standard)?|Wisconsin Standards for Mathematics\s+Wisconsin)\s*$", l.strip() and l) or re.match(r"^\s*(Area|Statement)\s", l):
        continue
    if not l.strip():
        close(); continue
    block.append(l)
close()

rows = {}
last_row = None
for blines, (dlm, ecol, acol) in blocks:
    ccs = [(i, norm(m.group(1))) for i, l in enumerate(blines) for m in [CC.search(l[:dlm])] if m]
    if not ccs:
        continue
    entries = []  # [start_line, ee_code, parts]
    pending, gap = [], False

    def code_soon(i):
        for l2 in blines[i + 1:i + 3]:
            m2 = l2[dlm:acol - 1] if len(l2) > dlm else ""
            if EE.search(m2[max(ecol - dlm - 6, 0):]):
                return True
        return False
    for i, l in enumerate(blines):
        mid = l[dlm:acol - 1] if len(l) > dlm else ""
        right = l[acol - 2:].strip() if len(l) > acol - 2 else ""
        e = EE.search(mid[max(ecol - dlm - 6, 0):])
        if not e and right.startswith("M.EE"):
            e = EE.match(right); right = right[e.end():].strip() if e else right
        starts_na = right.startswith("Not applicable")
        if e or starts_na:
            if pending:
                if e and not right:
                    right = " ".join(pending)  # text sat just above its EE code
                elif entries:
                    entries[-1][2] += pending
                elif last_row is not None:
                    last_row["ee_text"] = (last_row["ee_text"] + " " + " ".join(pending)).strip()
            pending = []
            entries.append([i, e.group(0) if e else "", []])
            gap = False
        if not right:
            gap = True
            continue
        if not entries:
            pending.append(right)  # text before any code in this block
        elif pending or (" ".join(entries[-1][2]).rstrip().endswith(".") and re.match(r"[A-Z]", right)
                         and not right.startswith(("For example", "Example")) and code_soon(i)):
            pending.append(right)
        else:
            entries[-1][2].append(right)
    if pending:
        if entries:
            entries[-1][2] += pending
        elif last_row is not None:
            last_row["ee_text"] = (last_row["ee_text"] + " " + " ".join(pending)).strip()
    # orphan text at the top of a block (carried over a page break) belongs to the previous row
    if entries and not entries[0][1] and not " ".join(entries[0][2]).startswith("Not applicable") and last_row is not None and ccs[0][0] > entries[0][0]:
        last_row["ee_text"] = (last_row["ee_text"] + " " + " ".join(entries[0][2])).strip()
        entries.pop(0)
    # pair entries with CC codes in order; extra entries merge into the previous one
    for k, (li, code) in enumerate(ccs):
        if k < len(entries):
            ent = entries[k]
            if k == len(ccs) - 1:
                for extra in entries[k + 1:]:
                    ent[2] += ([extra[1]] if extra[1] else []) + extra[2]
            text = re.sub(r"\s+", " ", " ".join(ent[2])).strip()
            text = re.sub(r"(\w)- (\w)", r"\1\2", text) if False else text
            rows.setdefault(code, {"cc_code": code, "ee_code": ent[1], "ee_text": text})
        else:
            rows.setdefault(code, {"cc_code": code, "ee_code": "", "ee_text": ""})
        last_row = rows[code]

final = list(rows.values())
json.dump(final, open(out, "w"), indent=1, ensure_ascii=False)
print(len(final), sum(1 for r in final if r["ee_code"]), "with EE code;",
      sum(1 for r in final if r["ee_text"].startswith("Not applicable")), "not applicable;",
      sum(1 for r in final if not r["ee_code"] and not r["ee_text"].startswith("Not applicable")), "unresolved")
