"""Word-level comparison of a generated report section with the benchmark section.

  python -I tools/eval/score_text.py --benchmark bench.txt --candidate cand.md [--json out.json]

Reports length, ROUGE-1/2/L F1 (lowercased word tokens), content-word recall (benchmark's distinct non-stopwords found in
the candidate), named-term recall (capitalised astrology terms, planets, signs, period names) and date recall (Month YYYY).
These measure overlap in wording only. Whether the candidate says the same THINGS is scored separately by the claim grader.
"""
import argparse, json, re, sys, collections
sys.stdout.reconfigure(encoding='utf-8')
STOP = set('''a an the and or but if then so of in on at to for from by with as is are was were be been being it its this that these those
there here which who whom whose what when where why how not no nor than too very can could may might will would shall should do does did
has have had having i you he she they we his her their our your my me him them us also into over under about after before during until
while within without between through up down out off again further once more most other some such only own same both each few all any
one two three per via vs etc just even much many often usually rather quite toward towards upon across'''.split())
MONTHS = {m: i for i, m in enumerate(['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'], 1)}


def strip_trace(t):
    return re.sub(r'(?s)<!--.*?-->', ' ', t)


def tokens(t):
    return re.findall(r"[a-z0-9]+(?:'[a-z]+)?", t.lower())


def ngrams(toks, n):
    return collections.Counter(tuple(toks[i:i + n]) for i in range(len(toks) - n + 1))


def f1(c, b):
    overlap = sum((c & b).values()); p = overlap / max(1, sum(c.values())); r = overlap / max(1, sum(b.values()))
    return 0 if p + r == 0 else 2 * p * r / (p + r), r


def lcs(a, b):
    prev = [0] * (len(b) + 1)
    for x in a:
        cur = [0]
        for j, y in enumerate(b):
            cur.append(prev[j] + 1 if x == y else max(prev[j + 1], cur[j]))
        prev = cur
    return prev[-1]


def dates(t):
    out = set()
    for m, y in re.findall(r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{4})\b', t.lower()):
        out.add(f'{y}-{MONTHS[m]:02d}')
    for y, mm in re.findall(r'\b(\d{4})-(\d{2})-\d{2}\b', t):
        out.add(f'{y}-{mm}')
    return out


def named_terms(t):
    words = re.findall(r"(?<![.!?]\s)(?<!^)\b([A-Z][a-z]+(?:[-–][A-Z][a-z]+)?)", t, flags=re.M)
    return {w.lower() for w in words if w.lower() not in STOP and len(w) > 2}


def score(bench, cand):
    bench, cand = strip_trace(bench), strip_trace(cand)
    bt, ct = tokens(bench), tokens(cand)
    r1, r1rec = f1(ngrams(ct, 1), ngrams(bt, 1)); r2, r2rec = f1(ngrams(ct, 2), ngrams(bt, 2))
    l = lcs(ct, bt); rl_p, rl_r = l / max(1, len(ct)), l / max(1, len(bt)); rl = 0 if l == 0 else 2 * rl_p * rl_r / (rl_p + rl_r)
    bc = {w for w in bt if w not in STOP and not w.isdigit()}; cc = set(ct)
    bn, cn = named_terms(bench), named_terms(cand) | set(ct)
    bd, cd = dates(bench), dates(cand)
    res = {'benchmark_words': len(bench.split()), 'candidate_words': len(cand.split()),
           'length_ratio': round(len(cand.split()) / max(1, len(bench.split())), 2),
           'rouge1_f1': round(r1, 3), 'rouge2_f1': round(r2, 3), 'rougeL_f1': round(rl, 3),
           'content_word_recall': round(len(bc & cc) / max(1, len(bc)), 3),
           'named_term_recall': round(len(bn & cn) / max(1, len(bn)), 3),
           'date_recall': round(len(bd & cd) / max(1, len(bd)), 3),
           'named_terms_missed': sorted(bn - cn)[:60], 'dates_missed': sorted(bd - cd)}
    res['word_score'] = round(100 * (res['content_word_recall'] + res['named_term_recall'] + res['date_recall'] + res['rouge1_f1']) / 4, 1)
    return res


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--benchmark', required=True); ap.add_argument('--candidate', required=True); ap.add_argument('--json')
    a = ap.parse_args()
    r = score(open(a.benchmark, encoding='utf-8').read(), open(a.candidate, encoding='utf-8').read())
    print(json.dumps(r, ensure_ascii=False, indent=1))
    if a.json: json.dump(r, open(a.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
