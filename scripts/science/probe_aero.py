import pdfplumber, sys, re
pdf = pdfplumber.open(sys.argv[1])
for pno in [4,5,8,13,31,32,33,34,35]:
    if pno >= len(pdf.pages): continue
    p = pdf.pages[pno]
    words = p.extract_words(keep_blank_chars=False, use_text_flow=False)
    hdr = [w for w in words if w['text'] in ('PreK','K','1','2','3','4','5','MS','HS') and w['top'] < 80]
    print(pno+1, p.width, [(w['text'], round(w['x0']), round(w['top'])) for w in hdr])
    codes = [w for w in words if re.match(r'^(PreK|K|[1-5]|3.5|K.2)[‐\-‐]', w['text'])]
    print('   codes', [(w['text'], round(w['x0']), round(w['top'])) for w in codes][:30])
