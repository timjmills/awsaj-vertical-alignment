"""Parse the AERO Science PK-5 Google Doc (HTML export of the same AERO matrix) table cells into code -> text."""
import re, sys, json, html
from html.parser import HTMLParser
class P(HTMLParser):
    def __init__(s):
        super().__init__(); s.tables = []; s.cell = None; s.row = None
    def handle_starttag(s, t, a):
        if t == 'table': s.tables.append([])
        elif t == 'tr': s.row = []; s.tables[-1].append(s.row)
        elif t == 'td': s.cell = []
        elif t in ('br', 'p') and s.cell is not None: s.cell.append('\n')
    def handle_endtag(s, t):
        if t == 'td' and s.cell is not None: s.row.append(''.join(s.cell)); s.cell = None
    def handle_data(s, d):
        if s.cell is not None: s.cell.append(d)
p = P(); p.feed(open(sys.argv[1], encoding='utf-8').read())
CODE = re.compile(r'((?:PreK|K|[1-5]|K-2|3-5|MS|HS)-(?:PS|LS|ESS|ETS)\d-\d+)[\.,]?')
out = {}
hdrs = []
for ti, t in enumerate(p.tables):
    for r in t:
        cells = [' '.join(html.unescape(c).replace('‐', '-').replace('‑', '-').split()) for c in r]
        if any(c in ('PreK', 'MS', 'HS') for c in cells): hdrs.append(cells); continue
        for ci, c in enumerate(cells):
            ms = list(CODE.finditer(c))
            for i, m in enumerate(ms):
                end = ms[i + 1].start() if i + 1 < len(ms) else len(c)
                txt = c[m.end():end].strip(' ,.')
                out.setdefault(m.group(1), []).append({'table': ti, 'col': ci, 'text': txt})
json.dump(out, open(sys.argv[2], 'w'), indent=1, ensure_ascii=False)
k5 = [c for c in out if not c.startswith(('PreK', 'MS', 'HS'))]
print(len(out), len(k5)); print(hdrs[:3])
