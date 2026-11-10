# Editor pass: remove repeated points

Run after sections 1-11 are written and before Guidance. You read every finished section and propose cuts; code
(`tools/apply_edits.py`) applies them. You never rewrite a section yourself.

## Inputs

- The finished sections `sections/<name>.md`: glance, personality, mind, career, finance, health, relationships,
  family, spirituality, yogas (the Timeline is not edited, but read it so you know what it already says).
- `report_inputs/ownership_map.md`: which section owns each recurring point.
- `repeats.md` from `python -I tools/repeat_finder.py --chart chart_data.json --sections sections --out repeats.md`:
  the sentences code has flagged as restating a point outside its owner, or defining a term again. **This is your
  main work list: give every flagged sentence an edit** (shorten it to what the point means for this area, or delete
  it), skipping only cosmetic matches and a must-cover point's single mention (shorten that one instead). Then add
  edits for any other repeats you find (yogas re-explained, near-copied sentences).

## What to cut

A reader goes through the report in order: glance, personality, mind, career, finance, health, relationships,
family, spirituality, yogas, timeline. Every point should be told in full once, by its owner.

1. **Core placements told again.** A planet's sign, house, dignity, cancelled debilitation, combustion distance,
   D9/D10 placement or character, told in a section that does not own it. Cut it to the one clause that says what it
   means for this section's area ("the 2nd lord's cancelled fall, covered under Career, here means..."), or remove
   the sentence when it adds nothing for the area. The Chart at a glance may keep one short clause per point.
2. **Yogas and doshas re-explained.** Outside Yogas and doshas (and Manglik outside Relationships), a yoga or dosha
   gets its name and what it means for this area in one clause; cut the definition, the strength discussion and any
   author quote.
3. **Terms defined again.** Atmakaraka, yogakaraka, combustion, vargottama, neecha bhanga, double transit and similar
   terms are defined once, in the first section that defines them. Cut later definitions and keep the term.
4. **The same sentence or near-copy in two sections.** Keep it in the owner (or the earlier section when no owner
   applies) and cut or shorten the other.
6. **Lint findings.** Run `python -I tools/eval/lint_report.py` on the sections first; any flagged phrase in an
   editable section gets an edit that removes or shortens it (the Timeline's findings are reported, not edited).
5. **Birth-time sensitivity** belongs to the Chart at a glance; elsewhere at most a clause ("the D10 reading is
   time-sensitive").

## What never to cut

- Anything the section says about its own area, including what another section's planet means for this area.
- The section's "When this area is most active" paragraph and its dates (these are already assigned to one or two
  sections each). Do not touch dates, degrees or numbers.
- Headings, tables and the hidden trace block.
- Cautions and softeners ("this is traditional astrology, not medical advice"; "one factor among many").
- A must-cover point: if a sentence is the section's only mention of a placement the section needs (the 7th lord in
  Relationships, the 10th lord in Career, a wealth house in Finance), shorten it but keep it.

## How to write each edit

- `old` is an exact copy of visible text from the section, a whole sentence or a run of whole sentences, copied
  character for character (same punctuation, same bold markers). Unique in that section.
- `new` is a shorter version of `old` (or empty to delete). It may only shorten: no new claim, no new planet, no
  new number, no "as noted earlier" filler beyond a short pointer such as "(see Career)". Keep the grammar of the
  surrounding paragraph intact; if deleting a sentence would leave a paragraph empty or orphan a "This...", shorten
  instead of deleting.
- Aim for the repeated material only: one edit per flagged sentence plus the others you find, typically removing
  10-25% of the words in the sections that repeat most, and very little from owner sections.

## Output

Write one JSON file, `edits.json`: `[{"section": "<name>", "old": "...", "new": "...", "reason": "<point> owned by
<section>"}]`. No other output file. Then run
`python -I tools/apply_edits.py --sections sections --edits edits.json --backup sections_pre_edit` and re-propose any
rejected edit once with an exact copy of the text.
