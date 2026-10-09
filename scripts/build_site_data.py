"""Write compact per-subject standards files for the static site (site/data/*.json).

index_<subject>.json: one entry per unique (framework, code) with the grades it is placed in.
detail_<subject>.json: full text, EE and descriptors keyed by "framework|code|grade".
Usage: python3 scripts/build_site_data.py
"""
import json, collections
rows = json.load(open("data/standards/all_standards.json"))
GORDER = ["K"] + [str(g) for g in range(1, 13)]
slug = {"Math": "math", "ELA": "ela", "Science": "science", "Social Studies": "social_studies"}
by_sub = collections.defaultdict(list)
for r in rows:
    by_sub[r["subject"]].append(r)
meta = {"subjects": [], "grades": GORDER, "built": __import__("datetime").date.today().isoformat()}
for sub, rs in by_sub.items():
    idx = {}
    detail = {}
    for r in rs:
        k = r["framework"] + "|" + r["code"]
        e = idx.setdefault(k, {"f": r["framework"], "c": r["code"], "s": r["strand"], "cl": r["cluster"],
                               "t": r["text"][:220], "ee": r["ee_code"], "pl": [], "sg": False, "band": r["grade_band"],
                               "div": [], "crs": []})
        if r["grade"] not in e["pl"]:
            e["pl"].append(r["grade"])
        e["sg"] = e["sg"] or r["grade_is_suggested"]
        if r["division"] not in e["div"]:
            e["div"].append(r["division"])
        if r["course"] and r["course"] not in e["crs"]:
            e["crs"].append(r["course"])
        detail[k + "|" + r["grade"]] = {k2: r[k2] for k2 in ("text", "ee_code", "ee_text", "descriptors", "descriptor_source",
                                                           "descriptor_flag", "descriptors_suggested", "crosswalk", "source",
                                                           "grade_band", "grade_is_suggested", "course", "cluster")}
    for e in idx.values():
        e["pl"].sort(key=GORDER.index)
    items = sorted(idx.values(), key=lambda e: (e["f"], GORDER.index(e["pl"][0]), e["s"], e["c"]))
    json.dump(items, open(f"site/data/index_{slug[sub]}.json", "w"), ensure_ascii=False, separators=(",", ":"))
    json.dump(detail, open(f"site/data/detail_{slug[sub]}.json", "w"), ensure_ascii=False, separators=(",", ":"))
    meta["subjects"].append({"name": sub, "slug": slug[sub], "frameworks": sorted({e["f"] for e in items}), "count": len(items)})
meta["subjects"].sort(key=lambda s: ["Math", "ELA", "Science", "Social Studies"].index(s["name"]))
meta["teams"] = json.load(open("data/teams.json"))
json.dump(meta, open("site/data/meta.json", "w"), indent=1, ensure_ascii=False)
print(json.dumps(meta["subjects"], indent=0))
