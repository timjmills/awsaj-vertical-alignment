import json, difflib, re, sys
base = '/home/claude/awsaj-va/data/source/science/'
n = json.load(open(base + 'ngss_pes.json'))['pes']; w = json.load(open(base + 'wi_sci.json'))['pes']; a = json.load(open(base + 'aero_raw.json'))
def nm(s): return re.sub(r'[^a-z0-9 ]', '', s.lower().replace('*', ''))
def r(x, y): return difflib.SequenceMatcher(None, nm(x), nm(y)).ratio()
bad = 0
for c in sorted(n):
    t = n[c]['text']
    r1 = r(t, w[c]['text']) if c in w else None
    r2 = max((r(t, x['text']) for x in a[c]), default=None) if c in a else None
    if (r1 is not None and r1 < float(sys.argv[1])) or (r2 is not None and r2 < float(sys.argv[2])):
        bad += 1; print(c, round(r1 or 0, 2), round(r2 or 0, 2)); print('  N:', t); print('  W:', w.get(c, {}).get('text', '')); print('  A:', (max(a.get(c) or [{'text': ''}], key=lambda x: r(t, x['text'])))['text'])
print('bad', bad)
