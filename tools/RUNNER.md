# Kundli report runner (v0.16)

`tools/run_report.py` runs the whole kundli-report pipeline with direct API calls, one task per call, instead of
Claude Code subagents reading the skill files. `tools/llm_client.py` is the HTTP client (standard library only; no SDK
or package to install). Run every command from the repository root with Python 3.10+ (`python`, or `python3` on
systems where that is the name).

## Run it

```
python -I tools/run_report.py --chart chart_data.json --name "Name" --out OUT \
    [--model M] [--provider anthropic|openai] [--base-url URL] [--max-workers 4] [--pdf] [--dry-run] \
    [--only glance,career,editor,guidance] [--inputs DIR] [--now YYYY-MM-DD] [--settings JSON|file] [--prepared "11 November 2026"]
```

What it does, in order:

1. **Inputs**: runs `report_input.py` and `dasha_facts.py` (their CLIs) into `OUT/inputs`. `--inputs DIR` reuses a
   folder that already holds the section inputs, `dasha_input.md`, `timeline_rows.md` and `ownership_map.md`.
2. **Writers** (in parallel, `--max-workers`): the 10 life sections and the Timeline. System prompt = `shared/rules.md`
   + the generic part of `life_areas.md` + only that section's row of the specs table (+ the "Doshas and yogas" notes
   for yogas and relationships). Timeline: `rules.md` + `timeline.md`. User message = the section input (Timeline:
   `dasha_input.md` + `timeline_rows.md`). A fixed output contract is appended; SKILL.md is not sent.
3. **Validation** of every output: starts with `## `; `eval/lint_report.lint` is empty; every rows block parses with
   `table_rows.parse_rows` and has every row key the input lists (remedies may leave planets out); no row cell trips
   the lint (it would print as "-"); a hidden trace block is present; visible words within 0.5x-1.6x of the spec
   target; not cut off at max tokens. On failure up to 2 retries, each a follow-up message listing the exact findings
   and asking for the full corrected section. The attempt with the fewest findings is kept; all are logged.
4. **Editor**: `repeat_finder.py`, then one call with `editor.md` + the ownership map + the repeat list + lint findings
   + all sections (Timeline read-only); the reply must be the edits JSON array (one retry on invalid JSON). Applied
   with `apply_edits.py`; originals kept in `OUT/sections_pre_edit`. Rejected edits are listed in the log.
5. **Guidance**: a writer call whose input is `guidance.md` + every edited section.
6. **Assemble**: `assemble_report.py` -> `OUT/report.html` (+ `OUT/report.pdf` with `--pdf`).
7. **Log**: `OUT/run_log.json` (per call: model, input/output tokens from the API usage field or chars/4 when absent,
   cached input tokens, stop reason, attempt, findings, words, seconds; plus every subprocess's output and the final
   lint per section). A summary table and the token total are printed.

Every prompt is written to `OUT/prompts/<step>.txt` (`<step>_retry1.txt` for retries), in real runs too.

`--only` runs just the listed steps; sections already in `OUT/sections` are reused. Example: fix one section and
rebuild Guidance on top of the existing edited sections: `--only career,guidance --inputs OUT/inputs`. A rerun writer
replaces the edited copy with a fresh unedited one, so include `editor` if the repeats matter.

`--dry-run` needs no key or network: all prompts are built and saved, and a mock provider returns the matching example
file (`--mock-dir`, default `examples/meera/open_run`: `sections_pre_edit/<sec>.md`
for writers, `sections/guidance.md`, `edits.json`), so validation, retries, the editor application and assembly all
run end to end. Mock output does not change on retry, so a section that fails validation shows all 3 attempts.

## File provider (any model, no API key in the runner)

`--provider file` hands each call to you as a file: the runner writes `OUT/prompts/<name>.txt` (a `=== SYSTEM ===`
part and the `=== USER ===` / `=== ASSISTANT ===` turns), stops with exit code 3 and lists the missing answers in
`OUT/PENDING.txt`. Put each answer in `OUT/responses/<name>.md` (by hand, with a chat UI, or with an agent following
`eval/briefs/RESPONDER_BRIEF.md`) and rerun the same command: answered steps are validated, failed ones get a
`<name>_retry1.txt` prompt, and the run continues through the editor, guidance and assembly.

## Keys and providers

| Provider | Flag | Key env var | Default URL |
|---|---|---|---|
| Anthropic Messages API | `--provider anthropic` (default) | `ANTHROPIC_API_KEY` | `https://api.anthropic.com/v1/messages` |
| OpenAI and compatible | `--provider openai` | `OPENAI_API_KEY`, else `LLM_API_KEY` (none needed for a local server) | `https://api.openai.com/v1/chat/completions` |

OpenAI-compatible examples (`--base-url` is the part before `/chat/completions`):

| Service | `--base-url` | `--model` |
|---|---|---|
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` |
| Qwen (DashScope intl.) | `https://dashscope-intl.aliyuncs.com/compatible-mode/v1` | `qwen-max` |
| OpenRouter | `https://openrouter.ai/api/v1` | e.g. `meta-llama/llama-3.3-70b-instruct` |
| vLLM / LM Studio | `http://localhost:8000/v1` | the served model name |
| Ollama | `http://localhost:11434/v1` | e.g. `qwen2.5:32b` |

Default models: `claude-opus-5-5` (anthropic), `gpt-4.1` (openai). The client retries 408/409/425/429/5xx/529 and
network errors with exponential backoff (honours `Retry-After`, 5 retries) and times out each request after 900 s.

## Plugging in a new model

Settings are resolved as `DEFAULTS` -> the first `MODEL_SETTINGS` prefix matching the model id -> `--settings`:

```
DEFAULTS = {'temperature': 0.3, 'max_tokens': {'section': 6000, 'timeline': 12000, 'editor': 8000, 'guidance': 6000},
            'extra': {}, 'timeout': 900}
```

- `temperature: null` leaves it out of the request. Current Claude models reject temperature, so the `claude-` entry
  sets it to null; it also raises the caps (16k sections, 32k timeline) because adaptive thinking counts toward
  `max_tokens`, and turns on automatic prompt caching (`extra: {"cache_control": {"type": "ephemeral"}}`) so retries
  re-read their long prefix from cache. Pass `--settings '{"extra":{}}'` to switch caching off if an endpoint rejects it.
- `extra` is merged into the request body, for provider-specific fields: e.g. `{"output_config": {"effort": "low"}}`
  on Claude, or `{"max_completion_tokens": 32000}` for OpenAI reasoning models (replaces `max_tokens`).
- For a model used often, add a prefix entry to `MODEL_SETTINGS` in `run_report.py`; for a one-off use
  `--settings '{"temperature":0.2,"max_tokens":{"section":8000}}'` or a JSON file path.
- A new wire format (neither Anthropic nor OpenAI-compatible) is a new branch in `llm_client.complete` returning
  `(text, usage)`.

What a weaker model needs: the cut-off check catches a too-small `max_tokens` (raise it); repeated lint findings on
the same phrase show in `run_log.json` under each call's `findings`.

## Token use and cost (dry run, test chart, 11 November 2026)

Estimated tokens (chars/4) from `--dry-run` on the tuned test chart, inputs built by the current
`report_input.py` / `dasha_facts.py` (`dasha_input.md` about 61k tokens, before the v0.16 input diet):

| Call | Input | Output |
|---|---:|---:|
| glance | 12,153 | 1,341 |
| personality | 12,418 | 1,809 |
| mind | 8,785 | 1,185 |
| career | 14,560 | 1,992 |
| finance | 11,655 | 1,767 |
| health | 10,355 | 898 |
| relationships | 12,543 | 1,231 |
| family | 13,112 | 1,504 |
| spirituality | 12,390 | 1,491 |
| yogas | 13,341 | 1,839 |
| timeline | 65,565 | 4,944 |
| editor | 24,691 | 5,738 |
| guidance | 32,677 | 1,365 |
| **First attempts (13 calls)** | **244,245** | **27,104** (271k total) |
| timeline retries 1 and 2 (run5 timeline has 4 lint hits + 1 rows-cell hit) | 146,763 | 9,888 |
| **All 15 calls** | **391,008** | **36,992** (428k total) |

A Timeline retry resends the whole conversation (about 70k tokens each with the current input), so the Timeline
input diet matters most: at the 30k target the first-attempt total falls to about 240k. With Claude prompt caching a
retry's repeated prefix is billed at the cache-read rate.

To estimate the cost of a report, multiply these token counts by your provider's current prices (per million tokens):

| | Input tokens | Output tokens |
|---|---:|---:|
| First attempts only | ~244k | ~27k |
| With 2 timeline retries | ~391k | ~37k |

Thinking tokens (on models that use them) come on top of the output column and are not counted in a dry run.
