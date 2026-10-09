"""Parse the AERO Social Studies K-5 Learning Progression (PDF pp. 11-16) into indicator rows.

Usage: python3 -I parse_aero_ss.py <pdf> <out.json>
Grade = the Learning Progression column (K..5) in which the indicator is printed.
"""
import json
import re
import sys

import pdfplumber

CODE = re.compile(r"^[1-8]\.[25]\.[a-j]$")
STD_NAMES = {}


def main(pdf_path, out_path):
    pdf = pdfplumber.open(pdf_path)
    out = []
    for pno in range(11, 17):
        page = pdf.pages[pno - 1]
        words = page.extract_words()
        hdr = [w for w in words if w["text"] in ("K", "1", "2", "3", "4", "5") and w["top"] < 300 and w["x0"] > 90]
        hdr = sorted({w["text"]: w for w in hdr}.values(), key=lambda w: w["x0"])
        centers = [(w["x0"] + w["x1"]) / 2 for w in hdr]
        bounds = [70] + [(centers[i] + centers[i + 1]) / 2 for i in range(5)] + [700]
        grades = [w["text"] for w in hdr]
        # standard banners
        lines = {}
        for w in words:
            lines.setdefault(round(w["top"]), []).append(w)
        banners = []
        for w in words:
            if w["text"] == "Standard" and w["x0"] < 40:
                banners.append(w["top"])
        for bt in banners:
            ws = sorted([w for w in words if bt - 2 <= w["top"] <= bt + 12 and w["x0"] >= 50], key=lambda w: (round(w["top"]), w["x0"]))
            txt = " ".join(w["text"] for w in ws)
            m = re.match(r"(\d)?\s*\((.*?)\)\s*(.*)", txt)
            if m:
                num = m.group(1) or [w["text"] for w in words if abs(w["top"] - bt) < 14 and w["x0"] < 70 and w["text"].isdigit()][0]
                STD_NAMES[num] = (m.group(2), m.group(3))
        body = [w for w in words if w["x0"] >= 70 and w["top"] > hdr[0]["top"] + 30 and not w["text"].startswith("pg")
                and not any(bt - 2 <= w["top"] <= bt + 12 for bt in banners)]
        for ci in range(6):
            cw = sorted([w for w in body if bounds[ci] <= w["x0"] < bounds[ci + 1]], key=lambda w: (round(w["top"]), w["x0"]))
            cur = None
            for w in cw:
                if CODE.match(w["text"]):
                    cur = {"code": w["text"], "grade": grades[ci], "words": [], "page": pno}
                    out.append(cur)
                elif cur is not None:
                    cur["words"].append(w["text"])
    for r in out:
        t = " ".join(r.pop("words"))
        r["text"] = re.sub(r"\s+", " ", t).strip()
        n = r["code"][0]
        r["standard_num"] = n
        r["strand"], r["standard_statement"] = STD_NAMES.get(n, ("", ""))
    out.sort(key=lambda r: (r["code"]))
    json.dump(out, open(out_path, "w"), indent=1, ensure_ascii=False)
    print(len(out), "AERO indicators")
    for k, v in sorted(STD_NAMES.items()):
        print(k, v)
    for r in out:
        print(r["grade"], r["code"], "|", r["text"])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
