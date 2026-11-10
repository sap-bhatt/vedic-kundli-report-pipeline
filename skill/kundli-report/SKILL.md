---
name: kundli-report
description: Write a long, detailed Vedic (Parashari) Janma Kundli report, section by section (chart at a glance, personality, mind, career, finance, health, relationships, family, spirituality, yogas and doshas, timeline, guidance), from calculator chart data and the researched Astro Library. Use when someone wants a full or detailed kundli report or PDF, or one report section such as a dasha/timeline report, rather than a short reading. It is built for the full report, not for a short reading or a single question.
---

# Kundli report from the Astro Library (v0.12 draft)

**Status:** draft. All sections are specified. Order of work: (1) write sections 1-11 (each from its own input, in any
order or in parallel); (2) run the editor pass (`references/editor.md`), which cuts points repeated outside their
owner section; (3) write Guidance last, reading the edited sections. Every input starts with the same
"Chart verdicts" block; statements that touch those points must match it in every section.

First read `../shared/rules.md`. It holds the rules on chart facts vs meanings, checked conditions, weighing,
writing, the hidden trace block and the guardrails. They apply to every section.

## Inputs

- **Timeline:** a `dasha_input.json` from `tools/dasha_facts.py` (run the commands from the repository root; this
  skill folder is `skill/kundli-report/` inside it, so the root is two levels up from this file):
  ```
  python -I tools/chart_data.py --date YYYY-MM-DD --time HH:MM --lat N --lon E --place "..." --sex ... --out chart_data.json
  python -I tools/dasha_facts.py --chart chart_data.json --out dasha_input.json --md dasha_input.md
  ```
  Read `dasha_input.md` (about 22k tokens; read all of it). The JSON holds the same data plus the conditions that do not
  hold, for tools and graders. The input contains the chart summary, facts for every planet, the dasha principles, every mahadasha with its library
  entry and every sub-period from now to the horizon with its entry, each entry's conditions already checked,
  the placement entries, and timing facts (transits, Saturn/Jupiter sign changes, Sade Sati, Yogini, Chara).

- **Other sections:** `tools/report_input.py --chart chart_data.json --outdir report_inputs/` writes one input file
  per section (`glance.md`, `personality.md`, ... `guidance.md`). Write each section from its own file only.

## Sections

| Section | Spec | Status |
|---|---|---|
| 1-10, 12 | `references/sections/life_areas.md` | draft |
| 11 Timeline | `references/sections/timeline.md` | pilot (iterations 1-6) |
| 13 Sources | built by code from the trace block | planned |

Tables (D1, D9, house table, functional roles), the North Indian chart drawings and the source list are produced by
code (`tools/assemble_report.py`), not written by the model.
