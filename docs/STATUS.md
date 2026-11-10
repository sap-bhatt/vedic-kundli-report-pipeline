# Status (November 2026, pipeline v0.16)

## What works

- **Library:** 876 entries across 20 layers, every expected key present (planet in house and sign, lord in house,
  Vimshottari mahadashas and all 81 sub-periods, dasha principles, Saturn/Jupiter transits, Sade Sati phases,
  Yogini, 30 yogas, 8 doshas, 27 nakshatras, 12 rising signs, chara karakas and karakamsha, D9/D10 principles,
  108 aspects, 36 conjunctions, panchang, remedies, profession). Review status: 471 accepted, 405 accepted with
  caveats (mostly thin modern sources). Confidence: 333 high, 367 medium, 176 low. See `index.json` and `quality.json`.
- **Pipeline:** chart calculation, per-section inputs with code-checked conditions, a shared "Chart verdicts" block,
  ownership of recurring points, writer calls with validation and feedback retries, an editor pass that cuts repeats,
  guidance written last, 20 code-built tables, North/South Indian chart drawings, sources from the trace blocks,
  HTML and PDF output. Runs against Anthropic, any OpenAI-compatible endpoint, or a file hand-off (`--provider file`).
- **Cost:** about 230-240k tokens per report on first attempts (estimate); each timeline retry adds about 45k.

## Results

Graded against an independent long report written by a strong model with live research (about 16k words per
chart), using the rubrics in `eval/`. Scores are out of 100 and weighted by the benchmark's section lengths.

| Chart | Report score | Timeline | Key period agrees with benchmark |
|---|---:|---:|---|
| Example: Meera (Capricorn rising) | 75.2 | 76.9 | yes |
| Example: Arjun (Aries rising) | 75.0 | 77.9 | no (benchmark's choice ranked 2nd) |
| Example: Devika (Leo rising) | 74.9 | 74.0 | no |
| Tuned chart (latest run) | 74.8 | 68.7 | yes |

Per-section scores for the examples are in `examples/scores.json`; the full grading files are in
`examples/<name>/grading/`. The example runs used a small, low-cost model (Claude Haiku) for every call. The limit
is coverage (about 45-60% of the benchmark's points), not accuracy (88-100 per section on checkable facts). Run-to-run
noise on a single section is about +-5 points, so compare report totals, not sections. The version history is in
`skill/kundli-report-versions/CHANGELOG.md`.

Known weak spots: about 30-36 points repeated in 3+ sections, 7-9 small cross-section contradictions per report,
readability 3/5 (reads like a compilation in places), guidance is the weakest life section.

## To do

### A. Report quality round
1. Group separate double-transit spells in the inputs (writers merge them into one long stretch).
2. One shared tone label per period, used by every section and the 10-year table.
3. Confirm the newer lint rules stop copied writer instructions.
4. Safety gate: a section still failing after its retries goes to a fallback model or a human, never to the reader.
5. Readability: fewer "(see X)" pointers and author names in the text.
6. Re-test on the three example charts.

### B. Library coverage additions (expected to move coverage from ~50% to the low 60s; not yet verified)
1. Absent yogas and why (the calculator already lists the yogas it checked and found absent).
2. Health transit windows in the health input (already computed).
3. Nakshatra deity and symbol, and pada meanings.
4. Chara dasha meanings and per-period condition checks.
5. D7 (children) chart and its entries.
6. Ashtakoota attributes of the native (full matching is a separate two-chart feature).
7. Foreign-link principles (Rahu, the 12th lord, 9/12 links, movable signs, Saturn).

### Other open items
- No D10 facts in the condition vocabulary yet.
- Nakshatra `as_lagna` notes are empty for nakshatras 1-14.
- The calculator's Dhana yoga rule has no exactly matching verse; ghata dosha has two meanings in the sources.
- Nodal aspects are disputed in the sources and sparse in the library.
