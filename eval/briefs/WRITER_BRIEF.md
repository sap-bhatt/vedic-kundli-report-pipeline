# Brief for one section writer (agent mode)

You write ONE section of a long Vedic (Parashari) kundli report with the kundli-report skill. You are given RUN (a
folder that holds `chart_data.json`, `inputs/` and `sections/`) and SECTION. All paths below are relative to the
repository root R.

1. Read in full, in order: `R/skill/kundli-report/SKILL.md` ; `R/skill/shared/rules.md` ; the section spec
   (`R/skill/kundli-report/references/sections/timeline.md` for SECTION = timeline, otherwise
   `R/skill/kundli-report/references/sections/life_areas.md`).
2. Read your input in full: `RUN/inputs/dasha_input.md` for timeline (long; read every part, in chunks), otherwise
   `RUN/inputs/SECTION.md`. For guidance, also read every finished file in `RUN/sections/`.
3. Write the section exactly as the spec says (title, length, subsections), using only the facts and entries in your
   input. The "Chart verdicts" block is final. Name every "Must cover" item. Entries marked "(explained in X)" get one
   clause at most, and the tag itself never appears in your text. End the file with the hidden trace block. Do the
   rules.md final self-check.
4. Save to `RUN/sections/SECTION.md` (Markdown, starting with "## <section title>").
5. Run the lint and fix every finding, rerunning until it reports 0:
   `python -I R/tools/eval/lint_report.py <your output file>`
6. Do not edit any other file. Reply with only: visible word count and final lint count.
