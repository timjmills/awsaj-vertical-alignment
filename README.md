# Awsaj Academy K-12 Vertical Alignment

Part 1: collaborative standards-coverage audit (Math, ELA, Science, Social Studies; Wisconsin CC + EE, NGSS/AERO).
Part 2: curriculum analysis of 2025-26 / 2026-27 plans from the school Drive (read-only).

## Layout
- `data/source/`   original documents pulled from the Drive (DPI standards PDFs, school CCEE sheet)
- `data/`          parsed standards (JSON) and generated descriptors
- `scripts/`       Python parsers and builders
- `outputs/`       generated workbooks

## Math pipeline
1. `pdftotext -layout` on the DPI PDFs
2. `python3 scripts/parse_wi_math.py data/source/WI_Math_Standards.txt data/wi_math_6_12.json`
3. `python3 scripts/parse_wi_ee_math.py data/source/WI_EE_Math_2022.txt data/wi_ee_math.json`
4. `python3 scripts/build_math_master.py`
5. `python3 scripts/build_math_xlsx.py "outputs/CCEE Math Standards K-12 (Extended).xlsx"`

See `docs/spec.md` for all design decisions.

## Part 1 site
- `site/` is a static site (no build step): `index.html`, `styles.css`, `app.js`, `config.js`, and `data/*.json`
  (rebuild data with `python3 scripts/build_site_data.py` after changing standards).
- Views: Rate, Heatmap, Gaps & repetition, Grade dashboard, Progressions, Activity. Exports: CSV, PNG, PDF (print).
- Run locally: `cd site && python3 -m http.server 8765`.
- Hosting: GitHub Pages via `.github/workflows/pages.yml`; `.github/workflows/keepalive.yml` stops the free database pausing.
