"""Part 2: find standards in curriculum plan text and count the weeks each appears.

Input : data/part2/manifest.json  -> list of plan sources:
        {"id": "...", "title": "...", "year": "2026-27", "grade": "5", "subjects": ["Math", ...],
         "kind": "weekly" | "unit", "drive_id": "...", "url": "...", "text_file": "data/source/plans/x.txt",
         "carried_forward": false}
Output: site/data/evidence.json
        {"built": date, "sources": [...without text_file...],
         "items": {"FRAMEWORK|CODE|GRADE_TAUGHT": {"weeks": n, "level": 1|2, "match": "cited"|"inferred",
                    "years": [...], "refs": [[source_index, ["Wk 3", ...]], ...]}}}

GRADE_TAUGHT is the grade of the plan, not the grade of the standard, so a Grade 5 plan that cites a
Grade 4 standard records below-grade teaching. Levels follow the shared scale: 1-2 weeks = Introduced,
3+ weeks = Taught in depth. Only CITED codes are handled here; inferred tagging (AI reading of uncoded
plans) writes the same structure with match "inferred" (see infer_plans.py).
2026-27 is primary; a 2025-26 source counts only for weeks the 2026-27 plans do not yet cover.
Usage: python3 scripts/part2/match_plans.py
"""
import json, re, collections, datetime

STD = json.load(open("data/standards/all_standards.json"))
MAN = json.load(open("data/part2/manifest.json"))

# ---- lookups from the standards engine ----
codes = {(r["framework"], r["code"]) for r in STD}
math_by_short = {}            # "5.NBT.1" and "5.NBT.A.1" -> "M.5.NBT.A.1"
for fw, c in codes:
    if fw != "WI-CC-MATH":
        continue
    m = re.match(r"M\.((?:[K0-9]+|N|A|F|G|SP)\.[A-Z]{1,4})\.([A-D])\.(\d+)(\.[a-z])?$", c)
    if m:
        dom, clu, num, sub = m.groups()
        math_by_short.setdefault(f"{dom}.{clu}.{num}{sub or ''}", c)
        math_by_short.setdefault(f"{dom}.{num}{sub or ''}", c)
ee_to_cc = collections.defaultdict(set)   # EE code -> CC codes it pairs with
for r in STD:
    for ee in re.split(r"[;|]", r.get("ee_code") or ""):
        if ee.strip():
            ee_to_cc[(r["framework"], ee.strip())].add(r["code"])
ela_codes = {c for fw, c in codes if fw == "WI-CC-ELA"}
xw = collections.defaultdict(set)         # crosswalk RL.5.1 -> R.5.1 etc.
for r in STD:
    if r["framework"] == "WI-CC-ELA":
        for x in r.get("crosswalk") or []:
            xw[x.split(":")[-1]].add(r["code"])
ngss = {c for fw, c in codes if fw == "NGSS"}
wisci = {c for fw, c in codes if fw == "WI-SCI"}
wiss = {c for fw, c in codes if fw == "WI-SS"}

PATTERNS = [
    ("math_ee", re.compile(r"\bM\.EE\.[K0-9]+\.[A-Z]{1,3}\.\d+[a-z]?\b")),
    ("math", re.compile(r"\b(?:M\.)?(?:K|[1-8])\.(?:CC|OA|NBT|NF|MD|G|RP|NS|EE|F|SP)\.(?:[A-D]\.)?\d+(?:\.?[a-e])?\b")),
    ("ngss", re.compile(r"\b(?:K|[1-5]|MS|HS|K-2|3-5)[- ](?:PS|LS|ESS|ETS)\d-\d\b")),
    ("wisci", re.compile(r"\bSCI\.[A-Z]{2,4}\d?(?:\.[A-Z])?\.[A-Za-z0-9,]+\b")),
    ("wiss", re.compile(r"\bSS\.[A-Za-z]+\d\.[a-z](?:\.[a-z0-9-]+)?\b")),
    ("ela", re.compile(r"\b(?:R|RL|RI|RF|W|SL|L)\.(?:K|[1-9]|1[0-2]|9-10|11-12)\.\d+(?:\.[a-f])?\b")),
]


def resolve(kind, raw):
    """Return a list of (framework, code) for one cited string."""
    s = raw.strip().replace(" ", "-") if kind == "ngss" else raw.strip()
    if kind == "math_ee":
        return [("WI-CC-MATH", c) for c in ee_to_cc.get(("WI-CC-MATH", s), [])]
    if kind == "math":
        s = s[2:] if s.startswith("M.") else s
        s = re.sub(r"\.([a-e])$", r"\1", s) if re.search(r"\d\.[a-e]$", s) else s
        c = math_by_short.get(s) or math_by_short.get(re.sub(r"[a-e]$", "", s))
        return [("WI-CC-MATH", c)] if c else []
    if kind == "ngss":
        return [("NGSS", s)] if s in ngss else []
    if kind == "wisci":
        return [("WI-SCI", s)] if s in wisci else []
    if kind == "wiss":
        return [("WI-SS", s)] if s in wiss else []
    if kind == "ela":
        if s in ela_codes:
            return [("WI-CC-ELA", s)]
        if s in xw:
            return [("WI-CC-ELA", c) for c in xw[s]]
        base = re.sub(r"\.[a-f]$", "", s)
        return [("WI-CC-ELA", base)] if base in ela_codes else []
    return []


def split_weeks(text, kind):
    """Yield (label, chunk). Weekly plans split on 'Year week: N'; unit plans are one chunk per unit."""
    if kind == "weekly":
        parts = re.split(r"(?=Year week:\s*\d+\s*of\s*\d+)", text)
        for p in parts:
            m = re.match(r"Year week:\s*(\d+)", p)
            if m:
                yield f"Wk {int(m.group(1))}", p
    else:
        weeks = re.search(r"Unit Duration:\s*([^\n|]+)", text)
        yield (weeks.group(1).strip() if weeks else "Unit"), text


def unit_weeks(label):
    """Rough week count for a unit-plan duration like '4 weeks', '11/10-29/10', '6/9-17/9'."""
    m = re.search(r"(\d+)\s*weeks?", label, re.I)
    if m:
        return int(m.group(1))
    d = re.findall(r"(\d{1,2})/(\d{1,2})", label)
    if len(d) == 2:
        a = datetime.date(2026, int(d[0][1]), int(d[0][0])); b = datetime.date(2026, int(d[1][1]), int(d[1][0]))
        return max(1, round(((b - a).days + 1) / 7))
    return 2


items = collections.defaultdict(lambda: {"weeks_by_year": collections.defaultdict(set), "refs": collections.defaultdict(list)})
unresolved = collections.Counter()
covered_weeks = collections.defaultdict(set)   # (grade, subject) -> weeks covered by 2026-27 sources
sources = []
for s in sorted(MAN, key=lambda x: x["year"], reverse=True):     # 2026-27 first
    text = open(s["text_file"], encoding="utf-8", errors="ignore").read()
    si = len(sources)
    sources.append({k: v for k, v in s.items() if k != "text_file"})
    for label, chunk in split_weeks(text, s["kind"]):
        found = set()
        for kind, pat in PATTERNS:
            for raw in pat.findall(chunk):
                res = resolve(kind, raw)
                if not res:
                    unresolved[raw] += 1
                found.update(res)
        wk_units = 1 if s["kind"] == "weekly" else unit_weeks(label)
        for fw, code in found:
            key = f"{fw}|{code}|{s['grade']}"
            slot = f"{s['year']}:{label}"
            if s["year"] != "2026-27" and slot.split(":")[1] in covered_weeks[(s["grade"], fw)]:
                continue   # 2025-26 only fills weeks not yet planned this year
            items[key]["weeks_by_year"][s["year"]].update({f"{label}#{i}" for i in range(wk_units)})
            items[key]["refs"][si].append(label)
            if s["year"] == "2026-27":
                covered_weeks[(s["grade"], fw)].add(label)

out = {}
for key, v in items.items():
    weeks = sum(len(w) for w in v["weeks_by_year"].values())
    out[key] = {"weeks": weeks, "level": 2 if weeks >= 3 else 1, "match": "cited",
                "years": sorted(v["weeks_by_year"]), "refs": [[si, sorted(set(l), key=lambda x: int(re.sub(r"\D", "", x) or 0))] for si, l in v["refs"].items()]}
json.dump({"built": datetime.date.today().isoformat(), "rule": "1-2 weeks = Introduced, 3+ weeks = Taught in depth",
           "sources": sources, "items": out}, open("site/data/evidence.json", "w"), ensure_ascii=False, separators=(",", ":"))
by_grade = collections.Counter()
for k in out:
    fw, code, g = k.split("|")
    by_grade[(fw, g)] += 1
print("evidence rows:", len(out), dict(by_grade))
print("unresolved citations:", unresolved.most_common(15))
