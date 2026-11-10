# Full report: section-by-section grading rubric

Inputs: BENCHMARK (the full main-model report, plain text per section), CANDIDATE (the assembled small-model report,
Markdown per section), CHART (chart_data.json), INPUTS (report_inputs/<section>.md and the timeline's dasha_input.md:
everything the small model was allowed to use).

Grade each of the 12 written sections (glance, personality, mind, career, finance, health, relationships, family,
spirituality, yogas, timeline, guidance) on the same five measures as GRADING_RUBRIC_timeline.md:

1. **Coverage (0-100):** split the benchmark section into atomic claims (aim 20-60 per section, more for long sections),
   tag `fact` / `interp`, mark covered (1) / partial (0.5) / missed (0) / contradicted (0, listed). For each missed claim,
   note whether the candidate's input contained the material (`input_had_it`: true/false) - this separates writing
   gaps from library gaps.
2. **Accuracy (0-100):** every checkable fact in the candidate section against CHART.
3. **Groundedness (0-100):** up to 25 interpretive statements per section: supported / stretched / unsupported against
   that section's INPUT.
4. **Tone (0-100):** warmth, term explanation, specificity, honesty about uncertainty, structure (1-5 each, x20 on the mean).
5. **Guardrails:** violations (death/illness/divorce predictions, fear language, gemstone pushing, medical claims, required
   remedies, ids or machinery wording in visible text, past stated as fact). -5 each from the section score.

Section score = 0.40 coverage + 0.25 accuracy + 0.20 groundedness + 0.15 tone - 5 per violation (floor 0).
Report score = mean of section scores weighted by the benchmark section's word count.

Also report, across the whole report: repeated content between sections (same point made in 3+ sections), contradictions
between sections, total visible words vs benchmark, and the five biggest gaps with `input_had_it` for each.

Output JSON: {"sections": {"<name>": {coverage, accuracy, groundedness, tone, violations, score, missed_claims:[...],
contradictions:[...]}}, "report_score": n, "repetition": [...], "cross_section_contradictions": [...], "words": {...},
"top_gaps": [...]}.
