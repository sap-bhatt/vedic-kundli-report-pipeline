# chart_data.json format

Everything in the report pipeline after the chart calculation reads one file, `chart_data.json`. The chart
calculator (`tools/chart_data.py` with `tools/engine/kundli_maker.py`) writes it, but you can produce it with any
calculator you like and skip ours. This page lists every field the tools read, what it means, and what happens when an
optional field is missing.

- Check a file with `python tools/validate_chart.py chart_data.json` (errors, warnings and sanity checks; exit code 1
  on errors). Add `--schema` to also check it against [`chart_data.schema.json`](chart_data.schema.json) (JSON
  Schema draft 2020-12) when the `jsonschema` package is installed.
- Three complete examples: `examples/meera/chart_data.json`, `examples/arjun/chart_data.json`,
  `examples/devika/chart_data.json`.
- Fields not listed here are ignored, so you may add your own.

**REQUIRED** means a tool stops with an error (or prints wrong facts) without it. **OPTIONAL** fields can be left out;
the "if missing" column says which part of the report is skipped or reduced. The claims below were checked by deleting
each field from an example chart and running every consumer (`report_input.py`, `dasha_facts.py`,
`chart_verdicts.py`, `report_tables.py`, `table_rows.py`, `assemble_report.py`, `lookup.py`).

## Conventions

| Topic | Convention |
|---|---|
| Zodiac | Sidereal, Lahiri (Chitrapaksha) ayanamsa. The library and the tests assume Lahiri; another ayanamsa runs but is untested, and the report cover still says "Lahiri". |
| Longitudes | `lon`: decimal degrees, `0 <= lon < 360`, sidereal. |
| Degree inside a sign | `deg_in_sign`: a display string, e.g. `"21°58'42\""` (any text; the chart drawing keeps the part up to the first `'`). Transit `deg`: a number, degrees within the sign (0-30). |
| Sign names | English, title case, exactly: `Aries Taurus Gemini Cancer Leo Virgo Libra Scorpio Sagittarius Capricorn Aquarius Pisces`. Used for `sign`, every `vargas` value, house signs, transits and ingresses. (Only `chara_current_and_next.sign` and `avakhada` may use Sanskrit names such as `Mithuna`.) |
| Sign numbers | `sign_num`: 1-12, Aries = 1 ... Pisces = 12, and must match `sign` and `lon`. |
| Houses | Whole-sign, 1-12, counted from the lagna sign: house 1 = the lagna sign, house 2 = the next sign, and so on. A planet's house = `(planet sign_num - lagna sign_num) mod 12 + 1`. |
| Planets | The nine grahas `Sun Moon Mars Mercury Jupiter Venus Saturn Rahu Ketu`, each exactly once (names spelt exactly so). `Gulika` is optional. Any other body is ignored. Ketu is exactly opposite Rahu (mean or true node, your choice; the cover says "mean lunar nodes"). |
| Aspects | Graha drishti by sign: every planet aspects the 7th sign from itself; Mars also the 4th and 8th, Jupiter the 5th and 9th, Saturn the 3rd and 10th, Rahu and Ketu the 5th and 9th. The tools recompute planet-to-planet aspects with this rule; `houses[].aspected_by` should follow it too. |
| Dignity | `exalted`, `moolatrikona`, `own`, `friend`, `neutral`, `enemy`, `debilitated` (natural friendship); Rahu and Ketu may use `-` when neither exalted nor debilitated. |
| Nakshatras | The 27 names exactly as the library spells them: `Ashwini Bharani Krittika Rohini Mrigashira Ardra Punarvasu Pushya Ashlesha Magha "Purva Phalguni" "Uttara Phalguni" Hasta Chitra Swati Vishakha Anuradha Jyeshtha Mula "Purva Ashadha" "Uttara Ashadha" Shravana Dhanishta Shatabhisha "Purva Bhadrapada" "Uttara Bhadrapada" Revati`. Another spelling still runs, but that nakshatra's library entry is not found. Pada: 1-4. |
| Vargas | Divisional charts as sign names: `vargas.D9` (navamsa) is required; `vargas.D10` (dashamsa) is optional; `D1`, `D2`, `D3`, `D7`, `D12` may be present but are not read. |
| Dates | ISO `YYYY-MM-DD` strings, zero-padded. The tools compare dates as text, so `2026-1-5` or `05/01/2026` give wrong results. |
| Dasha years | Vimshottari, 120-year cycle, years of 365.25 days. |
| "Now" | The as-of date is the date in the `transits_YYYY_MM_DD` key unless `--now` is given to the input builders. Running periods, "periods ahead", ages and the transit tables are all relative to it. |

## Top-level keys

| Key | Status | Used for | If missing |
|---|---|---|---|
| `birth` | REQUIRED | ages, first dasha start, the cover | input builders and assembly stop |
| `settings` | REQUIRED (`ayanamsa_value` only) | the cover line; `node_exalt` for a table footnote | assembly stops |
| `lagna` | REQUIRED | everything | every tool stops |
| `planets` | REQUIRED | everything | every tool stops |
| `houses` | REQUIRED | section inputs, house table, wealth and health tables | `report_input.py` stops |
| `vimshottari` | REQUIRED | the timeline, running period, dasha tables | input builders stop |
| `transits_YYYY_MM_DD` | REQUIRED (Jupiter and Saturn) | the as-of date, transit timing, double transits, transit table | input builders stop |
| `jupiter_ingresses_next_6y`, `saturn_ingresses_next_6y` | OPTIONAL | transit stretches, double-transit windows, sign-change table | the planet is assumed to stay in its current sign for one year; double-transit windows end after a year; the sign-change table is skipped |
| `panchang_at_birth` | OPTIONAL | Moon waxing/waning, birth tithi/weekday/yoga/karana entries, panchang table | the Moon counts as waning in dasha conditions; those Personality entries and table rows are left out |
| `avakhada` | OPTIONAL | gana and nadi entries, panchang table | those entries and rows are left out |
| `graha_yuddha` | OPTIONAL | planetary-war notes in the D1 table | no war notes (give `[]` when there is none) |
| `yogini_current_and_next` | OPTIONAL | Yogini periods in the timeline | Yogini left out of the timeline |
| `chara_current_and_next` | OPTIONAL | Chara periods table; dates in Relationships | table and line skipped |
| `yogas_present` | OPTIONAL | yoga entries in every section, yoga table, "forms: ..." notes | no yogas anywhere; the yoga table is skipped |
| `yogas_checked_absent` | OPTIONAL | nothing yet (kept for future "absent yogas" coverage) | no effect |
| `doshas` | OPTIONAL | Manglik verdict and table, dosha table and entries, Sade Sati phases | all of these are left out |

## `birth` (REQUIRED)

| Field | Status | Type, example | Notes |
|---|---|---|---|
| `date` | REQUIRED | `"1988-02-14"` | ISO date. Ages are counted from it; dasha periods that started before it are shown from it. |
| `time` | REQUIRED | `"06:40 IST"` | Display only (cover). |
| `place` | REQUIRED | `"Jaipur, Rajasthan (26.91N, 75.79E)"` | Display only (cover). |
| `sex` | OPTIONAL | `"female"` / `"male"` | Sets "husband"/"wife" wording for the spouse. Missing or anything else: "partner". |

## `settings` (REQUIRED object)

| Field | Status | Notes |
|---|---|---|
| `ayanamsa_value` | REQUIRED | String printed on the cover, e.g. `"23°41'31\""`. |
| `node_exalt` | OPTIONAL | e.g. `"taurus_scorpio"`; adds a footnote on node dignity to the D1 table. Missing: no footnote. |
| `ayanamsa`, `ayanamsa_deg`, `node`, `dasha_year_days`, `houses`, `sunrise`, `gulika`, `node_aspects`, `manglik_houses`, `benefics` | OPTIONAL | Informational; not read by the pipeline. The cover always reads "Computed with Swiss Ephemeris, Lahiri ayanamsa (...), mean lunar nodes, whole-sign houses": if your calculator differs, edit that line in `tools/assemble_report.py`. |

## `lagna` (REQUIRED object)

| Field | Status | Type, example | If missing |
|---|---|---|---|
| `lon` | REQUIRED | `291.9782` | verdicts (birth-time sensitivity) stop |
| `sign` | REQUIRED | `"Capricorn"` | inputs and cover stop |
| `sign_num` | REQUIRED | `10` | every tool stops |
| `deg_in_sign` | REQUIRED | `"21°58'42\""` | inputs and chart drawing stop |
| `nakshatra` | REQUIRED | `"Shravana"` | inputs stop |
| `vargas.D9` | REQUIRED | `"Cancer"` | verdicts and the D9 drawing stop |
| `vargas.D10` | OPTIONAL | `"Aries"` | see "D10" below |
| `pada` | OPTIONAL | `4` | the D1 table shows `-` |
| `nak_lord` | OPTIONAL | `"Moon"` | derived from the nakshatra name |

## `planets` (REQUIRED list)

One object per body. The nine grahas must all be present, each once.

| Field | Status | Type, example | Notes, if missing |
|---|---|---|---|
| `name` | REQUIRED | `"Sun"` | Exact spelling. |
| `lon` | REQUIRED | `300.8612` | Sidereal longitude; also used for chara karakas, combustion distance and avasthas. |
| `sign` | REQUIRED | `"Aquarius"` | |
| `sign_num` | REQUIRED | `11` | |
| `deg_in_sign` | REQUIRED | `"0°51'40\""` | Shown in the verdicts and tables. |
| `nakshatra` | REQUIRED | `"Dhanishta"` | |
| `nak_lord` | REQUIRED | `"Mars"` | Lord of the nakshatra (Vimshottari lord). |
| `dignity` | REQUIRED | `"enemy"` | See Conventions; nodes may use `"-"`. |
| `vargas.D9` | REQUIRED | `"Libra"` | Vargottama, D9 dignity, navamsa drawing, profession indicators, karakamsha. |
| `vargas.D10` | OPTIONAL | `"Aquarius"` | See "D10" below. |
| `pada` | OPTIONAL | `3` | D1 table shows `-`. |
| `house` | OPTIONAL | `2` | Recomputed from `sign_num` when missing. |
| `retro` | OPTIONAL | `false` | Treated as direct: no retrograde notes, `X_retro` conditions false. Ignored for the nodes. |
| `speed` | OPTIONAL | `1.011` (deg/day) | Picks the combustion orb (retrograde orbs for Mercury and Venus when negative); missing = direct orb. |
| `combust` | OPTIONAL | `false` | Treated as not combust. |

**Gulika** (OPTIONAL entry with `"name": "Gulika"`): needs `sign` and a `vargas` object (may be `{}`; give `D9` to draw
it in the navamsa); `deg_in_sign` and `house` are shown in the D1 table when present. Without Gulika, it is simply
absent from the D1 table and the chart drawings.

**D10:** give `vargas.D10` for the lagna and all nine grahas, or for none of them. A partial D10 stops the verdicts.
Without D10, the D10 table, the D10 line of the verdicts and the career section's D10 notes are skipped (the D10 library
principles are still offered to the Career writer).

## `houses` (REQUIRED list of 12)

| Field | Type, example | Meaning |
|---|---|---|
| `house` | `1` | 1-12, each once. |
| `sign` | `"Capricorn"` | Whole-sign: house 1 = lagna sign. |
| `lord` | `"Saturn"` | Lord of that sign (Mars, Venus, Mercury, Moon, Sun, Mercury, Venus, Mars, Jupiter, Saturn, Saturn, Jupiter for Aries..Pisces). |
| `lord_in_house` | `12` | House the lord occupies. |
| `lord_in_sign` | `"Sagittarius"` | Sign the lord occupies. |
| `lord_dignity` | `"neutral"` | The lord's `dignity`. |
| `occupants` | `["Mercury"]` | Grahas in that sign (Gulika may be left out; non-grahas are ignored). |
| `aspected_by` | `["Ketu"]` | Grahas casting a graha drishti on that sign (rule under Conventions). |

All eight fields are REQUIRED in every house: `report_input.py` stops without them, and the wealth and health tables
use them.

## `vimshottari` (REQUIRED object)

| Field | Status | Shape | If missing |
|---|---|---|---|
| `balance_at_birth` | REQUIRED | `{"lord": "Ketu", "years": 1.6203}` | `dasha_facts.py` stops |
| `mahadashas` | REQUIRED | list of `{"md": "Ketu", "start": "1982-09-28", "end": "1989-09-28"}` | input builders stop |
| `antardashas_by_md` | OPTIONAL, strongly recommended | `{"Ketu": [{"ad": "Ketu", "start": ..., "end": ...}, ... 9 items], "Venus": [...], ...}` | see below |
| `current_md_antardashas` | OPTIONAL | list of `{"ad", "start", "end", "current"}` for the running mahadasha | used only when `antardashas_by_md` lacks the running mahadasha (sub-period table) |

Rules (checked by `validate_chart.py`):

- `mahadashas` are in Vimshottari order (Ketu, Venus, Sun, Moon, Mars, Rahu, Jupiter, Saturn, Mercury, then again),
  contiguous (each `end` equals the next `start`), and the birth date falls inside the first one. The first
  mahadasha's `start` is its theoretical start before birth (birth minus the elapsed part), so its full length is
  kept; `balance_at_birth.years` is the time from birth to its end. Our calculator gives 9 mahadashas (120 years).
- Each list in `antardashas_by_md` holds the 9 sub-periods in order starting with the mahadasha lord itself, the first
  starting and the last ending with the mahadasha.
- The as-of date must fall inside the mahadashas.

Without `antardashas_by_md`: the timeline computes sub-periods itself at date level (they can be a day off), but the
"Periods ahead" list in every section input is empty, the 10-year summary table loses its sub-period rows, and the
section headers show the running sub-period as "None".

## `transits_YYYY_MM_DD` (REQUIRED)

The key name carries the as-of date, e.g. `transits_2026_11_03` (underscores). Only the first key starting with
`transits_` is used. The value maps graha names to their positions on that date:

```json
"transits_2026_11_03": {
  "Jupiter": {"sign": "Leo", "deg": 0.4, "retro": false, "house_from_lagna": 8, "house_from_moon": 9},
  "Saturn":  {"sign": "Pisces", "deg": 14.9, "retro": true, "house_from_lagna": 3, "house_from_moon": 4},
  "Rahu":    {"sign": "Aquarius", "house_from_lagna": 2, "house_from_moon": 3}
}
```

| Item | Status | Notes |
|---|---|---|
| `Jupiter`, `Saturn` | REQUIRED | Slow-transit entries, Sade Sati timing, double transits. |
| `Sun`, `Moon`, `Mars`, `Mercury`, `Venus`, `Rahu`, `Ketu` | OPTIONAL | Rows of the current-transits table and the vedha list. Ketu is derived from Rahu when absent. |
| `sign`, `house_from_lagna`, `house_from_moon` | REQUIRED in every entry given | Houses counted whole-sign from the natal lagna and the natal Moon sign. |
| `deg`, `retro` | OPTIONAL | Degrees within the sign; retrograde flag (shown as "(R)"). |

## `jupiter_ingresses_next_6y`, `saturn_ingresses_next_6y` (OPTIONAL)

Sign changes after the as-of date, in date order, each a three-item list `[date, sign entered, house from the lagna]`:

```json
"jupiter_ingresses_next_6y": [["2027-01-26", "Cancer", 7], ["2027-06-27", "Leo", 8]]
```

A retrograde return into the previous sign is just another item. They define how long each transit stretch lasts and
the double-transit windows (`data_until` is the earlier of the two lists' last date plus one year). Missing: the
planet is assumed to stay in its present sign for one year, and the sign-change table is skipped.

## `panchang_at_birth` (OPTIONAL)

| Field | Example | Drives |
|---|---|---|
| `paksha` | `"Shukla"` / `"Krishna"` | `moon_waxing` in library conditions (`Shukla` = waxing). Missing: waning. |
| `tithi` | `"Ekadashi"` | Panchang table; Personality must-cover line. |
| `tithi_num` | `26` | Entry `panchang/tithi/<n>`; 1-30 (Shukla 1-15, Krishna 16-30). A Krishna tithi numbered 1-15 is shifted by 15. |
| `vara` | `"Saturday"` | Entry `panchang/vara/<day>`; English weekday. |
| `nitya_yoga` | `"Vajra"` | Entry `panchang/nitya_yoga/<slug>`. |
| `karana` | `"Balava"` | Entry `panchang/karana/<slug>`. |
| `sunrise`, `sunset` | `"1988-02-14 07:08"` | Panchang table (time part only). |

Without a field, its entry and table row are left out (the Personality must-cover line then prints "None" for that
item).

## `avakhada` (OPTIONAL)

A flat object of strings and numbers, shown row by row in the panchang table. Known keys get labels: `rashi`,
`rashi_lord`, `nakshatra`, `pada`, `nak_lord`, `gana`, `yoni`, `nadi`, `varna`, `vashya`, `lagna`, `lagna_lord`
(also `tatva`/`tattva`, `paya`, `yunja`, `naam_akshar`). `gana` (`Deva`/`Manushya`/`Rakshasa`) and `nadi`
(`Adi`/`Madhya`/`Antya`) select the library entries `panchang/gana/<slug>` and `panchang/nadi/<slug>`.

## `graha_yuddha` (OPTIONAL)

List of planetary wars: `[{"planets": ["Mars", "Venus"], "sep_deg": 0.4, "winner_by_latitude": "Venus"}]`; `[]` when
none. Adds "planetary war with ... (wins/loses)" to the D1 table notes.

## `yogini_current_and_next`, `chara_current_and_next` (OPTIONAL)

```json
"yogini_current_and_next": [{"yogini": "Siddha", "planet": "Venus", "years": 7, "start": "2025-07-05", "end": "2032-07-05", "current": true}],
"chara_current_and_next": [{"sign": "Mithuna", "years": 7, "start": "2021-02-13", "end": "2028-02-14"}]
```

The current period and the next ones (the calculator gives three). Yogini names: Mangala, Pingala, Dhanya, Bhramari,
Bhadrika, Ulka, Siddha, Sankata (entries `yogini/<name>`); `planet` must be a graha. Chara signs may be English or
Sanskrit; Chara periods are dates only (no library meanings yet).

## `yogas_present` (OPTIONAL) and `yogas_checked_absent` (OPTIONAL)

`yogas_present` lists the yogas that formed, each `{"name": ..., "fired": true, "variant": "...", "conditions": {...}}`;
`conditions` (an object, may be `{}`) is shown to the writers as the calculator's evidence and used to say how the yoga
forms. `name` selects the library entry `yoga/<slug>`; names the library knows (the calculator's names):

`Gajakesari`, `Ruchaka`, `Bhadra`, `Hamsa`, `Malavya`, `Sasa`, `Budhaditya`, `Chandra-Mangala`, `Adhi`, `Amala`,
`Raja (kendra-trikona lords)`, `Yogakaraka present`, `Dharma-Karmadhipati`, `Parivartana`, `Dhana (1/2/5/9/11 lords)`,
`Lakshmi`, `Saraswati`, `Vasumati`, `Viparita Raja (Harsha)`, `Viparita Raja (Sarala)`, `Viparita Raja (Vimala)`,
`Neecha Bhanga (<Planet>)`, `Sunapha`, `Anapha`, `Durudhara`, `Kemadruma`, `Shakata`, `Shubha Kartari (lagna)`,
`Papa Kartari (lagna)`, `Grahan`.

Any other name is lower-cased with spaces and hyphens turned into underscores; if no entry has that slug, the yoga is
named as a fact only. A planet's "forms: ..." note lists every yoga whose `conditions` mention that planet's name in
double quotes, so put planet names in `conditions` exactly.

Condition keys with special handling (all others are printed as `key: value`):

| Yoga | Keys |
|---|---|
| Raja, Dhana | `pairs: [{"pair": ["Mars", "Saturn"], "how": ["conjunct"], "houses_owned": {"Mars": [4, 11], "Saturn": [1, 2]}}]` |
| Yogakaraka present | `yogakaraka: ["Venus"]` |
| Viparita Raja | `lord`, `lord_house`, `strict_fired` |
| Neecha Bhanga (Planet) | `c1_sign_lord_kendra` ... `c6_lord_of_exalt_sign_kendra` (booleans; the true ones are counted "n of 6 tests"), `debilitation_lord`, `exalt_planet`. The name must be `Neecha Bhanga (<Planet>)`; the D1 and roles tables then show the planet as "Debilitated (cancelled)". |
| Budhaditya | `sun_mercury_sep`, `mercury_combust` |
| Sunapha, Anapha, Durudhara | `second`, `twelfth` (planet lists) |
| Shakata | `moon_from_jupiter`, `cancelled` |
| Grahan | `combos: ["Sun+Rahu"]` |

`yogas_checked_absent` is a list of yoga names checked and not formed. No tool reads it yet.

## `doshas` (OPTIONAL object)

Each key is one dosha. A value of `false` or `null` means "absent" (row "Absent" in the dosha table, no entry). `true`
means "present, flag only" (no reference points or cancellations). An object gives the details. Keys with library
entries: `manglik`, `kaal_sarp`, `pitra`, `guru_chandal`, `shrapit`, `angarak`, `ghata`, `ganda_moola`; any other key
gets a generic table row and is named as a fact only.

**`manglik`** (drives the Manglik verdict in every input, the Manglik check table and the Relationships entry):

```json
"manglik": {"houses_used": [1, 2, 4, 7, 8, 12], "mars_house": {"lagna": 12, "moon": 1, "venus": 10},
            "hits": {"lagna": true, "moon": true, "venus": false}, "is_manglik_any": true,
            "cancel_flags": {"aspected_by_jupiter": true, "mars_retro": false}, "cancelled_any": true}
```

`mars_house` holds Mars's house counted from the lagna, the Moon and Venus; `hits` says which of those count;
`cancel_flags` lists named cancellation tests (any names; the true ones are quoted). Missing: no Manglik verdict or
table.

**`kaal_sarp`**: an object of modes (the calculator gives `mean` and `true` node), each
`{"degree_full": bool, "degree_partial_one_out": bool, "sign_mode_full": bool, "outside_planets": [...], "rahu_house": 3, "name": "Vasuki", "direction": null}`.
Present = any mode full; partial = one planet outside. Give the object form: a bare `true` is shown as "Present" in
the dosha table but read as "not present" in the section input (the validator warns).

**`pitra`**: `{"flags": {"<flag>": bool or list, ...}, "pyjhora_fired": bool}`. Other dict-shaped doshas may use
`present` or `fired` for the verdict; their other true or non-empty values are listed as "flags met".

**`sade_sati`** (drives the Sade Sati and Dhaiya phases in the timeline, Mind and Guidance, and the 10-year summary):

```json
"sade_sati": {"moon_sign": "Sagittarius", "saturn_now": "Pisces", "current": ["Dhaiya - Kantaka (4th)"],
              "intervals": [{"phase": "Sade Sati - rising (12th)", "saturn_in": "Scorpio",
                             "start": "1985-02-13", "end": "1985-06-01", "current": false}]}
```

`intervals` is REQUIRED inside `sade_sati`, in date order, one item per stay of Saturn in a phase sign (a retrograde
re-entry is a new item; consecutive items of the same phase are merged). `phase` must contain one of the words
`rising` (12th from the Moon), `peak` (1st), `setting` (2nd), `Kantaka` (4th) or `Ashtama` (8th) to get its library
entry. `moon_sign`, `saturn_now` and `current` are informational.

## A minimal file

A file with only the REQUIRED fields runs through the whole pipeline (tested with `run_report.py --dry-run`); the
validator then lists about twenty warnings, one per skipped feature. The required skeleton:

```json
{
  "birth": {"date": "1988-02-14", "time": "06:40 IST", "place": "Jaipur, Rajasthan (26.91N, 75.79E)"},
  "settings": {"ayanamsa_value": "23°41'31\""},
  "lagna": {"lon": 291.9782, "sign": "Capricorn", "sign_num": 10, "deg_in_sign": "21°58'42\"",
            "nakshatra": "Shravana", "vargas": {"D9": "Cancer"}},
  "planets": [
    {"name": "Sun", "lon": 300.8612, "sign": "Aquarius", "sign_num": 11, "deg_in_sign": "0°51'40\"",
     "nakshatra": "Dhanishta", "nak_lord": "Mars", "dignity": "enemy", "vargas": {"D9": "Libra"}}
  ],
  "houses": [
    {"house": 1, "sign": "Capricorn", "lord": "Saturn", "lord_in_house": 12, "lord_in_sign": "Sagittarius",
     "lord_dignity": "neutral", "occupants": ["Mercury"], "aspected_by": ["Ketu"]}
  ],
  "vimshottari": {"balance_at_birth": {"lord": "Ketu", "years": 1.6203},
                  "mahadashas": [{"md": "Ketu", "start": "1982-09-28", "end": "1989-09-28"}]},
  "transits_2026_11_03": {"Jupiter": {"sign": "Leo", "house_from_lagna": 8, "house_from_moon": 9},
                          "Saturn": {"sign": "Pisces", "house_from_lagna": 3, "house_from_moon": 4}}
}
```

(`planets` needs all nine grahas, `houses` all twelve houses and `mahadashas` the full sequence; one of each is shown.)
