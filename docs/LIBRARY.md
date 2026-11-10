# The interpretation library

A researched reference of Vedic (Parashari) astrology interpretations, built to be looked up by placement
and combined by a model (via the report pipeline or a skill) into kundli readings. Each entry is paraphrased from cited
sources; nothing here is computed. Chart facts (positions, houses, dignity, dashas) must come from code.

## Layers

| Folder | Key | Entries | Status |
|---|---|---|---|
| `planet_in_house/` | planet x house (1-12) | 9 x 12 = 108 | see `index.json` |
| `planet_in_sign/` | planet x sign (Aries..Pisces) | 9 x 12 = 108 | see `index.json` |
| `lord_in_house/` | lord of house N placed in house M | 12 x 12 = 144 | see `index.json` |

Planets: Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Rahu, Ketu. Houses by whole sign from the lagna.

## Using the library

| File / tool | What it is |
|---|---|
| `<layer>/*.json` | Source of truth: researched entries, one file per planet or house lord. Edit these. |
| `quality.json` | Review status per file: `accepted` (strict standard), `accepted_caveats`, `draft`. |
| `tools/build_library.py` | Validates every file and regenerates `library.json`, `index.json` and `md/`. Run after any change. |
| `library.json` | Generated: all entries keyed by id, each with `quality` and `file` added. |
| `index.json` | Generated: coverage per layer, confidence and quality counts, validation problems. |
| `md/` | Generated: readable Markdown per file, for browsing. |
| `tools/lookup.py` | Given a chart, returns the 30 entries that apply (9 planet-in-house, 9 planet-in-sign, 12 lord-in-house), each with its chart context. `--compact` trims entries for a small model (~19k tokens per chart). |

```
python -I tools/build_library.py
python -I tools/lookup.py --date 1990-01-01 --time 10:00 --lat 28.61 --lon 77.21 --compact --out reading_input.json
python -I tools/lookup.py --chart chart.json --compact          # chart.json from kundli_maker.py --json
```

`lookup.py` computes charts with `tools/engine/kundli_maker.py` (Swiss Ephemeris, Lahiri, mean node, whole-sign houses).
Chart facts never come from the library; the library only interprets them. Weigh entries by `confidence` and `quality`, and
treat `draft` entries as provisional.

## File format

One JSON file per planet (or per house lord), e.g. `planet_in_house/sun.json`, `lord_in_house/lord_07.json`.
Each file is a JSON array of 12 entries with this schema:

```json
{
  "id": "planet_in_house/sun/10",
  "layer": "planet_in_house",
  "key": {"planet": "Sun", "house": 10},
  "summary": "One or two plain-English sentences: the core meaning.",
  "themes": ["authority", "public role"],
  "common_outcomes": ["..."],
  "rare_outcomes": ["less-frequent or text-specific outcomes"],
  "by_area": {
    "personality": "", "career": "", "finance": "", "health": "",
    "relationships": "", "family": "", "spirituality": ""
  },
  "strengtheners": ["dignity, aspects, conjunctions, D9 or lagna conditions that improve results"],
  "weakeners_or_cancellations": ["conditions that spoil or modify results"],
  "lagna_or_context_notes": "how results change by lagna / functional role / sign, if sources say so",
  "source_views": [
    {"source": "Phaladeepika 8.x (tr. V. Subrahmanya Sastri)", "view": "paraphrase", "url": "https://..."}
  ],
  "disagreements": "where sources differ, each view stated",
  "confidence": "high | medium | low (how well-attested the core meaning is)",
  "phrasing_guidance": "how to say this to a user: balanced, no fatalism, no medical or death claims"
}
```

Rules for researchers: paraphrase, never copy long passages; cite text + chapter/verse + link; mark a source
"(via summary)" if only a secondary summary was read; keep every entry specific to its key; empty string if
a field has nothing sourced. Valid JSON only.

## Dasha layers (started 2026-11-10)

| Folder | Key | Entries | File |
|---|---|---|---|
| `dasha_principle/` | rule slug | ~15-20 | `principles.json` |
| `dasha_md/` | mahadasha lord | 9 | one file per planet, e.g. `rahu.json` (array of 1 entry) |
| `dasha_ad/` | mahadasha lord x antardasha lord | 81 | one file per mahadasha lord, e.g. `rahu.json` (array of 9, in Vimshottari order from the MD lord) |

Ids: `dasha_principle/<slug>`, `dasha_md/<planet>`, `dasha_ad/<md>/<ad>` (lowercase). Keys: `{"rule": slug}`, `{"md": "Rahu"}`,
`{"md": "Rahu", "ad": "Jupiter"}`. Entries keep every core field above (use empty strings/lists where nothing is sourced) and add:

```json
"conditional_results": [
  {"when": "ad_from_md in DUSTHANA or ad_house in DUSTHANA", "polarity": "bad",
   "effects": ["loss of wealth", "quarrels with relatives"], "source": "BPHS 5x.y (tr. Santhanam)"},
  {"when": "manual: if the antardasha lord is strong", "polarity": "good", "effects": ["..."], "source": "..."}
],
"remedies": [{"remedy": "recite the Durga Saptashati", "source": "BPHS 5x.y"}],
"phases": "how results differ at the start / middle / end of the period, if a source says so",
"duration_years": 18
```
(`duration_years` on `dasha_md` only.) For `dasha_principle`, `summary` states the rule, `common_outcomes` says how to apply it,
and `conditional_results` holds any checkable form of the rule.

### Condition vocabulary (`when`)

A `when` is either a boolean expression over the facts below or `manual: <text>` when the source's condition cannot be
checked from these facts (e.g. "if strong", "if associated with the lord of a benefic house from the dasha lord").
Operators: `and`, `or`, `not`, `in`, `==`, `!=`, `<`, `>`, lists `[1, 4]`, strings `'exalted'`. The code evaluates
expressions against the chart and tells the model which conditions hold; it never guesses `manual` ones.

Facts for the period lord, prefixed `md_` (mahadasha lord) or `ad_` (antardasha lord):

| Fact | Values |
|---|---|
| `md`, `ad` | planet name, e.g. `'Rahu'` |
| `X_house` | 1-12, counted from the lagna (whole sign) |
| `X_house_from_moon` | 1-12, counted from the Moon's sign |
| `ad_from_md` | 1-12, the antardasha lord's sign counted from the mahadasha lord's sign (same sign = 1) |
| `X_sign`, `X_sign_lord`, `X_nak_lord` | sign (lowercase, e.g. `'scorpio'`), its lord, nakshatra lord |
| `X_dignity` | `'exalted'`, `'moolatrikona'`, `'own'`, `'friend'`, `'neutral'`, `'enemy'`, `'debilitated'` (nodes, calculator default: Rahu exalted in Taurus and debilitated in Scorpio; Ketu exalted in Scorpio and debilitated in Taurus) |
| `X_combust`, `X_retro` | true / false |
| `X_vargottama` | true when the D1 and D9 signs are the same |
| `X_d9_dignity` | `'exalted'`, `'debilitated'`, `'own'`, `'other'` |
| `X_rules` | list of houses the planet rules (nodes: `[]`) |
| `X_role` | list from `'lagna_lord'`, `'yogakaraka'`, `'trikona_lord'` (5/9), `'kendra_lord'` (4/7/10), `'dusthana_lord'` (6/8/12), `'trishadaya_lord'` (3/6/11), `'maraka'` (2/7 lords), `'eighth_lord'` |
| `X_with`, `X_aspected_by` | lists of planets in the same sign / casting a graha drishti on its sign |
| `X_with_benefic`, `X_with_malefic`, `X_aspected_by_benefic`, `X_aspected_by_malefic` | true / false (natural benefics Jupiter, Venus, Mercury, Moon; malefics Sun, Mars, Saturn, Rahu, Ketu) |
| `X_in_benefic_sign` | true when the sign lord is a natural benefic |
| `moon_waxing` | true / false |

Named sets: `KENDRA` [1,4,7,10], `TRIKONA` [1,5,9], `DUSTHANA` [6,8,12], `UPACHAYA` [3,6,10,11], `MARAKA_HOUSES` [2,7].
Keep "from the lagna", "from the Moon" and "from the dasha lord" distinct: they are different facts.

## Timing layers: transits, Sade Sati, Yogini (started 2026-11-10)

| Folder | Key | Entries | File |
|---|---|---|---|
| `transit/` | slow planet x house counted from the natal Moon | Saturn 12, Jupiter 12 | `saturn.json`, `jupiter.json` (array of 12, houses 1-12) |
| `sade_sati/` | phase | 5: `rising` (Saturn 12th from Moon), `peak` (1st), `setting` (2nd), `kantaka_dhaiya` (4th), `ashtama_dhaiya` (8th) | `sade_sati.json` |
| `yogini/` | yogini | 8: `mangala` (Moon, 1 yr), `pingala` (Sun, 2), `dhanya` (Jupiter, 3), `bhramari` (Mars, 4), `bhadrika` (Mercury, 5), `ulka` (Saturn, 6), `siddha` (Venus, 7), `sankata` (Rahu, 8) | `yogini.json` |

Ids: `transit/saturn/7`, `sade_sati/peak`, `yogini/ulka`. Keys: `{"planet": "Saturn", "house_from_moon": 7}`, `{"phase": "peak"}`,
`{"yogini": "Ulka", "planet": "Saturn"}`. Same fields as the dasha layers (`conditional_results`, `remedies`, `phases` optional).

Extra condition facts for these layers (in addition to the dasha vocabulary, where `md_` facts describe the running mahadasha lord):

| Fact | Values |
|---|---|
| `tr_planet` | transiting planet, e.g. `'Saturn'` |
| `tr_house_from_moon`, `tr_house_from_lagna` | 1-12 |
| `tr_sign` | sign it is transiting (lowercase) |
| `tr_dignity` | dignity of the transiting planet in that sign: `'exalted'`, `'moolatrikona'`, `'own'`, `'debilitated'`, `'other'` |
| `tr_vedha_houses` | list of houses from the Moon occupied by the other transiting planets at that time (for vedha rules) |
| `tr_role`, `tr_natal_dignity`, `tr_natal_house` | the transiting planet's functional role list, natal dignity and natal house in this chart |
| `moon_dignity`, `moon_house`, `moon_waxing` | natal Moon facts |
| `yl_*` | for Yogini entries: the yogini's planet facts, same names as `md_*` (e.g. `yl_house`, `yl_dignity`, `yl_role`) |

## Yogas and doshas (started 2026-11-10)

One entry per yoga or dosha the calculator (kundli_maker.py) checks, so every computed result has an interpretation.
Ids `yoga/<slug>`, `dosha/<slug>`; layer `yoga` / `dosha`; key `{"name": "<calculator name>"}`.

| File | Slugs (calculator name in brackets where it differs) |
|---|---|
| `yoga/mahapurusha_lunar.json` | ruchaka, bhadra, hamsa, malavya, sasa, gajakesari, budhaditya, chandra_mangala, adhi, amala |
| `yoga/raja_dhana.json` | raja_kendra_trikona ("Raja (kendra-trikona lords)"), yogakaraka ("Yogakaraka present"), dharma_karmadhipati, parivartana, dhana ("Dhana (1/2/5/9/11 lords)"), lakshmi, saraswati, vasumati, viparita_harsha, viparita_sarala, viparita_vimala, neecha_bhanga |
| `yoga/moon_and_other.json` | sunapha, anapha, durudhara, kemadruma, shakata, shubha_kartari ("Shubha Kartari (lagna)"), papa_kartari ("Papa Kartari (lagna)"), grahan |
| `dosha/doshas.json` | manglik, kaal_sarp, pitra, guru_chandal, shrapit, angarak, ghata, ganda_moola |

Fields: all core fields, plus
- `definitions`: `[{"source": "...", "definition": "exact formation rule as that text gives it"}]` - texts often define a yoga
  differently; record each so the calculator's variant can be matched to a source.
- `cancellations`: `[{"condition": "...", "source": "..."}]` - conditions that cancel or weaken it (bhanga), as the sources give them.
- `rarity_and_weight`: how common it is and how much weight sources give it (e.g. "very common; minor unless ..."), sourced.
- `timing`: when it gives results (e.g. dashas of the forming planets), sourced.
- `remedies`: as in the dasha layers (doshas especially), sourced and optional.
`by_area` uses the same seven areas. `conditional_results` may stay empty: yoga strength mostly needs `manual:` judgement
from the calculator's `conditions` output.

## Report layers, step 5 (started 2026-11-10)

| Folder | Key | Entries | Files |
|---|---|---|---|
| `nakshatra/` | nakshatra | 27 | `nakshatras_01_14.json` (Ashwini..Chitra... see order below, 1-14), `nakshatras_15_27.json` (15-27) |
| `rising_sign/` | lagna sign | 12 | `rising_signs.json` (Aries..Pisces) |
| `karaka/` | chara karaka role, and karakamsha sign | 7 roles + 12 karakamsha signs | `chara_karakas.json` (atmakaraka, amatyakaraka, bhratrikaraka, matrikaraka, putrakaraka, gnatikaraka, darakaraka), `karakamsha.json` (karakamsha/aries..pisces) |
| `varga/` | divisional-chart principle or planet-in-D9 condition | open | `navamsa_d9.json`, `dashamsa_d10.json` |
| `aspect/` | aspecting planet x aspected house (graha drishti) | 9 x 12 = 108 | one file per aspecting planet, e.g. `saturn.json` |
| `conjunction/` | planet pair | 36 | `pairs.json` |
| `panchang/` | birth tithi, vara, nitya yoga, karana; avakhada gana, yoni, nadi | open | `tithi.json` (30), `vara.json` (7), `nitya_yoga.json` (27), `karana.json` (11), `avakhada.json` |
| `remedy/` | planet | 9 | `planet_remedies.json` |
| `profession/` | indicator planet (lord of the D9 sign held by the 10th lord; Phaladeepika 5, Brihat Jataka 10) + the rule | 8: `rule`, sun..saturn (Rahu/Ketu own no sign, so never the indicator) | `profession.json` |

Nakshatra order: Ashwini, Bharani, Krittika, Rohini, Mrigashira, Ardra, Punarvasu, Pushya, Ashlesha, Magha, Purva Phalguni,
Uttara Phalguni, Hasta, Chitra | Swati, Vishakha, Anuradha, Jyeshtha, Mula, Purva Ashadha, Uttara Ashadha, Shravana,
Dhanishta, Shatabhisha, Purva Bhadrapada, Uttara Bhadrapada, Revati.

Ids: `nakshatra/<slug>` (lowercase, spaces to underscores, e.g. `nakshatra/purva_phalguni`), `rising_sign/<sign>`,
`karaka/<role>`, `karaka/karakamsha_<sign>`, `aspect/<planet>/<house>`, `conjunction/<planet1>_<planet2>` (planets in
order Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Rahu, Ketu), `remedy/<planet>`, `panchang/tithi/<n>`, etc.
All core fields. Extra fields where useful:
- nakshatra: `attributes` ({"lord", "deity", "symbol", "gana", "yoni", "nadi", "nature", "sign_span"} - sourced),
  `as_lagna`, `as_moon`, `planets_in_it` (short sourced notes on a planet occupying it), `padas` (notes per pada if sourced).
- rising_sign: `attributes` (lord, element, modality), `functional_roles` (sourced list of yogakaraka/benefics/malefics/marakas).
- karaka: `significations` (what the role governs), `karakamsha` notes.
- remedy: `remedies` list of {type: mantra | charity | fasting | worship | lifestyle | gemstone, remedy, source}; gemstones
  recorded only with their source and always flagged optional.
