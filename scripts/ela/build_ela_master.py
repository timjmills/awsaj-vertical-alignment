"""Build data/standards/ela.json (K-12 Wisconsin ELA + Essential Elements master list).

Inputs (all produced by the other scripts in scripts/ela/):
  data/ela/school_k5.json, data/ela/merged_6_12.json, data/ela/descriptors/*.json
Run from /home/claude/awsaj-va:  python3 -I scripts/ela/build_ela_master.py
"""
import json, re, glob, os

K5 = json.load(open("data/ela/school_k5.json"))
M = json.load(open("data/ela/merged_6_12.json"))
DESC = {}
for f in sorted(glob.glob("data/ela/descriptors/ela_desc_g[0-9]*.json")):
    if "gaps" in f:
        continue
    DESC.update(json.load(open(f)))
GAPS = json.load(open("data/ela/descriptors/ela_desc_g9_10_gaps.json"))
LEVELS = ["cc_advanced", "cc_at_target", "cc_approaching", "cc_emerging", "ee_at_target"]

SRC_K5 = "Awsaj EE ELA New Standards 2025 V1 Complete (school sheet, K-5)"
SRC_910 = "Awsaj G9-10 ELA New Standards 2024 (school sheet)"
SRC_OFF = "Wisconsin Standards for ELA (DPI 2020); Wisconsin Essential Elements for ELA (DPI 2022)"


def tidy(s, official=False):
    s = (s or "").replace("—", ", ").replace("–", "-").replace(" ", " ")
    s = re.sub(r"\s*\(cont\.\)\s*", " ", s)
    if official:
        s = re.sub(r"(\w)- (\w)", r"\1-\2", s)          # line-break artefacts: "letter- sound", "one- on- one"
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r" ,", ",", s)
    return s.strip()


def is_na(t):
    return bool(re.match(r"^\s*([a-z]\.\s*)?(not applicable|n/a)\b", t or "", re.I))


def crosswalk(code, text):
    """WI 2020 Reading standards carry (RL)/(RI)/(RI&RL) tags; list the CCSS-style codes they replace."""
    if not code.startswith("R."):
        return []
    p = code.split(".")
    tags = re.findall(r"\((RI ?& ?RL|RL ?& ?RI|RL|RI)\)", text)
    kinds = set()
    for t in tags:
        if "RL" in t:
            kinds.add("RL")
        if "RI" in t:
            kinds.add("RI")
    return [f"{k}.{p[1]}.{p[2]}" for k in sorted(kinds, key=lambda k: 0 if k == "RL" else 1)]


def division(g):
    return "Elementary" if g in ("K", "1", "2", "3", "4", "5") else "Middle" if g in ("6", "7", "8") else "High"


out = []
# ---------- K-5 (school) ----------
for r in K5:
    d = {k: tidy(r["descriptors"].get(k, "")) for k in LEVELS}
    for extra in ("ee_advanced", "ee_approaching", "ee_emerging"):
        if r["descriptors"].get(extra):
            d[extra] = tidy(r["descriptors"][extra])
    ee_text = tidy(r["ee_text"])
    ee_code, ee_note = r["ee_code"], r["ee_code_original"]
    if ee_code.startswith("EE.E."):          # school typo "E.W.4.3.b"
        ee_note, ee_code = ee_code[3:], "EE." + ee_code[5:]
        ee_text = re.sub(r"^E\.[A-Z]+\.[\dK]+\.\d+(\.[a-z])?\.?\s*", "", ee_text)
    if not ee_code and ee_text:
        # sub-item rows where the school sheet left the EE code cell blank (e.g. SL.3.1.b, RF.3.3.e)
        ee_code = "EE." + r["code"]
        ee_note = "(blank in school sheet; code derived from the CC row)"
        ee_text = re.sub(r"^\.\s*", "", ee_text)
    if not d["ee_at_target"] and is_na(ee_text):
        d["ee_at_target"] = ee_text
    out.append({
        "subject": "ELA", "framework": "WI-CC-ELA", "code": r["code"], "grade": r["grade"], "grade_band": "",
        "grade_is_suggested": False, "division": "Elementary", "course": "", "strand": r["strand"],
        "cluster": r["cluster"], "text": tidy(r["text"]), "ee_code": ee_code, "ee_text": ee_text,
        "crosswalk": crosswalk(r["code"], r["text"]), "descriptors": d, "descriptor_source": "school",
        "power_standard": r["power_standard"], "source": SRC_K5, "text_source": "school sheet",
        "code_original": r["code_original"], "ee_code_original": ee_note,
        "ee_text_source": "school sheet", "descriptor_draft_fields": [],
    })

# ---------- 6-12 ----------
COURSE = {"9": "English Language Arts 9", "10": "English Language Arts 10",
          "11": "English Language Arts 11", "12": "English Language Arts 12"}
for r in M:
    official = r["text_source"] == "official"
    ee_text = tidy(r["ee_text"], official=r["ee_source"] == "official")
    if r["ee_source"] == "school sheet":
        ee_text = re.sub(r"\s*Overarching Statement:.*$", "", ee_text)   # stray banner text pasted into school cells
    if r["band"] == "9-10":
        sd = r["school_desc"]
        d = {k: tidy(sd.get(k, "")) for k in LEVELS}
        for extra in ("ee_advanced", "ee_approaching", "ee_emerging"):
            if sd.get(extra):
                d[extra] = tidy(sd[extra])
        drafted = []
        for k, v in GAPS.get(r["code"], {}).items():
            if not d.get(k):
                d[k] = v
                drafted.append(k)
        dsrc = "school"
    else:
        vals = DESC[r["code"]]
        d = dict(zip(LEVELS, vals))
        drafted = list(LEVELS)
        dsrc = "draft"
    if is_na(ee_text):
        d["ee_at_target"] = ee_text
        if "ee_at_target" in drafted:
            drafted.remove("ee_at_target")
    grades = [r["band"]] if r["band"] in ("6", "7", "8") else r["band"].split("-")
    for g in grades:
        out.append({
            "subject": "ELA", "framework": "WI-CC-ELA", "code": r["code"], "grade": g,
            "grade_band": r["band"] if "-" in r["band"] else "", "grade_is_suggested": "-" in r["band"],
            "division": division(g), "course": COURSE.get(g, ""), "strand": r["strand"], "cluster": r["cluster"],
            "text": tidy(r["text"], official=official), "ee_code": r["ee_code"], "ee_text": ee_text,
            "crosswalk": crosswalk(r["code"], r["text"]), "descriptors": d, "descriptor_source": dsrc,
            "power_standard": None, "source": SRC_910 if r["band"] == "9-10" else SRC_OFF,
            "text_source": r["text_source"], "code_original": r["code_original"],
            "ee_code_original": r["ee_code_original"], "ee_text_source": r["ee_source"],
            "descriptor_draft_fields": drafted,
        })

# =====================================================================================
# Fix round 1 (independent check, 2026-10-09). JSON only; the school's K-5 tabs stay unchanged.
# =====================================================================================
OFF_K5 = {r["code"]: r for r in json.load(open("data/ela/wi_ela_k5.json"))}
EE_K5 = json.load(open("data/ela/wi_ee_ela_k5.json"))["ee"]
EE_612 = json.load(open("data/ela/wi_ee_ela_6_12.json"))["ee"]
FIXLOG = []


def parent_of(code):
    return ".".join(code.split(".")[:3])


def letter_of(code):
    p = code.split(".")
    return p[3] if len(p) > 3 else ""


def ee_clean(t):
    t = tidy(t, official=True)
    t = re.sub(r"\s*Related to (language|Reading Foundational) standards:.*$", "", t)
    # overarching-statement and cluster-header fragments that the column split left at page ends
    t = re.sub(r"\s+(goals\. Be able|K-5 and adapt|and situations in order|Presentation of Knowledge|Comprehension & Collaboration)\b.*$", "", t)
    return t.strip()


def official_ee(code):
    """(ee_code, ee_text) for a code from the WI EE for ELA 2022 document, matched by sub-item letter."""
    e = (EE_K5 if code.split(".")[1] in "K12345" and "-" not in code.split(".")[1] else EE_612).get(parent_of(code))
    if not e:
        return None
    L = letter_of(code)
    subs = dict((a, b) for a, b in e["subs"])
    if L and L in subs:
        sub = ee_clean(subs[L])
        if is_na(sub):
            return f"{e['ee_code']}.{L}", sub
        return f"{e['ee_code']}.{L}", f"{ee_clean(e['stem'])} {L}. {sub}"
    if e["subs"]:
        return e["ee_code"], ee_clean(e["stem"] + " " + " ".join(f"{a}. {b}" for a, b in e["subs"]))
    return e["ee_code"], ee_clean(e["stem"])


BROKEN_EE = re.compile(r"^\s*\.|^\s*I can\b|CC Emerging|EE Emerging|At Target|Approaching:", re.I)
PLACEHOLDER = re.compile(r"^\s*(not applicable|n/a|-|\.)?\s*\.?\s*$", re.I)

# 1. corrupt school EE cells (K-5): replace with the official EE
for r in out:
    if r["division"] != "Elementary":
        continue
    if r["ee_text"] and BROKEN_EE.search(r["ee_text"]) or (r["code"] == "RF.K.2.a"):
        oe = official_ee(r["code"])
        if oe:
            FIXLOG.append(f"{r['code']}: EE replaced from WI EE for ELA 2022 (school cell was '{r['ee_text'][:40]}')")
            r["ee_code_original"] = r["ee_code"] if r["ee_code"] != oe[0] else r["ee_code_original"]
            r["ee_code"], r["ee_text"] = oe
            r["ee_text_source"] = "official"

# 3-5. CC text fixes from the official WI 2020 standards
TEXT_FIX = {
    "W.K.4": OFF_K5["W.K.4"]["stem"],
    "R.1.6": OFF_K5["R.1.6"]["stem"],
    "R.1.7": OFF_K5["R.1.7"]["stem"],
    "RF.1.2.e": OFF_K5["RF.1.2.e"]["stem"] + " e. " + OFF_K5["RF.1.2.e"]["sub"],
}
# L.5.6.a-c: the school cells hold the RF.5.3 / RF.5.4 text by mistake
for c in ("L.5.6.a", "L.5.6.b", "L.5.6.c"):
    if c in OFF_K5:
        TEXT_FIX[c] = OFF_K5[c]["stem"] + f" {c[-1]}. " + OFF_K5[c]["sub"]
for r in out:
    if r["code"] in TEXT_FIX and r["division"] == "Elementary":
        FIXLOG.append(f"{r['code']}: CC text replaced with official WI 2020 text (school cell: '{r['text'][:40]}')")
        r["text"] = tidy(TEXT_FIX[r["code"]], official=True)
        r["text_source"] = "official"
        oe = official_ee(r["code"])
        if r["code"] in ("W.K.4", "RF.1.2.e") and oe:
            r["ee_code"], r["ee_text"], r["ee_text_source"] = oe[0], oe[1], "official"
    if r["code"] == "L.K.6" and r["text"].endswith("(RF.K.3"):
        r["text"] += ")."
        FIXLOG.append("L.K.6: truncated ending '(RF.K.3' completed to '(RF.K.3).' as in WI 2020")

# 3-4. rows whose CC item does not exist in WI 2020 at that grade: drop; attach their EE sub-item to the
#      nearest real CC row of the same standard
DROP = ["L.K.1.b", "L.K.5.e", "L.K.5.f", "RF.2.1", "L.2.5.c", "L.2.5.d", "L.2.5.e", "L.2.5.f", "L.2.6.e",
        "RF.4.3.b", "RF.1.2.f"]
kept = []
for r in out:
    if r["division"] == "Elementary" and r["code"] in DROP:
        prev = [k for k in kept if parent_of(k["code"]) == parent_of(r["code"]) and k["grade"] == r["grade"]]
        e = EE_K5.get(parent_of(r["code"]))
        L = letter_of(r["code"])
        sub = dict((a, b) for a, b in e["subs"]).get(L) if e else None
        if prev and sub and not is_na(sub):
            t = prev[-1]
            t["ee_text"] = t["ee_text"].rstrip() + f" {L}. {ee_clean(sub)}"
            first = t["ee_code"].split(".")[-1]
            base = t["ee_code"] if not re.match(r"^[a-z](-[a-z])?$", first) else t["ee_code"].rsplit(".", 1)[0]
            start = first.split("-")[0] if re.match(r"^[a-z](-[a-z])?$", first) else ""
            t["ee_code"] = f"{base}.{start}-{L}" if start else t["ee_code"]
            FIXLOG.append(f"{r['code']}: row dropped (no such CC item in WI 2020); EE {L} attached to {t['code']}")
        else:
            FIXLOG.append(f"{r['code']}: row dropped (no such CC item in WI 2020)")
        continue
    kept.append(r)
out = kept

# 2. 9-10: lettered rows whose school EE code is the parent EE (or carries several letters): use the
#    official lettered EE sub-item
for r in out:
    if r["grade_band"] == "9-10" and r["code"] in ("L.9-10.1.a", "L.9-10.2.a", "L.9-10.3.a", "L.9-10.6.a"):
        oe = official_ee(r["code"])
        if oe and (r["ee_code"] != oe[0] or r["ee_text"] != oe[1]):
            r["ee_code_original"] = r["ee_code"]
            r["ee_code"], r["ee_text"], r["ee_text_source"] = oe[0], oe[1], "official"
            if r["grade"] == "9":
                FIXLOG.append(f"{r['code']}: EE set to the lettered official item {oe[0]}")

# EE "c. Not applicable" -> "Not applicable" (letter prefix left over from the school cell)
for r in out:
    r["ee_text"] = re.sub(r"^[a-z]\.\s*(?=(not applicable|n/a)\b)", "", r["ee_text"], flags=re.I)

# 8. band standards copied into every grade of the band are not a suggested placement
for r in out:
    if r["grade_band"]:
        r["grade_is_suggested"] = False

# 6. placeholder descriptor levels count as empty, then fill drafts
FILL = {}
if os.path.exists("data/ela/descriptors/ela_desc_fill.json"):
    FILL = json.load(open("data/ela/descriptors/ela_desc_fill.json"))
for r in out:
    d = r["descriptors"]
    ee_na = is_na(r["ee_text"]) or (r["ee_text"] or "").strip().startswith("(Begins")
    for k in LEVELS:
        v = d.get(k, "") or ""
        if k == "ee_at_target" and ee_na:
            if d.get(k) != r["ee_text"]:
                d[k] = r["ee_text"]
            continue
        if PLACEHOLDER.match(v) or is_na(v) or re.match(r"^\S+\.\s*([a-z]\.\s*)?(not applicable|n/a)", v, re.I):
            d[k] = ""
    for k in LEVELS:
        if not d.get(k):
            key = f"{r['code']}|{r['grade_band'] or r['grade']}"
            val = FILL.get(key, {}).get(k)
            if val:
                d[k] = val
                if k not in r["descriptor_draft_fields"]:
                    r["descriptor_draft_fields"].append(k)

# L.9-10.3.a: the school's CC Advanced only repeats the standard
for r in out:
    if r["code"] == "L.9-10.3.a" and r["grade_band"] == "9-10":
        r["descriptors"]["cc_advanced"] = ("I can explain how figurative language and subtle differences in connotation "
                                           "shape tone and meaning, and choose precise words for my own effect.")
        if "cc_advanced" not in r["descriptor_draft_fields"]:
            r["descriptor_draft_fields"].append("cc_advanced")

# 7. school descriptors that describe a different standard: flag + suggested drafts
FLAGS = {}
if os.path.exists("data/ela/descriptors/ela_desc_flags.json"):
    FLAGS = json.load(open("data/ela/descriptors/ela_desc_flags.json"))
for r in out:
    key = f"{r['code']}|{r['grade_band'] or r['grade']}"
    f = FLAGS.get(key)
    r["descriptor_flag"] = "School descriptor may not match this standard" if f else ""
    r["descriptors_suggested"] = dict(zip(LEVELS, f["suggested"])) if f else None
    if f:
        r["descriptor_flag_note"] = f["why"]

json.dump(FIXLOG, open("data/ela/fixlog_round1.json", "w"), indent=1, ensure_ascii=False)
os.makedirs("data/standards", exist_ok=True)
json.dump(out, open("data/standards/ela.json", "w"), indent=1, ensure_ascii=False)
print("rows", len(out))
