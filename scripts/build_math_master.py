"""Merge Wisconsin CC (6-12) + EE crosswalk + suggested HS course into one list, and slice for descriptor writing.

Usage: python3 build_math_master.py
"""
import json, re

cc = json.load(open("data/wi_math_6_12.json"))
ee = {r["cc_code"]: r for r in json.load(open("data/wi_ee_math.json"))}

COURSE_GRADE = {"Algebra 1": "9", "Geometry": "10", "Algebra 2": "11", "Pre-Calculus": "12"}


def course(r):
    c, tags = r["code"], r["tags"]
    dom = c.split(".")[1]
    sub = ".".join(c.split(".")[1:3])
    if dom == "G":
        return "Pre-Calculus" if "+" in tags and sub == "G.GPE" else "Geometry"
    if dom == "SP":
        if sub == "SP.ID": return "Algebra 1"
        if sub == "SP.CP": return "Geometry"
        return "Algebra 2"
    if "+" in tags:
        return "Pre-Calculus"
    if sub in ("N.CN", "F.TF"): return "Algebra 2"
    if sub == "N.VM": return "Pre-Calculus"
    if sub == "A.APR" and c.split(".")[3] in ("B", "C", "D"): return "Algebra 2"
    if sub == "F.BF" and c.split(".")[3] == "B" and int(c.split(".")[4]) >= 4: return "Algebra 2"
    if sub == "F.LE" and "log" in r["text"].lower(): return "Algebra 2"
    return "Algebra 1"


def fix(t):
    return re.sub(r"(\w)- ([a-z])", r"\1-\2", t or "")


rows = []
for r in cc:
    e = ee.get(r["code"], {})
    hs = r["section"] == "HS"
    crs = course(r) if hs else ""
    rows.append({
        "code": r["code"],
        "grade": COURSE_GRADE[crs] if hs else r["section"],
        "course": crs if hs else f"Grade {r['section']} Math",
        "course_is_suggested": hs,
        "domain": r["domain"], "domain_code": r["domain_code"],
        "cluster": r["cluster"], "major_cluster": r["major_cluster"],
        "wi_tags": ",".join(r["tags"]),
        "cc_text": fix(r["text"]),
        "ee_code": e.get("ee_code") or "",
        "ee_text": fix(e.get("ee_text", "")),
    })
json.dump(rows, open("data/math_6_12_merged.json", "w"), indent=1, ensure_ascii=False)
# slices for descriptor writing (about 60 each)
n = 4
for i in range(n):
    part = rows[i::n]
    json.dump([{k: r[k] for k in ("code", "course", "cc_text", "ee_code", "ee_text")} for r in part],
              open(f"data/slices/math_slice_{i+1}.json", "w"), indent=1, ensure_ascii=False)
from collections import Counter
print(len(rows), Counter(r["course"] for r in rows))
