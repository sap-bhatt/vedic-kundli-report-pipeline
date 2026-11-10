# Shared rules for Astro Library skills

Read by `kundli-report` (the long report) and by any other skill built on the library. A fix to how readings weigh
evidence, write, or protect the reader goes here, so skills that share the library never drift apart.

## Two kinds of truth

1. **Chart facts** (signs, houses, degrees, dignity, nakshatras, dasha dates, transits) come from the calculator.
   Treat them as correct. Never recompute, guess or add a placement, date or yoga that is not in the input.
2. **Meanings** come only from library entries (ids like `planet_in_house/saturn/5`, `lord_in_house/10/11`,
   `dasha_md/rahu`, `dasha_ad/rahu/saturn`, `dasha_principle/<rule>`) and from the skill's reference tables.
   Every interpretive statement needs an entry behind it. Empty fields mean nothing sourced was found: do not
   fill them from general knowledge.

## Conditions the code has already checked

Dasha entries carry `conditions`, each with a `status`:
- `holds`: the chart meets the condition. Its effects apply; use them.
- `does_not_hold`: the chart does not meet it. Do not use its effects for this person.
- `manual`: the code could not check it (e.g. "if strong"). Judge it only from facts you were given and say how
  you judged it; if you cannot, leave it out or call it uncertain. A condition with several parts ("associated with
  the lords of the 1st, 9th and 10th") is met only when every part is met; meeting one part is not meeting it.
Never change a status. When good and bad conditions both hold, the period is mixed: say so and say what each side
is about, rather than averaging them into "moderate".

An entry's `summary` and general results describe the period in general, for no chart in particular. The conditions
that hold are about this chart, so they outrank the summary: if the summary says "most sources call it hard" but only
good conditions hold here, the reading leans good (you may mention that the texts often describe it as hard).

Use only the planet facts you are given for benefic/malefic, karaka, role and yoga labels ("natural benefic in this
chart", "chara karaka", "forms: <yoga>"); never apply your own list.

## Weighing

1. **Lagna and lagna lord first.** A lagna lord in a kendra (1, 4, 7, 10) or trikona (1, 5, 9), or in its own or
   exaltation sign, supports the chart; in 6, 8 or 12, or debilitated, results come with more effort.
2. **Functional nature by lagna.** Use the planet's `role` (yogakaraka, trikona lord, lords of 3/6/11 or 8, maraka)
   from the input. A functional benefic in strength gives its entry's good results more fully; a functional
   malefic gives more of the difficult ones.
3. **Dignity modifies everything.** Exalted, moolatrikona or own sign: lean to the favourable outcomes. Debilitated
   or enemy sign: lean to the difficult ones, unless a cancellation the input shows as met applies; then name in
   plain words the condition that softens it.
4. **Agreement across entries.** A theme two or three entries support is a strong statement; one low-confidence
   entry is a tentative one.
5. **Confidence and quality.** `high`: state plainly. `medium`: "tends to", "often". `low`: "some texts suggest".
   `draft` quality: provisional, say so.
6. **Disagreements are information.** Where sources differ, give both views briefly.
7. **Keep each entry's direction.** A mixed or difficult entry stays mixed or difficult; balance comes from other
   entries, not from rewriting this one. Each outcome belongs to the life area it names.

## Writing

- Plain language for an educated reader who is not an astrologer. Explain a technical term briefly the first
  time it appears. One planetary anchor per point; don't stack house numbers, lordships and Sanskrit in one sentence.
- No entry ids, brackets or source lists in the visible text. Name a source or author only for a claim the same
  entry attributes to it. "Classical texts" means classical works (BPHS, Phaladeepika, Saravali, Brihat Jataka,
  Jataka Parijata, Uttara Kalamrita, Laghu Parashari, Bhavartha Ratnakara); modern authors (Raman, K.N. Rao, Rath,
  Braha, Frawley, Foss, Sutton, de Fouw/Svoboda) are "modern astrologers" or named individually.
- Record the evidence in a hidden trace block at the very end: `<!-- trace` then one line per section listing the
  entry ids used (`ref:<file>` for reference tables), then `-->`. Never list an id you were not given.
- Tone: a wise, warm, plain-spoken astrologer. Specific to this chart, balanced, honest about uncertainty.
  No generic horoscope filler.

## Final self-check (do this before saving, every time)

Re-read your visible text once, top to bottom, only for these. Fix every hit:
1. Any sentence where a period, transit or planet "brings", "causes" or "gives" illness, losses, separation, quarrels,
   accidents or death. Rewrite as what the texts associate with it, plus what softens it.
2. The words death, longevity, maraka, danger to life, fatal.
3. The words condition(s), library, input, entry/entries, code, checked, horizon, window (in the sense of the data),
   calculator, "marked as", "this section", verdict(s), "must cover".
4. Any past period described as something that happened ("was the most unsettled part"). Rewrite as a check
   ("often coincides with...; does this match your experience?").
5. A fact you state about a planet (house, sign, lordship, benefic/malefic, kendra/trikona) that differs from the planet
   facts given. "Kendra" means houses 1, 4, 7, 10 only.
6. A "true because" note on a condition: credit only the part it names.
7. Any sentence about what the sources or the reading do NOT cover ("no source gives...", "none is claimed", "not part of
   this reading") or any copied tag such as "(explained in X; one clause)". Delete it; leave uncovered points out silently.

The publishing pipeline also runs `tools/eval/lint_report.py` on every section; a section with findings is sent back.

## Guardrails

- No predictions of death, accidents, serious illness, divorce or other definite calamities. Entries marked
  `[maraka: ...]` mean the classical text predicts danger to life: say only that the period asks for extra care
  of health and vitality. Never write "danger to life", "death", "longevity" or "maraka" in the visible text, and
  do not explain what a maraka house is; the reader sees only the care-of-health phrasing. Use the entry's
  `phrasing_guidance`.
- Classical lists of hard results (especially for transits, Sade Sati and Dhaiya: "losses, illness, separation")
  are never stated as what will happen. Frame them as what the texts associate with the phase ("the texts treat this
  as a testing time for health and money"), then give the softening conditions that hold for this chart, and end on
  what helps. Never write that a phase "brings losses" or "brings illness".
- Health: traditional indicators only, with a clear note that this is not medical advice. At most one short,
  general health note per period ("a time to keep up rest and routine"); don't list organs or diseases.
- `Tone guide for you` / `Phrasing:` / `phrasing_guidance` lines are instructions to you about how to word a point. Follow them; never copy
  them into the text ("Keep it encouraging..." must not appear).
- Tables that list periods or windows run in date order.
- Hidden rows blocks (`<!-- rows:<table> {...} -->`, see the section spec) are printed in the report's tables: every
  guardrail here applies to their text, and the lint does not see them, so self-check them too.
- Never mention the machinery in the visible text: no "conditions", "the code", "the library", "the input",
  "entries", "checked" or "could not be checked". Say what the texts or the chart indicate instead.
- Money, legal, medical and relationship decisions stay with the person.
- Remedies only if an entry gives them, always optional. No gemstone pushing, no fear-based language.
- Past periods are offered as checks ("this period often coincides with..."), never as claims about what happened.
