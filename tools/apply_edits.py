"""Apply the editor pass's cuts to finished report sections, safely.

  python -I tools/apply_edits.py --sections <dir> --edits edits.json [--backup <dir>]

edits.json: [{"section": "finance", "old": "exact visible text", "new": "shorter text or empty", "reason": "..."}]

An edit is applied only when `old` occurs exactly once in the section's visible text (outside the hidden trace
comment), is not inside a heading or table row, and `new` is shorter than `old` and adds no digits (dates and degrees
must not change). Everything else is rejected and listed. Originals are copied to --backup first. Prints a summary
and the words removed per section.
"""
import argparse, json, os, re, shutil, sys
sys.stdout.reconfigure(encoding='utf-8')


def split_trace(t):
    m = re.search(r'(?s)<!--.*?-->\s*$', t)
    return (t[:m.start()], t[m.start():]) if m else (t, '')


def words(t):
    return len(re.findall(r"\b\w[\w'-]*\b", re.sub(r'(?s)<!--.*?-->', ' ', t)))


def check(body, old, new):
    if not old or len(old) < 12: return 'old too short'
    n = body.count(old)
    if n != 1: return f'old found {n} times'
    i = body.index(old)
    line = body[body.rfind('\n', 0, i) + 1: body.find('\n', i) if body.find('\n', i) >= 0 else len(body)]
    if line.lstrip().startswith(('#', '|')): return 'touches a heading or table row'
    if len(new) >= len(old): return 'new is not shorter'
    if set(re.findall(r'\d+', new)) - set(re.findall(r'\d+', old)): return 'new adds numbers'
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sections', required=True); ap.add_argument('--edits', required=True); ap.add_argument('--backup')
    a = ap.parse_args()
    edits = json.load(open(a.edits, encoding='utf-8'))
    if isinstance(edits, dict): edits = edits.get('edits', [])
    if a.backup:
        os.makedirs(a.backup, exist_ok=True)
        for f in os.listdir(a.sections):
            if f.endswith('.md') and not os.path.exists(os.path.join(a.backup, f)):
                shutil.copy(os.path.join(a.sections, f), os.path.join(a.backup, f))
    texts, before = {}, {}
    ok, bad = 0, []
    for e in edits:
        sec = e.get('section', '').strip()
        path = os.path.join(a.sections, f'{sec}.md')
        if sec == 'timeline' or not os.path.exists(path):
            bad.append((sec, 'no such editable section', e.get('old', '')[:80])); continue
        if sec not in texts:
            texts[sec] = open(path, encoding='utf-8').read(); before[sec] = words(texts[sec])
        body, trace = split_trace(texts[sec])
        old, new = e.get('old', ''), e.get('new', '') or ''
        why = check(body, old, new)
        if why:
            bad.append((sec, why, old[:80])); continue
        body = body.replace(old, new, 1)
        body = re.sub(r'[ \t]{2,}', ' ', body)
        body = re.sub(r' +([.,;:])', r'\1', body)
        body = re.sub(r'\n{3,}', '\n\n', body)
        texts[sec] = body + trace; ok += 1
    for sec, t in texts.items():
        open(os.path.join(a.sections, f'{sec}.md'), 'w', encoding='utf-8').write(t)
    print(f'applied {ok} of {len(edits)} edits')
    for sec in sorted(texts):
        print(f'  {sec:14s} {before[sec]:5d} -> {words(texts[sec]):5d} words')
    for sec, why, old in bad:
        print(f'  REJECTED {sec}: {why}: "{old}"')


if __name__ == '__main__':
    main()
