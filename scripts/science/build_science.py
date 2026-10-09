"""Build data/standards/science.json (NGSS, WI-SCI, AERO-SCI) for the Awsaj K-12 Vertical Alignment site.

Inputs (all parsed by the other scripts in scripts/science/ into data/source/science/):
  ngss_pes.json     NGSS PEs from NGSS 'DCI Arrangements' (nextgenscience.org AllDCI.pdf)
  wi_sci.json       Wisconsin Standards for Science 2017 (dpi.wi.gov accessible .docx)
  wi_ee_sci.json    Wisconsin Essential Elements for Science (school sheet 'Science Standards CCEE PRIME.xlsx', Sheet2)
  aero_raw.json     AERO Science PK-5 matrix (school PDF)
  school_rows.json  school K-5 report-card sheet 'Science Standards.xlsx'
  data/descriptors/science/*.json  draft descriptors (keys 'NGSS:<code>', 'WI:<code>', 'EE:<ee code>')
Run: python3 -I scripts/science/build_science.py
"""
import json, re, glob, difflib, os
from collections import OrderedDict, defaultdict

ROOT = '/home/claude/awsaj-va'
SRC = ROOT + '/data/source/science/'
ngss_all = json.load(open(SRC + 'ngss_pes.json'))
NG = ngss_all['pes']
COMPNAME = ngss_all['component_names']
WI = json.load(open(SRC + 'wi_sci.json'))
EE = json.load(open(SRC + 'wi_ee_sci.json'))
AERO = json.load(open(SRC + 'aero_raw.json'))
SCHOOL = json.load(open(SRC + 'school_rows.json'))
DESC = {}
for f in sorted(glob.glob(ROOT + '/data/descriptors/science/*.json')):
    DESC.update(json.load(open(f)))

def clean(s):
    s = s.replace('‐', '-').replace('‑', '-').replace(' ', ' ')
    s = s.replace('—', ', ').replace('–', '-')
    s = re.sub(r'(\w)- (\w)', r'\1-\2', s)          # line-break hyphen artifacts: 'evidence- based'
    s = re.sub(r'\s+([.,;:])', r'\1', s)
    return ' '.join(s.split()).strip()

# ---------------------------------------------------------------- names
DOMAIN = {'PS': 'Physical Science', 'LS': 'Life Science', 'ESS': 'Earth and Space Science',
          'ETS': 'Engineering, Technology, and Applications of Science'}
DISC = {'PS1': 'Matter and Its Interactions', 'PS2': 'Motion and Stability: Forces and Interactions', 'PS3': 'Energy',
        'PS4': 'Waves and Their Applications in Technologies for Information Transfer',
        'LS1': 'From Molecules to Organisms: Structures and Processes', 'LS2': 'Ecosystems: Interactions, Energy, and Dynamics',
        'LS3': 'Heredity: Inheritance and Variation of Traits', 'LS4': 'Biological Evolution: Unity and Diversity',
        'ESS1': "Earth's Place in the Universe", 'ESS2': "Earth's Systems", 'ESS3': 'Earth and Human Activity',
        'ETS1': 'Engineering Design', 'ETS2': 'Links Among Engineering, Technology, Science, and Society',
        'ETS3': 'Nature of Science and Engineering'}
COURSE = {'9': 'Earth Environmental Science', '10': 'Physics', '11': 'Biology', '12': 'Chemistry'}

def division(g):
    if g in ('K', '1', '2', '3', '4', '5'): return 'Elementary'
    return 'Middle' if g in ('6', '7', '8') else 'High'

# ---------------------------------------------------------------- MS placement
APPK = {6: 'MS-PS3-3 MS-PS3-4 MS-PS3-5 MS-LS1-1 MS-LS1-2 MS-LS1-3 MS-LS1-4 MS-LS1-5 MS-LS1-8 MS-LS3-2 MS-ESS2-4 MS-ESS2-5 MS-ESS2-6 MS-ESS3-3 MS-ESS3-5',
        7: 'MS-PS1-1 MS-PS1-2 MS-PS1-3 MS-PS1-4 MS-PS1-5 MS-PS1-6 MS-LS1-6 MS-LS1-7 MS-LS2-1 MS-LS2-2 MS-LS2-3 MS-LS2-4 MS-LS2-5 MS-ESS2-1 MS-ESS2-2 MS-ESS2-3 MS-ESS3-1 MS-ESS3-2',
        8: 'MS-PS2-1 MS-PS2-2 MS-PS2-3 MS-PS2-4 MS-PS2-5 MS-PS3-1 MS-PS3-2 MS-PS4-1 MS-PS4-2 MS-PS4-3 MS-LS3-1 MS-LS4-1 MS-LS4-2 MS-LS4-3 MS-LS4-4 MS-LS4-5 MS-LS4-6 MS-ESS1-1 MS-ESS1-2 MS-ESS1-3 MS-ESS1-4 MS-ESS3-4'}
SCOPE_2025 = {6: 'MS-PS1-1 MS-PS1-4', 7: 'MS-LS1-6 MS-LS2-3 MS-LS2-4 MS-ESS2-2',
              8: 'MS-ESS1-4 MS-LS4-1 MS-LS4-4 MS-LS4-6 MS-PS2-1 MS-PS2-2 MS-PS2-4 MS-PS3-1'}
UNITS_2026 = {6: 'MS-ESS1-1 MS-ESS2-5 MS-ESS2-6 MS-ESS3-2 MS-ESS2-1 MS-ESS2-4 MS-ESS3-1',
              8: 'MS-PS1-2 MS-PS1-5 MS-PS2-1 MS-PS2-2 MS-PS3-2'}
MS_GRADE, MS_BASIS = {}, {}
for src, label in ((APPK, 'NGSS Appendix K Table 3A (California integrated model)'),
                   (SCOPE_2025, "Awsaj Secondary Science Scope and Sequence (2025)"),
                   (UNITS_2026, 'Awsaj 2026-27 unit plans')):
    for g, codes in src.items():
        for c in codes.split():
            MS_GRADE[c] = str(g); MS_BASIS[c] = label

def hs_grades(code):
    if code.startswith('HS-ETS'): return ['9', '10', '11', '12']
    if code.startswith('HS-ESS'): return ['9']
    if code.startswith('HS-LS'): return ['11']
    if code.startswith('HS-PS1') or code == 'HS-PS3-4': return ['12']
    return ['10']

def pe_grades(code):
    """-> list of (grade, grade_band, suggested, course)"""
    if code.startswith('K-2-'): return [(g, 'K-2', True, '') for g in ('K', '1', '2')]
    if code.startswith('3-5-'): return [(g, '3-5', True, '') for g in ('3', '4', '5')]
    if code.startswith('MS-'):
        gs = ['6', '7', '8'] if code.startswith('MS-ETS') else [MS_GRADE[code]]
        return [(g, '6-8', True, '') for g in gs]
    if code.startswith('HS-'):
        return [(g, '9-12', True, COURSE[g]) for g in hs_grades(code)]
    return [(code.split('-')[0], '', False, '')]

def disc_of(code):  # 'MS-PS1-1' -> 'PS1'
    return re.search(r'(PS\d|LS\d|ESS\d|ETS\d)', code).group(1)

# ---------------------------------------------------------------- WI codes
WIC = WI['codes']
def wi_level(code): return code.rsplit('.', 1)[1]
def wi_comp(code): return code.split('.', 1)[1].rsplit('.', 1)[0]
def ngss_level(code, grade):
    if code.startswith('MS-'): return ['m']
    if code.startswith('HS-'): return ['h']
    if code.startswith('K-2-'): return ['K-2', grade]
    if code.startswith('3-5-'): return ['3-5', grade]
    return [grade]

def wi_key(comp, lv):
    k = f'SCI.{comp}.{lv}'
    if k in WIC: return k
    for kk in WIC:   # comma-coded grade lists such as SCI.ESS3.B.3,4
        if kk.startswith(f'SCI.{comp}.') and ',' in kk and lv in wi_level(kk).split(','): return kk
    return None

def ngss_to_wi(code, grade):
    out = []
    for comp in NG[code]['dci']:
        for lv in ngss_level(code, grade):
            k = wi_key(comp, lv)
            if k and k not in out: out.append(k)
        # K-5 PEs whose DCI component WI places in a different K-5 grade of the same band: link to that code too
        if not code.startswith(('MS-', 'HS-')) and not any(o.startswith(f'SCI.{comp}.') for o in out):
            band = ['K', '1', '2'] if grade in ('K', '1', '2') else ['3', '4', '5']
            for lv in band:
                k = wi_key(comp, lv)
                if k and k not in out: out.append(k)
    if not out and not code.startswith(('MS-', 'HS-')):   # fall back: WI codes of the same disciplinary standard at that grade
        d = disc_of(code)
        out = [k for k in WIC if k.startswith(f'SCI.{d}.') and grade in wi_level(k).split(',')]
    return out

# ---------------------------------------------------------------- EE
EE_BY_PE = {v['pe']: v for v in EE.values()}
def ee_fields(code):
    e = EE_BY_PE.get(code)
    if not e: return '', ''
    txt = f"Target Level: {clean(e['target'])} Precursor Level: {clean(e['precursor'])} Initial Level: {clean(e['initial'])}"
    return e['ee_code'], txt

# ---------------------------------------------------------------- school descriptors
SCH = {(r['grade'], r['code']): r for r in SCHOOL}
SCH_BY_CODE = defaultdict(list)
for r in SCHOOL: SCH_BY_CODE[r['code']].append(r)
def school_desc(code, grade):
    r = SCH.get((grade, code))
    if r is None and SCH_BY_CODE.get(code):   # banded ETS PEs: reuse the school descriptors written for that PE
        r = SCH_BY_CODE[code][0]
    if r is None or r['n_levels'] < 4: return None, None
    return {k: clean(r['levels'][k]) for k in ('cc_advanced', 'cc_at_target', 'cc_approaching', 'cc_emerging')}, r

# School descriptors judged (row-by-row review of all 81 school rows) to describe a different standard
SCHOOL_MISMATCH = set('K-PS2-2 K-PS3-1 K-ESS2-2 K-2-ETS1-2 K-2-ETS1-3 1-LS1-2 1-PS4-1 1-PS4-2 1-PS4-3 1-PS4-4 1-ESS1-2 '
                      '2-LS2-1 2-LS2-2 2-LS4-1 2-PS1-1 2-PS1-2 2-PS1-3 2-PS1-4 2-ESS1-1 2-ESS2-1 2-ESS2-2 2-ESS2-3 3-PS2-4'.split())
FLAG_TEXT = 'School descriptor may not match this standard'
def flag_fields(code, src_flag, ee_at):
    if src_flag == 'school' and code in SCHOOL_MISMATCH:
        d = DESC.get('SUG:' + code)
        if d is None:
            missing['SUG:' + code] = {'text': NG[code]['text'], 'extra': ''}
            return FLAG_TEXT, None
        sug = {k: d[k] for k in ('cc_advanced', 'cc_at_target', 'cc_approaching', 'cc_emerging')}
        sug['ee_at_target'] = ee_at
        return FLAG_TEXT, sug
    return '', None

missing = OrderedDict()
def draft(key, text, extra=''):
    d = DESC.get(key)
    if d is None:
        missing[key] = {'text': text, 'extra': extra}
        return {'cc_advanced': '', 'cc_at_target': '', 'cc_approaching': '', 'cc_emerging': ''}
    return {k: d[k] for k in ('cc_advanced', 'cc_at_target', 'cc_approaching', 'cc_emerging')}

def ee_at_target(ee_code, ee_text):
    if not ee_code: return ''
    d = DESC.get('EE:' + ee_code)
    if d is None:
        missing['EE:' + ee_code] = {'text': ee_text, 'extra': ''}
        return ''
    return d['ee_at_target']

def row(**kw):
    base = OrderedDict([('subject', 'Science'), ('framework', ''), ('code', ''), ('grade', ''), ('grade_band', ''),
        ('grade_is_suggested', False), ('division', ''), ('course', ''), ('strand', ''), ('cluster', ''), ('text', ''),
        ('ee_code', ''), ('ee_text', ''), ('crosswalk', []), ('descriptors', {}), ('descriptor_source', 'draft'), ('descriptor_flag', ''), ('descriptors_suggested', None),
        ('power_standard', None), ('source', ''), ('text_source', 'official')])
    base.update(kw)
    return base

rows = []
NGSS_SRC = 'NGSS DCI Arrangements (Achieve 2013, nextgenscience.org AllDCI.pdf)'
AERO_SRC = 'AERO Science PK-5 Framework Progressions Matrix (school copy)'
WI_SRC = 'Wisconsin Standards for Science 2017 (dpi.wi.gov)'
order_key = lambda c: (['K', '1', '2', 'K-2', '3', '4', '5', '3-5', 'MS', 'HS'].index(c.rsplit('-', 2)[0]),
                       ['PS', 'LS', 'ESS', 'ETS'].index(re.match(r'[A-Z]+', disc_of(c)).group(0)), disc_of(c), int(c.rsplit('-', 1)[1]))
school_mismatch = []
for code in sorted(NG, key=order_key):
    pe = NG[code]; d = disc_of(code)
    ee_code, ee_txt = ee_fields(code)
    for g, band, sugg, course in pe_grades(code):
        wi = ngss_to_wi(code, g)
        xw = [f'WI-SCI:{w}' for w in wi]
        is_k5 = not code.startswith(('MS-', 'HS-'))
        if is_k5: xw = [f'AERO-SCI:{code}'] + xw
        desc, srow = school_desc(code, g) if is_k5 else (None, None)
        src_flag = 'school' if desc else 'draft'
        if not desc: desc = draft('NGSS:' + code, pe['text'], pe.get('clarification', ''))
        desc['ee_at_target'] = ee_at_target(ee_code, ee_txt)
        cluster = f"{d} {DISC[d]} ({', '.join(c + ' ' + COMPNAME.get(c, '') for c in pe['dci'])})".replace(' )', ')')
        fl, sug_d = flag_fields(code, src_flag, desc['ee_at_target'])
        rows.append(row(framework='NGSS', code=code, grade=g, grade_band=band, grade_is_suggested=sugg, division=division(g),
                        course=course, strand=DOMAIN[re.match(r'[A-Z]+', d).group(0)], cluster=clean(cluster), text=clean(pe['text']),
                        ee_code=ee_code, ee_text=ee_txt, crosswalk=xw, descriptors=desc, descriptor_source=src_flag,
                        descriptor_flag=fl, descriptors_suggested=sug_d,
                        source=NGSS_SRC))

# ---------------------------------------------------------------- AERO-SCI (K-5)
def nm(s): return re.sub(r'[^a-z0-9 ]', '', s.lower())
aero_variants = []
for code in sorted([c for c in NG if not c.startswith(('MS-', 'HS-'))], key=order_key):
    cands = AERO.get(code, [])
    best = max(cands, key=lambda x: difflib.SequenceMatcher(None, nm(x['text']), nm(NG[code]['text'])).ratio())
    txt = clean(best['text']).rstrip('*').strip()
    txt = re.sub(r'^-(?=[a-z])', 'R', txt)
    ratio = difflib.SequenceMatcher(None, nm(txt), nm(NG[code]['text'])).ratio()
    if ratio < 0.99: aero_variants.append((code, round(ratio, 2), txt, NG[code]['text']))
    d = disc_of(code)
    ee_code, ee_txt = ee_fields(code)
    for g, band, sugg, course in pe_grades(code):
        wi = ngss_to_wi(code, g)
        desc, srow = school_desc(code, g)
        src_flag = 'school' if desc else 'draft'
        if not desc: desc = draft('NGSS:' + code, NG[code]['text'])
        desc['ee_at_target'] = ee_at_target(ee_code, ee_txt)
        fl, sug_d = flag_fields(code, src_flag, desc['ee_at_target'])
        rows.append(row(framework='AERO-SCI', code=code, grade=g, grade_band=band, grade_is_suggested=sugg, division=division(g),
                        strand=DOMAIN[re.match(r'[A-Z]+', d).group(0)], cluster=f'{d} {DISC[d]}', text=txt,
                        ee_code=ee_code, ee_text=ee_txt, crosswalk=[f'NGSS:{code}'] + [f'WI-SCI:{w}' for w in wi],
                        descriptors=desc, descriptor_source=src_flag, descriptor_flag=fl, descriptors_suggested=sug_d, source=AERO_SRC))

# ---------------------------------------------------------------- WI-SCI
# reverse map WI code -> NGSS PEs (and their grades)
wi_links = defaultdict(list)
for r in rows:
    if r['framework'] != 'NGSS': continue
    for x in r['crosswalk']:
        if x.startswith('WI-SCI:'): wi_links[x[7:]].append((r['code'], r['grade']))
def wi_strand(code):
    comp = wi_comp(code)
    if comp.startswith('CC'): return 'Crosscutting Concepts'
    if comp.startswith('SEP'): return 'Science and Engineering Practices'
    return DOMAIN[re.match(r'[A-Z]+', comp).group(0)]
for code, v in sorted(WIC.items(), key=lambda kv: kv[1]['order']):
    lv = wi_level(code); comp = wi_comp(code)
    links = wi_links.get(code, [])
    pe_codes = list(OrderedDict.fromkeys(c for c, g in links))
    if all(x in ('K', '1', '2', '3', '4', '5') for x in lv.split(',')): places = [(x, '', False, '') for x in lv.split(',')]
    elif lv == 'K-2': places = [(g, 'K-2', True, '') for g in ('K', '1', '2')]
    elif lv == '3-5': places = [(g, '3-5', True, '') for g in ('3', '4', '5')]
    elif lv == 'm':
        gs = sorted({g for c, g in links}, key=int) if comp[:2] in ('PS', 'LS', 'ES') else []
        places = [(g, '6-8', True, '') for g in (gs or ['6', '7', '8'])]
    else:
        gs = sorted({g for c, g in links}, key=int) if comp[:2] in ('PS', 'LS', 'ES') else []
        if not gs and comp[:2] in ('PS', 'LS', 'ES'):
            gs = hs_grades('HS-' + comp.split('.')[0] + '-0')
        places = [(g, '9-12', True, COURSE[g]) for g in (gs or ['9', '10', '11', '12'])]
    label = clean(v['label'])
    label = re.sub(r'^SCI\.', '', label)
    for g, band, sugg, course in places:
        xw = [f'NGSS:{c}' for c in pe_codes if any(gg == g for cc, gg in links if cc == c)] or [f'NGSS:{c}' for c in pe_codes]
        if g in ('K', '1', '2', '3', '4', '5'): xw += [x.replace('NGSS:', 'AERO-SCI:') for x in xw if x.startswith('NGSS:')]
        rows.append(row(framework='WI-SCI', code=code, grade=g, grade_band=band, grade_is_suggested=sugg, division=division(g),
                        course=course, strand=wi_strand(code), cluster=label, text=clean(v['text']),
                        crosswalk=xw, descriptors=dict(draft('WI:' + code, clean(v['text']), label), ee_at_target=''),
                        source=WI_SRC + (f'; printed in source as {v["printed_code"]}' if v.get('printed_code') and v['printed_code'] != code else '')))
# WI-only ETS3 sample performance indicators (Wisconsin additions to the NGSS PEs)
for code, v in WI['pes'].items():
    if code in NG: continue
    pre = code.split('-')[0]
    if pre == 'MS': places = [(g, '6-8', True, '') for g in ('6', '7', '8')]
    elif pre == 'HS': places = [(g, '9-12', True, COURSE[g]) for g in ('9', '10', '11', '12')]
    else: places = [(pre, '', False, '')]
    ref = re.search(r'\(((?:SEP\.?\d|(?:LS|PS|ESS|ETS)\d)\.?[A-E]?\.?(?:K|[1-5]|m|h))\)\s*\.?$', v['text'])
    wcodes = []
    if ref:
        r0 = ref.group(1).replace('SEP.', 'SEP')
        cand = 'SCI.' + r0
        if cand in WIC: wcodes.append(cand)
        else:
            m0 = re.match(r'(SEP\d)\.(h|m)', r0)
            wcodes += [k for k in WIC if m0 and k.startswith(f'SCI.{m0.group(1)}.') and k.endswith('.' + m0.group(2))]
    for g, band, sugg, course in places:
        rows.append(row(framework='WI-SCI', code=code, grade=g, grade_band=band, grade_is_suggested=sugg, division=division(g),
                        course=course, strand=DOMAIN['ETS'], cluster='ETS3 Nature of Science and Engineering (Wisconsin sample performance indicator)',
                        text=clean(v['text']), crosswalk=[f'WI-SCI:{w}' for w in wcodes],
                        descriptors=dict(draft('WI:' + code, clean(v['text'])), ee_at_target=''), source=WI_SRC))

# grade_is_suggested rule: true only when one grade/course was chosen for a banded standard;
# a banded standard copied into every grade of its band keeps grade_band and gets false. MS/HS bands labelled 'MS'/'HS'.
BAND_GRADES = {'K-2': {'K', '1', '2'}, '3-5': {'3', '4', '5'}, 'MS': {'6', '7', '8'}, 'HS': {'9', '10', '11', '12'}}
for r in rows:
    if r['grade_band'] == '6-8': r['grade_band'] = 'MS'
    if r['grade_band'] == '9-12': r['grade_band'] = 'HS'
placed = defaultdict(set)
for r in rows: placed[(r['framework'], r['code'])].add(r['grade'])
for r in rows:
    b = r['grade_band']
    if not b: r['grade_is_suggested'] = False; continue
    r['grade_is_suggested'] = placed[(r['framework'], r['code'])] != BAND_GRADES[b]

os.makedirs(ROOT + '/data/standards', exist_ok=True)
json.dump(rows, open(ROOT + '/data/standards/science.json', 'w'), indent=1, ensure_ascii=False)
json.dump(missing, open(SRC + 'descriptors_needed.json', 'w'), indent=1, ensure_ascii=False)
json.dump({'aero_variants': aero_variants, 'ms_basis': MS_BASIS, 'ms_grade': MS_GRADE}, open(SRC + 'build_notes.json', 'w'), indent=1, ensure_ascii=False)
from collections import Counter
print('rows', len(rows)); print(Counter(r['framework'] for r in rows)); print('missing descriptors', len(missing))
print(Counter(k.split(':')[0] for k in missing))
