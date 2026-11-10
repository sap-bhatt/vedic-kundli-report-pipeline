# Timeline section: claim-level grading rubric

Inputs to the grader: BENCHMARK (the timeline section of the full main-model report, written with live web research),
CANDIDATE (the section written by the small model with the kundli-report skill), CHART (chart_data.json, the calculator's
facts) and INPUT (dasha_input.json, everything the small model was allowed to use).

## 1. Coverage of the benchmark (0-100)
Break the BENCHMARK into atomic claims (one fact or one interpretation each; aim for 50-80). Tag each claim with a part:
`intro`, `md_table`, `past`, `current_md`, `ad:<Planet>` (one per sub-period), `transits`, `sade_sati`, `yogini`, `chara`,
`overview`. Tag each claim `fact` (a date, position or computed item) or `interp` (a meaning or judgement).
Mark each claim in the CANDIDATE: `covered` (same point, 1), `partial` (related but thinner or vaguer, 0.5), `missed` (0),
`contradicted` (says the opposite, 0, listed separately).
Coverage = 100 * sum / number of claims, reported overall, per part, and for two groups:
- `library_covered`: parts the library had entries for (`intro`, `md_table`, `current_md`, `ad:*`)
- `library_gap`: parts with no library layer yet (`past`, `transits`, `sade_sati`, `yogini`, `chara`, `overview`)

## 2. Factual accuracy (0-100)
List every checkable factual statement in the CANDIDATE (dates, periods, signs, houses, dignities, lordships, roles,
aspects, house-from-dasha-lord counts). Check each against CHART/INPUT. Accuracy = 100 * correct / total. List every error.

## 3. Groundedness (0-100)
List the CANDIDATE's interpretive statements (up to 40, all of them if fewer). For each, find support in INPUT
(a library entry's text, a condition with status `holds`, a principle, a placement entry): `supported`, `stretched`
(loosely related or over-generalised) or `unsupported` (not in INPUT, i.e. from the model's memory). Also flag any use of a
condition whose status is `does_not_hold`. Groundedness = 100 * (supported + 0.5 * stretched) / total.

## 4. Language and tone match (1-5 each, then x20 for 0-100 on the average)
Compare CANDIDATE with BENCHMARK on: warmth and plain-spoken voice; explaining terms the first time; specificity to this
chart (vs generic filler); honesty about uncertainty and mixed periods; structure (tables, flow, depth per sub-period).
Quote one short example per dimension.

## 5. Guardrails
Count violations: predictions of death/accident/illness/divorce, fear language, gemstone pushing, medical claims, remedies
presented as required, entry ids or source lists in visible text, past periods stated as fact.

## Output (JSON)
```
{"coverage": {"overall": n, "library_covered": n, "library_gap": n, "by_part": {...}, "claims": [{"part", "type", "claim", "mark"}]},
 "contradictions": [...],
 "accuracy": {"score": n, "checked": n, "errors": [...]},
 "groundedness": {"score": n, "checked": n, "unsupported": [...], "stretched": [...], "used_does_not_hold": [...]},
 "tone": {"scores": {...}, "score": n, "examples": {...}},
 "guardrails": {"violations": n, "items": [...]},
 "overall": n}
```
Overall = 0.35 coverage.library_covered + 0.15 coverage.library_gap + 0.25 accuracy + 0.15 groundedness + 0.10 tone,
minus 5 per guardrail violation (floor 0).
