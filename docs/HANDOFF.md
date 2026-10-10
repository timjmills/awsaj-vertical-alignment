# Handover: status on 9 October 2026

## Done
1. **Standards engine** (`data/standards/`): Math, ELA, Science, Social Studies, K-12, 2,557 rows.
   - Wisconsin CC + Essential Elements for Math and ELA; NGSS + Wisconsin Science + AERO (K-5) for Science;
     Wisconsin Social Studies + EE, plus AERO (K-5) for Social Studies.
   - Checked against official totals (all 208 NGSS PEs, 253 WI-SCI, 254 WI-SS, 97 AERO-SS, all WI math codes).
   - An independent check found and the teams fixed garbled PDF text, wrong EE codes and placeholder rows.
   - 123 school descriptors flagged as possibly describing a different standard (each has a suggested draft).
   - Extended workbooks for the committee were delivered to Tim directly (not in this repo).
2. **Database** (Supabase, see CLAUDE.md): schema in `supabase/migrations/001_part1_schema.sql`; standards and 35
   teams loaded; admin passcode set; loader locked.
3. **Part 1 site** (`site/`): Rate, Heatmap, Gaps & repetition, Grade dashboard, Progressions, Activity; standard
   popup (text, EE, "I can" levels, grade strip you can click, grade before/after, comments, history); CSV/PNG/PDF
   export; "?" explanations everywhere; traffic-light colours. Tested end to end against the live database
   (save, history, undo with passcode, wrong passcode rejected).
4. **Part 2 page** ("Vertical Alignment Audit" tab, view id "plans"): layout and empty states are ready; it reads `site/data/evidence.json`
   when that file exists. `scripts/part2/match_plans.py` is written but has NOT been run (Tim asked to hold it).

## Waiting on Tim
- **Turn on GitHub Pages**: repo Settings, Pages, Source = GitHub Actions, then re-run the failed "Publish site"
  run. Site URL: https://timjmills.github.io/awsaj-vertical-alignment
- Awsaj logo and colours: now taken from awsaj.qa (symbol in site/awsaj-symbol.svg, palette in CLAUDE.md). Confirm with the school if an official brand guide exists.

## Next steps
1. After Pages is on: open the live site, check every view, then share the link with the committee.
2. Committee review items (listed in each workbook's About tab):
   - draft descriptors (1,725 rows) and the 123 flagged school descriptors;
   - suggested HS course placement (math, science, social studies) and MS science placement
     (G6 21 / G7 11 / G8 23 NGSS PEs, decided by teachers in Part 1);
   - elementary science and social studies: AERO or NGSS / Wisconsin (both selectable for now);
   - Power Standards columns are empty in every school sheet.
3. **Part 2** (when Tim says go):
   - Inventory plans in the shared Drive (read-only). 2026-27 first; 2025-26 only for weeks not yet planned.
     Known folders: `2026-2027 Curriculum` (Middle School / High School > Unit Plans, Lesson Plans by grade and
     course), elementary grade folders and `Awsaj 2025-2026 > Programming and Planning (Archive 2025-2026)`.
     Skip House of Scholars rewards sheets. Mark "Copy of" files as carried forward.
   - Export each plan to text into `data/source/plans/` (git-ignored), write `data/part2/manifest.json`, run
     `scripts/part2/match_plans.py` for cited codes, then an inferred-tagging pass for plans without codes
     (label every match "inferred"; Tim chose no human review), and merge into `site/data/evidence.json`.
   - Strip teacher names from plan titles before they reach `evidence.json` (public repo).
   - Early finding from a quick look: Grade 5 2026-27 plans cite many Grade 3, 4 and 6 math codes
     (e.g. 6.RP.A.3 29 times): expect a full below/above-grade report.
4. Optional later: Social Studies HS course placement review; Arabic/Islamic/Qatar History are out of scope.

## Access needed in Claude Code
- GitHub: push to `timjmills/awsaj-vertical-alignment`.
- Supabase: Tim's account (Supabase MCP or CLI) for migrations; the site itself only needs the public key.
- Google Drive (school account 2sk234) for Part 2: a Google Drive connector signed in to that account, or exports
  Tim downloads into `data/source/plans/`.
