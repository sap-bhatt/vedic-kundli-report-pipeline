# Section 11: Timeline

Length: 2,000-2,800 words of visible text. Output Markdown, starting with `## Timeline`.

## What goes in, in this order

1. **How timing works (one short paragraph).** Vimshottari dashas: nine major periods of fixed length, starting from
   the lord of the Moon's nakshatra at birth; the person's starting period and balance from `chart.dasha_balance_at_birth`.
   A period brings forward what its planet rules and signifies in this chart; slow transits show when promises trigger
   (only if a principle entry says so).
2. **Mahadasha table: built by code.** Do not write it. Keep the heading `### How timing works` (code places the
   mahadasha table after it) and go straight on to the past periods.
3. **Past periods: validation notes.** One short paragraph per past mahadasha, phrased as "this period often coincides
   with...". Build each from that planet's placement and lordship entries (`placement_entries`), its `dasha_md`
   entry if present, and the principles that apply. These are checks the reader can compare with their life, not claims.
4. **The current mahadasha (the core of the section).** Explain what the period lord does in this chart: houses ruled,
   house occupied, dignity, associations and aspects, and for Rahu/Ketu the sign lord, nakshatra lord and aspects, as the
   principles direct. Then the `dasha_md` entry's conditions that hold, and what they mean together. Give a realistic
   overall expectation, including how the period may unfold over time if `phases` is given.
5. **Sub-period table: built by code.** Do not write it. Start the sub-period paragraphs under a heading containing
   "Sub-period" (e.g. `### Sub-periods of the Rahu period`); code places the table there.
6. **Every sub-period of the current mahadasha, and later ones listed in the input.** Cover each one in the input,
   to the end of the current mahadasha even if it runs past ten years; never mention a "horizon" or "window" of the
   input in the visible text. One paragraph each (longer for the current one and for any that the
   checked conditions mark as clearly strong or clearly difficult). Use the `dasha_ad` entry's conditions that hold,
   the sub-lord's role and placement, its house counted from the period lord (`ad_house_from_md_lord`), and the
   principles that apply. Say plainly which sub-period is the key window of the next decade and why.
   **Choosing the key window.** The tally line counts conditions, and several similar rules can each add a point, so
   never pick by count alone. Rank sub-periods in this order: (1) the sub-lord's functional role (yogakaraka first, then
   lagna lord and trikona lords; lords of 3/6/8/11 last; Rahu and Ketu rule no houses, so rank a node sub-period by its
   sign lord's role and always below a planet that holds that role itself: a trikona lord's own sub-period outranks a
   node sitting in a trikona); (2) whether any bad condition holds (none is a strong sign);
   (3) dignity (exalted, moolatrikona, own); (4) whether it forms a yoga present in the chart ("forms:"), which the
   principles say gives results in its own periods; (5) then the tally; (6) finally, check the slow timers for the top two: a sub-period mostly covered by a Sade Sati
   peak or an Ashtama/Kantaka Dhaiya phase drops below an otherwise close rival that runs under supportive transits,
   and agreement of the Yogini period and a double transit on a good house lifts a sub-period. Name the reasons in plain words. If a second
   sub-period is also strong, describe it as another bright stretch rather than a rival.
   **Use the chart-specific links.** For each period lord, mention when relevant: any yoga it forms, whether it is the
   lagna nakshatra lord, and the houses it rules. These are what make the section about this person. Chara karaka
   roles take their meaning only from the "Chara karaka meanings" block of the input; use it where a period lord
   holds such a role, and say no more than that block says.
   **Sub-periods already past** in the current mahadasha: one or two sentences each, as validation checks.
7. **Transits, Sade Sati and secondary timers.** Use the "Slow transits", "Sade Sati and Dhaiya" and "Yogini" sections
   of the input; each stretch has its library entry and the conditions that hold for it (including whether Saturn is
   the yogakaraka, the transit sign's dignity and the dasha running at the time). Cover: where Saturn and Jupiter are
   now counted from the Moon and what that brings, their coming sign changes and what each new position means; the
   current Sade Sati/Dhaiya phase and the coming ones (and, in the past-period notes, the past ones as validation
   checks); how each transit sits with the dasha running then (a hard transit during a supportive sub-period, or the
   reverse); and the current and next Yogini periods with their entries. Group back-and-forth sign changes into one
   stretch ("Saturn moves into Aries in June 2027, returns to Pisces briefly, and settles in Aries from Feb 2028").
   Chara periods have no library entry yet: give their dates only, as a timing marker.
   **Computed timing windows.** The input lists double-transit windows (Jupiter and Saturn both acting on a house from
   the lagna) and Saturn's passage over natal planets. Use them to name the concrete windows the reader should watch:
   pick the houses that matter for the running sub-periods (e.g. the 7th for partnership, the 10th for career, the 4th
   for home and property, the 5th for children and creative work, the 2nd/11th for money) and say which sub-period
   each window falls in. Saturn over a natal planet brings that planet's houses under review for those dates; say so
   using the planet's houses, without predicting events. Group a house's back-to-back windows into one stretch.
7b. **Past timers as checks.** In the past-period notes, name each past Sade Sati/Dhaiya phase with the sub-period it
   fell in ("the first Sade Sati, Sep 2004 - Aug 2012, ran through most of the Moon period"), as a check.
7c. **Optional remedies.** For the current sub-period and the key window, you may add one line with the remedy the
   entry gives ("Remedies (optional)"), presented as an optional traditional practice.
8. **The next ten years at a glance: the table is built by code; you fill its last column.** Write the heading
   `### The next ten years at a glance` and one or two sentences under it naming the key window and the main bright
   and testing stretches. Write no list or table of periods there: code builds the table (sub-periods, double-transit
   stretches and Saturn phases in date order, with their dates) and places it after that heading.
9. **Rows block.** `report_inputs/timeline_rows.md` (from `tools/report_input.py`) lists the exact row keys. At the end
   of the section, just before the trace block, add one hidden line of valid JSON with one entry per listed key:

   `<!-- rows:summary_10y {"Rahu-Jupiter": "one line", "DT7-2027": "one line", "SS-rising-2034": "one line"} -->`

   Each value is one plain line (up to 20 words, no dates) on what that stretch is about, consistent with your
   paragraphs, under the same guardrails as the visible text. A key you leave out shows "-".

## Rules for this section

- Never write a mahadasha table, a sub-period table or a list of the next ten years: code builds them.
- Every date comes from the input. Never compute or round dates yourself; copy them (you may write them as "Jan 2027").
- If a period has `library_entry_missing`, do not invent its meaning: use only the placement entries and principles
  for that planet, and keep the paragraph short.
- Condition `status` is final (see shared rules). When both good and bad conditions hold for a sub-period, say it is
  mixed and name what each side is about.
- Trace block lines for this section: `Timeline-intro`, `Timeline-past`, `Timeline-current`, one per sub-period
  (`Timeline-<MD>-<AD>`), `Timeline-transits`. List entry ids (e.g. `dasha_principle/houses_ruled_and_occupied`), never
  the P-codes; each P-code line in the input shows its id. Never write a P-code in visible text either.
