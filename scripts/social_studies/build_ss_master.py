"""Build data/standards/social_studies.json from the parsed sources + descriptor modules.

Run from anywhere:  python3 -I /home/claude/awsaj-va/scripts/social_studies/build_ss_master.py
"""
import json
import os
import re
import sys

ROOT = "/home/claude/awsaj-va"
SRC = f"{ROOT}/data/source/social_studies"
sys.path.insert(0, f"{ROOT}/scripts/social_studies")

from crosswalk_ss import AERO_TO_WI  # noqa: E402
from desc_aero import D as D_AERO  # noqa: E402
from desc_wi_k5 import D as D_WI_K5  # noqa: E402
from desc_wi_68 import D as D_WI_68  # noqa: E402
from desc_wi_hs import D as D_WI_HS  # noqa: E402
from desc_ee import D as D_EE  # noqa: E402

D_WI = {}
for d in (D_WI_K5, D_WI_68, D_WI_HS):
    D_WI.update(d)

KEYS = ["subject", "framework", "code", "grade", "grade_band", "grade_is_suggested", "division", "course", "strand",
        "cluster", "text", "ee_code", "ee_text", "crosswalk", "crosswalk_is_suggested", "descriptors",
        "descriptor_flag", "descriptors_suggested", "descriptor_source", "power_standard", "source", "text_source"]

HS_COURSE = {"9": "Geography", "10": "World History 10", "11": "Economics", "12": "World History 12"}
HS_PLACEMENT = {"Geog": ["9"], "Hist": ["10", "12"], "Econ": ["11"], "PS": ["12"], "BH": ["12"],
                "Inq": ["9", "10", "11", "12"]}
GRADES = ["K", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]

AERO_SRC = "AERO Social Studies Curriculum Framework: K-5 Learning Progression (school copy, 'Social Studies Standards K-5 Aero .pdf')"
WI_SRC = "Wisconsin Standards for Social Studies (DPI, 2018)"
EE_SRC = "Wisconsin Essential Elements for Social Studies (DPI, adopted 2021, published 2022)"
SCHOOL_SRC = "Awsaj 'Social Studies Standards.xlsx' (K-5 report-card sheet)"

# Text fixes for the AERO PDF where pdftotext/pdfplumber dropped glyphs; each verified against the page image.
AERO_TEXT_FIX = {
    "4.2.e": "Describe the expectations of how to act in one’s own culture and compare this with behavioral expectations of other cultures.",
    "5.5.h": "Examine the difference between “acceptance” and “tolerance”.",
    "8.2.a": "Distinguish between \"tool\" and \"technique.\"",
    "3.5.d": "Describe ways physical and human-made features have changed over time.",
    "7.5.a": "Describe characteristics, locations, uses, and management of renewable and non-renewable resources.",
}
LP_FIX = {"Econ1.b: I ncentives": "Econ1.b: Incentives", "Inq5.a: Civic e ngagement": "Inq5.a: Civic engagement",
          "P S4.a: Argumentation": "PS4.a: Argumentation", "Econ 3.c: Economic fluctuations and business cycles":
          "Econ3.c: Economic fluctuations and business cycles", "Geog2d. Urbanization": "Geog2.d: Urbanization"}

# School descriptor rows whose descriptors clearly describe a different standard (reviewed by hand).
MISMATCHED_SCHOOL = {("K", "1.2.a"), ("K", "6.2.a"), ("K", "6.2.b"), ("K", "7.2.a"), ("K", "8.2.a"),
                     ("2", "1.2.c"), ("2", "2.2.c"), ("2", "3.2.b"), ("2", "3.2.c"), ("2", "3.2.d"), ("2", "3.2.e"),
                     ("2", "3.2.f"), ("3", "3.5.a"), ("3", "5.5.a"), ("3", "6.5.a"), ("4", "2.5.b"), ("5", "2.5.c"),
                     ("5", "3.5.c"), ("5", "4.5.c"), ("5", "6.5.c"), ("5", "7.5.c"), ("5", "8.5.c")}
FLAG_TEXT = "School descriptor may not match this standard"

AERO_STRANDS = {"1": "Time, Continuity, and Change", "2": "Connections and Conflict", "3": "Geography", "4": "Culture",
                "5": "Society and Identity", "6": "Government", "7": "Production, Distribution, and Consumption",
                "8": "Science, Technology, and Society"}


def division(g):
    return "Elementary" if g in GRADES[:6] else ("Middle" if g in ("6", "7", "8") else "High")


def icans(t):
    a, b, c, d = t
    f = lambda s: s if s.startswith("I can") else "I can " + s
    return {"cc_advanced": f(a), "cc_at_target": f(b), "cc_approaching": f(c), "cc_emerging": f(d)}


def wi_grades(code):
    suf = code.split(".")[-1]
    if suf == "e":
        return ["K", "1", "2"], "K-2", False
    if suf == "i":
        return ["3", "4", "5"], "3-5", False
    if suf == "m":
        return ["6", "7", "8"], "6-8", False
    if suf == "h":
        strand = re.match(r"SS\.([A-Za-z]+)", code).group(1)
        return HS_PLACEMENT[strand], "9-12", True
    if "-" in suf:
        a, b = suf.split("-")
        ga = GRADES.index(a)
        gb = GRADES.index(b)
        return GRADES[ga:gb + 1], suf, False
    return [suf], "", False


def band_of(g):
    return "K-2" if g in ("K", "1", "2") else ("3-5" if g in ("3", "4", "5") else None)


def main():
    wi = json.load(open(f"{SRC}/wi_ss_parsed.json"))
    ee = {r["standard"]: r for r in json.load(open(f"{SRC}/wi_ee_ss_parsed.json"))}
    aero = json.load(open(f"{SRC}/aero_ss_parsed.json"))
    school = json.load(open(f"{SRC}/school_ss_parsed.json"))
    aero_by_code = {a["code"]: a for a in aero}
    for c, t in AERO_TEXT_FIX.items():
        aero_by_code[c]["text"] = t

    # ---- WI-SS rows -------------------------------------------------------------------------------
    wi_rows = []
    lp_codes = {}  # LP key (e.g. Hist3.a) -> list of (code, grades)
    for ind in wi["indicators"]:
        code = ind["code"]
        lp = LP_FIX.get(ind["learning_priority"], ind["learning_priority"])
        lp_key = re.match(r"SS\.(\w+\d\.[a-e])", code).group(1)
        grades, band, sugg = wi_grades(code)
        lp_codes.setdefault(lp_key, []).append((code, grades))
        e = ee[ind["standard"]]
        ee_text = e["ee_text"].replace("follow- up", "follow-up")
        if code not in D_WI:
            raise SystemExit(f"missing WI descriptor {code}")
        desc = icans(D_WI[code])
        desc["ee_at_target"] = D_EE[e["ee_code"]]
        cluster = f"{ind['standard']}: {ind['standard_statement']} | {lp}"
        for g in grades:
            wi_rows.append({
                "subject": "Social Studies", "framework": "WI-SS", "code": code, "grade": g, "grade_band": band,
                "grade_is_suggested": sugg, "division": division(g), "course": HS_COURSE.get(g, "") if division(g) == "High" else "",
                "strand": ind["strand"], "cluster": cluster, "text": ind["text"].replace("\u2013", "-").replace("\u2014", ", "), "ee_code": e["ee_code"],
                "ee_text": ee_text, "crosswalk": [], "crosswalk_is_suggested": False, "descriptors": dict(desc),
                "descriptor_flag": "", "descriptors_suggested": None,
                "descriptor_source": "draft", "power_standard": None, "source": f"{WI_SRC}; EE: {EE_SRC}",
                "text_source": "official", "_lp": lp_key, "_page": ind["page"]})

    # ---- AERO-SS rows -----------------------------------------------------------------------------
    aero_rows = {}
    for a in aero:
        g = a["grade"]
        aero_rows[(a["code"], g)] = {
            "subject": "Social Studies", "framework": "AERO-SS", "code": a["code"], "grade": g,
            "grade_band": "K-2" if a["code"][2] == "2" else "3-5", "grade_is_suggested": True, "division": "Elementary", "course": "",
            "strand": f"Standard {a['code'][0]}: {AERO_STRANDS[a['code'][0]]}", "cluster": "",
            "text": aero_by_code[a["code"]]["text"], "ee_code": "", "ee_text": "", "crosswalk": [],
            "crosswalk_is_suggested": False, "descriptors": None, "descriptor_source": "draft", "power_standard": None,
            "source": AERO_SRC, "text_source": "official", "_placement": "AERO Learning Progression"}
    for s in school:
        key = (s["code"], s["grade"])
        if key not in aero_rows:
            base = dict(aero_rows[next(k for k in aero_rows if k[0] == s["code"])])
            base.update({"grade": s["grade"], "descriptors": None, "descriptor_source": "draft",
                         "_placement": "School report-card sheet only"})
            aero_rows[key] = base
        r = aero_rows[key]
        r["source"] = f"{AERO_SRC}; placement and descriptors: {SCHOOL_SRC}" if s["descriptors"] else f"{AERO_SRC}; placement: {SCHOOL_SRC}"
        r["grade_is_suggested"] = False  # grade confirmed by the school's own report-card sheet
        if r["_placement"] == "AERO Learning Progression":
            r["_placement"] = "AERO Learning Progression + school sheet"
        r["_school_printed"] = s["printed"]
        if s["descriptors"]:
            d = dict(s["descriptors"])
            d["ee_at_target"] = ""
            r["descriptors"] = {k: d[k] for k in ["cc_advanced", "cc_at_target", "cc_approaching", "cc_emerging", "ee_at_target"]}
            r["descriptor_source"] = "school"
    for (code, g), r in aero_rows.items():
        r["descriptor_flag"], r["descriptors_suggested"] = "", None
        if (g, code) in MISMATCHED_SCHOOL:
            if r["descriptor_source"] != "school":
                raise SystemExit(f"flag on non-school row {code} {g}")
            sd = icans(D_AERO[code])
            sd["ee_at_target"] = ""
            r["descriptor_flag"], r["descriptors_suggested"] = FLAG_TEXT, sd
        if r["descriptors"] is None:
            if code not in D_AERO:
                raise SystemExit(f"missing AERO descriptor {code}")
            d = icans(D_AERO[code])
            d["ee_at_target"] = ""
            r["descriptors"] = d

    # ---- crosswalk (suggested) --------------------------------------------------------------------
    for (code, g), r in aero_rows.items():
        band = band_of(g)
        cw = []
        for lp in AERO_TO_WI.get(code, []):
            for wcode, wgr in lp_codes.get(lp, []):
                if any(band_of(x) == band for x in wgr) and wcode not in cw:
                    cw.append(wcode)
        r["crosswalk"] = cw
        r["crosswalk_is_suggested"] = bool(cw)
    for r in wi_rows:
        band = band_of(r["grade"])
        if band is None:
            continue
        cw = []
        for (code, g), a in sorted(aero_rows.items(), key=lambda kv: (kv[0][0])):
            if band_of(g) == band and r["_lp"] in AERO_TO_WI.get(code, []) and code not in cw:
                cw.append(code)
        r["crosswalk"] = cw
        r["crosswalk_is_suggested"] = bool(cw)

    # ---- assemble ---------------------------------------------------------------------------------
    def aero_sort(r):
        return (GRADES.index(r["grade"]), [int(x) if x.isdigit() else x for x in r["code"].split(".")])
    strand_order = ["Inquiry Practices and Processes", "Behavioral Sciences", "Economics", "Geography", "History", "Political Science"]
    ordered_wi = sorted(wi_rows, key=lambda r: (GRADES.index(r["grade"]), strand_order.index(r["strand"]), r["_page"], r["code"]))
    ordered_aero = sorted(aero_rows.values(), key=aero_sort)
    meta = {}
    out = []
    for r in ordered_aero + ordered_wi:
        meta[(r["framework"], r["code"], r["grade"])] = {k: r[k] for k in r if k.startswith("_")}
        out.append({k: r[k] for k in KEYS})
    os.makedirs(f"{ROOT}/data/standards", exist_ok=True)
    json.dump(out, open(f"{ROOT}/data/standards/social_studies.json", "w"), indent=1, ensure_ascii=False)
    json.dump({"|".join(k): v for k, v in meta.items()}, open(f"{SRC}/build_meta.json", "w"), indent=1, ensure_ascii=False)
    print("rows:", len(out))


if __name__ == "__main__":
    main()
