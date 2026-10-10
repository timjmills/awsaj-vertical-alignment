# Awsaj K-12 Vertical Alignment

A website for Awsaj Academy (Qatar Foundation, Doha) where teacher teams record how each standard is taught in
their grade (Part 1), and where curriculum plans are compared with those ratings (Part 2). Owner: Tim Mills,
Elementary Curriculum Coordinator. Users: the K-12 Vertical Alignment Committee and grade/subject teams.
Committee meetings: Nov 3, Dec 15, Jan 19, Mar 23, Apr 20/27. **Part 1 must be live for all four subjects by Nov 3.**

Read `docs/HANDOFF.md` first (current status and next steps), then `docs/spec.md` (every decision so far).

## Hard rules
- The school Google Drive (account 2sk234@awsaj.qfschools.qa) is **read-only**. Never create, edit, move or delete
  anything there.
- **No student names or student data** anywhere: not in data files, the database, the site, or commits.
- Teacher names should not appear on the public site (plan file titles often contain them; strip them).
- This repo is **public** (GitHub Pages). Never commit downloaded school files (`data/source/` is git-ignored),
  the extended workbooks (`outputs/`), passwords, the admin passcode, or any service key. The Supabase
  *publishable* key in `site/config.js` is meant to be public.
- Writing style for anything people read: plain English for teachers, **no em dashes or en dashes** (use commas,
  colons, parentheses or separate sentences).
- Draft "I can" descriptors are labelled `draft`; school descriptors are never rewritten, only flagged
  (`descriptor_flag` + `descriptors_suggested`).
- Every part of the site needs a "?" explanation (`site/help.js`). Add one whenever you add a control or section.

## Layout
- `site/` static site, no build step: `index.html`, `styles.css`, `app.js`, `help.js`, `config.js`, `data/*.json`.
  Run locally: `cd site && python3 -m http.server 8765`.
- `data/standards/` one JSON per subject plus `all_standards.json` (2,557 rows, schema in
  `docs/standards_team_brief.md`). `data/teams.json` team list.
- `scripts/` parsers and builders. Math: `parse_wi_math.py`, `parse_wi_ee_math.py`, `build_math_master.py`,
  `build_math_json.py`, `build_math_xlsx.py`. Other subjects: `scripts/ela|science|social_studies/`.
  `build_site_data.py` regenerates `site/data/` from `data/standards/`. `load_supabase.py` loads standards and
  teams. `part2/match_plans.py` (written, not yet run) finds standard codes in plan text.
- `supabase/` schema migrations and notes. `.github/workflows/` Pages publish + keep-alive ping.

## Database (Supabase)
Project `awsaj-vertical-alignment` (ref `mmcblwddwgwhtlhrqmfi`, region ap-south-1, Free plan) in Tim's
"mycurricula.app" organisation. No sign-in: tables are read-only to the public key through RLS; all writes go
through `set_rating`, `add_comment`, `admin_undo`, `admin_hide_comment` (admin ones need the committee passcode,
stored only as a bcrypt hash in `app_settings`; Tim has it). Ratings are keyed by (framework, code, grade) so any
grade can claim a band standard suggested for another grade. `load_rows()` (bulk loader) exists but its EXECUTE is
revoked; re-grant temporarily with a fresh token when reloading standards, then revoke again.
Free projects pause after 7 days idle; `keepalive.yml` pings every 3 days.

## Rating scale and colours
Awsaj brand (from awsaj.qa logo and stylesheet): dark green #024638 (frame, headings, buttons), greys #56595A / #75787B,
and the four symbol ribbons: orange #ED8B00, blue #0092BC, magenta #D00070, lime #78BE21. Font: Barlow (free, DIN-like;
the school uses DIN Next and QF, which are licensed). Ratings: 0 Not taught (magenta #D00070), 1 Introduced / exposed
(blue #0092BC), 2 Taught in depth (lime #78BE21), unrated white. Orange is only for highlights (selection, focus,
celebrations): never make orange and lime two rating levels, colour-blind readers cannot tell them apart. Dark green
outline = suggested grade; dot = taught in a grade other than the suggested one. Part 2 uses the same scale: 1-2 weeks in
plans = Introduced, 3+ weeks = Taught in depth.

Teachers use one guided flow (view "flow": one standard at a time); the committee and "Explore" get the full tabs.

## Testing
Use Playwright (Chromium) against the local server, and check every view (Rate, Heatmap, Gaps, Dashboard,
Progressions, Activity, Plans vs ratings) plus a standard popup. Do not leave test ratings in the live database:
if you write one, undo it.
