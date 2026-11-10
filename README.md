# vedic-kundli-report-pipeline

Turns birth details into a long Vedic (Parashari) Janma Kundli report: about 40 pages as HTML and PDF, with twelve
written sections (chart at a glance, personality, mind, career, finance, health, relationships, family, spirituality,
yogas and doshas, timeline, guidance), about twenty tables built from the chart, North or South Indian chart drawings
and a source list.

See a finished one first: `examples/meera/open_run/report.pdf` (also `examples/arjun/...` and
`examples/devika/...`). The three example people are invented.

The repository has three parts you can use together or on their own:

- **A chart calculator** (`tools/chart_data.py` with `tools/engine/kundli_maker.py`): birth details in,
  `chart_data.json` out (positions, houses, dashas, yogas, doshas, transits).
- **An interpretation library** (`library.json`, 876 entries): what each placement, period, yoga or dosha means,
  paraphrased from classical texts and modern authors, with a citation on every entry.
- **A report pipeline**: code picks the library entries that apply to a chart and checks every condition it can; a
  language model writes one section at a time from that prepared input; code checks the result, builds the tables
  and assembles the PDF.

Any capable model works: Claude, OpenAI, or any OpenAI-compatible endpoint (DeepSeek, Qwen, OpenRouter, vLLM, Ollama,
LM Studio). You can also run it without an API key (answer the prompts yourself or with another tool), or as a
Claude Code skill.

## How it works

```
 birth details
      |
      v
 chart calculator (tools/chart_data.py)        or  your own calculator
      |                                                |
      +------------------> chart_data.json <-----------+     format: docs/CHART_DATA_FORMAT.md
                                |                            check:  tools/validate_chart.py
                                v
 input builders (tools/report_input.py, tools/dasha_facts.py)  +  library.json
      |   one Markdown input per section: chart verdicts, the entries that apply,
      |   conditions already checked, periods ahead, a must-cover list
      v
 tools/run_report.py
   1. writers    one model call per section (11 calls, in parallel)
   2. checks     lint, length, table rows, hidden trace; up to 2 retries with the findings
   3. editor     1 call: cuts points repeated outside the section that owns them
   4. guidance   1 call, written last from the edited sections
   5. assembly   code-built tables, chart drawings, sources  (tools/assemble_report.py)
      |
      v
 report.html, report.pdf, run_log.json
```

The model never computes a chart fact: positions, dates, dignities, yogas and doshas come from `chart_data.json`, and
meanings come only from the library entries in its input.

## Limits

- **Quality.** Reports score about 75 out of 100 against a long benchmark report written by a strong model with live
  research (`docs/STATUS.md`). Facts are almost always right; the gap is coverage (the library does not yet hold
  everything a full reading covers) and some repetition between sections.
- **One school.** Parashari rules, Lahiri ayanamsa, whole-sign houses. Other settings are untested.
- **Birth time.** The lagna, D9 and D10 depend on an accurate birth time; the report says when a position is close to
  a boundary.
- **Not advice.** This is traditional astrology, a tradition of interpretation, not a science. Nothing in a report is
  medical, financial, legal or psychological advice, and the writing rules forbid predictions of death, illness or
  divorce.

## Install

You need Python 3.10 or newer. Run every command in this README from the repository root (the folder that holds this
file). Where your system calls Python `python3`, type that instead of `python`.

```
python -m venv .venv
. .venv/bin/activate                    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install chromium   # optional: only for PDF output
```

`requirements.txt` installs pyswisseph (used only by the chart calculator) and Playwright (used only for the PDF).
Everything else uses the Python standard library. Without Playwright's Chromium, the PDF step falls back to an
installed Chrome, Chromium or Edge; the HTML report never needs a browser.

## Three ways to use this

| | You have | You run |
|---|---|---|
| **A** | birth details | the chart calculator, then the pipeline |
| **B** | your own astrology software | export `chart_data.json` in our format, validate it, then the pipeline |
| **C** | your own application | only the library: `library.json` and `tools/lookup.py` |

### A. Full pipeline with the chart calculator

**Step 1. Compute the chart.**

```
python tools/chart_data.py --date 1990-01-01 --time 10:00 --lat 28.6139 --lon 77.2090 --tz 5.5 --place "New Delhi, India" --sex female --now 2026-11-11 --out out/chart_data.json
```

- `--date` YYYY-MM-DD and `--time` HH:MM are the local birth date and clock time; `--tz` is that clock's offset from
  UTC in hours (5.5 for India, the default; -5 for New York in winter).
- `--lat` is positive north, `--lon` positive east (decimal degrees).
- `--sex female|male` chooses husband/wife wording; leave it out for "partner".
- `--now` is the date the report treats as today (running periods, transits); default: today.

**Step 2. Check it** (optional for charts from our calculator, but quick):

```
python tools/validate_chart.py out/chart_data.json
```

**Step 3. Try a dry run** (no API key, no network, no cost):

```
python tools/run_report.py --chart out/chart_data.json --name "Test" --out out/run --dry-run
```

This builds every input and every prompt, then a stand-in model answers with the sections of the Meera example (a
different chart, so the text will not match yours). Checks, the editor step and assembly all run, so you can see the
whole flow, read the prompts in `out/run/prompts/` and see the token counts. Open `out/run/report.html`.

**Step 4. Run it with a model.** Set the key for your provider, then run the same command without `--dry-run`:

```
# Anthropic (default provider)
export ANTHROPIC_API_KEY=...            # Windows PowerShell: $env:ANTHROPIC_API_KEY="..."
python tools/run_report.py --chart out/chart_data.json --name "Test" --out out/run --pdf

# OpenAI
export OPENAI_API_KEY=...
python tools/run_report.py --chart out/chart_data.json --name "Test" --out out/run --provider openai --model gpt-4.1 --pdf

# Any OpenAI-compatible endpoint: the key goes in OPENAI_API_KEY or LLM_API_KEY
export LLM_API_KEY=...
python tools/run_report.py --chart out/chart_data.json --name "Test" --out out/run --provider openai --base-url https://api.deepseek.com/v1 --model deepseek-chat --pdf
python tools/run_report.py --chart out/chart_data.json --name "Test" --out out/run --provider openai --base-url https://openrouter.ai/api/v1 --model meta-llama/llama-3.3-70b-instruct --pdf

# A local server (Ollama, vLLM, LM Studio): no key needed
python tools/run_report.py --chart out/chart_data.json --name "Test" --out out/run --provider openai --base-url http://localhost:11434/v1 --model qwen2.5:32b --pdf
```

| Option | Meaning |
|---|---|
| `--name` | the name printed on the cover and page headers |
| `--provider` | `anthropic` (default), `openai` (OpenAI and every compatible endpoint) or `file` (see below) |
| `--model` | model id; defaults: `claude-opus-5-5` (anthropic), `gpt-4.1` (openai) |
| `--base-url` | for `openai`: the endpoint up to (not including) `/chat/completions` |
| `--pdf` | also write `report.pdf` |
| `--max-workers N` | how many section calls run at once (default 4) |
| `--only career,guidance` | rerun only some steps (section names, `editor`, `guidance`); finished sections are reused |
| `--settings '{"temperature":0.2}'` | per-run model settings (JSON or a file); see `tools/RUNNER.md` |

More endpoints, model settings and retries are described in `tools/RUNNER.md`.

**No API key?** Use `--provider file`. The runner writes each prompt to `out/run/prompts/<name>.txt`, lists the
missing answers in `out/run/PENDING.txt` and stops (exit code 3). Paste each prompt into any chat model (or let an
agent answer it with `eval/briefs/RESPONDER_BRIEF.md`), save the answer as `out/run/responses/<name>.md`, and run the
same command again; it checks the answers, asks for retries the same way, and continues through the editor,
guidance and assembly.

```
python tools/run_report.py --chart out/chart_data.json --name "Test" --out out/run --provider file
```

**What you get** in the `--out` folder:

| Path | What it is |
|---|---|
| `report.html`, `report.pdf` | the report (the HTML embeds its fonts and works offline) |
| `inputs/` | what each section's model call was given (`<section>.md`, `dasha_input.md` for the timeline) |
| `prompts/` | every prompt exactly as sent (`<step>_retry1.txt` for retries) |
| `sections/` | the final section texts; `sections_pre_edit/` holds them before the editor step |
| `run_log.json` | one record per model call: model, input and output tokens, cached tokens, stop reason, attempt number, the check findings, word count, seconds; plus the output of every tool step and the final lint per section |

A summary table with the tokens per call is also printed at the end.

**Tokens per report:** about 210-270k tokens on first attempts (13 calls: about 185-245k in, 27k out), measured with
`--dry-run`. Each retry of the long timeline call adds roughly 45-70k. On Claude models the runner turns on prompt
caching, so a retry re-reads its long prefix at the cache rate; thinking tokens come on top of the output. To
estimate cost, multiply the token counts in `tools/RUNNER.md` by your provider's prices.

**Optional single steps.** `run_report.py` runs these for you; you can also run them yourself:

```
python tools/report_input.py --chart out/chart_data.json --outdir out/inputs
python tools/dasha_facts.py --chart out/chart_data.json --out out/inputs/dasha_input.json --md out/inputs/dasha_input.md
python tools/assemble_report.py --chart out/chart_data.json --sections out/run/sections --name "Test" --out out/report.html --pdf out/report.pdf
```

The inputs are plain Markdown: open one to see exactly what a model is given. `assemble_report.py` turns any folder
of section files (from a run, or written by hand or by an agent) into the report; add `--chart-style south` for South
Indian chart drawings.

### B. Your own calculator

1. Export your chart as `chart_data.json` following `docs/CHART_DATA_FORMAT.md` (machine-readable:
   `docs/chart_data.schema.json`). The format uses sidereal Lahiri longitudes, English sign names, sign numbers 1-12,
   whole-sign houses 1-12 and ISO dates. Only a handful of blocks are required (birth, settings, lagna, the nine
   planets, the twelve houses, the Vimshottari mahadashas and one transits block); the rest switch on extra tables and
   sections. `examples/meera/chart_data.json` is a complete example to copy from.
2. Validate it, and fix every error:

   ```
   python tools/validate_chart.py my_chart.json
   ```

   Errors (exit code 1) mean the pipeline would stop or print wrong facts. Warnings name each feature that will be
   skipped because an optional field is missing. The sanity checks confirm the nine grahas, sign and house numbering,
   dates, dasha order and the agreement between the lagna, the planets, the houses and the transits. Add `--schema`
   to check against the JSON Schema too (needs `pip install jsonschema`).
3. Continue from step 3 of A (dry run, then a real run) with `--chart my_chart.json`.

Nothing after `chart_data.json` uses the Swiss Ephemeris, so this route never runs the chart calculator.

### C. The knowledge base only

`library.json` is one JSON object: entry id -> entry. Ids are `<layer>/<key>`, lowercase:

| Id example | Meaning |
|---|---|
| `planet_in_house/sun/8` | the Sun in the 8th house |
| `planet_in_sign/venus/pisces` | Venus in Pisces |
| `lord_in_house/2/10` | the lord of the 2nd house placed in the 10th |
| `dasha_md/rahu` | the Rahu mahadasha |
| `dasha_ad/rahu/saturn` | the Saturn sub-period inside the Rahu mahadasha |
| `transit/saturn/7`, `sade_sati/peak`, `yogini/ulka` | Saturn transiting the 7th from the Moon; the Sade Sati peak; the Ulka yogini |
| `yoga/gajakesari`, `dosha/manglik` | a yoga; a dosha |
| `nakshatra/purva_phalguni`, `rising_sign/leo` | a nakshatra; a lagna sign |
| `aspect/saturn/7`, `conjunction/sun_mercury` | Saturn aspecting the 7th house; the Sun with Mercury |
| `karaka/atmakaraka`, `remedy/saturn`, `panchang/tithi/26`, `varga/...`, `profession/...` | other layers |

Every entry has `id`, `layer`, `key`, `summary`, `themes`, `common_outcomes`, `rare_outcomes`, `by_area` (personality,
career, finance, health, relationships, family, spirituality), `strengtheners`, `weakeners_or_cancellations`,
`lagna_or_context_notes`, `source_views` (source, paraphrase, link), `disagreements`, `confidence` (high, medium,
low), `phrasing_guidance`, plus `quality` and `file` added by the build. Dasha, transit and yoga layers add
`conditional_results` (rules with a checkable `when` condition), `remedies`, `phases`, `definitions`, `cancellations`,
`rarity_and_weight` or `timing`. The full schema and the condition vocabulary are in `docs/LIBRARY.md`; coverage and
review status are in `index.json` and `quality.json`.

`tools/lookup.py` returns the 30 entries that apply to a chart (9 planet in house, 9 planet in sign, 12 lord in house),
each with the chart context it was chosen for:

```
python tools/lookup.py --chart examples/meera/chart_data.json --compact --out out/lookup.json
python tools/lookup.py --date 1990-01-01 --time 10:00 --lat 28.61 --lon 77.21 --compact --out out/lookup.json
```

`--chart` takes any `chart_data.json` (it needs only `lagna` and `planets`); `--date ...` computes the chart with
the chart calculator. `--compact` trims each entry for a small model.

The layer folders (`planet_in_house/`, `dasha_ad/`, `yoga/` ...) are the source of truth: one JSON file per planet,
house lord or topic. After editing any of them, rebuild and validate the generated files (`library.json`,
`index.json`, and readable Markdown in `md/`):

```
python tools/build_library.py
```

## Run it as a Claude Code skill

The skill holds the same writing rules and section specs the runner sends to a model, read by Claude Code instead.

1. Open Claude Code in the repository root.
2. Copy both skill folders into the project's skills folder, side by side (`SKILL.md` reads `../shared/rules.md`):

   ```
   mkdir -p .claude/skills
   cp -r skill/kundli-report skill/shared .claude/skills/
   ```

3. Ask for a report with the birth details, for example: "Write a full kundli report for a woman born 1 January 1990,
   10:00, New Delhi (28.6139 N, 77.2090 E)". You can also name the skill: "use the kundli-report skill". It computes
   the chart and the inputs with the tools above, writes each section from its own input, runs the editor step,
   writes Guidance last and assembles the PDF.
4. For a large report, give each section to its own agent with `eval/briefs/WRITER_BRIEF.md`.

## Evaluating quality

| Tool or file | Use |
|---|---|
| `eval/GRADING_RUBRIC_full_report.md`, `eval/GRADING_RUBRIC_timeline.md` | how a section is scored: coverage of the benchmark's points, accuracy against the chart, groundedness in the input, tone, -5 per guardrail breach |
| `eval/briefs/GRADER_BRIEF.md` | brief for a grading agent |
| `examples/<name>/benchmark/`, `examples/<name>/grading/`, `examples/scores.json` | benchmark texts and the grades of the example runs |
| `python tools/eval/lint_report.py out/run/sections/*.md` | guardrail lint on the visible text (fatalistic or medical wording, death words, copied instructions, entry ids); exit code 1 on findings |
| `python tools/repeat_finder.py --chart out/chart_data.json --sections out/run/sections --out out/repeats.md` | points told again outside the section that owns them |
| `python tools/eval/check_conditions.py examples/meera/chart_data.json` | evaluates every library condition against charts; reports unknown facts or bad syntax |
| `python tools/eval/score_text.py --benchmark examples/meera/benchmark/career.txt --candidate out/run/sections/career.md` | word-overlap scores (ROUGE, term and date recall) against a benchmark section |
| `tools/eval/check_input_diet.py` | proves a slimmer input kept every date, entry id and holding condition |

## Contributing to the library

1. Read `docs/LIBRARY.md` (schema and condition vocabulary) and the research rules: `docs/ENRICHMENT_RULES.md`
   (improving an existing layer file) and `docs/DASHA_RESEARCH_RULES.md` (dasha entries). In short: paraphrase,
   cite text + chapter/verse + link on every claim, mark "(via summary)" when you did not read the source itself,
   record disagreements, and leave a field empty rather than unsourced.
2. Edit the layer file (keep ids, keys and order), then run `python tools/build_library.py` and fix any problem it
   lists in `index.json`.
3. If you added conditions, run `python tools/eval/check_conditions.py examples/*/chart_data.json` to check them.
4. Open a pull request naming the sources you read.

## Repository layout

| Path | What it is |
|---|---|
| `tools/chart_data.py`, `tools/engine/kundli_maker.py` | the chart calculator (Swiss Ephemeris) |
| `tools/validate_chart.py` | checks a `chart_data.json` |
| `tools/report_input.py`, `tools/dasha_facts.py`, `tools/chart_verdicts.py` | input builders |
| `tools/run_report.py`, `tools/llm_client.py` | the runner and its HTTP client (`tools/RUNNER.md`) |
| `tools/repeat_finder.py`, `tools/apply_edits.py` | the editor step |
| `tools/report_tables.py`, `tools/table_rows.py`, `tools/assemble_report.py`, `tools/report_assets/` | tables, assembly, styles and fonts |
| `tools/lookup.py`, `tools/build_library.py` | library lookup and build |
| `tools/eval/` | lint, condition checks, input checks, text scoring |
| `<layer>/` folders, `library.json`, `index.json`, `quality.json` | the interpretation library |
| `skill/` | writing rules and section specs (also the Claude Code skill); `skill/kundli-report-versions/CHANGELOG.md` |
| `eval/` | grading rubrics and agent briefs |
| `examples/` | three invented charts with inputs, sections, finished reports, benchmarks and grades |
| `docs/` | chart data format and schema, library format, research rules, status |

## Licence

MIT (`LICENSE`). The fonts embedded in the report are under the SIL Open Font Licence (texts in
`tools/report_assets/fonts/`); `THIRD_PARTY_NOTICES.md` lists them and credits the sources behind the library.

## Disclaimer

Reports are produced by software and a language model from traditional astrological rules. They describe tendencies
as the tradition sees them, can be wrong, and are not medical, financial, legal or psychological advice. Make
decisions about health, money, relationships and the law with qualified professionals.
