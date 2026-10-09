"""Parse Wisconsin Essential Elements for Science (Sheet2 of 'Science Standards CCEE PRIME.xlsx')."""
import openpyxl, re, sys, json
ws = openpyxl.load_workbook(sys.argv[1])['Sheet2']
vals = [str(r[0]).strip() for r in ws.iter_rows(values_only=True) if r[0] is not None]
ees = {}; dups = []
cur = {}; section = ''
started = False
for v in vals:
    t = ' '.join(v.split())
    if t.startswith('Essential Elements for'): started = True
    if not started: continue
    if t.startswith('Essential Elements for'): section = t.replace('Essential Elements for ', '').split(' ', 1)[0]; continue
    if t.startswith('Domain:'): cur = {'section_header': section, 'domain': t.split(':', 1)[1].strip()}
    elif t.startswith('Core Idea:'): cur['core_idea'] = t.split(':', 1)[1].strip()
    elif t.startswith('Topic:'): cur['topic'] = t.split(':', 1)[1].strip()
    elif t.startswith('State Standard for General Education:'):
        s = t.split(':', 1)[1].strip(); m = re.match(r'((?:K|\d|MS|HS)-[A-Z]+\d-\d+)\s*[:.]?\s*(.*)', s)
        if not m: print('BAD', s[:80]); continue
        cur['pe'] = m.group(1); cur['pe_text'] = m.group(2)
    elif t.startswith('Essential Element:'):
        m = re.match(r'Essential Element:\s*(EE\.\S+)\s*Target Level:\s*(.*)', t); cur['ee_code'] = m.group(1); cur['target'] = m.group(2)
    elif t.startswith('Precursor Level:'): cur['precursor'] = t.split(':', 1)[1].strip()
    elif t.startswith('Initial Level:'):
        cur['initial'] = t.split(':', 1)[1].strip()
        k = cur['ee_code']
        if k in ees:
            same = all(ees[k][f] == cur[f] for f in ('target', 'precursor', 'initial'))
            dups.append((k, same))
        else: ees[k] = dict(cur)
json.dump(ees, open(sys.argv[2], 'w'), indent=1, ensure_ascii=False)
print(len(ees), 'dups', dups)
print([k for k, v in ees.items() if v['ee_code'] != 'EE.' + v['pe']])
