"""Run the whole kundli-report pipeline with direct API calls against any capable model (v0.16 runner).

  python -I tools/run_report.py --chart chart_data.json --name "Name" --out OUT
         [--model M] [--provider anthropic|openai] [--base-url URL] [--max-workers N] [--pdf] [--dry-run]
         [--only glance,career,...] [--inputs DIR] [--now YYYY-MM-DD] [--settings JSON|file] [--mock-dir DIR]

Steps (one call per item; writers run in parallel):
  1 inputs    tools/report_input.py and tools/dasha_facts.py CLIs -> OUT/inputs (or reuse --inputs DIR)
  2 writers   10 life sections + timeline. System = shared/rules.md + generic part of life_areas.md + that section's
              spec row (+ "Doshas and yogas" notes for yogas/relationships); timeline: rules.md + timeline.md.
  3 validate  starts with "## ", lint clean, rows blocks parse (table_rows.parse_rows) with every row key, a trace
              block, visible words within 0.5x-1.6x of the spec target, not cut off. Up to 2 retries with the
              findings; the attempt with the fewest findings is kept.
  4 editor    repeat_finder -> one call (editor.md + ownership map + repeats + lint + sections) -> edits JSON
              -> apply_edits (backup in OUT/sections_pre_edit). One retry on invalid JSON.
  5 guidance  as a writer, with every edited section appended to its input.
  6 assemble  assemble_report.py -> OUT/report.html (+ OUT/report.pdf with --pdf).
  7 log       OUT/run_log.json + a summary table with total tokens.

--dry-run: no key, no network. Every prompt is still built and written to OUT/prompts/<step>.txt; a MockProvider
returns the matching file from --mock-dir (default: examples/meera/open_run: sections_pre_edit/<sec>.md for writers,
sections/guidance.md for guidance, edits.json for the editor), so validation, retries, the editor application and
assembly all run end to end. Token counts in a dry run are estimates (chars/4).
--only: run only the listed steps (section keys, "editor", "guidance"); sections already in OUT/sections are reused.
See tools/RUNNER.md.
"""
import argparse, concurrent.futures as CF, datetime as D, json, os, re, shutil, subprocess, sys, threading, time
sys.stdout.reconfigure(encoding='utf-8')
TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
SKILL = os.path.join(ROOT, 'skill')
sys.path.insert(0, TOOLS); sys.path.insert(0, os.path.join(TOOLS, 'eval'))
import llm_client
from lint_report import lint
import table_rows as TR

RULES = os.path.join(SKILL, 'shared', 'rules.md')
LIFE = os.path.join(SKILL, 'kundli-report', 'references', 'sections', 'life_areas.md')
TIMELINE_SPEC = os.path.join(SKILL, 'kundli-report', 'references', 'sections', 'timeline.md')
EDITOR_SPEC = os.path.join(SKILL, 'kundli-report', 'references', 'editor.md')
DEFAULT_MOCK = os.path.join(ROOT, 'examples', 'meera', 'open_run')

LIFE_SECTIONS = ['glance', 'personality', 'mind', 'career', 'finance', 'health', 'relationships', 'family',
                 'spirituality', 'yogas']
WRITERS = LIFE_SECTIONS + ['timeline']
EDITABLE = LIFE_SECTIONS[1:]
DOSHA_NOTES_FOR = {'yogas', 'relationships'}
MAX_RETRIES = 2

# Model settings: DEFAULTS, then the first MODEL_SETTINGS prefix that matches the model id, then --settings.
DEFAULTS = {'temperature': 0.3, 'max_tokens': {'section': 6000, 'timeline': 12000, 'editor': 8000, 'guidance': 6000},
            'extra': {}, 'timeout': 900}
MODEL_SETTINGS = {
    # Current Claude models reject temperature, and adaptive thinking counts toward max_tokens: leave room.
    # Top-level cache_control turns on automatic prompt caching, so a retry re-reads its long prefix from cache.
    'claude-': {'temperature': None, 'extra': {'cache_control': {'type': 'ephemeral'}}, 'max_tokens': {'section': 16000, 'timeline': 32000, 'editor': 16000, 'guidance': 16000}},
    # Reasoning models on OpenAI-compatible endpoints: reasoning tokens count toward the cap too.
    'deepseek-reasoner': {'temperature': None, 'max_tokens': {'section': 16000, 'timeline': 32000, 'editor': 16000, 'guidance': 16000}},
    'o3': {'temperature': None, 'extra': {'max_completion_tokens': 32000}},
    'gpt-5': {'temperature': None, 'extra': {'max_completion_tokens': 32000}},
}
DEFAULT_MODEL = {'anthropic': 'claude-opus-5-5', 'openai': 'gpt-4.1', 'file': 'external'}

CONTRACT = ("\n\n## Output contract\n\nOutput only the section Markdown starting with '## {title}', then the hidden rows "
            "block if your input lists one, then the hidden trace block. No preamble.")


def read(p):
    return open(p, encoding='utf-8').read()


def merge(a, b):
    out = dict(a)
    for k, v in (b or {}).items():
        out[k] = merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def settings_for(model, override):
    s = DEFAULTS
    for pre, v in MODEL_SETTINGS.items():
        if model.startswith(pre):
            s = merge(s, v); break
    return merge(s, override)


def est(s):
    return llm_client.est_tokens(s)


# ---------- spec parsing ----------
def life_spec():
    t = read(LIFE)
    i = t.index('## Section specs')
    j = t.find('## Doshas and yogas', i)
    generic = t[:i].rstrip()
    table = t[i:j if j > 0 else len(t)]
    dosha = t[j:].strip() if j > 0 else ''
    lines = [l for l in table.split('\n') if l.startswith('|')]
    head, sep, rows = lines[0], lines[1], {}
    for l in lines[2:]:
        cells = [c.strip() for c in l.strip().strip('|').split('|')]
        rows[cells[0]] = {'line': l, 'title': cells[1], 'target': cells[2]}
    return generic, head, sep, rows, dosha


def target_range(s):
    m = re.search(r'([\d,]+)\s*-\s*([\d,]+)', s)
    return (int(m.group(1).replace(',', '')), int(m.group(2).replace(',', ''))) if m else None


def system_prompt(sec):
    rules = read(RULES).strip()
    if sec == 'timeline':
        spec = read(TIMELINE_SPEC).strip()
        rng = target_range(re.search(r'Length:\s*([^\n]+)', spec).group(1))
        return rules + '\n\n' + spec + CONTRACT.format(title='Timeline'), 'Timeline', rng
    generic, head, sep, rows, dosha = life_spec()
    r = rows[sec]
    parts = [rules, generic, '## Section spec\n\n' + '\n'.join([head, sep, r['line']])]
    if sec in DOSHA_NOTES_FOR and dosha: parts.append(dosha)
    return '\n\n'.join(parts) + CONTRACT.format(title=r['title']), r['title'], target_range(r['target'])


# ---------- validation ----------
def visible_words(t):
    return len(re.findall(r"\b\w[\w'-]*\b", re.sub(r'(?s)<!--.*?-->', ' ', t)))


def expected_rows(input_text):
    """{table_key: [row keys]} from the 'Table rows to fill' blocks in an input."""
    out = {}
    for m in re.finditer(r'## Table rows to fill: (\w+)(.*?)(?=\n## |\Z)', input_text, re.S):
        out[m.group(1)] = re.findall(r'^- `([^`]+)`:', m.group(2), re.M)
    return out


def clean(text):
    t = (text or '').strip()
    m = re.match(r'^```[a-zA-Z]*\n(.*?)\n```\s*$', t, re.S)
    return (m.group(1).strip() if m else t) + '\n'


def validate(text, rows_expected, rng, stop=None):
    f = []
    if not text.lstrip().startswith('## '): f.append('The output must start with the section heading ("## ..."), with no preamble.')
    if stop in ('max_tokens', 'length'): f.append('The output was cut off at the token limit; write it complete, a little shorter.')
    vis = re.sub(r'(?s)<!--.*?-->', ' ', text).split('\n')
    for i, kind, hit, ctx in lint(text):
        line = vis[i - 1] if 0 < i <= len(vis) else ctx
        k = line.find(hit)
        ctx = line[max(0, k - 70): k + len(hit) + 70].strip() if k >= 0 else ctx
        f.append(f'Guardrail lint, line {i} [{kind}]: "{hit}" in: ...{ctx}...')
    parsed = TR.parse_rows(text)
    n_blocks = len(TR.ROWS_RE.findall(text))
    if n_blocks > len(parsed): f.append('A hidden rows block is not valid JSON on one line (double quotes, no trailing comma).')
    for tk, keys in rows_expected.items():
        if tk not in parsed:
            f.append(f'The hidden rows block `<!-- rows:{tk} {{...}} -->` is missing or not valid one-line JSON.'); continue
        got = parsed[tk]
        miss = [k for k in keys if TR._norm_key(k) not in got]
        if miss and tk != 'remedies': f.append(f'rows:{tk} is missing row keys: {", ".join(miss)}.')
        for k, v in got.items():
            for _, kind, hit, _c in lint(v):
                f.append(f'rows:{tk} row "{k}" trips the guardrail lint [{kind}]: "{hit}" (that cell would print as "-").')
    if not re.search(r'<!--\s*trace\b', text): f.append('The hidden trace block (<!-- trace ... -->) is missing at the end.')
    w = visible_words(text)
    if rng:
        lo, hi = int(rng[0] * 0.5), int(rng[1] * 1.6)
        if w < lo: f.append(f'Visible length is {w} words; the target is {rng[0]}-{rng[1]}. Write a fuller section (at least {lo}).')
        if w > hi: f.append(f'Visible length is {w} words; the target is {rng[0]}-{rng[1]}. Cut to at most {hi}.')
    return f, w


# ---------- providers ----------
class Pending(Exception):
    """provider 'file': the prompt is written to OUT/prompts/<name>.txt and no response file exists yet."""


class Caller:
    def __init__(self, a, settings, out):
        self.a, self.s, self.out, self.log, self.lock = a, settings, out, [], threading.Lock()
        os.makedirs(os.path.join(out, 'prompts'), exist_ok=True)

    def mock(self, step):
        md = self.a.mock_dir
        if step == 'editor': return read(os.path.join(md, 'edits.json'))
        for p in ([os.path.join(md, 'sections', 'guidance.md')] if step == 'guidance' else
                  [os.path.join(md, 'sections_pre_edit', f'{step}.md'), os.path.join(md, 'sections', f'{step}.md')]):
            if os.path.exists(p): return read(p)
        return f'## {step}\n\n(mock: no file for this step)\n'

    def call(self, step, kind, system, messages, attempt):
        name = step if attempt == 0 else f'{step}_retry{attempt}'
        with open(os.path.join(self.out, 'prompts', f'{name}.txt'), 'w', encoding='utf-8') as fh:
            fh.write('=== SYSTEM ===\n' + system + '\n')
            for m in messages: fh.write(f"\n=== {m['role'].upper()} ===\n" + m['content'] + '\n')
        mt = self.s['max_tokens'].get(kind, self.s['max_tokens']['section'])
        t0 = time.time()
        if self.a.provider == 'file':  # answers come from OUT/responses/<name>.md, written by an outside model run
            rp = os.path.join(self.out, 'responses', f'{name}.md')
            if not os.path.exists(rp):
                raise Pending(name)
            text = read(rp)
            usage = {'input_tokens': est(system) + sum(est(m['content']) for m in messages), 'output_tokens': est(text),
                     'estimated': True, 'stop': None, 'attempts': 1}
        elif self.a.dry_run:
            text = self.mock(step)
            usage = {'input_tokens': est(system) + sum(est(m['content']) for m in messages), 'output_tokens': est(text),
                     'estimated': True, 'stop': 'mock', 'attempts': 1}
        else:
            text, usage = llm_client.complete(messages, system, self.a.model, self.a.provider, self.a.base_url, mt,
                                              self.s['temperature'], timeout=self.s.get('timeout', 900),
                                              extra=self.s.get('extra'))
        rec = {'step': step, 'attempt': attempt, 'model': 'mock:' + self.a.model if self.a.dry_run else self.a.model,
               'max_tokens': mt, **usage, 'seconds': round(time.time() - t0, 1)}
        with self.lock: self.log.append(rec)
        return text, rec


# ---------- steps ----------
def run(cmd, log, label):
    r = subprocess.run([sys.executable, '-I'] + cmd, capture_output=True, text=True, encoding='utf-8')
    log.append({'step': label, 'cmd': ' '.join(cmd), 'returncode': r.returncode, 'stdout': r.stdout[-4000:], 'stderr': r.stderr[-4000:]})
    if r.returncode != 0:
        raise SystemExit(f'{label} failed ({r.returncode}):\n{r.stderr[-3000:]}')
    return r.stdout


def build_inputs(a, out, events):
    ind = os.path.join(out, 'inputs')
    if a.inputs:
        if os.path.abspath(a.inputs) != os.path.abspath(ind):
            shutil.copytree(a.inputs, ind, dirs_exist_ok=True)
        events.append({'step': 'inputs', 'reused': a.inputs}); return ind
    os.makedirs(ind, exist_ok=True)
    now = ['--now', a.now] if a.now else []
    run([os.path.join(TOOLS, 'report_input.py'), '--chart', a.chart, '--outdir', ind] + now, events, 'inputs:report_input')
    run([os.path.join(TOOLS, 'dasha_facts.py'), '--chart', a.chart, '--out', os.path.join(ind, 'dasha_input.json'),
         '--md', os.path.join(ind, 'dasha_input.md')] + now, events, 'inputs:dasha_facts')
    return ind


def write_section(C, sec, user, secdir, kind='section'):
    system, title, rng = system_prompt('guidance' if sec == 'guidance' else sec)
    rows_exp = expected_rows(user)
    messages = [{'role': 'user', 'content': user}]
    attempts = []
    for k in range(MAX_RETRIES + 1):
        raw, rec = C.call(sec, kind, system, messages, k)
        text = clean(raw)
        f, w = validate(text, rows_exp, rng, rec.get('stop'))
        rec.update({'findings': f, 'words': w, 'target': rng})
        attempts.append((len(f), k, text))
        if not f: break
        if k < MAX_RETRIES:
            messages = messages + [{'role': 'assistant', 'content': raw},
                                   {'role': 'user', 'content': 'Your section has these problems:\n' + '\n'.join(f'- {x}' for x in f) +
                                    f"\n\nReturn the full corrected section, starting with '## {title}', then the hidden rows block "
                                    "if your input lists one, then the hidden trace block. No preamble."}]
    best = min(attempts)
    open(os.path.join(secdir, f'{sec}.md'), 'w', encoding='utf-8').write(best[2])
    # safety gate: a section that still fails after its retries is BLOCKED (production must not send it; use a
    # fallback model or human review). The test run keeps it so it can be graded, and reports it.
    return {'section': sec, 'kept_attempt': best[1], 'attempts': len(attempts), 'findings_left': best[0],
            'blocked': best[0] > 0}


def editor_step(C, a, ind, secdir, out, events):
    reps = os.path.join(out, 'repeats.md')
    run([os.path.join(TOOLS, 'repeat_finder.py'), '--chart', a.chart, '--sections', secdir, '--out', reps], events, 'editor:repeat_finder')
    lint_lines = []
    secs = {}
    for s in LIFE_SECTIONS + ['timeline']:
        p = os.path.join(secdir, f'{s}.md')
        if not os.path.exists(p): continue
        secs[s] = read(p)
        if s in EDITABLE:
            lint_lines += [f'- {s} line {i} [{kind}] "{hit}" | {ctx}' for i, kind, hit, ctx in lint(secs[s])]
    system = read(EDITOR_SPEC).strip() + (
        '\n\n## Output contract\n\nThe tools named above are run for you: the ownership map, the repeat list and the lint '
        'findings are in the user message. Output only the JSON array of edits '
        '([{"section": ..., "old": ..., "new": ..., "reason": ...}]), nothing else: no preamble, no code fence.')
    user = ('# Ownership map\n\n' + read(os.path.join(ind, 'ownership_map.md')) + '\n\n' + read(reps) +
            '\n\n# Lint findings in editable sections\n\n' + ('\n'.join(lint_lines) or 'none') + '\n\n# Finished sections\n')
    for s, t in secs.items():
        user += f"\n\n===== SECTION: {s}{' (read only, not editable)' if s == 'timeline' else ''} =====\n\n{t}"
    messages = [{'role': 'user', 'content': user}]
    edits, err = None, None
    for k in range(2):
        raw, rec = C.call('editor', 'editor', system, messages, k)
        edits, err = parse_edits(raw)
        rec['findings'] = [err] if err else []
        rec['edits'] = len(edits or [])
        if edits is not None: break
        messages = messages + [{'role': 'assistant', 'content': raw},
                               {'role': 'user', 'content': f'That was not a valid JSON array of edits ({err}). Output only the JSON array, nothing else.'}]
    if edits is None:
        events.append({'step': 'editor:apply', 'skipped': f'no valid edits JSON: {err}'}); return None
    ep = os.path.join(out, 'edits.json')
    json.dump(edits, open(ep, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    so = run([os.path.join(TOOLS, 'apply_edits.py'), '--sections', secdir, '--edits', ep,
              '--backup', os.path.join(out, 'sections_pre_edit')], events, 'editor:apply_edits')
    return so


def parse_edits(raw):
    t = (raw or '').strip()
    t = re.sub(r'^```[a-zA-Z]*\s*\n', '', t); t = re.sub(r'\n```\s*$', '', t)
    i, j = t.find('['), t.rfind(']')
    if i < 0 or j < i: return None, 'no JSON array found'
    try:
        obj = json.loads(t[i:j + 1])
    except Exception as e:
        return None, f'JSON error: {e}'
    if isinstance(obj, dict): obj = obj.get('edits')
    if not isinstance(obj, list): return None, 'not a list'
    good = [e for e in obj if isinstance(e, dict) and isinstance(e.get('section'), str) and isinstance(e.get('old'), str)]
    if obj and not good: return None, 'no item has "section" and "old" strings'
    return good, None


def summary(log):
    rows = [r for r in log if 'input_tokens' in r]
    hdr = f"{'call':22s} {'model':24s} {'in':>8s} {'out':>7s} {'est':>3s} {'words':>6s} {'find':>4s} {'secs':>6s}"
    lines = [hdr, '-' * len(hdr)]
    for r in rows:
        name = r['step'] + (f"#{r['attempt']}" if r['attempt'] else '')
        lines.append(f"{name:22s} {r['model'][:24]:24s} {r['input_tokens']:8d} {r['output_tokens']:7d} {'y' if r['estimated'] else 'n':>3s} "
                     f"{str(r.get('words', '')):>6s} {len(r.get('findings', [])):4d} {r['seconds']:6.1f}")
    ti, to = sum(r['input_tokens'] for r in rows), sum(r['output_tokens'] for r in rows)
    first = [r for r in rows if r['attempt'] == 0]
    lines.append('-' * len(hdr))
    lines.append(f"{'TOTAL (' + str(len(rows)) + ' calls)':22s} {'':24s} {ti:8d} {to:7d}   = {ti + to} tokens")
    lines.append(f"{'first attempts only':22s} {'':24s} {sum(r['input_tokens'] for r in first):8d} {sum(r['output_tokens'] for r in first):7d}"
                 f"   = {sum(r['input_tokens'] + r['output_tokens'] for r in first)} tokens")
    return '\n'.join(lines), ti, to


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--chart', required=True); ap.add_argument('--name', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--model'); ap.add_argument('--provider', choices=['anthropic', 'openai', 'file'], default='anthropic')
    ap.add_argument('--base-url'); ap.add_argument('--max-workers', type=int, default=4)
    ap.add_argument('--pdf', action='store_true'); ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--only', help='comma list of steps: section keys, editor, guidance')
    ap.add_argument('--inputs', help='reuse an existing inputs folder instead of building one')
    ap.add_argument('--now', help='as-of date passed to the input builders (default: the chart transit date)')
    ap.add_argument('--settings', help='JSON string or file overriding model settings, e.g. {"temperature":0.2,"max_tokens":{"section":8000}}')
    ap.add_argument('--mock-dir', default=DEFAULT_MOCK, help='dry run: folder with sections_pre_edit/, sections/ and edits.json')
    ap.add_argument('--prepared', help='date printed on the cover')
    a = ap.parse_args()
    a.chart, out = os.path.abspath(a.chart), os.path.abspath(a.out)
    a.model = a.model or DEFAULT_MODEL[a.provider]
    ov = {}
    if a.settings:
        ov = json.load(open(a.settings, encoding='utf-8')) if os.path.exists(a.settings) else json.loads(a.settings)
    S = settings_for(a.model, ov)
    only = set(x.strip() for x in a.only.split(',')) if a.only else None
    want = lambda step: only is None or step in only
    os.makedirs(out, exist_ok=True)
    secdir = os.path.join(out, 'sections'); os.makedirs(secdir, exist_ok=True)
    events, t0 = [], time.time()
    C = Caller(a, S, out)
    print(f"runner: model {a.model} via {a.provider}{' (DRY RUN, mock provider)' if a.dry_run else ''}; settings {json.dumps(S)}")

    ind = build_inputs(a, out, events)
    print(f'inputs: {ind}')

    # writers
    jobs = {}
    for sec in WRITERS:
        if not want(sec): continue
        if sec == 'timeline':
            user = read(os.path.join(ind, 'dasha_input.md'))
            tr = os.path.join(ind, 'timeline_rows.md')
            if os.path.exists(tr): user += '\n\n' + read(tr)
            jobs[sec] = (user, 'timeline')
        else:
            jobs[sec] = (read(os.path.join(ind, f'{sec}.md')), 'section')
    results = []
    with CF.ThreadPoolExecutor(max_workers=max(1, a.max_workers)) as ex:
        futs = {ex.submit(write_section, C, s, u, secdir, k): s for s, (u, k) in jobs.items()}
        for fu in CF.as_completed(futs):
            try:
                r = fu.result()
            except Pending as e:
                r = {'section': futs[fu], 'pending': str(e)}
            except Exception as e:
                r = {'section': futs[fu], 'error': repr(e)}
            results.append(r)
            print(f"  writer {r['section']:14s} " + (f"ERROR {r['error']}" if 'error' in r else f"PENDING {r['pending']}" if 'pending' in r else
                  f"attempts {r['attempts']}, kept #{r['kept_attempt']}, findings left {r['findings_left']}"
                  + (' BLOCKED' if r.get('blocked') else '')))
    events.append({'step': 'writers', 'results': sorted(results, key=lambda r: WRITERS.index(r['section']))})
    pend = [r['pending'] for r in results if 'pending' in r]

    def stop_pending(names):
        open(os.path.join(out, 'PENDING.txt'), 'w', encoding='utf-8').write('\n'.join(names) + '\n')
        print(f"\nPENDING {len(names)}: answer OUT/prompts/<name>.txt into OUT/responses/<name>.md, then rerun: {', '.join(names)}")
        raise SystemExit(3)
    if pend: stop_pending(pend)
    if os.path.exists(os.path.join(out, 'PENDING.txt')): os.remove(os.path.join(out, 'PENDING.txt'))

    # editor
    if want('editor'):
        done_flag = os.path.join(out, 'EDITOR_DONE')
        if os.path.exists(done_flag):
            print('editor: already applied (EDITOR_DONE)')
        else:
            try:
                so = editor_step(C, a, ind, secdir, out, events)
            except Pending as e:
                stop_pending([str(e)])
            open(done_flag, 'w').write('ok')
            if so: print('editor: ' + so.strip().replace('\n', '\n        '))

    # guidance
    if want('guidance'):
        user = read(os.path.join(ind, 'guidance.md')) + '\n\n# Finished sections (already edited)\n'
        for s in LIFE_SECTIONS + ['timeline']:
            p = os.path.join(secdir, f'{s}.md')
            if os.path.exists(p): user += f'\n\n===== SECTION: {s} =====\n\n' + read(p)
        try:
            r = write_section(C, 'guidance', user, secdir, 'guidance')
        except Pending as e:
            stop_pending([str(e)])
        events.append({'step': 'guidance', 'result': r})
        print(f"  guidance: attempts {r['attempts']}, kept #{r['kept_attempt']}, findings left {r['findings_left']}")

    # final lint of what will be assembled
    events.append({'step': 'final_lint', 'findings': {f[:-3]: len(lint(read(os.path.join(secdir, f))))
                                                      for f in sorted(os.listdir(secdir)) if f.endswith('.md')}})
    # assemble
    cmd = [os.path.join(TOOLS, 'assemble_report.py'), '--chart', a.chart, '--sections', secdir, '--name', a.name,
           '--out', os.path.join(out, 'report.html')]
    if a.pdf: cmd += ['--pdf', os.path.join(out, 'report.pdf')]
    if a.prepared: cmd += ['--prepared', a.prepared]
    so = run(cmd, events, 'assemble')
    print('assemble: ' + so.strip().split('\n')[-1] if so.strip() else 'assemble: done')

    table, ti, to = summary(C.log)
    log = {'model': a.model, 'provider': a.provider, 'base_url': a.base_url, 'dry_run': a.dry_run, 'settings': S,
           'started': D.datetime.fromtimestamp(t0).isoformat(timespec='seconds'), 'wall_seconds': round(time.time() - t0, 1),
           'total_input_tokens': ti, 'total_output_tokens': to, 'calls': C.log, 'events': events}
    json.dump(log, open(os.path.join(out, 'run_log.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
    print('\n' + table)
    print(f"\nwall time {log['wall_seconds']} s; log {os.path.join(out, 'run_log.json')}")


if __name__ == '__main__':
    main()
