"""Extract K-5 AERO Science PEs (code + text) from the AERO Science PK-5 matrix PDF using word positions."""
import pdfplumber, sys, re, json
CODE = re.compile(r'^(PreK|K|[1-5]|K[‐\-]2|3[‐\-]5)[‐\-](PS|LS|ESS|ETS)\d[‐\-]\d+[\.,]?$')
HDR = {'PreK','K','1','2','3','4','5','MS','HS'}
def norm(s): return s.replace('‐','-').replace('‑','-')
pdf = pdfplumber.open(sys.argv[1])
out = {}
for pno, p in enumerate(pdf.pages):
    words = p.extract_words()
    merged = []
    for w in words:
        if merged:
            pw = merged[-1]
            same = abs(pw['top'] - w['top']) < 2 and 0 <= w['x0'] - pw['x1'] < 8
            if same and ((re.match(r'^K[\u2010\-]2$', pw['text']) and re.match(r'^ETS1[\u2010\-]\d\.?$', w['text'])) or
                         (re.search(r'ETS1[\u2010\-]$', pw['text']) and re.match(r'^\d$', w['text']))):
                sep = '-' if pw['text'].startswith('K') and not pw['text'].endswith(('-', '\u2010')) else ''
                merged[-1] = dict(pw, text=pw['text'] + sep + w['text'], x1=w['x1']); continue
        merged.append(w)
    words = merged
    # header row: line containing 'MS' and 'HS' near top
    hdr = [w for w in words if w['text'] in HDR and w['top'] < 90]
    colx = sorted({round(w['x0']) for w in hdr})
    codes = [w for w in words if CODE.match(w['text'])]
    if not codes: continue
    other = [w for w in words if re.match(r'^(MS|HS)[\u2010\-‐](PS|LS|ESS|ETS)', w['text'])]
    allx = sorted(set([round(c['x0']) for c in codes] + [round(o['x0']) for o in other]))
    for c in codes:
        x0 = c['x0']
        right = [x for x in allx if x > x0 + 15]
        xmax = right[0] - 2 if right else x0 + 120
        below = [d for d in codes if abs(d['x0'] - x0) < 15 and d['top'] > c['top'] + 2]
        ymax = min([d['top'] for d in below], default=p.height - 30)
        ws = [w for w in words if w['top'] > c['top'] + 2 and w['top'] < ymax - 1 and w['x0'] >= x0 - 4 and w['x0'] < xmax and w is not c]
        ws.sort(key=lambda w: (round(w['top']), w['x0']))
        txt = ' '.join(w['text'] for w in ws)
        code = norm(c['text']).rstrip('.,')
        out.setdefault(code, []).append({'page': pno + 1, 'text': norm(txt)})
json.dump(out, open(sys.argv[2], 'w'), indent=1, ensure_ascii=False)
print(len(out), sorted(out))
