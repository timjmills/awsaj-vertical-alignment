"""Join the official WI ELA 2020 rows (grades 6-12) with the WI Essential Elements for ELA (2022) and,
for 9-10, overlay the school's G9-10 sheet (codes, text, descriptors where present).

Usage: python3 -I merge_6_12.py   (run from /home/claude/awsaj-va)
Writes data/ela/merged_6_12.json : one row per standard per band (bands 6,7,8,9-10,11-12)
"""
import json, re

off = json.load(open("data/ela/wi_ela_6_12.json"))
ee_all = json.load(open("data/ela/wi_ee_ela_6_12.json"))
EE, EE_FIX = ee_all["ee"], ee_all["fixes"]
school = json.load(open("data/ela/school_910.json"))

CLUSTER_FIX = {"Vocabulary Acquisition &Use": "Vocabulary Acquisition & Use",
               "Conventions of Standard English": "Conventions of Standardized English",
               "Vocabulary Acquisition & use": "Vocabulary Acquisition & Use"}


def is_na(t):
    return bool(re.match(r"^(not applicable|n/a)\b", t.strip(), re.I))


def ee_for(parent, letter, n_letters_std, is_last_letter):
    """Return (ee_code, ee_text) for an official row."""
    e = EE.get(parent)
    if not e:
        return "", ""
    subs = e["subs"]
    if not subs:
        return e["ee_code"], e["stem"]
    if not letter:
        return e["ee_code"], (e["stem"] + " " + " ".join(f"{L}. {t}" for L, t in subs)).strip()
    picked = [(L, t) for L, t in subs if L == letter]
    if is_last_letter:   # extra EE sub-items beyond the standard's last letter belong with the last row
        picked += [(L, t) for L, t in subs if L > letter]
    if not picked:
        return e["ee_code"], (e["stem"] + " " + " ".join(f"{L}. {t}" for L, t in subs)).strip()
    if len(picked) == 1 and is_na(picked[0][1]):
        return f"{e['ee_code']}.{letter}", picked[0][1]
    code = f"{e['ee_code']}.{letter}" if len(picked) == 1 else f"{e['ee_code']}.{picked[0][0]}-{picked[-1][0]}"
    return code, (e["stem"] + " " + " ".join(f"{L}. {t}" for L, t in picked)).strip()


rows = []
by_parent = {}
for r in off:
    by_parent.setdefault(r["parent"], []).append(r)
for parent, group in by_parent.items():
    letters = [g["code"].split(".")[-1] for g in group if g["code"] != parent]
    for g in group:
        L = g["code"].split(".")[-1] if g["code"] != parent else ""
        ee_code, ee_text = ee_for(parent, L, len(letters), bool(letters) and L == letters[-1])
        rows.append({
            "band": g["band"], "code": g["code"], "code_original": g["code_original"], "parent": parent,
            "strand": g["strand"], "cluster": CLUSTER_FIX.get(g["cluster"], g["cluster"]), "text": g["text"],
            "ee_code": ee_code, "ee_text": ee_text,
            "ee_code_original": EE_FIX.get(EE.get(parent, {}).get("ee_code", ""), ""),
            "text_source": "official", "ee_source": "official",
            "school_desc": None,
        })

# ---- overlay the school's 9-10 sheet ----
off_910 = {r["code"]: r for r in rows if r["band"] == "9-10"}
new_910 = []
for s in school:
    o = off_910.get(s["code"])
    parent = re.sub(r"\.[a-z]$", "", s["code"])
    if o is None:
        # school row with no exact official twin (e.g. school "W.9-10.6" vs official W.9-10.6.a-c)
        twins = [r for r in rows if r["band"] == "9-10" and r["parent"] == parent]
        o = twins[0] if twins else None
    ee_code, ee_text, ee_src = s["ee_code"], s["ee_text"], "school sheet"
    if not ee_code or not ee_text:
        L = s["code"].split(".")[-1] if s["code"] != parent else ""
        letters = [r["code"].split(".")[-1] for r in rows if r["band"] == "9-10" and r["parent"] == parent and r["code"] != parent]
        oc, ot = ee_for(parent, L, len(letters), bool(letters) and L == letters[-1])
        if not ee_code:
            ee_code = oc
        if not ee_text or (ee_text.upper() == "N/A" and ot):
            ee_text, ee_src = ot, "official"
    new_910.append({
        "band": "9-10", "code": s["code"], "code_original": s["code_original"], "parent": parent,
        "strand": s["strand"], "cluster": CLUSTER_FIX.get(s["cluster"], s["cluster"]) or (o["cluster"] if o else ""),
        "text": s["text"], "ee_code": ee_code, "ee_text": ee_text, "ee_code_original": s["ee_code_original"],
        "text_source": "school sheet", "ee_source": ee_src, "school_desc": s["descriptors"],
        "official_text": o["text"] if o else "", "official_code": o["code"] if o else "",
    })
# fill blank school clusters from the row above (merged cells in the sheet)
for i, r in enumerate(new_910):
    if not r["cluster"] and i:
        r["cluster"] = new_910[i - 1]["cluster"]
school_codes = {r["code"] for r in new_910}
missing_official = [r["code"] for r in rows if r["band"] == "9-10" and r["code"] not in school_codes]
rows = [r for r in rows if r["band"] != "9-10"] + new_910
order = {"6": 0, "7": 1, "8": 2, "9-10": 3, "11-12": 4}
pre = {"R": 0, "W": 1, "SL": 2, "L": 3}


def key(r):
    p = r["code"].split(".")
    return (order[r["band"]], pre[p[0]], int(p[2]), p[3] if len(p) > 3 else "")


rows.sort(key=key)
json.dump(rows, open("data/ela/merged_6_12.json", "w"), indent=1, ensure_ascii=False)
from collections import Counter
print(Counter(r["band"] for r in rows))
print("official 9-10 codes not in the school sheet:", missing_official)
print("school 9-10 codes not in official:", [r["code"] for r in new_910 if r["code"] not in off_910])
print("rows without EE:", [r["code"] for r in rows if not r["ee_code"]])
