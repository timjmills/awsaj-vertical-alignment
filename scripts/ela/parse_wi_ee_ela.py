"""Parse the per-grade EE streams (from ee_columns.py) into {standard_code: {...EE...}} for grades 6-12.

Handles source typos: "EE W.6.7", "E.L.8.2", "EE.L.9-10.3.1" (printed for EE.L.9-10.1).
Usage: python3 -I parse_wi_ee_ela.py <stream_dir> <out.json> [bands, e.g. K,1,2,3,4,5]
"""
import json, re, sys, os

BANDS = sys.argv[3].split(",") if len(sys.argv) > 3 else ["6", "7", "8", "9-10", "11-12"]
STD = re.compile(r"^(RF|R|W|SL|L)\.(K|1|2|3|4|5|6|7|8|9-10|9\.10|11-12)\.(\d+)\b\s*(.*)$")
EE = re.compile(r"^E{1,2}[ .]{0,2}(RF|R|W|SL|L)\.(K|1|2|3|4|5|6|7|8|9-10|11-12)\.(\d+)((?:\.\d+)?)\.?\s*(.*)$")
HDR = re.compile(r"\bGrades? \d|\bKindergarten\b")
SUB = re.compile(r"^([a-h])\.\s+(.*)$")


def clean(s):
    s = s.replace(" ", " ").replace("—", ", ").replace("–", "-")
    s = re.sub(r"(\w)- (\w)", lambda m: m.group(1) + "-" + m.group(2) if False else m.group(0), s)
    return re.sub(r"\s+", " ", s).strip()


def join_lines(lines):
    out = ""
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        if out.endswith("-") and not out.endswith(" -"):
            # hyphenated line break: keep the hyphen only for real compounds (e.g. "low-" + "stakes")
            out = out + ln
        else:
            out = (out + " " + ln) if out else ln
    return clean(out)


result = {}
fixes = {}
for b in BANDS:
    lines = open(os.path.join(sys.argv[1], f"ee_stream_{b}.txt")).read().split("\n")
    # drop the page-top overarching-statement fragments and cluster headers that follow each page marker
    keep = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("<<page"):
            keep.append(ln)
            window = []
            for w in lines[i + 1:i + 8]:
                if w.startswith("<<page"):
                    break
                window.append(w)
            hdr_idx = None
            for j, w in enumerate(window):
                if HDR.search(w):
                    hdr_idx = j
            if hdr_idx is not None and all(not STD.match(w) and not EE.match(w) for w in window[:hdr_idx + 1]):
                i = i + 1 + hdr_idx + 1
                continue
            i += 1
            continue
        if HDR.search(ln) and not STD.match(ln) and not EE.match(ln) and len(ln) < 70:
            i += 1
            continue
        keep.append(ln)
        i += 1
    blocks = []
    cur = None
    for ln in keep:
        if ln.startswith("<<page"):
            if cur is not None:
                cur["lines"].append(ln)
            continue
        m = STD.match(ln)
        e = EE.match(ln)
        if e:
            num = e.group(3)
            raw = ln.split()[0] if not ln.startswith("EE W") else "EE W." + ln.split()[1][2:]
            code = f"EE.{e.group(1)}.{e.group(2)}.{num}"
            if e.group(4):   # "EE.L.9-10.3.1" printed for EE.L.9-10.1
                code = f"EE.{e.group(1)}.{e.group(2)}.{e.group(4)[1:]}"
            orig = ln.split(" Use")[0].split(" Demonstrate")[0] if code == "EE.L.9-10.1" else ln[:len(code) + 1].strip()
            cur = {"kind": "ee", "code": code, "lines": [e.group(5)], "raw": ln[:14]}
            blocks.append(cur)
        elif m:
            cur = {"kind": "std", "code": f"{m.group(1)}.{m.group(2)}.{m.group(3)}", "lines": [m.group(4)]}
            blocks.append(cur)
        elif cur is not None:
            cur["lines"].append(ln)
    for bl in blocks:
        if bl["kind"] != "ee":
            continue
        # cut at the first page marker if what follows is not a continuation (last block of the doc etc.)
        ls = bl["lines"]
        text_lines, stop = [], False
        for k, ln in enumerate(ls):
            if ln.startswith("<<page"):
                continue
            text_lines.append(ln)
        stem, subs = [], []
        for ln in text_lines:
            sm = SUB.match(ln.strip())
            if sm:
                subs.append([sm.group(1), [sm.group(2)]])
            elif subs:
                subs[-1][1].append(ln)
            else:
                stem.append(ln)
        std_code = bl["code"][3:]
        raw = bl["raw"].split()[0] if not bl["raw"].startswith("EE W") else "EE W." + bl["raw"].split()[1][2:]
        if raw.rstrip(".") != bl["code"]:
            fixes[bl["code"]] = bl["raw"].strip()
        result[std_code] = {"ee_code": bl["code"], "stem": join_lines(stem),
                            "subs": [[L, join_lines(t)] for L, t in subs]}

json.dump({"ee": result, "fixes": fixes}, open(sys.argv[2], "w"), indent=1, ensure_ascii=False)
print(len(result), "EEs; source code fixes:", fixes)
