"""Load standards and teams into Supabase through the token-protected load_rows() function.

Usage: SUPABASE_URL=... SUPABASE_ANON_KEY=... LOAD_TOKEN=... python3 load_supabase.py
"""
import json, os, urllib.request

URL, KEY, TOKEN = os.environ["SUPABASE_URL"], os.environ["SUPABASE_ANON_KEY"], os.environ["LOAD_TOKEN"]
COLS = {"subject", "framework", "code", "grade", "grade_band", "grade_is_suggested", "division", "course", "strand",
        "cluster", "text", "ee_code", "ee_text", "crosswalk", "descriptors", "descriptor_source", "descriptor_flag",
        "descriptors_suggested", "power_standard", "source", "text_source"}


def rpc(table, rows):
    body = json.dumps({"p_table": table, "p_rows": rows, "p_token": TOKEN}).encode()
    req = urllib.request.Request(f"{URL}/rest/v1/rpc/load_rows", data=body, method="POST", headers={
        "apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


rows = json.load(open("data/standards/all_standards.json"))
out = []
for r in rows:
    o = {k: r.get(k) for k in COLS}
    o["crosswalk"] = [str(x) for x in (r.get("crosswalk") or [])]
    o["extra"] = {k: v for k, v in r.items() if k not in COLS}
    out.append(o)
total = 0
for i in range(0, len(out), 250):
    total += rpc("standards", out[i:i + 250])
print("standards loaded:", total)

ALL = ["Math", "ELA", "Science", "Social Studies"]
teams = [{"name": "Vertical Alignment Committee", "subjects": ALL, "grades": ["K"] + [str(g) for g in range(1, 13)]}]
for g in ["K", "1", "2", "3", "4", "5"]:
    teams.append({"name": "Kindergarten" if g == "K" else f"Grade {g}", "subjects": ALL, "grades": [g]})
for g in ["6", "7", "8"]:
    for s in ALL:
        teams.append({"name": f"Grade {g} {s}", "subjects": [s], "grades": [g]})
HS = [("Algebra 1", "Math", "9"), ("Geometry", "Math", "10"), ("Algebra 2", "Math", "11"), ("Pre-Calculus", "Math", "12"),
      ("English 9", "ELA", "9"), ("English 10", "ELA", "10"), ("English 11", "ELA", "11"), ("English 12", "ELA", "12"),
      ("Earth Environmental Science", "Science", "9"), ("Physics", "Science", "10"), ("Biology", "Science", "11"),
      ("Chemistry", "Science", "12"), ("Geography", "Social Studies", "9"), ("World History 10", "Social Studies", "10"),
      ("Economics", "Social Studies", "11"), ("World History 12", "Social Studies", "12")]
for n, s, g in HS:
    teams.append({"name": n, "subjects": [s], "grades": [g]})
json.dump(teams, open("data/teams.json", "w"), indent=1)
print("teams loaded:", rpc("teams", teams))
