# Awsaj K-12 Vertical Alignment Site: Decisions (as of 9 October 2026)

Source context: K-12 Vertical Alignment proposal (meetings Nov 3, Dec 15, Jan 19, Mar 23, Apr 20/27; Math, Literacy, Science/Social Studies teams). Data source: the 2sk234@awsaj.qfschools.qa Google Drive (read-only).

## Standards engine
- Subjects in v1: Math, ELA, Science, Social Studies. National Subjects (Arabic, Islamic, Qatar History) excluded.
- Spine: Wisconsin Common Core (CC) paired with Wisconsin Essential Elements (EE).
- Math: extend "CCEE Math Standards 2024 V1 Complete.xlsx" into a NEW sheet (original untouched) covering K-8 and HS courses (Algebra 1, Geometry, Algebra 2, Pre-Calc), with "I can" descriptors added.
- Science: secondary plans cite NGSS codes (MS-ESS2-1, HS-PS1-7). Elementary: map to BOTH AERO Science PK-5 and NGSS; both selectable in Part 1 until elementary practice is confirmed. Middle and high school science teams default to NGSS in the Rate view.
- Social Studies: Wisconsin Standards for Social Studies plus Wisconsin Essential Elements for Social Studies (2022). Elementary also has AERO (the school's current framework), both selectable.
- ELA: the school uses Wisconsin 2020 codes (one Reading strand, e.g. R.6.1); RL/RI codes are kept as crosswalk.

## Standards engine: built
- One shared JSON schema for all subjects (docs/standards_team_brief.md); 2,557 rows in data/standards/all_standards.json.
- Math 406 rows, ELA 652, Science 844 (NGSS 240, WI-SCI 514, AERO-SCI 90), Social Studies 655 (WI-SS 548, AERO-SS 107).
- Completeness checked against official totals: all 208 NGSS PEs, 253 WI-SCI, 254 WI-SS, 97 AERO-SS, all WI math codes present.
- School descriptors are copied unchanged; 123 that seem to describe a different standard are flagged with a suggested draft. 1,725 rows carry draft descriptors for committee review.
- HS course placement (grade_is_suggested): Math Alg1=9, Geo=10, Alg2=11, Pre-Calc=12; Science Earth Env=9, Physics=10, Biology=11, Chemistry=12; SS Geography=9, World History 10, Economics=11, World History 12. MS science placed by 2026-27 unit plans, then the 2025 scope and sequence, then NGSS Appendix K (G6 21 / G7 11 / G8 23 MS PEs plus the 4 MS-ETS1 in each grade).

## Suggested placements are settled by teachers in Part 1
- Do not rebalance suggested placements in advance.
- For band standards (MS/HS science, HS math and social studies courses, other bands), teachers see ALL standards in the band and report which are actually taught in their grade, on the same 3-level scale.
- Ratings are stored per standard per grade; the site highlights standards taught outside their suggested grade so the committee can move them.

## Part 1: Collaborative audit
- 3-level scale (shared with Part 2): Not taught (red) / Introduced-Exposed (amber) / Taught in Depth (green).
- Teachers rate their own grade's CC standards and the matching EE (plus the whole band for band standards).
- Open editing, no sign-in. Team chosen from a dropdown (remembered per device); every change logged with team and time; admin undo with passcode.
- Comments on individual standards (no separate meeting pages).
- Filters: subject, framework, division, grade, strand, search.
- Views: Rate, K-12 heatmap, gaps and repetition, grade dashboard with summary analysis, progressions, activity.
- Popups: CC text, EE, "I can" levels, grade strip, grade before/after, comments, history, Part 2 evidence.
- Exports: PDF (print), CSV, PNG.
- Every control and section has a "?" explanation.

## Part 2: Curriculum analysis
- Reads elementary, middle and high school plans in the 2sk234 Drive, read-only.
- 2026-27 is primary; 2025-26 fills weeks not yet planned this year. No year-vs-year view.
- Amount measured by weeks a standard appears: 1-2 weeks Introduced, 3+ Taught in depth.
- Cited codes counted directly; uncoded content AI-tagged with no review, labelled "inferred".
- Says vs shows comparison with Part 1, framed gently ("not yet recorded in plans").
- Flag "Copy of" files as carried forward. Exclude House of Scholars rewards sheets. No student names.
- Status: page ready to view with empty states; analysis not yet run (Tim asked to hold).

## Build
- Supabase database + static site on GitHub Pages (public repo timjmills/awsaj-vertical-alignment); Python scripts for data; vanilla JavaScript for views and charts.
- Light, white design: maroon #8A1538, teal #0F8B8D (official logo and colours still to come from Tim).
- Target: Part 1 live for all four subjects by Nov 3. Part 2 after.
