# Brief for a report grader

You grade part of a kundli report (CANDIDATE) against an independent report written by a strong model (BENCHMARK)
for one chart. You are given CHART (a folder, e.g. `examples/meera`), RUN (the run folder inside it, e.g.
`examples/meera/open_run`) and PART (A, B or C). All paths are relative to the repository root R.

Files: BENCHMARK `CHART/benchmark/<section>.txt` ; CANDIDATE `RUN/sections/<section>.md` (visible text; the hidden
trace block only for groundedness) ; CHART FACTS `CHART/chart_data.json` ; INPUTS `RUN/inputs/<section>.md` (timeline:
`RUN/inputs/dasha_input.md` and `dasha_input.json`). Guidance was also allowed to use the finished sections in
`RUN/sections/`.

Rubrics (follow exactly): `R/eval/GRADING_RUBRIC_full_report.md` for life-area sections;
`R/eval/GRADING_RUBRIC_timeline.md` for the timeline (overall formula there). The benchmark is itself model-written: if
a benchmark claim contradicts the chart facts, do not count it as a candidate miss; list it under "benchmark_errors".

PART A: glance, personality, mind, career.
PART B: finance, health, relationships, family, spirituality.
PART C: yogas, guidance, timeline (timeline rubric), plus the WHOLE REPORT review: read all 12 files in `RUN/sections/`
and list points made in 3+ sections ("repetition"), contradictions between sections ("cross_section_contradictions":
topic, both sides with section and quote, severity), readability 1-5 with reason, total visible words vs the benchmark.
For calibration: a well-tuned run had about 30 repeated points, 7 contradiction topics (all minor/moderate) and
readability 3/5.

Be strict and consistent: 20-60 atomic claims per section; covered/partial/missed/contradicted; input_had_it for
misses; every fact checked against CHART FACTS; groundedness against that section's INPUT; -5 per guardrail violation.
Write JSON to `CHART/grading/grading_<PART>.json`: {"sections": {name: {coverage, accuracy, groundedness, tone,
violations, score, missed_claims, contradictions}}, "benchmark_errors": [...], "top_gaps": [...]} (+ for PART C:
"timeline" with the timeline rubric's components and overall and whether the key window agrees, "repetition",
"cross_section_contradictions", "readability", "words"). For the timeline, put its overall into sections.timeline.score.
Reply with only a compact table of section scores with their components, and (PART C) the repetition count,
contradiction count, readability, and key-window agreement.

The report score is the mean of the section scores weighted by each benchmark section's word count
(`R/eval/GRADING_RUBRIC_full_report.md`); `examples/scores.json` shows the format.
