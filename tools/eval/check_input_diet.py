"""Check that a slimmed-down set of report inputs kept every fact the writers need (v0.16 input diet).

  python -I tools/eval/check_input_diet.py OLD_DIR NEW_DIR [OLD_DIR NEW_DIR ...]

For every *.md in OLD_DIR (the same file must exist in NEW_DIR):
- dates: every YYYY-MM-DD and "Mon YYYY" string in the old file is in the new one;
- entry ids: every `type/...` id in backticks in the old file is in the new one;
- holding conditions: every condition that holds (lines under "Conditions that HOLD", the "Same entry ... HOLD for this
  stretch" lists and the principle lines) is in the new file under the same period heading, with the same polarity and
  the same "true because" parts; principle codes (P1, P2 ...) in the new file are resolved through their legend;
- section inputs: the fixed blocks (everything before "## Chart facts for this section": verdicts, ownership note,
  periods ahead, must-cover; the chart facts; the rows block from "## Table rows to fill") are unchanged, and any
  line carrying "true because" or a [polarity] condition is still there word for word.
Prints old -> new token estimates (characters / 4) per file and exits 1 on any loss.
"""
import os, re, sys
sys.stdout.reconfigure(encoding='utf-8')

DATE = re.compile(r'\b\d{4}-\d{2}-\d{2}\b')
MON = re.compile(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{4}\b')
EID = re.compile(r'`([a-z][a-z0-9_]*/[^`\s]+)`')
COND = re.compile(r'^\s*- (?:P\d+ )?\[(good|bad|mixed|neutral)\] (?:`[^`]+`: )?(.*?)(?:  \[true because: (.*?)\])? -> ')
LEGEND = re.compile(r'^\s*- (P\d+) \[(good|bad|mixed|neutral)\] (.*?) -> ')
REF = re.compile(r'\b(P\d+) \[(good|bad|mixed|neutral)\]')
SAME = re.compile(r'^Same entry as above \(`[^`]+`\)\. Conditions that HOLD for this stretch: (.*)$')
PRINC = re.compile(r'^Principles whose conditions hold')


def tok(s):
    return len(s) // 4


def is_block_heading(line):
    return line.startswith('#') and 'Library entry' not in line


def holding(text):
    """{period heading: set of (polarity, when, true_because)} for the conditions that hold."""
    lines = text.split('\n')
    legend = {}
    for ln in lines:
        m = LEGEND.match(ln)
        if m: legend[m.group(1)] = (m.group(2), m.group(3))
    out, block, mode = {}, '(top)', None
    for ln in lines:
        if is_block_heading(ln):
            block = ln.strip(); mode = None; continue
        if ln.startswith('Conditions that HOLD'): mode = 'hold'; continue
        if ln.startswith('Principles whose conditions hold for this'):
            mode = 'princ'
            if ':' in ln and REF.search(ln):  # v0.16 one-line form with codes
                for code, pol in REF.findall(ln):
                    p, w = legend.get(code, (pol, f'<code {code} has no legend line>'))
                    out.setdefault(block, set()).add((pol if p == pol else f'{pol}<>{p}', w, None))
                mode = None
            continue
        m = SAME.match(ln)
        if m:
            if m.group(1).strip() != 'none':
                for part in re.split(r'; (?=\[(?:good|bad|mixed|neutral)\] )', m.group(1)):
                    pm = re.match(r'\[(\w+)\] (.*)$', part.strip())
                    out.setdefault(block, set()).add((pm.group(1), pm.group(2), None))
            continue
        if mode in ('hold', 'princ'):
            m = COND.match(ln)
            if m and not m.group(2).startswith('manual'):
                out.setdefault(block, set()).add((m.group(1), m.group(2), m.group(3)))
                continue
            if not ln.startswith('- '): mode = None
    return out


def fixed_blocks(text):
    a = text.find('## Chart facts for this section')
    b = text.find('## Library entries that apply')
    r = text.find('## Table rows to fill')
    return {'head': text[:a] if a >= 0 else '', 'facts': text[a:b] if a >= 0 and b > a else '',
            'rows': text[r:] if r >= 0 else ''}


def check_file(old, new, name):
    errs = []
    for rx, lab in ((DATE, 'date'), (MON, 'month date'), (EID, 'entry id')):
        miss = sorted(set(rx.findall(old)) - set(rx.findall(new)))
        if miss: errs.append(f'{lab}s missing: {miss[:12]}{" ..." if len(miss) > 12 else ""}')
    if 'Dasha input' in old[:200]:
        ho, hn = holding(old), holding(new)
        n = 0
        for blk, conds in ho.items():
            got = hn.get(blk, set())
            # a condition repeated by the 'Same entry' path carries no 'true because' in the old file either
            got_loose = {(p, w) for p, w, _ in got}
            for c in conds:
                n += 1
                if c not in got and not (c[2] is None and (c[0], c[1]) in got_loose):
                    errs.append(f'holding condition lost under "{blk[:70]}": [{c[0]}] {c[1][:90]}'
                                + (f' [true because: {c[2][:60]}]' if c[2] else ''))
        if not errs: errs_note = f'{n} holding conditions kept in {len(ho)} blocks'
        else: errs_note = ''
    else:
        fo, fn = fixed_blocks(old), fixed_blocks(new)
        for k in fo:
            if fo[k] != fn[k]: errs.append(f'fixed block changed: {k}')
        nl = set(new.split('\n'))
        for ln in old.split('\n'):
            if ('true because' in ln or COND.match(ln)) and ln not in nl:
                errs.append(f'condition line lost: {ln[:100]}')
        errs_note = ''
    return errs, errs_note


def main(argv):
    if len(argv) < 2 or len(argv) % 2:
        print(__doc__); return 2
    bad = 0
    for i in range(0, len(argv), 2):
        od, nd = argv[i], argv[i + 1]
        print(f'\n== {od} -> {nd}')
        print(f"{'file':22s} {'old':>7s} {'new':>7s} {'change':>7s}  check")
        to = tn = 0
        for f in sorted(x for x in os.listdir(od) if x.endswith('.md')):
            old = open(os.path.join(od, f), encoding='utf-8').read()
            p = os.path.join(nd, f)
            if not os.path.exists(p):
                print(f'{f:22s} missing in new'); bad += 1; continue
            new = open(p, encoding='utf-8').read()
            errs, note = check_file(old, new, f)
            to += tok(old); tn += tok(new)
            ch = (tok(new) - tok(old)) / max(1, tok(old)) * 100
            print(f"{f:22s} {tok(old):7d} {tok(new):7d} {ch:6.0f}%  {'OK' if not errs else 'FAIL'}{' (' + note + ')' if note else ''}")
            for e in errs: print('    - ' + e)
            bad += bool(errs)
        print(f"{'TOTAL':22s} {to:7d} {tn:7d} {(tn - to) / max(1, to) * 100:6.0f}%")
    print('\nALL CHECKS PASSED' if not bad else f'\n{bad} file(s) FAILED')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
