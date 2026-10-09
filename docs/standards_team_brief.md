# Standards Team Brief (shared by the ELA, Science and Social Studies teams)

Project: Awsaj Academy (Qatar Foundation, Doha) K-12 Vertical Alignment site. Part 1 lets teachers rate how
each standard is taught at their grade (Not taught / Introduced-Exposed / Taught in Depth). Every subject needs one
clean master list of standards in the SAME JSON schema so the site can load them all.

Students: mostly English language learners (Arabic L1), often 2-3 years below grade level, including SPED.

## Hard rules
- The school's Google Drive is READ-ONLY. Never create, edit, move or delete anything in Drive.
- No student names anywhere.
- Never use em dashes or en dashes as punctuation in anything you write (use commas, colons, separate sentences).
- Standards text must come from an official or school source, never from memory. If you must fill a gap from memory,
  set `"text_source": "memory - verify"` on that row and list it in your final report.
- Work only inside /home/claude/awsaj-va. Put downloads in data/source/<subject>/ (create it), your scripts in
  scripts/<subject>/, outputs as listed below. Run any Python that reads downloaded files with `python3 -I`.
- Network: the shell can reach dpi.wi.gov (official Wisconsin DPI PDFs) and GitHub. Use `pdftotext -layout` for PDFs.
  Google Drive files are reached with the Google Drive connector tools (search_files / download_file_content /
  read_file_content); large downloads are saved to a tool-results JSON file whose `content` field is base64.

## Grade / division model
- Grades: "K","1".."12". Division: Elementary = K-5, Middle = 6-8, High = 9-12.
- High school courses map to a grade the way the school's 2026-27 High School folders do (e.g. Grade 9 ELA = "English
  Language Arts 9"; Biology = Grade 11; Chemistry = Grade 12; Physics = Grade 10; Earth Environmental Science = Grade 9;
  Geography = Grade 9; World History 10 = Grade 10; Economics = Grade 11; World History 12 = Grade 12).
  If a standard is a grade band (e.g. 9-10, 11-12, HS), keep the band in `grade_band` and set `grade` to the course
  grade you place it in (mark `"grade_is_suggested": true`).

## Output 1: data/standards/<subject>.json  (subject = ela | science | social_studies)
A JSON list. One object per standard per framework:
{
  "subject": "ELA" | "Science" | "Social Studies",
  "framework": e.g. "WI-CC-ELA", "WI-SCI" (Wisconsin Standards for Science), "NGSS", "AERO-SCI", "WI-SS", "AERO-SS",
  "code": official code exactly as the source prints it (e.g. "RL.5.1", "5-PS1-1", "SCI.LS1.A.5", "SS.Hist1.a.i"),
  "grade": "K".."12",  "grade_band": "" or e.g. "9-10", "grade_is_suggested": bool,
  "division": "Elementary" | "Middle" | "High",
  "course": "" or the HS course name,
  "strand": top-level strand/domain (e.g. "Reading Literature", "Physical Science", "History"),
  "cluster": sub-strand / disciplinary core idea / cluster heading if any, else "",
  "text": full standard text,
  "ee_code": matching Essential Element code or "",
  "ee_text": EE text, or "Not applicable..." exactly as the source says, or "" if no EE framework exists,
  "crosswalk": list of related codes in other frameworks (e.g. an AERO science row lists its NGSS code, an NGSS row
               lists its WI-SCI code) so the site can show "same standard, other framework",
  "descriptors": {"cc_advanced": "...", "cc_at_target": "...", "cc_approaching": "...", "cc_emerging": "...",
                  "ee_at_target": "..."},
  "descriptor_source": "school" (copied from an existing school sheet) | "draft" (written by you),
  "power_standard": true/false if the school sheet marks it, else null,
  "source": short name of the source document,
  "text_source": "official" | "school sheet" | "memory - verify"
}

## "I can" descriptors (when the school sheet does not already have them)
- Each starts with "I can", 1-2 sentences, max ~35 words, concrete and measurable, student-friendly.
- Advanced = extends/applies; At Target = exactly the standard; Approaching = partial with support;
  Emerging = the foundational prerequisite with heavy support. ee_at_target = the EE as an "I can" statement, or the
  EE "Not applicable" text copied exactly, or "" if no EE exists.
- Where a school sheet already has descriptors (K-5 tabs), COPY them, parsed into the 4 levels, with
  descriptor_source "school". Do not rewrite school descriptors.
- You may split descriptor writing across your own sub-agents for speed; validate their output.

## Output 2: outputs/<Subject> Standards K-12 (Extended).xlsx
- If a school workbook exists for the subject, start from a copy of it: keep its existing tabs UNCHANGED, add the new
  grade/course tabs in the same column layout and styling, and add an "About" tab first (sources, what is draft,
  what needs committee review). Original file in Drive is never touched.
- Calibri, wrapped text, frozen header row, domain rows as merged full-width banner rows. Mirror the school's header
  colours (blue C9DAF8 for CC columns, green BAD682 for EE columns).
- Use the openpyxl library. No formulas are needed.

## Validation before you finish
- JSON parses; every object has every key; no duplicate (framework, code, grade) rows; no "—" or "–" anywhere.
- Count of standards per grade per framework printed in your report, and compared with the official document's count.
- Spot-check 10 random rows' text against the source document.

## Final report (keep it short)
Counts per framework and grade; files written; anything filled from memory; anything the committee must decide.
