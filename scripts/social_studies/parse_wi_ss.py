"""Parse the Wisconsin Standards for Social Studies (2018) PDF into performance-indicator rows.

Usage: python3 -I parse_wi_ss.py <pdf> <out.json>
Uses pdfplumber word coordinates: column starts come from the header words
"K-2", "3-5", "6-8", "9-12" on each table page; each SS.* code token starts a cell.
"""
import json
import re
import sys

import pdfplumber

CODE_RE = re.compile(r"^SS\.(Inq|BH|Econ|Geog|Hist|PS)\d\.[a-e]\.(e|i|m|h|K-1|K|1-2|1|2|3-4|3|4-5|4|5)$")
LP_RE = re.compile(r"^(Inq|BH|Econ|Geog|Hist|PS) ?\d\.?[a-e][:.]?$")
STRANDS = {"Inq": "Inquiry Practices and Processes", "BH": "Behavioral Sciences", "Econ": "Economics",
           "Geog": "Geography", "Hist": "History", "PS": "Political Science"}


HYPH_LOG = []


def fix_hyphens(text):
    def rep(m):
        a, b = m.group(1), m.group(2)
        HYPH_LOG.append(m.group(0))
        # suspended hyphens ("open- and closed-ended") and real compounds keep the hyphen
        if b in ("or", "and") or a.lower() in KEEP_HYPHEN_BEFORE:
            return a + "-" + (" " if b in ("or", "and") else "") + b
        return a + b
    return re.sub(r"(\w+)- (\w+)", rep, text)


KEEP_HYPHEN_BEFORE = {"teacher", "student", "place", "self", "non", "cost", "well", "long", "short", "real", "decision",
                      "problem", "fact", "first", "second", "multi", "co", "pre", "cross", "time", "age"}


def join(words):
    lines = []
    cur_top = None
    for w in sorted(words, key=lambda w: (round(w["top"]), w["x0"])):
        if cur_top is None or abs(w["top"] - cur_top) > 3:
            lines.append([w["text"]])
            cur_top = w["top"]
        else:
            lines[-1].append(w["text"])
    text = " ".join(" ".join(l) for l in lines)
    # re-join hyphenated line breaks such as "govern- ment" or "Contextualiza- tion"
    text = fix_hyphens(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def main(pdf_path, out_path):
    pdf = pdfplumber.open(pdf_path)
    rows = []
    standards = {}
    for pno, page in enumerate(pdf.pages, start=1):
        words = page.extract_words()
        heads = {w["text"]: w for w in words if w["text"] in ("K-2", "3-5", "6-8", "9-12")}
        if len(heads) < 4 or not any(CODE_RE.match(w["text"]) for w in words):
            continue
        # standard statement
        std_words = []
        top_header = heads["K-2"]["top"]
        full = " ".join(w["text"] for w in sorted(words, key=lambda w: (round(w["top"]), w["x0"])) if w["top"] < top_header - 15)
        m = re.search(r"Standard:? (SS\.\w+?\d):\s*(.*?)(?: Performance Indicators|$)", full)
        if m:
            sc = m.group(1)
            stmt = m.group(2).replace("(cont’d)", "").replace("(cont'd)", "").strip()
            stmt = re.sub(r"\s+", " ", stmt).strip()
            if sc not in standards:
                standards[sc] = stmt
        bounds = [0, heads["K-2"]["x0"] - 3, heads["3-5"]["x0"] - 3, heads["6-8"]["x0"] - 3, heads["9-12"]["x0"] - 3, 10000]
        footer_top = min([w["top"] for w in words if w["text"] in ("NOTE:",) and w["top"] > top_header] +
                         [w["top"] for w in words if w["text"] == "Wisconsin" and w["top"] > page.height - 60] + [page.height])
        body = [w for w in words if top_header + 5 < w["top"] < footer_top - 1]

        def col(w):
            for i in range(5):
                if bounds[i] <= w["x0"] < bounds[i + 1]:
                    return i
            return 4
        codes = [w for w in body if CODE_RE.match(w["text"])]
        lps = [w for w in body if col(w) == 0 and LP_RE.match(w["text"])]
        row_tops = sorted(set([round(w["top"]) for w in codes] + [round(w["top"]) for w in lps]))
        # merge row tops within 6pt
        merged = []
        for t in row_tops:
            if not merged or t - merged[-1] > 6:
                merged.append(t)
        row_tops = merged + [footer_top]
        for ri in range(len(row_tops) - 1):
            r0, r1 = row_tops[ri] - 4, row_tops[ri + 1] - 4
            rw = [w for w in body if r0 <= w["top"] < r1]
            lp_text = join([w for w in rw if col(w) == 0])
            for c in range(1, 5):
                cw = [w for w in rw if col(w) == c]
                cc = [w for w in cw if CODE_RE.match(w["text"])]
                if not cc:
                    if cw:
                        print("WARN text without code", pno, c, join(cw)[:60], file=sys.stderr)
                    continue
                code = cc[0]["text"]
                text = join([w for w in cw if w is not cc[0]])
                strand_key = re.match(r"SS\.([A-Za-z]+)", code).group(1)
                std = re.match(r"(SS\.[A-Za-z]+\d)", code).group(1)
                rows.append({"code": code, "strand": STRANDS[strand_key], "standard": std,
                             "learning_priority": lp_text, "text": text, "page": pno})
    # attach standard statements
    for r in rows:
        r["standard_statement"] = standards.get(r["standard"], "")
    json.dump({"standards": standards, "indicators": rows}, open(out_path, "w"), indent=1, ensure_ascii=False)
    print(len(rows), "indicators;", len(standards), "standards")
    print("hyphen joins:", sorted(set(HYPH_LOG)), file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
