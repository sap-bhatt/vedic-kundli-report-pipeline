"""Build the dasha (timeline) input for one chart: every Vimshottari period that matters, the facts about each period
lord, the matching dasha library entries, and which of their conditions hold in this chart.

  python -I tools/dasha_facts.py --chart chart_data.json --out dasha_input.json [--years 10]

--chart is a chart_data.json from tools/chart_data.py (needs lagna, planets with vargas, vimshottari, panchang_at_birth).
Condition expressions use the vocabulary in docs/LIBRARY.md ("Condition vocabulary"). The code decides which conditions hold;
`manual:` conditions are passed through for the model to judge and are never marked as holding.
"""
import argparse, json, os, re, sys, datetime as D
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from lookup import select as placement_select

SIGNS = ['aries', 'taurus', 'gemini', 'cancer', 'leo', 'virgo', 'libra', 'scorpio', 'sagittarius', 'capricorn', 'aquarius', 'pisces']
SIGN_LORD = ['Mars', 'Venus', 'Mercury', 'Moon', 'Sun', 'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn', 'Saturn', 'Jupiter']
ORDER = ['Ketu', 'Venus', 'Sun', 'Moon', 'Mars', 'Rahu', 'Jupiter', 'Saturn', 'Mercury']
YEARS = {'Ketu': 7, 'Venus': 20, 'Sun': 6, 'Moon': 10, 'Mars': 7, 'Rahu': 18, 'Jupiter': 16, 'Saturn': 19, 'Mercury': 17}
EXALT_SIGN = {'Sun': 0, 'Moon': 1, 'Mars': 9, 'Mercury': 5, 'Jupiter': 3, 'Venus': 11, 'Saturn': 6, 'Rahu': 1, 'Ketu': 7}
ASP = {'Mars': [4, 7, 8], 'Jupiter': [5, 7, 9], 'Saturn': [3, 7, 10], 'Rahu': [5, 7, 9], 'Ketu': [5, 7, 9]}
BENEFIC = {'Jupiter', 'Venus', 'Mercury', 'Moon'}
MALEFIC = {'Sun', 'Mars', 'Saturn', 'Rahu', 'Ketu'}
NAK_LORD = {n: ORDER[i % 9] for i, n in enumerate(['Ashwini', 'Bharani', 'Krittika', 'Rohini', 'Mrigashira', 'Ardra', 'Punarvasu', 'Pushya',
            'Ashlesha', 'Magha', 'Purva Phalguni', 'Uttara Phalguni', 'Hasta', 'Chitra', 'Swati', 'Vishakha', 'Anuradha', 'Jyeshtha', 'Mula',
            'Purva Ashadha', 'Uttara Ashadha', 'Shravana', 'Dhanishta', 'Shatabhisha', 'Purva Bhadrapada', 'Uttara Bhadrapada', 'Revati'])}
SETS = {'KENDRA': [1, 4, 7, 10], 'TRIKONA': [1, 5, 9], 'DUSTHANA': [6, 8, 12], 'UPACHAYA': [3, 6, 10, 11], 'MARAKA_HOUSES': [2, 7]}
COMPACT = ['id', 'summary', 'common_outcomes', 'rare_outcomes', 'by_area', 'strengtheners', 'weakeners_or_cancellations',
           'phases', 'disagreements', 'confidence', 'quality', 'phrasing_guidance']


def planet_facts(chart):
    L = chart['lagna']['sign_num'] - 1
    P = {p['name']: p for p in chart['planets'] if p['name'] in YEARS}
    moon = P['Moon']['sign_num'] - 1
    waxing = str(chart.get('panchang_at_birth', {}).get('paksha', '')).lower().startswith('shukla')
    # natural benefics for this chart: Jupiter and Venus always; Mercury unless it joins a malefic; Moon when waxing
    hard = {'Sun', 'Mars', 'Saturn', 'Rahu', 'Ketu'}
    merc_afflicted = any(q in hard and P[q]['sign_num'] == P['Mercury']['sign_num'] for q in P)
    _d = abs(P['Moon']['lon'] - P['Sun']['lon']) % 360; _d = min(_d, 360 - _d)
    moon_strong = _d >= 90  # Parashara: Moon benefic from Shukla Ashtami to Krishna Ashtami (90+ deg from the Sun)
    ben = {'Jupiter', 'Venus'} | ({'Mercury'} if not merc_afflicted else set()) | ({'Moon'} if moon_strong else set())
    mal = set(P) - ben
    # Jaimini chara karakas, 7-karaka scheme (Sun..Saturn by degree within sign, highest first)
    names7 = ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn']
    kar = ['Atmakaraka', 'Amatyakaraka', 'Bhratrikaraka', 'Matrikaraka', 'Putrakaraka', 'Gnatikaraka', 'Darakaraka']
    karaka = {g: kar[i] for i, g in enumerate(sorted(names7, key=lambda g: -(P[g]['lon'] % 30)))}
    rules = {g: [] for g in YEARS}
    for h in range(1, 13):
        rules[SIGN_LORD[(L + h - 1) % 12]].append(h)
    out = {}
    for g, p in P.items():
        s = p['sign_num'] - 1
        d9 = SIGNS.index(p['vargas']['D9'].lower())
        ex = EXALT_SIGN[g]
        d9dig = 'exalted' if d9 == ex else 'debilitated' if d9 == (ex + 6) % 12 else 'own' if SIGN_LORD[d9] == g and g not in ('Rahu', 'Ketu') else 'other'
        r = rules[g]; role = []
        if 1 in r: role.append('lagna_lord')
        if any(h in (4, 7, 10) for h in r) and any(h in (5, 9) for h in r): role.append('yogakaraka')
        if any(h in (5, 9) for h in r): role.append('trikona_lord')
        if any(h in (4, 7, 10) for h in r): role.append('kendra_lord')
        if any(h in (6, 8, 12) for h in r): role.append('dusthana_lord')
        if any(h in (3, 6, 11) for h in r): role.append('trishadaya_lord')
        if any(h in (2, 7) for h in r): role.append('maraka')
        if 8 in r: role.append('eighth_lord')
        withp = [q for q, pq in P.items() if q != g and pq['sign_num'] == p['sign_num']]
        asp = [q for q, pq in P.items() if q != g and ((s - (pq['sign_num'] - 1)) % 12 + 1) in ASP.get(q, [7])]
        out[g] = {'house': (s - L) % 12 + 1, 'house_from_moon': (s - moon) % 12 + 1, 'sign': SIGNS[s], 'sign_lord': SIGN_LORD[s],
                  'nak_lord': p.get('nak_lord'), 'nakshatra': p.get('nakshatra'), 'dignity': p.get('dignity'),
                  'combust': bool(p.get('combust')), 'retro': bool(p.get('retro')) if g not in ('Rahu', 'Ketu') else False,
                  'vargottama': d9 == s, 'd9_sign': SIGNS[d9], 'd9_dignity': d9dig, 'rules': r, 'role': role,
                  'with': withp, 'aspected_by': asp,
                  'with_benefic': any(q in ben for q in withp), 'with_malefic': any(q in mal for q in withp),
                  'aspected_by_benefic': any(q in ben for q in asp), 'aspected_by_malefic': any(q in mal for q in asp),
                  'in_benefic_sign': SIGN_LORD[s] in BENEFIC, 'karaka': karaka.get(g), 'natural': 'benefic' if g in ben else 'malefic',
                  '_sign_num': s}
    return out


def add_years(date_str, years):
    return (D.date.fromisoformat(date_str) + D.timedelta(days=years * 365.25)).isoformat()


def antardashas(md, start):
    """Fallback only (date-level arithmetic, can be a day off): chart_data.py exports exact sub-periods."""
    i = ORDER.index(md); t = start; out = []
    for k in range(9):
        ad = ORDER[(i + k) % 9]
        dur = YEARS[md] * YEARS[ad] / 120
        end = (D.date.fromisoformat(t) + D.timedelta(days=dur * 365.25)).isoformat()
        out.append({'ad': ad, 'start': t, 'end': end}); t = end
    return out


def env_for(F, md, ad=None, moon_waxing=None):
    env = dict(SETS); env['md'] = md; env['moon_waxing'] = moon_waxing
    for pre, g in (('md', md), ('ad', ad)):
        if not g: continue
        for k, v in F[g].items():
            if not k.startswith('_'): env[f'{pre}_{k}'] = v
    if ad:
        env['ad'] = ad
        env['ad_from_md'] = (F[ad]['_sign_num'] - F[md]['_sign_num']) % 12 + 1
    return env


def evaluate(when, env):
    w = (when or '').strip()
    if not w or w.lower().startswith('manual'):
        return 'manual'
    try:
        return 'holds' if eval(w, {'__builtins__': {}}, env) else 'does_not_hold'
    except NameError as e:
        name = str(e).split("'")[1] if "'" in str(e) else ''
        if (name == 'ad' or name.startswith('ad_')) and 'ad' not in env:
            return 'not_applicable'  # a sub-period rule checked at mahadasha level
        if name in env.get('_unknown', ()):
            return 'not_checkable'  # fact not known for this date (e.g. other planets' transits in future)
        return f'error: NameError: {e}'
    except Exception as e:
        return f'error: {type(e).__name__}: {e}'


def split_top(expr, word):
    """Split an expression on a top-level boolean word (' or ' / ' and '), ignoring brackets."""
    parts, depth, cur, i = [], 0, '', 0
    w = f' {word} '
    while i < len(expr):
        ch = expr[i]
        if ch in '([': depth += 1
        elif ch in ')]': depth -= 1
        if depth == 0 and expr[i:i + len(w)] == w:
            parts.append(cur); cur = ''; i += len(w); continue
        cur += ch; i += 1
    parts.append(cur)
    return [x.strip() for x in parts if x.strip()]


def because(when, env):
    """For a condition that holds, the top-level 'or' parts that are true (so the model credits the right fact)."""
    parts = split_top(when or '', 'or')
    if len(parts) < 2: return None
    true = [x for x in parts if evaluate(x, env) == 'holds']
    return true or None


def compact_entry(e, env):
    if not e: return None
    body = {k: e.get(k) for k in COMPACT if e.get(k) not in (None, '', [], {})}
    body['sources'] = [s.get('source', '') for s in e.get('source_views', [])]
    conds = []
    for c in e.get('conditional_results', []) or []:
        st = evaluate(c.get('when'), env)
        conds.append({'status': st, 'when': c.get('when'), 'polarity': c.get('polarity'),
                      'effects': c.get('effects'), 'source': c.get('source'),
                      'true_parts': because(c.get('when'), env) if st == 'holds' else None})
    if conds: body['conditions'] = conds
    if e.get('remedies'): body['remedies'] = e['remedies']
    return body


def principle_hits(principles, env):
    hits = []
    for e in principles:
        for c in e.get('conditional_results', []) or []:
            if 'ad' in env and not re.search(r'\bad(_|\b)', c.get('when') or ''):
                continue  # mahadasha-only rule: already listed once under the mahadasha
            st = evaluate(c.get('when'), env)
            if st == 'holds' or st.startswith('error'):
                hits.append({'rule': e['id'], 'status': st, 'when': c.get('when'), 'polarity': c.get('polarity'),
                             'effects': c.get('effects'), 'source': c.get('source'),
                             'true_parts': because(c.get('when'), env) if st == 'holds' else None})
    return hits


def tally(entry, hits):
    conds = (entry or {}).get('conditions', []) + (hits or [])
    t = {'good': 0, 'bad': 0, 'mixed': 0, 'to_judge': 0}
    for c in conds:
        if c['status'] == 'holds':
            t[c.get('polarity') if c.get('polarity') in ('good', 'bad', 'mixed') else 'mixed'] += 1
        elif c['status'] == 'manual':
            t['to_judge'] += 1
    return t


def lord_summary(F, g):
    f = F[g]
    return {'planet': g, 'house': f['house'], 'sign': f['sign'].title(), 'dignity': f['dignity'], 'rules_houses': f['rules'],
            'role': f['role'], 'with': f['with'], 'aspected_by': f['aspected_by'], 'nakshatra_lord': f['nak_lord'],
            'sign_lord': f['sign_lord'], 'house_from_moon': f['house_from_moon'], 'vargottama': f['vargottama'],
            'd9_dignity': f['d9_dignity'], 'retro': f['retro'], 'combust': f['combust'], 'karaka': f['karaka'], 'natural': f['natural'], 'in_yogas': f.get('in_yogas', [])}


MT_SIGN = {'Sun': 4, 'Moon': 1, 'Mars': 0, 'Mercury': 5, 'Jupiter': 8, 'Venus': 6, 'Saturn': 10}
SADE_SLUG = {'rising': 'rising', 'peak': 'peak', 'setting': 'setting', 'kantaka': 'kantaka_dhaiya', 'ashtama': 'ashtama_dhaiya'}
YOGINI_SLUG = {'Mangala': 'mangala', 'Pingala': 'pingala', 'Dhanya': 'dhanya', 'Bhramari': 'bhramari', 'Bhadrika': 'bhadrika',
               'Ulka': 'ulka', 'Siddha': 'siddha', 'Sankata': 'sankata'}


def sign_dignity(g, s):
    ex = EXALT_SIGN[g]
    if s == ex: return 'exalted'
    if s == (ex + 6) % 12: return 'debilitated'
    if MT_SIGN.get(g) == s: return 'moolatrikona'
    if SIGN_LORD[s] == g and g not in ('Rahu', 'Ketu'): return 'own'
    return 'other'


def dasha_at(chart, date):
    for md, ads in chart['vimshottari'].get('antardashas_by_md', {}).items():
        for a in ads:
            if a['start'] <= date < a['end']:
                return md, a['ad']
    for m in chart['vimshottari']['mahadashas']:
        if m['start'] <= date < m['end']:
            return m['md'], None
    return None, None


def timing_env(F, chart, planet, sign, date, waxing, vedha=None):
    md, ad = dasha_at(chart, date)
    env = env_for(F, md, ad, waxing) if md else dict(SETS)
    L = chart['lagna']['sign_num'] - 1; moon = F['Moon']['_sign_num']
    env.update({'tr_planet': planet, 'tr_sign': SIGNS[sign], 'tr_house_from_moon': (sign - moon) % 12 + 1,
                'tr_house_from_lagna': (sign - L) % 12 + 1, 'tr_dignity': sign_dignity(planet, sign),
                'tr_role': F[planet]['role'], 'tr_rules': F[planet]['rules'], 'tr_natal_dignity': F[planet]['dignity'],
                'tr_natal_house': F[planet]['house'], 'moon_dignity': F['Moon']['dignity'], 'moon_house': F['Moon']['house'],
                'moon_waxing': waxing})
    if vedha is not None:
        env['tr_vedha_houses'] = vedha
    else:
        env['_unknown'] = ('tr_vedha_houses',)
    return env, md, ad


def _segments(chart, planet, key, now, tr):
    segs = [(now, SIGNS.index(tr[planet]['sign'].lower()))] + [(d, SIGNS.index(sg.lower())) for d, sg, _ in chart.get(key) or []]
    last = max(d for d, _ in segs)
    out = []
    for i, (start, sg) in enumerate(segs):
        end = segs[i + 1][0] if i + 1 < len(segs) else add_years(last, 1.0)
        out.append((start, end, sg))
    return out


def computed_windows(F, chart, now):
    """Double transit (Jupiter and Saturn both occupying or aspecting a house from the lagna) and Saturn over natal planets."""
    tr_key = next((k for k in chart if k.startswith('transits_')), None); tr = chart.get(tr_key) or {}
    L = chart['lagna']['sign_num'] - 1
    J = _segments(chart, 'Jupiter', 'jupiter_ingresses_next_6y', now, tr)
    S = _segments(chart, 'Saturn', 'saturn_ingresses_next_6y', now, tr)
    data_end = min(J[-1][1], S[-1][1])

    def touch(planet, sign, house_sign):
        d = (house_sign - sign) % 12 + 1
        return 'occupies' if d == 1 else 'aspects' if d in ASP[planet] or d == 7 else None

    raw = []
    for js, je, jsg in J:
        for ss, se, ssg in S:
            a, b = max(js, ss), min(je, se, data_end)
            if a >= b: continue
            for h in range(1, 13):
                hs = (L + h - 1) % 12
                tj, ts = touch('Jupiter', jsg, hs), touch('Saturn', ssg, hs)
                if tj and ts:
                    raw.append({'house': h, 'from': a, 'to': b, 'jupiter': (f'in it ({SIGNS[jsg].title()})' if tj == 'occupies' else f'aspects it from {SIGNS[jsg].title()}'),
                                'saturn': (f'in it ({SIGNS[ssg].title()})' if ts == 'occupies' else f'aspects it from {SIGNS[ssg].title()}')})
    raw.sort(key=lambda x: (x['house'], x['from']))
    merged = []
    for x in raw:  # join touching intervals for the same house
        if merged and merged[-1]['house'] == x['house'] and merged[-1]['to'] >= x['from']:
            merged[-1]['to'] = max(merged[-1]['to'], x['to'])
            for k in ('jupiter', 'saturn'):
                if x[k] not in merged[-1][k]: merged[-1][k] += ' / ' + x[k]
        else:
            merged.append(dict(x))
    over = []
    for ss, se, ssg in S:
        for g, f in F.items():
            if f['_sign_num'] == ssg:
                over.append({'planet': g, 'natal_house': f['house'], 'from': ss, 'to': min(se, data_end), 'saturn_in': SIGNS[ssg].title()})
    return {'double_transit': merged, 'saturn_over_natal': over, 'data_until': data_end,
            'method': 'A house is double-transited while Jupiter and Saturn each occupy it or aspect it (Jupiter 5/7/9, Saturn 3/7/10), '
                      'counted from the lagna; see dasha_principle/transits_during_dasha.'}


def timing_layers(F, chart, lib, now, horizon, waxing):
    birth = chart['birth']['date']; moon = F['Moon']['_sign_num']
    tr_key = next((k for k in chart if k.startswith('transits_')), None); tr = chart.get(tr_key) or {}
    out = {'transits': [], 'sade_sati': [], 'yogini': [], 'windows': computed_windows(F, chart, now)}
    for planet, key in (('Saturn', 'saturn_ingresses_next_6y'), ('Jupiter', 'jupiter_ingresses_next_6y')):
        segs = [(now, SIGNS.index(tr[planet]['sign'].lower()))] + [(d, SIGNS.index(sg.lower())) for d, sg, _ in chart.get(key) or []]
        for i, (start, sg) in enumerate(segs):
            end = segs[i + 1][0] if i + 1 < len(segs) else None
            vedha = None
            if i == 0:
                vedha = sorted({v['house_from_moon'] for k, v in tr.items() if k not in (planet, 'Moon')})
            env, md, ad = timing_env(F, chart, planet, sg, start, waxing, vedha)
            eid = f"transit/{planet.lower()}/{env['tr_house_from_moon']}"
            out['transits'].append({'planet': planet, 'sign': SIGNS[sg].title(), 'from': start, 'to': end or '(beyond data)',
                                    'house_from_moon': env['tr_house_from_moon'], 'house_from_lagna': env['tr_house_from_lagna'],
                                    'transit_dignity': env['tr_dignity'], 'running_dasha': f'{md}-{ad}' if ad else md,
                                    'library_entry': compact_entry(lib.get(eid), env), 'id': eid})
    groups = []
    for iv in chart.get('doshas', {}).get('sade_sati', {}).get('intervals', []):
        if iv['end'] < birth or iv['start'] > horizon: continue
        if groups and groups[-1]['phase'] == iv['phase'] and groups[-1]['saturn_in'] == iv['saturn_in']:
            groups[-1]['end'] = iv['end']; groups[-1]['spans'] += 1; groups[-1]['current'] |= bool(iv.get('current'))
        else:
            groups.append({**iv, 'spans': 1, 'current': bool(iv.get('current'))})
    for gph in groups:
        slug = next((v for k, v in SADE_SLUG.items() if k in gph['phase'].lower()), None)
        sg = SIGNS.index(gph['saturn_in'].lower())
        env, md, ad = timing_env(F, chart, 'Saturn', sg, max(gph['start'], birth), waxing)
        status = 'past' if gph['end'] <= now else 'current' if gph['start'] <= now < gph['end'] or gph['current'] else 'future'
        out['sade_sati'].append({'phase': gph['phase'], 'saturn_in': gph['saturn_in'], 'from': gph['start'], 'to': gph['end'],
                                 'status': status, 'note': 'Saturn moves back and forth across the sign boundary' if gph['spans'] > 1 else '',
                                 'running_dasha_at_start': f'{md}-{ad}' if ad else md, 'id': f'sade_sati/{slug}',
                                 'library_entry': compact_entry(lib.get(f'sade_sati/{slug}'), env)})
    for y in chart.get('yogini_current_and_next') or []:
        g = y['planet']; md, ad = dasha_at(chart, max(y['start'], now))
        env = env_for(F, md, ad, waxing) if md else dict(SETS)
        for k, v in F[g].items():
            if not k.startswith('_'): env[f'yl_{k}'] = v
        slug = YOGINI_SLUG.get(y['yogini'], y['yogini'].lower())
        out['yogini'].append({'yogini': y['yogini'], 'planet': g, 'from': y['start'], 'to': y['end'], 'current': y.get('current'),
                              'planet_facts': lord_summary(F, g), 'id': f'yogini/{slug}',
                              'library_entry': compact_entry(lib.get(f'yogini/{slug}'), env)})
    return out


YOGA_MAP = {'Raja (kendra-trikona lords)': 'raja_kendra_trikona', 'Yogakaraka present': 'yogakaraka',
            'Dhana (1/2/5/9/11 lords)': 'dhana', 'Viparita Raja (Harsha)': 'viparita_harsha',
            'Viparita Raja (Sarala)': 'viparita_sarala', 'Viparita Raja (Vimala)': 'viparita_vimala',
            'Shubha Kartari (lagna)': 'shubha_kartari', 'Papa Kartari (lagna)': 'papa_kartari',
            'Dharma-Karmadhipati': 'dharma_karmadhipati', 'Chandra-Mangala': 'chandra_mangala', 'Guru-Chandal': None}


def yoga_slug(name):
    if name in YOGA_MAP: return YOGA_MAP[name]
    if name.startswith('Neecha Bhanga'): return 'neecha_bhanga'
    return name.lower().replace('-', '_').replace(' ', '_')


def yoga_brief(lib, name):
    slug = yoga_slug(name)
    e = lib.get(f'yoga/{slug}') if slug else None
    if not e: return None
    return {'id': e['id'], 'summary': e.get('summary'), 'rarity_and_weight': e.get('rarity_and_weight'),
            'timing': e.get('timing'), 'confidence': e.get('confidence'), 'quality': e.get('quality'),
            'phrasing_guidance': e.get('phrasing_guidance')}


def build(chart, lib, now, years):
    F = planet_facts(chart)
    for g in F:  # yogas (calculator) in which this planet takes part
        F[g]['in_yogas'] = [y['name'] for y in chart.get('yogas_present', []) if f'"{g}"' in json.dumps(y.get('conditions'))]
    waxing = str(chart.get('panchang_at_birth', {}).get('paksha', '')).lower().startswith('shukla')
    principles = [e for k, e in lib.items() if k.startswith('dasha_principle/')]
    birth = chart['birth']['date']; horizon = add_years(now, years)
    def age(d):  # completed years at date d (YYYY-MM-DD)
        a = int(d[:4]) - int(birth[:4]) - (1 if d[5:10] < birth[5:10] else 0)
        return max(0, a)
    mds = chart['vimshottari']['mahadashas']
    out_mds = []
    for m in mds:
        md = m['md']
        if m['start'] > horizon:  # beyond the horizon: table row only (dates, lord facts), no entries
            out_mds.append({'md': md, 'start': m['start'], 'end': m['end'], 'status': 'future_beyond_horizon',
                            'age': f"{age(m['start'])}-{age(m['end'])}", 'lord': lord_summary(F, md)})
            continue
        env = env_for(F, md, moon_waxing=waxing)
        status = 'past' if m['end'] <= now else 'current' if m['start'] <= now < m['end'] else 'future'
        item = {'md': md, 'start': max(m['start'], birth), 'end': m['end'], 'status': status,
                'age': f"{age(max(m['start'], birth))}-{age(m['end'])}", 'lord': lord_summary(F, md),
                'library_entry': compact_entry(lib.get(f'dasha_md/{md.lower()}'), env),
                'principles_that_apply': principle_hits(principles, env)}
        item['tally'] = tally(item['library_entry'], item['principles_that_apply'])
        if item['library_entry'] is None: item['library_entry_missing'] = f'dasha_md/{md.lower()}'
        if status in ('current', 'future') or m['end'] > now:
            ads = []
            exact = chart['vimshottari'].get('antardashas_by_md', {}).get(md)
            for a in exact or antardashas(md, m['start']):
                # the current mahadasha is covered in full (past sub-periods as checks); later ones up to the horizon
                if status != 'current' and (a['end'] <= now or a['start'] > horizon): continue
                envA = env_for(F, md, a['ad'], waxing)
                x = {'ad': a['ad'], 'start': a['start'], 'end': a['end'], 'current': a['start'] <= now < a['end'],
                     'past': a['end'] <= now,
                     'ad_lord': lord_summary(F, a['ad']), 'ad_house_from_md_lord': envA['ad_from_md'],
                     'library_entry': compact_entry(lib.get(f"dasha_ad/{md.lower()}/{a['ad'].lower()}"), envA),
                     'principles_that_apply': principle_hits(principles, envA)}
                x['tally'] = tally(x['library_entry'], x['principles_that_apply'])
                if x['library_entry'] is None: x['library_entry_missing'] = f"dasha_ad/{md.lower()}/{a['ad'].lower()}"
                ads.append(x)
            item['antardashas_from_now'] = ads
        out_mds.append(item)
    tr_key = next((k for k in chart if k.startswith('transits_')), None)
    timing_facts = {'note': 'Computed facts only. No library layer for transits, Sade Sati, Yogini or Chara yet: '
                            'state dates and positions, do not interpret beyond the principles provided.',
                    'transits': chart.get(tr_key), 'transit_date': tr_key[len('transits_'):].replace('_', '-') if tr_key else None,
                    'jupiter_sign_changes': chart.get('jupiter_ingresses_next_6y'), 'saturn_sign_changes': chart.get('saturn_ingresses_next_6y'),
                    'sade_sati_and_dhaiya': chart.get('doshas', {}).get('sade_sati'),
                    'yogini': chart.get('yogini_current_and_next'), 'chara': chart.get('chara_current_and_next')}
    errors = sorted({c['when'] + ' -> ' + c['status'] for m in out_mds for blk in [m] + m.get('antardashas_from_now', [])
                     for c in (blk.get('library_entry') or {}).get('conditions', []) + blk.get('principles_that_apply', [])
                     if c['status'].startswith('error')})
    timing = timing_layers(F, chart, lib, now, horizon, waxing)
    karakas = {}
    for g in F:
        role = (F[g].get('karaka') or '').lower()
        e = lib.get(f'karaka/{role}') if role else None
        if e:
            sig = e.get('significations')
            karakas[g] = {'id': e['id'], 'role': F[g]['karaka'], 'summary': e.get('summary'),
                          'significations': sig if isinstance(sig, str) else '; '.join(sig or [])[:300]}
    ak = next((g for g in F if F[g].get('karaka') == 'Atmakaraka'), None)
    if ak:
        e = lib.get(f"karaka/karakamsha_{F[ak]['d9_sign']}")
        if e: karakas['_karakamsha'] = {'id': e['id'], 'role': f"Karakamsha {F[ak]['d9_sign'].title()}", 'summary': e.get('summary')}
    errors += sorted({c['when'] + ' -> ' + c['status'] for blk in timing['transits'] + timing['sade_sati'] + timing['yogini']
                      for c in (blk.get('library_entry') or {}).get('conditions', []) if c['status'].startswith('error')})
    return {'as_of': now, 'horizon': horizon, 'timing': timing, 'karakas': karakas,
            'chart': {'lagna': chart['lagna']['sign'], 'lagna_degree': chart['lagna']['deg_in_sign'], 'lagna_nakshatra': chart['lagna']['nakshatra'],
                      'moon_sign': next(p['sign'] for p in chart['planets'] if p['name'] == 'Moon'),
                      'moon_nakshatra': next(p['nakshatra'] for p in chart['planets'] if p['name'] == 'Moon'),
                      'moon_waxing': waxing, 'dasha_balance_at_birth': chart['vimshottari']['balance_at_birth'],
                      'lagna_nakshatra_lord': chart['lagna'].get('nak_lord') or NAK_LORD.get(chart['lagna']['nakshatra'])},
            'yogas_present': [{'name': y['name'], 'conditions': y.get('conditions'), 'library': yoga_brief(lib, y['name'])}
                              for y in chart.get('yogas_present', [])],
            'planet_facts': {g: lord_summary(F, g) for g in F},
            'principles': [compact_entry(e, {}) | {'conditions': None} for e in principles],
            'mahadashas': out_mds, 'timing_facts': timing_facts,
            'placement_entries': placement_select(chart, lib, compact=True)['entries'],
            'condition_errors': errors}


def _lst(xs, cap=None):
    xs = [x for x in (xs or []) if x]
    return '; '.join(xs[:cap] if cap else xs)


def _lord_line(l):
    bits = [f"house {l['house']}", l['sign'], l['dignity']]
    if l['rules_houses']: bits.append('rules ' + ', '.join(map(str, l['rules_houses'])))
    if l['role']: bits.append('role: ' + ', '.join(l['role']))
    if l['with']: bits.append('with ' + ', '.join(l['with']))
    if l['aspected_by']: bits.append('aspected by ' + ', '.join(l['aspected_by']))
    bits.append(f"sign lord {l['sign_lord']}, nakshatra lord {l['nakshatra_lord']}, {l['house_from_moon']} from Moon")
    for k in ('vargottama', 'retro', 'combust'):
        if l[k]: bits.append(k)
    if l['d9_dignity'] != 'other': bits.append(f"D9 {l['d9_dignity']}")
    if l.get('karaka'): bits.append(f"chara karaka: {l['karaka']}")
    if l.get('natural'): bits.append(f"natural {l['natural']} in this chart")
    if l.get('in_yogas'): bits.append('forms: ' + ', '.join(l['in_yogas']) + (' (in a Neecha Bhanga named for another planet, this planet is one of the cancelling factors, not the debilitated one)' if any('Neecha' in y and l['planet'] not in y for y in l['in_yogas']) else ''))
    return '; '.join(bits)


_SEEN = {}   # entry id -> set of fields already printed for it
_ONCE = {}   # long text already printed -> entry id where it was printed (v0.16 input diet: print once, then refer)
_RULE = {}   # (when, effects, source) of a holding condition -> entry id where it was printed in full
_SRC_TR = re.compile(r"\s*\((?:tr\.|ed\.|transl|Subodhini)[^()]*(?:\([^()]*\)[^()]*)*\)")
_SRC_DUP = re.compile(r"\b([A-Za-z]+ )(\d+) (\2\.)")
_SENT = re.compile(r"(?<=[a-z0-9\)\]'\"])\. (?=[A-Z])")
# what each tier prints from a library entry (v0.16): past periods are validation checks only; later periods drop the
# per-area detail and the disagreements; the current period (and the current stretch of each timer) gets everything
TIERS = {'past': {'summary', 'results', 'phrasing'},
         'future': {'summary', 'results', 'phases', 'judge', 'remedies', 'phrasing'},
         'current': {'summary', 'results', 'by_area', 'phases', 'judge', 'dis_full', 'remedies', 'phrasing'}}


def _src(s):
    """Source citation without translator/edition detail: 'Phaladeepika 26 (tr. V. Subrahmanya Sastri) 26.32' -> 'Phaladeepika 26.32'."""
    s = _SRC_TR.sub('', s or '')
    return _SRC_DUP.sub(r'\1\3', s).strip()


def _once(txt, eid, minlen=80):
    t = (txt or '').strip()
    if len(t) < minlen: return t
    first = _ONCE.setdefault(t, eid)
    return t if first == eid else f'same as in `{first}`'


def _first_sentences(t, cap=320, tail=''):
    """Whole sentences from the start, up to about cap characters (at least one)."""
    parts = _SENT.split((t or '').strip())
    keep = parts[0]
    for p in parts[1:]:
        if len(keep) + len(p) + 2 > cap: return keep.rstrip('.') + '.' + tail
        keep += '. ' + p
    return t.strip()


def _lord_short(l):
    """Period-lord line for sub-periods and timers: what ranks the period (full facts are under Planet facts)."""
    bits = [f"{l['planet']} in house {l['house']}", l['sign'], l['dignity']]
    if l['rules_houses']: bits.append('rules ' + ', '.join(map(str, l['rules_houses'])))
    if l['role']: bits.append('role: ' + ', '.join(l['role']))
    for k in ('retro', 'combust', 'vargottama'):
        if l[k]: bits.append(k)
    if l['d9_dignity'] != 'other': bits.append(f"D9 {l['d9_dignity']}")
    if l.get('in_yogas'): bits.append('forms: ' + ', '.join(l['in_yogas']) + (' (in a Neecha Bhanga named for another planet, this planet is one of the cancelling factors, not the debilitated one)' if any('Neecha' in y and l['planet'] not in y for y in l['in_yogas']) else ''))
    return '; '.join(bits) + ' (all facts under Planet facts)'


def _hold_line(c, eid):
    tb = '  [true because: ' + ' ; '.join(c['true_parts']) + ']' if c.get('true_parts') else ''
    key = (c['when'], _lst(c['effects']), _src(c['source']))
    if key in _RULE:  # the same rule, word for word, was printed in full earlier
        return f"- [{c['polarity']}] {c['when']}{tb} -> same result as this rule under `{_RULE[key]}` above\n"
    _RULE[key] = eid
    return f"- [{c['polarity']}] {c['when']}{tb} -> {key[1]} ({key[2]})\n"


def _remedies(e):
    rs = [_once(r.get('remedy', '') + f" ({_src(r.get('source', ''))})", e['id']) for r in e['remedies']]
    return _lst(list(dict.fromkeys(rs)))


def _entry_md(e, out, depth='####', show_manual=True, brief=False, tier=None, remedies=True):
    """tier 'past' (validation checks: summary, general results, the conditions that hold, phrasing), 'future' (adds
    phases, conditions to judge, remedies) or 'current' (everything, with the by-area detail and the disagreements).
    brief=True is the old name for tier 'past'. Each field of an entry is printed once; a later stretch under the same
    entry lists only the conditions that hold for it (and any field its tier adds)."""
    if not e:
        out.append('_No library entry for this period: use only the placement entries and principles._\n'); return
    tier = tier or ('past' if brief else 'current')
    eid = e['id']; done = _SEEN.setdefault(eid, set()); first_time = not done
    conds = e.get('conditions') or []
    hold = [c for c in conds if c['status'] == 'holds']; man = [c for c in conds if c['status'] == 'manual']
    has = {'summary': True, 'results': bool(e.get('common_outcomes')), 'by_area': any((e.get('by_area') or {}).values()),
           'phases': bool(e.get('phases')), 'judge': bool(man) and show_manual and first_time,
           'dis_full': bool(e.get('disagreements')) and e['disagreements'] != 'None.',
           'remedies': bool(e.get('remedies')) and remedies, 'phrasing': bool(e.get('phrasing_guidance'))}
    want = {f for f in TIERS[tier] - done if has[f]}
    if not first_time and not want:  # printed earlier; repeat only what holds for this stretch
        out.append(f"Same entry as above (`{eid}`). Conditions that HOLD for this stretch: "
                   + ('; '.join(f"[{c['polarity']}] {c['when']}" for c in hold) if hold else 'none') + '\n\n')
        return
    done |= want | {'header'}
    if first_time:
        out.append(f"{depth} Library entry `{eid}` ({e.get('confidence')}, {e.get('quality')})\n")
    else:
        out.append(f"{depth} Library entry `{eid}` (continued: its other fields are printed above, under an earlier stretch)\n")
    if 'summary' in want: out.append(f"Summary: {e.get('summary', '')}\n")
    if 'results' in want: out.append(f"General results: {_once(_lst(e['common_outcomes']), eid)}\n")
    if 'by_area' in want:
        out.append('By area: ' + ' | '.join(f'{k}: {_once(v, eid)}' for k, v in e['by_area'].items() if v) + '\n')
    if 'phases' in want: out.append(f"Phases: {_once(e['phases'], eid)}\n")
    if hold:
        out.append('Conditions that HOLD in this chart (apply them):\n')
        out += [_hold_line(c, eid) for c in hold]
    skipped = len(conds) - len(hold) - len(man)
    if 'judge' in want:
        out.append('Conditions to JUDGE (code could not check; use only facts given, else leave out):\n')
        out += [f"- [{c['polarity']}] {c['when']} -> {_lst(c['effects'])} ({_src(c['source'])})\n" for c in man]
    elif man:
        out.append(f"({len(man)} further conditions need judgement the input cannot support; leave them out.)\n")
    if skipped: out.append(f"({skipped} other conditions do not hold for this chart and are omitted.)\n")
    if 'dis_full' in want: out.append(f"Disagreements: {_once(e['disagreements'], eid)}\n")
    if 'remedies' in want: out.append('Remedies (optional): ' + _remedies(e) + '\n')
    if 'phrasing' in want: out.append(f"Tone guide for you (follow it, never copy its words): {_once(e['phrasing_guidance'], eid)}\n")
    out.append('\n')

def _flat(v):
    """Calculator facts as a short line instead of a JSON dump."""
    if isinstance(v, dict):
        return '; '.join(f'{k}: ' + ('none' if x in (None, [], {}) else f'({_flat(x)})' if isinstance(x, dict) else _flat(x))
                         for k, x in v.items())
    if isinstance(v, list):
        if not v: return 'none'
        return ' | '.join(f'({_flat(x)})' for x in v) if any(isinstance(x, dict) for x in v) else ', '.join(_flat(x) for x in v)
    if v is True: return 'yes'
    if v is False: return 'no'
    if v is None: return 'none'
    return str(v)


def to_markdown(res):
    _SEEN.clear(); _ONCE.clear(); _RULE.clear(); now = res['as_of']
    # principle rules that hold somewhere: printed once under their principle, referenced by code in each period
    pcode, plegend = {}, {}
    blocks = [b for m in res['mahadashas'] for b in [m] + m.get('antardashas_from_now', [])]
    order = {p['id']: i for i, p in enumerate(res['principles'])}
    hits = sorted({(h['rule'], h['when'], h['polarity'], _lst(h['effects']), _src(h['source']))
                   for b in blocks for h in b.get('principles_that_apply', [])}, key=lambda k: (order.get(k[0], 99), k[1]))
    for i, k in enumerate(hits, 1):
        pcode[k] = f'P{i}'; plegend.setdefault(k[0], []).append(k)

    def refs(b, label):
        hs = b.get('principles_that_apply') or []
        if not hs: return ''
        return (f'{label} (rule codes under Dasha principles): '
                + '; '.join(f"{pcode[k]} [{k[2]}] {k[3]}" for k in dict.fromkeys(
                    (h['rule'], h['when'], h['polarity'], _lst(h['effects']), _src(h['source'])) for h in hs)) + '\n\n')

    c = res['chart']; out = [f"# Dasha input (as of {res['as_of']}, horizon {res['horizon']})\n\n",
                             f"Lagna {c['lagna']} {c['lagna_degree']} ({c['lagna_nakshatra']}); Moon {c['moon_sign']} in {c['moon_nakshatra']}, "
                             f"{'waxing' if c['moon_waxing'] else 'waning'}; dasha balance at birth: {c['dasha_balance_at_birth']}; "
                             f"lagna nakshatra lord: {c.get('lagna_nakshatra_lord')}\n\n"
                             "Natural benefics in this chart: Jupiter, Venus, Mercury unless it joins a malefic, the Moon when 90 deg or more from the Sun (Shukla Ashtami to Krishna Ashtami); the rest are malefics.\n\n",
                             '## Planet facts\n\n']
    out += [f"- **{g}**: {_lord_line(l)}\n" for g, l in res['planet_facts'].items()]
    if res.get('karakas'):
        out.append('\n## Chara karaka meanings (library)\n\n')
        for g, k in res['karakas'].items():
            who = '' if g.startswith('_') else f'{g} is the '
            out.append(f"- {who}{k['role']} (`{k['id']}`): {k.get('summary') or ''}"
                       + (f" Governs: {k['significations']}" if k.get('significations') else '') + '\n')
    if res.get('yogas_present'):
        out.append('\n## Yogas present (calculator facts; meanings only from library yoga entries when provided)\n\n')
        for y in res['yogas_present']:
            out.append(f"- **{y['name']}** (calculator): {_flat(y['conditions'])[:300]}\n")
            b = y.get('library')
            if b:
                out.append(f"  - Library `{b['id']}` ({b.get('confidence')}): {_first_sentences(b.get('summary'), 260, '')}\n")
                if b.get('rarity_and_weight'): out.append(f"  - Weight: {_first_sentences(b['rarity_and_weight'], 200, '')}\n")
                if b.get('timing'): out.append(f"  - Timing: {b['timing']}\n")
                if b.get('phrasing_guidance'): out.append(f"  - Tone guide for you (follow it, never copy its words): {b['phrasing_guidance']}\n")
            else:
                out.append('  - No library entry yet: name it as a fact only.\n')
    out.append('\n## Dasha principles (general rules; P-codes are the rules that hold in some period below)\n\n')
    for p in res['principles']:
        out.append(f"- `{p['id']}` ({p.get('confidence')}): {_first_sentences(p.get('summary'), 320, '')} How to apply: {_lst(p.get('common_outcomes'), 3)}\n")
        out += [f"  - {pcode[k]} = `{p['id']}` [{k[2]}] {k[1]} -> {k[3]} ({k[4]})\n" for k in plegend.get(p['id'], [])]
    out.append('\n## Mahadashas\n\n')
    for m in res['mahadashas']:
        beyond = m['status'] == 'future_beyond_horizon'
        out.append(f"### {m['md']} mahadasha, {m['start']} to {m['end']} (age {m['age']}, {m['status']})\n\n"
                   f"Lord: {_lord_short(m['lord']) if beyond else _lord_line(m['lord'])}\n\n")
        if beyond:
            out.append('_Beyond the horizon: for the mahadasha table only._\n\n'); continue
        _entry_md(m.get('library_entry'), out, tier=m['status'])
        out.append(refs(m, 'Principles whose conditions hold for this period'))
        for a in m.get('antardashas_from_now', []):
            out.append(f"#### Sub-period {m['md']}-{a['ad']}, {a['start']} to {a['end']}{' (CURRENT)' if a['current'] else ' (PAST: validation check only)' if a.get('past') else ''}\n\n"
                       f"Sub-lord: {_lord_short(a['ad_lord'])}; it is {a['ad_house_from_md_lord']} from the mahadasha lord\n\n"
                       f"Tally of conditions holding (entry + principles): good {a['tally']['good']}, bad {a['tally']['bad']}, "
                       f"mixed {a['tally']['mixed']}; to judge {a['tally']['to_judge']}\n\n")
            _entry_md(a.get('library_entry'), out, '#####', tier='past' if a.get('past') else 'current' if a['current'] else 'future')
            out.append(refs(a, 'Principles whose conditions hold for this sub-period'))
    tm = res.get('timing') or {}
    if tm.get('transits'):
        out.append('## Slow transits (library entries; houses counted from the natal Moon)\n\n')
        for x in tm['transits']:
            out.append(f"### {x['planet']} in {x['sign']}, {x['from']} to {x['to']}: {x['house_from_moon']} from Moon, "
                       f"{x['house_from_lagna']} from lagna, sign dignity {x['transit_dignity']}; running dasha {x['running_dasha']}\n\n")
            _entry_md(x.get('library_entry'), out, show_manual=False, remedies=False,
                      tier='current' if x['from'] <= now and (x['to'] > now or x['to'].startswith('(')) else 'future')
    w = tm.get('windows') or {}
    if w.get('double_transit') or w.get('saturn_over_natal'):
        out.append(f"## Computed timing windows (to {w['data_until']})\n\n{w['method']}\n\n")
        out.append('Double transit, by house from the lagna:\n')
        out += [f"- House {x['house']}: {x['from']} to {x['to']} (Jupiter {x['jupiter']}; Saturn {x['saturn']})\n" for x in w['double_transit']]
        out.append('\nSaturn passing over natal planets (same sign):\n')
        out += [f"- {x['planet']} (natal house {x['natal_house']}): {x['from']} to {x['to']}, Saturn in {x['saturn_in']}\n" for x in w['saturn_over_natal']]
        out.append('\n')
    if tm.get('sade_sati'):
        out.append('## Sade Sati and Dhaiya phases (library entries)\n\n')
        for x in tm['sade_sati']:
            out.append(f"### {x['phase']}: Saturn in {x['saturn_in']}, {x['from']} to {x['to']} ({x['status']}); "
                       f"dasha at start {x['running_dasha_at_start']}{'; ' + x['note'] if x['note'] else ''}\n\n")
            _entry_md(x.get('library_entry'), out, show_manual=False, remedies=False, tier=x['status'])
    if tm.get('yogini'):
        out.append('## Yogini periods (library entries; a secondary timer)\n\n')
        for x in tm['yogini']:
            out.append(f"### {x['yogini']} ({x['planet']}), {x['from']} to {x['to']}{' (CURRENT)' if x.get('current') else ''}\n\n"
                       f"Planet: {_lord_short(x['planet_facts'])}\n\n")
            _entry_md(x.get('library_entry'), out, remedies=False, tier='current' if x.get('current') else 'future')
    t = res['timing_facts']
    out.append(f"## Timing facts (computed)\n\n{t['note']}\n\n")
    out.append(f"Transits on {t['transit_date']}: " + '; '.join(f"{k} in {v['sign']}{' retrograde' if v.get('retro') else ''} ({v['house_from_lagna']} from lagna, {v['house_from_moon']} from Moon)"
                                                         for k, v in (t['transits'] or {}).items()) + '\n\n')
    out.append('Jupiter sign changes: ' + '; '.join(f'{d} into {s} ({h} from lagna)' for d, s, h in t['jupiter_sign_changes'] or []) + '\n\n')
    out.append('Saturn sign changes: ' + '; '.join(f'{d} into {s} ({h} from lagna)' for d, s, h in t['saturn_sign_changes'] or []) + '\n\n')
    ss = t.get('sade_sati_and_dhaiya') or {}
    out.append('Sade Sati and Dhaiya phases: ' + '; '.join(f"{i['phase']} (Saturn in {i['saturn_in']}) {i['start']} to {i['end']}{' CURRENT' if i.get('current') else ''}"
                                                       for i in ss.get('intervals', [])) + '\n\n')
    out.append('Yogini: ' + '; '.join(f"{y['yogini']} ({y['planet']}) {y['start']} to {y['end']}{' CURRENT' if y.get('current') else ''}" for y in t['yogini'] or []) + '\n\n')
    out.append('Chara: ' + '; '.join(f"{y['sign']} {y['start']} to {y['end']}" for y in t['chara'] or []) + '\n\n')
    out.append('## Placement entries (for the planets behind each period: summary and main results)\n\n')
    for e in res['placement_entries']:
        if e.get('missing'): continue
        out.append(f"- `{e['id']}` ({e.get('confidence')}): {_first_sentences(e.get('summary'), 260, '')} Results: {_lst(e.get('common_outcomes'), 3)}\n")
    return soften_health(''.join(out))


# Classical result lists name fevers, wounds, weapons, fire... Writers (especially smaller models) copied them into the
# report even when told not to, and every holdout timeline needed a retry for it. The input now carries neutral words;
# the library itself keeps the classical wording.
_SOFT = [(r'\b(fevers?|febrile)\b', 'health strain'), (r'\billness(es)?\b', 'health strain'), (r'\bdiseases?\b', 'health strain'),
         (r'\b(wounds?|injur(y|ies)|cuts)\b', 'mishaps'), (r'\b(weapons?|sharp tools|sharp instruments)\b', 'risk'),
         (r'\bpoison\w*\b', 'what one takes in'), (r'\baccidents?\b', 'mishaps'),
         (r'\b(from|by|with|around|near) fire\b', r'\1 heat'), (r'\bfire and\b', 'heat and')]


def soften_health(text):
    import re as _re
    for pat, rep in _SOFT:
        text = _re.sub(pat, rep, text, flags=_re.I)
    return text



if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--chart', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--md', help='also write a compact Markdown rendering for small models to this path')
    ap.add_argument('--now'); ap.add_argument('--years', type=float, default=10)
    a = ap.parse_args()
    chart = json.load(open(a.chart, encoding='utf-8'))
    tr_key = next((k for k in chart if k.startswith('transits_')), None)
    now = a.now or (tr_key[len('transits_'):].replace('_', '-') if tr_key else D.date.today().isoformat())
    lib = json.load(open(os.path.join(ROOT, 'library.json'), encoding='utf-8'))
    res = build(chart, lib, now, a.years)
    for p in (a.out, a.md):
        if p: os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
    txt = json.dumps(res, ensure_ascii=False, indent=1, default=str)
    open(a.out, 'w', encoding='utf-8').write(txt)
    if a.md:
        md = to_markdown(res)
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import chart_verdicts as CV  # same verdict block as every other section (v0.9)
        vt, _ = CV.verdicts(chart, now)
        cut = md.find('\n## ', 1)
        md = (md[:cut] + '\n\n' + vt + md[cut:]) if cut > 0 else vt + '\n' + md
        open(a.md, 'w', encoding='utf-8').write(md)
        print(f'wrote {a.md}: {len(md)//4} tokens approx, {md.count(chr(10))} lines')
    n_missing = sum(1 for m in res['mahadashas'] for b in [m] + m.get('antardashas_from_now', []) if b.get('library_entry') is None and b.get('status') != 'future_beyond_horizon')
    print(f"wrote {a.out}: {len(txt)//4} tokens approx; periods {sum(1 + len(m.get('antardashas_from_now', [])) for m in res['mahadashas'])}, "
          f"missing entries {n_missing}, condition errors {len(res['condition_errors'])}")
