# Sections 1-10 and 12 (everything except the Timeline)

Each section is written from its own input file (`report_inputs/<section>.md` from `tools/report_input.py`). Output
Markdown starting with `## <section title>`, then `###` subsections. Visible length targets are guides, not quotas:
write less when the input has less, never pad. Every section ends with its own trace lines in the hidden trace block
(`<Section>-<subsection>: ids`).

## How every life-area section is built

1. **Lead with the strongest evidence.** The house lord's placement and the planets in the house come first; then the
   significator planets and karakas; then aspects and conjunctions; then nakshatra and D9/D10 notes; then yogas.
2. **Weigh, don't list.** Apply the shared weighing rules: functional role for this lagna, dignity, agreement across
   entries, confidence. Say which factor dominates and why, in plain words. When entries pull in different directions,
   say what each side is about and how they net out.
3. **Use the section's own area text.** Entries show "For this section (<area>)" when they have area-specific text; use
   that. Lines marked "General results (not specific to this area)" may be used only where they clearly fit the section.
4. **Dated timing paragraph.** End each life-area section with a short "When this area is most active" paragraph built
   from the "Periods ahead for this section" block: name at most three of the most area-specific sub-periods and double-transit
   windows with their dates (month and year), grouping back-to-back windows into one stretch, and say in a clause why
   each matters for this area (the reason given in the block). Meanings stay with the Timeline; no predictions of events.
5. **Missing entries.** Items marked "no library entry yet" are facts only: you may name them, never interpret them.
6. **Chart verdicts are final.** The "Chart verdicts" block is identical in every section's input. Any statement about
   a planet's net dignity (including a cancelled debilitation), its distance from the Sun and combustion, its natural
   nature versus its functional role, the nature of an aspect, Manglik status, D9/D10 placements or birth-time
   sensitivity must match it. An aspect takes the aspecting planet's natural nature (benefic or malefic); when an
   entry's general text calls an aspect "supportive" but the verdict says it is a malefic aspect, follow the verdict and
   use the entry only for what the aspecting planet's houses add. When a planet's natural and functional natures differ,
   say both, as the verdicts block shows. Never leave a verdict open ("if Mercury is very close to the Sun...").
7. **Ownership: say each point once.** Entries marked "(explained in X)" belong to another section. Use them in one
   clause at most, only for what they add to this section's area, and do not re-describe the planet's sign or house
   character there. Spend the words on what this section owns.
8. **Must cover.** Name every item in the "Must cover" list at least briefly (a clause is enough for items another
   section owns). These are the points readers check first.
9. **Never restate the core placements as background.** A planet's sign character, dignity and cancellation are told
   once, by their owner. Elsewhere write only what it means for this area ("the 2nd lord's cancelled fall, described
   under Career, here means..."), and don't re-define terms (Atmakaraka, yogakaraka, combustion) already defined in
   an earlier section.
10. **No instructions or absences in the text.** Never write your own instructions to yourself ("keep to one general
   note", "keep to care with temper") or what the sources don't cover ("is recorded", "not reported as met",
   "nothing more is said"). Leave such points out.
11. **Rows blocks (finance, health, guidance).** Code builds one table in each of these sections and you fill only its
   last column. The input ends with a "Table rows to fill" block giving the table key and the exact row keys. At the end
   of the section, just before the trace block, add one hidden line of valid JSON (double quotes, no trailing comma),
   one entry per row key, each value one plain line of up to 20 words, no dates:
   - Finance: `<!-- rows:wealth_houses {"2": "...", "11": "...", "5": "...", "9": "...", "12": "..."} -->` (what each
     house says about money here).
   - Health: `<!-- rows:body_correspondences {"1": "...", "6": "...", "8": "...", "12": "..."} -->` (one general care
     note per house: rest, routine, habits; never organs, illnesses or diseases).
   - Guidance: `<!-- rows:remedies {"Sun": "...", ...} -->` with the planets listed in the input (the traditional
     practice in one line, always optional; a planet left out shows "-").
   The rows are printed in a table, so the guardrails apply to them exactly as to the visible text. Do not repeat the
   table in prose: the house-by-house paragraphs stay, the table is a summary beside them.

## Section specs

| Section | Title | Target words | Subsections (adapt to what the input supports) |
|---|---|---|---|
| glance | Chart at a glance | 600-900 (tables are added by code) | The chart's shape (from the verdicts: empty kendras, planets in dusthanas, D9 strength, dispositor chains), in plain words; the themes that define this chart (5-6 numbered themes, each 2-3 sentences, each tied to its planets, pointing to the section that explains it rather than explaining it); strengths and tensions in one view; birth-time sensitivity exactly as the verdicts give it; functional roles for this lagna |
| personality | Personality and temperament | 1,000-1,400 | The rising sign; the lagna nakshatra; the lagna lord and its placement; planets in the lagna or aspecting it; the Sun; the Moon sign briefly (detail is in Mind); synthesis of temperament |
| mind | Mind, emotions and inner life | 600-900 | The Moon's sign, house and nakshatra; aspects and company of the Moon; Moon yogas (Sunapha/Anapha/Durudhara/Kemadruma) if present; Mercury and thinking style; emotional needs and patterns |
| career | Career and vocation | 1,100-1,500 | The 10th house and its lord; planets in the 10th; career significators (Sun, Saturn, the Amatyakaraka, strongest planets); D10 if present (state birth-time caution); suitable fields (only from entries); working style; career timing pointer |
| finance | Finance and wealth | 600-900 (code adds a wealth-houses table after the first paragraph) | The wealth houses one by one (2nd, 11th, 5th, 9th); Dhana yogas present; gains versus expenses (11th vs 12th); overall; timing pointer |
| health | Health and vitality | 400-600 (code adds a body-correspondence table after the first paragraph) | Overall constitution (lagna, lagna lord, Sun, Moon); traditional sensitivities from the 6th/8th/12th, at most a few, general; periods to take more care (pointer). Open with one sentence that this is traditional astrology, not medical advice |
| relationships | Relationships, marriage and partner | 800-1,100 | The 7th house and lord; Venus (and Jupiter for women's charts where sources say so); the Darakaraka and D9 notes; Manglik status exactly as the calculator and dosha entry give it, with its cancellations; timing pointer; friendships (11th). Never raise separation, loss of a spouse, divorce, more than one marriage or infidelity, not even as something "to keep in view"; where an entry lists such results, write only the softer theme it points to (e.g. "the relationship needs patience and steady effort") |
| family | Family, home, siblings, children and education | 650-900 | Family of origin (2nd); mother and home (4th, Moon); father and fortune (9th, Sun); siblings (3rd, 11th, Mars); children (5th, Jupiter); education (4th, 5th, Mercury, Jupiter) |
| spirituality | Spirituality, the 8th and 12th houses, hidden talents and foreign links | 600-900 | The 8th house; the 9th (dharma, teachers); the 12th and Ketu; karakamsha if present; hidden talents; foreign links (only where entries mention travel/foreign) |
| yogas | Yogas and doshas | 800-1,100 (no tables: code builds the yoga and dosha tables) | Each yoga present: what it means, how strong it is in this chart (use the entry's weight notes and the calculator's conditions), when it gives results; doshas: each one the calculator reports, with its provenance and cancellations, in calm language; notable absent yogas only if useful |
| guidance | Strengths, challenges, guidance and optional remedies | 700-1,000 | **Written last**, from the finished sections (read every `sections/*.md` file) plus its own input. Strengths to build on (3-5) and challenges to manage (3-5), each a synthesis across sections in one or two sentences, pointing to the section that explains it, never re-describing signs; practical guidance by life area: what to do and how to work with the chart's tendencies (habits, choices, attitudes, drawn from the sections), each with at most one dated period, and at most five dated periods in the whole section (this is not a second Timeline); traditional remedies: keep the heading `### Traditional remedies (optional)` (code places the remedies table after it) with one or two sentences of framing, and put the one-line practice per planet in the `remedies` rows block, not in a prose list (always optional, no gemstone pushing). Must not contradict any finished section. Write it as prose an astrologer would say, not an index: section pointers sparingly (at most one per subsection), and end with a short closing word (3-4 sentences) on the chart as a whole |

## Doshas and yogas: extra care

- State a dosha exactly as computed (present, absent, cancelled, which reference points). If the entry says the
  dosha is a later or regional construct, say so plainly; many readers have been frightened by such labels.
- A yoga's name alone is not a promise. Use its weight notes ("common", "needs strength") and say when it is modest.
