"""Parse NGSS PEs (code, text, clarification, DCI components) from NGSS 'DCI Arrangements' (AllDCI.pdf, pdftotext raw)."""
import re, sys, json
raw = open(sys.argv[1], encoding='utf-8').read()
raw = raw.replace('‐', '-').replace('‑', '-').replace('–', '-').replace('—', '-')
pages = raw.split('\f')
PE = re.compile(r'(?m)^((?:K|[1-5]|K-2|3-5|MS|HS)-(?:PS|LS|ESS|ETS)\d-\d+)\.(?:\s|$)')
pes = {}
dci = {}
COMP = re.compile(r'^((?:PS|LS|ESS|ETS)\d\.[A-E]):\s*(.*)$')
ccc_names = ['Patterns', 'Cause and Effect', 'Scale, Proportion', 'Systems and System Models', 'Energy and Matter',
             'Structure and Function', 'Stability and Change', 'Connections to', 'Influence of', 'Interdependence of', '-----']
def compact(s): return re.sub(r'[^A-Z0-9]', '', s.upper())
lay_pages = open(sys.argv[1].replace('_raw', ''), encoding='utf-8').read().replace('\u2010', '-').replace('\u2011', '-').split('\f')
CLAR = re.compile(r'\[\s*C\s*larification\s*S\s*tatement\s*:(.*?)\]', re.S)
ASB = re.compile(r'\[\s*A\s*ssessment\s*B\s*oundary\s*:(.*?)\]', re.S)
for pg, text in enumerate(lay_pages):
    if 'Students who demonstrate understanding can' not in text: continue
    head, _, rest = text.partition('Students who demonstrate understanding can:')
    body = rest.split('The performance expectations above were developed')[0]
    ms = list(re.finditer(r'(?m)^\s*((?:K|[1-5]|K-2|3-5|MS|HS)-(?:PS|LS|ESS|ETS)\d-\d+)\.(?=\s)', body))
    for i, m in enumerate(ms):
        end = ms[i + 1].start() if i + 1 < len(ms) else len(body)
        chunk = ' '.join(body[m.end():end].split())
        stmt = re.split(r'\s?\[\s*(?:C\s*larification|A\s*ssessment)', chunk)[0].strip()
        stmt = re.sub(r'\s+([.,;])', r'\1', stmt)
        clar = CLAR.search(chunk); ab = ASB.search(chunk)
        eng = stmt.endswith('*')
        stmt = stmt.rstrip('*').strip()
        pes.setdefault(m.group(1), {'code': m.group(1), 'text': stmt, 'engineering': eng,
            'clarification': ' '.join(clar.group(1).split()) if clar else '', 'assessment_boundary': ' '.join(ab.group(1).split()) if ab else '',
            'page': pg + 1, 'topic': ' '.join(head.split()[-12:])})
# 4-PS3-4 is split away from its text in raw mode; take it from the -layout text of the same official PDF
lay = open(sys.argv[1].replace('_raw', ''), encoding='utf-8').read()
if '4-PS3-4' not in pes:
    m = re.search(r'4-PS3-4\.\s+(.*?)\n\s*\n', lay, re.S)
    chunk = ' '.join(m.group(1).split())
    stmt = re.split(r'\s\[(?:Clarification|Assessment)', chunk)[0].strip()
    clar = re.search(r'\[Clarification Statement:(.*?)\]', chunk)
    ab = re.search(r'\[Assessment Boundary:(.*?)\]', chunk)
    pes['4-PS3-4'] = {'code': '4-PS3-4', 'text': stmt.rstrip('*').strip(), 'engineering': stmt.endswith('*'),
        'clarification': clar.group(1).strip() if clar else '', 'assessment_boundary': ab.group(1).strip() if ab else '',
        'page': 31, 'topic': '4-PS3 Energy'}
comp_names = {}
for pg in pages:
    for m in re.finditer(r'(?m)^((?:PS|LS|ESS|ETS)\d\.[A-E]):\s*(.+)$', pg.replace('‐', '-')):
        comp_names.setdefault(m.group(1), m.group(2).strip())
import pdfplumber
pdf = pdfplumber.open(sys.argv[3])
for p in pdf.pages:
    ve = [e for e in p.edges if e['orientation'] == 'v' and e['bottom'] - e['top'] > 50]
    L = [e for e in ve if 150 < e['x0'] < 300]
    R = [e for e in ve if 380 < e['x0'] < 520]
    if not L or not R: continue
    lt = max(L, key=lambda e: e['bottom'] - e['top'])
    rt = [e for e in R if e['top'] < lt['bottom'] and e['bottom'] > lt['top']]
    if not rt: continue
    x0 = max(e['x0'] for e in L if abs(e['top'] - lt['top']) < 3) + 1
    x1 = min(e['x0'] for e in rt) - 1
    top, bot = lt['top'], lt['bottom']
    txt = p.crop((x0, top, x1, bot)).extract_text() or ''
    txt = txt.replace('\u2010', '-').replace('\u2011', '-')
    cur = None; buf = []
    def flush():
        if cur:
            j = re.sub(r'\(secondary to[^)]*\)', '', ' '.join(buf), flags=re.S)
            dci.setdefault(cur, set()).update(compact(r) for r in re.findall(r'\(([^()]*)\)', j))
    for ln in txt.split('\n'):
        s2 = ln.strip()
        m = re.match(r'^((?:PS|LS|ESS|ETS)\d\.[A-E]):', s2)
        if m:
            flush(); cur = m.group(1); buf = [s2[m.end():]]; continue
        if s2.startswith(('Connections to', 'Articulation', '----')):
            flush(); cur = None; buf = []; continue
        if cur: buf.append(s2)
    flush()
key = {compact(c): c for c in pes}
pe_dci = {c: [] for c in pes}
key = {compact(c): c for c in pes}
for comp, refs in dci.items():
    for r in refs:
        for part in re.split(r'[,;]', r):
            pass
        if r in key: pe_dci[key[r]].append(comp)
        else:
            # refs like 'KPS21KPS22' when multiple in one paren
            for c in key:
                if c in r and comp not in pe_dci[key[c]]: pe_dci[key[c]].append(comp)
# DCI components read manually from the -layout text of AllDCI where the column crop failed
MANUAL = {'MS-LS1-7': ['LS1.C'], 'HS-PS1-2': ['PS1.A', 'PS1.B'], 'HS-PS1-7': ['PS1.B'], 'HS-LS1-7': ['LS1.C'], '4-PS3-4': ['PS3.B', 'PS3.D']}
for c, v in MANUAL.items():
    if not pe_dci.get(c): pe_dci[c] = v
for c in pe_dci: pe_dci[c] = sorted(set(pe_dci[c]))
for c, v in pes.items(): v['dci'] = pe_dci[c]
json.dump({'pes': pes, 'component_names': comp_names}, open(sys.argv[2], 'w'), indent=1, ensure_ascii=False)
from collections import Counter
cnt = Counter(c.split('-')[0] if not c.startswith(('K-2', '3-5')) else c[:3] for c in pes)
print(len(pes), dict(cnt))
print('no dci:', [c for c in pes if not pe_dci[c]])
