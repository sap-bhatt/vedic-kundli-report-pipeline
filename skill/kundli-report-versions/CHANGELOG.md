# kundli-report changelog

## v0.15 (2026-11-11) - code-built tables, model-row tables, layout, server-ready PDF; run 5 = 74.8
Run 5: glance 77.9, personality 75.3, mind 75.6, career 72.4, finance 81.6, health 71.7, relationships 77.8, family 75.0,
spirituality 73.4, yogas 81.9, guidance 76.9, timeline 68.7 (two -5 leaks; 77.0 weighted without them). Repetition 29,
contradictions 7, readability 3/5, key window agrees.
- tools/report_tables.py, tools/table_rows.py, profession layer, assembler rework (see docs/STATUS.md).
- timeline.md: no mahadasha/sub-period tables or ten-year list from the writer (code builds them); rows block for the
  ten-year table. life_areas.md: rows blocks for finance, health, guidance; Yogas writes no tables.
- report_input.py: "Table rows to fill" blocks; timeline_rows.md; Career input gets profession/rule and the three indicators.
- lint: "Describe it/this", "Call it", "run only to", "named here", "data runs/range", "(around|near|with) fire".
- chart_verdicts.py: aspect rows say "<A> sits in house X and casts its aspect N houses ahead, onto house Y".

## v0.14 (2026-11-10) - after full report run 4 (weighted 74.8, best so far; run 3 72.2, run 2 74.1)
Run 4 (v0.13): glance 79.1, personality 70.8, mind 70.6, career 65.5, finance 78.3, health 73.7, relationships 77.0,
family 68.8, spirituality 73.8, yogas 77.6, guidance 74.0, timeline 78.9 (key window agrees). Repetition 28,
contradictions 4, readability 3/5. Three -5 for writer instructions copied into the text (career "Speak of advisory
and service leadership. This is not a promise of ...", family "Lead with the intelligence...", yogas "Name both planets").
- lint: imperative_to_writer group (sentence-initial "Lead with", "Speak of", "Frame it/this", "Present it", "Emphasise
  the", "Stress the", "Do not copy/say/mention"); "this is not a promise", "speak of X and".
- chart_verdicts.py: each aspect row gives its house distance and "full strength" (special aspects named); a closing
  line says no listed aspect is partial (personality called Mars's 4th aspect 3/4 from a library note).
- repeat_finder.py: Yogas and doshas not flagged for placements (they are yoga conditions there).
Not re-run.

## v0.13 (2026-11-10) - after full report run 3 (weighted 72.2; run 2 74.1)
Run 3 (v0.12): glance 73.4, personality 73.5, mind 76.3, career 70.6, finance 80.3, health 72.6, relationships 77.0,
family 76.8, spirituality 71.0, yogas 76.5, guidance 64.2, timeline 66.8 (81.8 before three -5: fevers/fire/weapons,
"care with fevers", "illness"; key window agrees). Repetition 29 (was 32): the editor cut only ~7% of words; core
placements still in 8-10 sections. Contradictions 6. Readability 3/5. 12.5k words vs 14.0k benchmark.
- tools/repeat_finder.py (new): flags sentences restating a planet's placement/dignity outside its owner and term
  definitions given again; editor.md makes that list the main work list (one edit per flagged sentence).
- lint: health_list group (fevers, weapons, wounds, injury, illness, disease, burns, accidents, sharp tools); leaked
  phrases "named here only as a placement", "lead with the strengths".
- periods ahead: each row carries the sub-lord's tone (supportive / neutral / mixed or demanding / node) so a 3/6/11
  lord's period is not sold as the best time (run 3: Career and Guidance called the Sun-Moon stretch the peak while
  the Timeline called the Sun one of the less supportive sub-lords).
- report_input.py: Kaal Sarp gets a plain VERDICT line (not present / partial / full); the "Kulik" type name in the
  data had been read as a partial form three runs running.
- chart_verdicts.py: dispositor chains name which planets end in each loop; a planet in its own sign that disposes
  of no one is no longer called "final dispositor".
- life_areas.md guidance: habits and choices first, at most one dated period per area and five in all; one remedy
  line per planet with a remedy entry.

## v0.12 (2026-11-10) - repetition (run 2: 32 points in 3+ sections; holdouts 29-37)
- chart_verdicts.py `period_assignment`: each upcoming sub-period goes to at most two life sections, judged by the
  sub-lord only (significator 5, ruled house 3, ruled dusthana 1, occupied house 2); double-transit windows only to the
  house's owner section; Saturn over a natal planet only to that planet's owner; Sade Sati only to Mind (and
  Guidance); Chara dates only to Relationships. Glance gets no periods block. (Run 2 had the same sub-periods in 5-7
  sections because the period lord tied every sub-period to every section.)
- `ownership_map` written as report_inputs/ownership_map.md.
- New editor pass (references/editor.md + tools/apply_edits.py): after sections 1-11, a model proposes exact cuts of
  points told outside their owner; code applies only unique exact matches that shorten and add no numbers, never in
  headings, tables, the trace block or the Timeline. Guidance is then written from the edited sections.
- dasha_facts.py: mahadasha age column in completed years (was a calendar-year difference, off by one).

## v0.11 (2026-11-10) - after the 3 made-up holdouts (Meera 75.8, Arjun 73.9, Devika 75.4; v0.10)
- report_input.py: boolean dosha flags (ghata, ganda_moola, guru_chandal) were silently dropped; now included.
  Running MD and AD spans in every header. Disagreement notes up to 1,500 chars (were cut at 400).
- dasha_facts.py / chart_verdicts.py: Moon benefic when >= 90 deg from the Sun (Shukla Ashtami to Krishna Ashtami),
  not by paksha; `moon_waxing` fact unchanged for conditions. Neecha Bhanga participants labelled as cancelling factors.
- timeline.md key-window ranking: nodes rank by sign lord's role, below planets holding the role; step 6 slow-timer
  tie-breaker (Sade Sati peak / Ashtama or Kantaka Dhaiya lowers; Yogini + double transit on a good house lifts).
  Key window agreed on 3 of 5 charts tested (tuned chart, real chart 2, Meera); missed on Arjun (node) and Devika (Dhaiya).
- life_areas.md relationships: no separation / loss of spouse / multiple marriage / infidelity, even as a caution.
- lint: marriage_calamity group.
Not re-run yet.

## v0.10 (2026-11-10) - after full report run 2 (weighted 74.1; run 1 71.1)
Run 2 (v0.9): glance 73.6, personality 74.0, mind 73.4, career 75.6, finance 62.0 (three -5 for copied "(explained in X;
one clause)" tags; 72.0 without), health 74.5, relationships 77.0, family 80.1, spirituality 62.1 (two -5 for "no source
here gives..." absence wording), yogas 80.0, guidance 66.2, timeline 77.5 (key window agrees). Coverage ~50-61 (was
29-65), groundedness 84-96. Contradiction topics 7 (was 8, all minor/moderate now; Manglik, Mars-on-Saturn and Mercury
distance resolved). Repetition WORSE: 32 points in 3+ sections (was 18): verdicts restated as background and the same
dated sub-periods in 5-7 sections. Readability 3/5.
- Verdict block: reference facts, not content; use only where it changes the area's reading.
- Periods ahead: at most three, area-specific; life_areas.md rule 4 to match.
- life_areas.md rules 9 (no restating core placements or re-defining terms) and 10 (no self-instructions or
  absence statements); guidance as prose with a closing word, pointers sparingly.
- lint: copied tags ("one clause", "(explained in X)"), absence wording ("no source gives", "is recorded", "none is
  claimed", "not reported as met", "nothing more is said"), self-instructions ("keep to one general note").
- chart_verdicts.py: Health must-cover list; D9 dignity uses one function (moolatrikona vs own was inconsistent).
- dasha_facts.py: double-transit rows say "aspects it from <sign>" / "in it (<sign>)" (Haiku misread the sign in
  brackets as the house's sign and dropped valid rows).

## v0.9 (2026-11-10) - after full report run 1 (weighted 71.1)
Run 1: accuracy 90-98, groundedness 80-95, coverage 29-65; 18 points repeated in 3+ sections; 5 cross-section
contradictions (Mars/Moon aspect on Saturn, Manglik, Mercury-Sun distance, Saturn aspect on the 2nd, Mercury's nature);
readability 3/5; guidance generic.
- tools/chart_verdicts.py (new): one code-computed "Chart verdicts" block, identical in every section input and the
  timeline input: per-planet net dignity (neecha bhanga tests met), distance from the Sun with combustion limit, natural
  vs functional nature, D9/D10 sign/house/dignity, aspect natures (incl. mutual, node caveat), conjunction distances,
  Manglik exactly as computed incl. cancellation, chart shape (kendras, dusthanas, D9 strength, dispositor loops),
  D9 7th and D10 10th, birth-time sensitivity (lagna/D9/D10 position in division).
- Ownership map: entries owned by another section arrive trimmed and tagged "(explained in X)"; one clause at most.
- "Periods ahead for this section" block (dated sub-periods tied to the section's houses/significators, double
  transits on those houses, Saturn over natal significators, Sade Sati for mind/health/career, Chara dates).
- "Must cover" checklist per section (lagna, lagna nakshatra and lord, vargottama, aspects on the lagna/Moon, 7th/10th
  facts, D9 7th, Manglik, wealth houses...).
- life_areas.md: rules 4 (dated timing paragraph), 6 (verdicts final), 7 (ownership), 8 (must cover); glance opens with
  chart shape; guidance written last from the finished sections.
- lint + rules self-check: "marked as", "this section", "calculator", "verdict", "must cover".

## v0.8 (2026-11-10) - after iteration-7 grade (76.1, 0 violations)
Iteration 7 (v0.7): coverage 63.9 (covered 66.1, gap 45.5; sade_sati 100, yogini 91.7), accuracy 98.7, groundedness 90.0,
tone 80, 0 violations, lint 0 findings (self-check made 4 fixes). Contradiction: Moon period read as steady while the first
Sade Sati overlaps it. Word score 67.5, date recall 0.98.
- dasha_facts.py: chara karaka meanings block (karaka layer) incl. karakamsha.
- timeline.md: karaka meanings only from that block; 7b past Sade Sati/Dhaiya named with the period they fell in;
  7c optional remedy line for the current sub-period and the key window.
- life_areas.md + tools/report_input.py + tools/assemble_report.py: full report (sections 1-10, 12) and assembly.

## v0.7 (2026-11-10) - after iteration-6 grade (66.4; 76.4 before two -5 guardrail penalties)
Iteration 6: coverage 67.1 (best; covered 69.9, gap 40.9), accuracy 97.9, groundedness 91.2 (best), tone 76; word score
67.7 (best). Violations: Rahu-Venus "brings ... illness"; a past sub-period stated as fact. Real-chart-2 holdout word score
65.8 vs control 55.8 (claim grade pending).
- tools/eval/lint_report.py: guardrail lint on visible text (fatalistic "brings illness/losses", death/maraka words,
  machinery words, copied instructions, entry ids, gemstone push). Iterations 1-6: 16, 5, 7, 22, 9, 2 findings; real chart 2: 0.
  assemble_report.py prints lint findings for every section.
- dasha_facts.py: "true because" on holding conditions with top-level `or` (iteration 6 credited Ketu's relief to the
  Sun/Mercury, which are malefics here; it held through Jupiter's aspect).
- shared/rules.md: final self-check list (fatalistic verbs, death words, machinery words, past-as-fact, fact mismatch,
  kendra = 1/4/7/10, credit only the true part).

## v0.6 (2026-11-10) - after iteration-4 grade (71.3; 76.3 before a -5 guardrail penalty)
Iteration-4 grade (transits/sade_sati/yogini now counted as library_covered): coverage 65.4 (covered 69.5, gap 50.0;
transits 46.9, sade_sati 100, yogini 68.8, past 59.1), accuracy 97.3, groundedness 86.2, tone 72, 1 violation
(Saturn transit stated flatly as "bringing losses, illness and separation"). Iteration 5 (v0.5) word score 63.2 (best).
- shared/rules.md: hard classical lists for transits/Sade Sati framed as what texts associate, paired with holding
  softeners; never "brings losses/illness".
- timeline.md: every sub-period of the current mahadasha covered; no "horizon"/"window" wording (iteration 5 skipped
  Rahu-Moon and Rahu-Mars as "after the ten-year window").
Open: double-transit windows and Saturn crossing natal planets need code (biggest remaining transit gap).

## v0.5 (2026-11-10) - after iteration-3 grade (76.8)
Iteration-3 grade: coverage 58.5 (library_covered 68.8, gap 44.8), accuracy 98.6, groundedness 86.1, tone 84, 0 violations,
no contradictions (key window now Rahu-Saturn, matching the benchmark).
- timeline.md: removed my own "soul planet"/"career planet" glosses (unsupported: no karaka layer yet); karaka labels
  are facts only until a library entry gives meaning; past sub-periods of the current MD as short validation checks.
- shared/rules.md: no pipeline wording in visible text ("conditions", "the code", "library", "input", "checked");
  at most one general health note per period, no organ/disease lists.
- dasha_facts.py: the current mahadasha's sub-periods are all included (past ones marked as checks), not cut at the
  10-year horizon (iteration 3 missed Rahu-Rahu, Rahu-Moon, Rahu-Mars).

## v0.4b (2026-11-10) - timing layers wired in (used by iteration 4)
- dasha_facts.py: transit (Saturn, Jupiter from the Moon), Sade Sati/Dhaiya and Yogini entries per stretch, with the
  running dasha, transit-sign dignity, Saturn's role and vedha (current date only) checked; repeated entries printed once;
  unjudgeable manual conditions hidden for timing layers (count shown). Input 42.6k tokens.
- timeline.md item 7 rewritten to interpret transits, Sade Sati and Yogini from their entries.

## v0.4 (2026-11-10) - after iteration-2 grade (67.7; 72.7 before a -5 guardrail penalty)
- shared/rules.md: multi-part manual conditions are met only when every part is met (Rahu-Sun "lords of 1, 9 and 10"
  was judged met from the 9th lord alone); maraka wording banned from visible text ("danger to life", "death",
  "longevity", "maraka") after a guardrail violation.
Iteration-2 grade: coverage 51.9 (library_covered 60.7, gap 41.7), accuracy 97.9, groundedness 87.5, tone 76.

## v0.3 (2026-11-10) - timeline pilot, iteration 3
Why: iteration-1 grade 71.1 (coverage 52, accuracy 98.3, groundedness 88.8, tone 68). Key-window contradiction (picked
Rahu-Venus over Rahu-Saturn), transit Jupiter called retrograde, Mercury called benefic, chart-specific links missing.
Changes:
- dasha_facts.py: chart-specific natural benefics (Mercury malefic when joined with a malefic; Moon benefic only when
  waxing); 7-karaka chara karakas; lagna nakshatra lord; calculator yogas + each planet's yoga membership ("forms:");
  per-period tally of holding conditions; transit retro flags in Markdown; all nine mahadashas listed (beyond the
  horizon = table row only); fixed regex bug that dropped all sub-period principle hits.
- shared/rules.md: holding conditions outrank an entry's general summary; use only given benefic/karaka/role/yoga labels.
- sections/timeline.md: key-window ranking order (role, no bad conditions, dignity, yoga, then tally); use chart-specific links.
Open: karaka meanings have no library layer yet (step 5); tone guidance unchanged pending iteration-2 grade.

## v0.2 (2026-11-10) - iteration 2
Input rendered as compact Markdown (65k -> 22k tokens): only holding/manual conditions, mahadasha-only rules listed once.
Haiku read the whole input (iteration 1 had skipped parts). Word score 61.2 (iteration 1: 61.6; control 51.7).

## v0.1 (2026-11-10) - iteration 1
First draft: SKILL.md + shared/rules.md + sections/timeline.md; JSON input. Word score 61.6; grade 71.1.
