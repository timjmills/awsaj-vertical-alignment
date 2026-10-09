import json, random, re, difflib
from collections import Counter
ROOT = '/home/claude/awsaj-va'
rows = json.load(open(ROOT + '/data/standards/science.json'))
KEYS = ['subject', 'framework', 'code', 'grade', 'grade_band', 'grade_is_suggested', 'division', 'course', 'strand', 'cluster',
        'text', 'ee_code', 'ee_text', 'crosswalk', 'descriptors', 'descriptor_source', 'descriptor_flag', 'descriptors_suggested', 'power_standard', 'source', 'text_source']
DK = ['cc_advanced', 'cc_at_target', 'cc_approaching', 'cc_emerging', 'ee_at_target']
errs = []
for r in rows:
    if list(r.keys()) != KEYS: errs.append(('keys', r['code']))
    if sorted(r['descriptors']) != sorted(DK): errs.append(('dkeys', r['code']))
    for k in DK[:4]:
        v = r['descriptors'][k]
        if not v.startswith('I can') and r['descriptor_source'] == 'draft': errs.append(('notIcan', r['framework'], r['code'], k))
        if r['descriptor_source'] == 'draft' and len(v.split()) > 36: errs.append(('long', r['framework'], r['code'], k, len(v.split())))
        if not v: errs.append(('empty', r['framework'], r['code'], k))
    if r['ee_code'] and not r['descriptors']['ee_at_target'].startswith('I can'): errs.append(('ee', r['code']))
    if not r['text']: errs.append(('notext', r['code']))
    if r['descriptor_flag'] and (not r['descriptors_suggested'] or sorted(r['descriptors_suggested']) != sorted(DK)): errs.append(('sug', r['code']))
    if not r['descriptor_flag'] and r['descriptors_suggested'] is not None: errs.append(('sug2', r['code']))
    if r['descriptors_suggested']:
        for k in DK[:4]:
            vv = r['descriptors_suggested'][k]
            if not vv.startswith('I can') or len(vv.split()) > 36: errs.append(('sugtext', r['code'], k))
dup = [k for k, v in Counter((r['framework'], r['code'], r['grade']) for r in rows).items() if v > 1]
blob = json.dumps(rows, ensure_ascii=False)
print('rows', len(rows), 'errors', len(errs), errs[:15])
print('duplicates', dup)
print('em/en dashes', blob.count('—'), blob.count('–'))
GR = ['K', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12']
for fw in ('NGSS', 'AERO-SCI', 'WI-SCI'):
    c = Counter(r['grade'] for r in rows if r['framework'] == fw)
    print(fw, 'rows by grade:', {g: c[g] for g in GR if c[g]}, 'unique codes:', len({r['code'] for r in rows if r['framework'] == fw}))
print('flagged', Counter((r['framework'], r['grade']) for r in rows if r['descriptor_flag']))
print('suggested true', Counter((r['framework'], r['grade_band']) for r in rows if r['grade_is_suggested']), 'false banded', Counter((r['framework'], r['grade_band']) for r in rows if r['grade_band'] and not r['grade_is_suggested']))
print('descriptor_source', Counter((r['framework'], r['descriptor_source']) for r in rows))
print('EE paired rows', Counter(r['framework'] for r in rows if r['ee_code']), 'unique EE', len({r['ee_code'] for r in rows if r['ee_code']}))
# spot-check against sources
SRC = ROOT + '/data/source/science/'
ng = json.load(open(SRC + 'ngss_pes.json'))['pes']; wi = json.load(open(SRC + 'wi_sci.json')); ae = json.load(open(SRC + 'aero_raw.json'))
lay = open(SRC + 'ngss_alldci.txt', encoding='utf-8').read()
wtxt = ' '.join(open(SRC + 'wi_sci_raw.txt', encoding='utf-8').read().split())
random.seed(7)
for r in random.sample(rows, 10):
    t = r['text']
    probe = ' '.join(t.split()[:7])
    if r['framework'] == 'NGSS':
        hay = ' '.join(lay.replace('‐', '-').split())
    elif r['framework'] == 'WI-SCI':
        hay = wtxt
    else:
        hay = ' '.join(' '.join(x['text'] for x in ae[r['code']]).split())
    print('SPOT', r['framework'], r['code'], r['grade'], '| first words found in source PDF/text:', probe in hay, '|', t[:90])
