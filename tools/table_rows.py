"""Model-row tables for the long kundli report (v0.15): tables whose fact columns come from code and whose last column
is one line per row written by the section writer in a hidden block at the end of the section:

    <!-- rows:wealth_houses {"2": "one line", "11": "one line", "5": "...", "9": "...", "12": "..."} -->

build(chart, F, now, lib, sections_md) -> {key: {"title", "html", "note"}} for wealth_houses (finance),
body_correspondences (health), summary_10y (timeline) and remedies (guidance). A missing or unreadable block gives the
same table with "-" in the model column. Row keys per table come from row_keys() so tools/report_input.py tells the
writer exactly what to fill. Model text that trips the guardrail lint is dropped to "-".
"""
import html, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasha_facts as DF
import chart_verdicts as CV
try:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'eval'))
    from lint_report import lint as _lint
except Exception:  # lint is a safety net only
    _lint = None

GRAHAS = ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn', 'Rahu', 'Ketu']
SIGN_TITLE = [s.title() for s in DF.SIGNS]
MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

WEALTH_HOUSES = [(2, 'Savings, family money, speech'), (11, 'Income and gains'), (5, 'Investments, intelligence, past merit'),
                 (9, 'Fortune and blessings'), (12, 'Expenses and outflow')]
# Kalapurusha: the 12 houses (and the 12 signs in natural order) map to body regions, head to feet (Brihat Jataka 1.4;
# BPHS ch. 4). General regions only: the report never names organs or diseases.
KALAPURUSHA = {1: 'Head', 2: 'Face and throat', 3: 'Shoulders and arms', 4: 'Chest', 5: 'Upper abdomen',
               6: 'Abdomen and waist', 7: 'Lower back and lower abdomen', 8: 'Pelvic region', 9: 'Hips and thighs',
               10: 'Knees', 11: 'Calves and ankles', 12: 'Feet'}
HEALTH_HOUSES = [(1, 'Body and vitality'), (6, 'Daily health and routine'), (8, 'Recovery and resilience'), (12, 'Rest and sleep')]
SUMMARY_DT_HOUSES = [1, 2, 4, 5, 7, 9, 10, 11]
HOUSE_TOPIC = {1: 'self and health', 2: 'money and family', 3: 'effort and siblings', 4: 'home and property',
               5: 'children and creative work', 6: 'work routine and health', 7: 'partnership', 8: 'change and research',
               9: 'fortune and teachers', 10: 'career', 11: 'gains and friends', 12: 'expenses and retreat'}
REMEDY_DAY = {'Sun': 'Sunday', 'Moon': 'Monday', 'Mars': 'Tuesday', 'Mercury': 'Wednesday', 'Jupiter': 'Thursday',
              'Venus': 'Friday', 'Saturn': 'Saturday', 'Rahu': 'Saturday', 'Ketu': 'Tuesday'}
TITLES = {'wealth_houses': 'The wealth houses', 'body_correspondences': 'Traditional body correspondences',
          'summary_10y': 'The next ten years at a glance', 'remedies': 'Optional traditional remedies'}
TABLE_SECTION = {'wealth_houses': 'finance', 'body_correspondences': 'health', 'summary_10y': 'timeline', 'remedies': 'guidance'}
ROW_HINT = {
    'wealth_houses': 'what this house says about money in this chart, in one plain line',
    'body_correspondences': 'one short, general care note for this house (habits, rest, routine); never organs, illnesses or diseases',
    'summary_10y': 'what this stretch is about in one plain line (no dates: the table gives them)',
    'remedies': 'the traditional practice in one short line (optional; leave a planet out to show "-")',
}

ROWS_RE = re.compile(r'<!--\s*rows:([a-z0-9_]+)\s*(.*?)-->', re.S | re.I)


def esc(x):
    return html.escape(str(x if x not in (None, '') else '-'))


def month(d):
    y, m = d[:4], int(d[5:7])
    return f'{MONTHS[m - 1]} {y}'


def ordinal(h):
    return f"{h}{'th' if 10 <= h % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(h % 10, 'th')}"


def table(head, rows):
    th = ''.join(f'<th>{esc(h)}</th>' for h in head)
    tb = ''.join('<tr>' + ''.join(f'<td>{esc(c)}</td>' for c in r) + '</tr>' for r in rows)
    return f'<table><thead><tr>{th}</tr></thead><tbody>{tb}</tbody></table>'


# ---------- parsing ----------
def _norm_key(k):
    k = str(k).strip().strip('"\'')
    m = re.fullmatch(r'(?i)(?:house\s*)?(\d{1,2})(?:st|nd|rd|th)?(?:\s*house)?', k)
    if m: return str(int(m.group(1)))
    return k.lower().replace(' ', '')


def parse_rows(md):
    """All rows blocks in a Markdown text -> {table_key: {normalised row key: text}}. Lenient about trailing commas and
    curly quotes; a block that still is not a JSON object is ignored."""
    out = {}
    for m in ROWS_RE.finditer(md or ''):
        key, body = m.group(1).lower(), m.group(2).strip()
        body = re.sub(r',\s*}', '}', body)
        obj = None
        for cand in (body, body.replace('“', '"').replace('”', '"')):
            try:
                obj = json.loads(cand); break
            except Exception:
                pass
        if not isinstance(obj, dict): continue
        rows = out.setdefault(key, {})
        for k, v in obj.items():
            if isinstance(v, (str, int, float)):
                t = re.sub(r'\s+', ' ', str(v)).strip().strip('*')
                if t: rows[_norm_key(k)] = t[:240]
    return out


def _safe(t):
    if not t: return '-'
    if _lint and _lint(t): return '-'
    return t


# ---------- row keys (shared with report_input.py) ----------
def _house_cond(chart, h):
    x = next((y for y in chart.get('houses', []) if y.get('house') == h), None)
    if not x: return None
    occ = [o for o in x.get('occupants', []) if o in GRAHAS]
    dig = x.get('lord_dignity')
    if dig == 'debilitated' and any(y.get('name') == f"Neecha Bhanga ({x['lord']})" for y in chart.get('yogas_present', [])):
        dig = 'debilitated, cancelled'
    lord = f"{x['sign']}; lord {x['lord']} in the {ordinal(x['lord_in_house'])} ({x['lord_in_sign']}{', ' + dig if dig and dig != 'other' else ''})"
    return lord, (', '.join(occ) or 'none')


def remedy_planets(F, lib=None):
    """Planets that get a remedy line in Guidance: debilitated or in an enemy sign, in a dusthana, or combust (the same rule
    report_input.py has always used), kept only when the library has a remedy entry for them."""
    out = []
    for g in GRAHAS:
        f = F.get(g)
        if not f: continue
        if f['dignity'] in ('debilitated', 'enemy') or f['house'] in (6, 8, 12) or f['combust']:
            if lib is None or lib.get(f'remedy/{g.lower()}'): out.append(g)
    return out


DIG_WORDS = {'debilitated': 'debilitated', 'enemy': "in an enemy's sign", 'friend': "in a friend's sign", 'neutral': 'in a neutral sign',
             'exalted': 'exalted', 'own': 'in its own sign', 'moolatrikona': 'in its moolatrikona sign'}


def _remedy_why(f, g=None, chart=None):
    bits = []
    d = f.get('dignity')
    if d in DIG_WORDS:
        w = DIG_WORDS[d]
        if d == 'debilitated' and g and chart and any(y.get('name') == f'Neecha Bhanga ({g})' for y in chart.get('yogas_present', [])):
            w = 'debilitated, cancelled'
        bits.append(w)
    bits.append(f"in the {ordinal(f['house'])}")
    if f.get('combust'): bits.append('close to the Sun')
    return ', '.join(bits)


def _merge(spells, gap_days=400):
    """Join a list of (from, to) date strings whose gaps are short into stretches."""
    import datetime as D
    out = []
    for a, b in sorted(spells):
        if out and (D.date.fromisoformat(a) - D.date.fromisoformat(out[-1][1])).days <= gap_days:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def summary_periods(chart, F, now, years=10):
    """Rows of the ten-year summary in date order: [{id, kind, from, to, link}]. Ids: '<MD>-<AD>' for a sub-period,
    'DT<house>-<year>' for a double-transit stretch on a non-dusthana house, 'SS-<phase>-<year>' for a Saturn phase."""
    end = DF.add_years(now, years)
    rows = []
    for md, ads in (chart.get('vimshottari', {}).get('antardashas_by_md') or {}).items():
        for a in ads:
            if a['end'] <= now or a['start'] >= end: continue
            g = a['ad']
            f = F.get(g, {})
            if g in ('Rahu', 'Ketu'):
                link = f"{g} in the {ordinal(f.get('house', 0))}, through its sign lord {f.get('sign_lord')}"
            else:
                link = f"{g} rules {'/'.join(map(str, f.get('rules', []))) or '-'}, sits in the {ordinal(f.get('house', 0))}"
            rows.append({'id': f'{md}-{g}', 'kind': f'Sub-period {md}-{g}' + (' (now)' if a['start'] <= now < a['end'] else ''),
                         'from': a['start'], 'to': a['end'], 'link': link})
    try:
        win = DF.computed_windows(F, chart, now)
    except Exception:
        win = {'double_transit': []}
    for h in SUMMARY_DT_HOUSES:
        sp = [(w['from'], w['to']) for w in win.get('double_transit', []) if w['house'] == h and w['from'] < end]
        for a, b in _merge(sp):
            rows.append({'id': f'DT{h}-{a[:4]}', 'kind': f'Double transit on the {ordinal(h)}', 'from': a, 'to': b,
                         'link': HOUSE_TOPIC[h]})
    ss = (chart.get('doshas') or {}).get('sade_sati') or {}
    by_phase = {}
    for i in ss.get('intervals', []) if isinstance(ss, dict) else []:
        if i.get('end', '') <= now or i.get('start', '') >= end: continue
        by_phase.setdefault(i['phase'], []).append((i['start'], i['end']))
    for ph, sp in by_phase.items():
        tag = re.sub(r'[^a-z]+', '', ph.split('-')[-1].split('(')[0].lower()) or 'phase'
        for a, b in _merge(sp):
            rows.append({'id': f'SS-{tag}-{a[:4]}', 'kind': f'Saturn: {ph}', 'from': a, 'to': b,
                         'link': 'a slow testing phase counted from the Moon'})
    rows.sort(key=lambda r: (r['from'], r['to']))
    return rows


def row_keys(chart, F, now, lib=None):
    """{table_key: [(row key, label)]}: the exact keys each writer fills."""
    return {
        'wealth_houses': [(str(h), f'{ordinal(h)} house: {lab}') for h, lab in WEALTH_HOUSES],
        'body_correspondences': [(str(h), f'{ordinal(h)} house: {lab}') for h, lab in HEALTH_HOUSES],
        'summary_10y': [(r['id'], f"{r['kind']}, {month(r['from'])} to {month(r['to'])}: {r['link']}") for r in summary_periods(chart, F, now)],
        'remedies': [(g, f"{g}: {_remedy_why(F[g], g, chart)}") for g in remedy_planets(F, lib)],
    }


def rows_prompt(table_key, keys):
    """The 'Table rows to fill' text for one table (used by report_input.py)."""
    ex = ', '.join(f'"{k}": "..."' for k, _ in keys)
    lines = [f'## Table rows to fill: {table_key}\n',
             f'Code builds the "{TITLES[table_key]}" table from the chart; you write only its last column, one line per row: '
             f'{ROW_HINT[table_key]}. Up to 20 words each, plain words, no dates, same guardrails as the visible text. '
             'Put this hidden block at the end of your section, just before the trace block, as valid JSON on one line '
             '(double quotes, no trailing comma):\n',
             f'`<!-- rows:{table_key} {{{ex}}} -->`\n', 'Row keys:']
    lines += [f'- `{k}`: {lab}' for k, lab in keys]
    return '\n'.join(lines) + '\n'


# ---------- tables ----------
def build(chart, F, now, lib, sections_md):
    sections_md = sections_md or {}
    rows = {}
    for sec, md in sections_md.items():
        for k, v in parse_rows(md).items():
            rows.setdefault(k, {}).update(v)
    out = {}

    def model(tk, key):
        return _safe((rows.get(tk) or {}).get(_norm_key(key)))

    try:
        r = []
        for h, lab in WEALTH_HOUSES:
            c = _house_cond(chart, h)
            if c: r.append([ordinal(h), lab, c[0], c[1], model('wealth_houses', h)])
        if r:
            out['wealth_houses'] = {'title': TITLES['wealth_houses'],
                                    'html': table(['House', 'Matters', 'Sign and lord', 'Planets there', 'What it says'], r)}
    except Exception:
        pass
    try:
        L = chart['lagna']['sign_num'] - 1
        r = []
        for h, lab in HEALTH_HOUSES:
            c = _house_cond(chart, h)
            if not c: continue
            s = (L + h - 1) % 12
            r.append([ordinal(h), lab, SIGN_TITLE[s], KALAPURUSHA[h], KALAPURUSHA[s + 1], c[1], model('body_correspondences', h)])
        if r:
            out['body_correspondences'] = {
                'title': TITLES['body_correspondences'],
                'html': table(['House', 'Matters', 'Sign', 'Body area (by house)', 'Body area (by sign)', 'Planets there', 'Care note'], r),
                'note': 'Traditional kalapurusha correspondences (houses and signs from head to feet), general regions only. '
                        'This is traditional astrology, not medical advice; health decisions stay with you and your doctor.'}
    except Exception:
        pass
    try:
        sp = summary_periods(chart, F, now)
        if sp:
            out['summary_10y'] = {'title': TITLES['summary_10y'],
                                  'html': table(['From', 'To', 'Period or window', 'Chart link', 'What it is about'],
                                                [[month(x['from']), month(x['to']), x['kind'], x['link'], model('summary_10y', x['id'])] for x in sp]),
                                  'note': 'In date order. Sub-periods are Vimshottari; a double transit is Jupiter and Saturn both '
                                          'acting on a house from the lagna; Saturn phases are counted from the Moon.'}
    except Exception:
        pass
    try:
        gs = remedy_planets(F, lib)
        if gs:
            out['remedies'] = {'title': TITLES['remedies'],
                               'html': table(['Planet', 'Why it is suggested', 'Traditional day', 'Practice', 'Status'],
                                             [[g, _remedy_why(F[g], g, chart), REMEDY_DAY[g], model('remedies', g), 'Optional'] for g in gs]),
                               'note': 'All remedies are optional traditional practices. No gemstone is needed.'}
    except Exception:
        pass
    return out


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument('--chart', required=True); ap.add_argument('--sections')
    a = ap.parse_args()
    ch = json.load(open(a.chart, encoding='utf-8'))
    tk = next((k for k in ch if k.startswith('transits_')), None)
    nw = tk[len('transits_'):].replace('_', '-')
    lb = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'library.json'), encoding='utf-8'))
    sm = {}
    if a.sections:
        for fn in os.listdir(a.sections):
            if fn.endswith('.md'): sm[fn[:-3]] = open(os.path.join(a.sections, fn), encoding='utf-8').read()
    for k, v in build(ch, DF.planet_facts(ch), nw, lb, sm).items():
        print(k, '|', v['title'], '|', v['html'].count('<tr>') - 1, 'rows')
