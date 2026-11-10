"""Code-built tables for the long kundli report (v0.15, module A).

    build(chart, F, now, lib, sections_md) -> {key: {"title": str, "html": "<table>...</table>", "note": str (optional)}}

Every value comes from chart_data.json (and library.json for meaning/weight columns), never from model text. A key is
omitted when its data is missing; no function raises on a missing field. Keys and the sections they go into: see
SLOTS in tools/assemble_report.py.
"""
import html, json, os, re, sys, datetime as D
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasha_facts as DF
import chart_verdicts as CV

GRAHAS = ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn', 'Rahu', 'Ketu']
SEVEN = GRAHAS[:7]
SIGNS = DF.SIGNS
SIGN_LORD = DF.SIGN_LORD
SIGN_EN = [s.title() for s in SIGNS]
SIGN_SA = {'mesha': 'Aries', 'vrishabha': 'Taurus', 'vrishabh': 'Taurus', 'mithuna': 'Gemini', 'mithun': 'Gemini', 'karka': 'Cancer',
           'karkata': 'Cancer', 'simha': 'Leo', 'kanya': 'Virgo', 'tula': 'Libra', 'vrischika': 'Scorpio', 'vrishchika': 'Scorpio',
           'dhanu': 'Sagittarius', 'dhanus': 'Sagittarius', 'makara': 'Capricorn', 'kumbha': 'Aquarius', 'meena': 'Pisces', 'mina': 'Pisces'}
# natural (naisargika) friendships, Parashara
FRIENDS = {'Sun': {'Moon', 'Mars', 'Jupiter'}, 'Moon': {'Sun', 'Mercury'}, 'Mars': {'Sun', 'Moon', 'Jupiter'},
           'Mercury': {'Sun', 'Venus'}, 'Jupiter': {'Sun', 'Moon', 'Mars'}, 'Venus': {'Mercury', 'Saturn'}, 'Saturn': {'Mercury', 'Venus'}}
ENEMIES = {'Sun': {'Venus', 'Saturn'}, 'Moon': set(), 'Mars': {'Mercury'}, 'Mercury': {'Moon'}, 'Jupiter': {'Mercury', 'Venus'},
           'Venus': {'Sun', 'Moon'}, 'Saturn': {'Sun', 'Moon', 'Mars'}}
DIG_BALA = {'Jupiter': 1, 'Mercury': 1, 'Sun': 10, 'Mars': 10, 'Saturn': 7, 'Moon': 4, 'Venus': 4}
DIGNITY_WORDS = {'exalted': 'Exalted', 'debilitated': 'Debilitated', 'moolatrikona': 'Moolatrikona', 'own': 'Own sign',
                 'friend': "Friend's sign", 'enemy': "Enemy's sign", 'neutral': 'Neutral sign', 'other': '-'}
MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


# ---------- small helpers ----------
def esc(x):
    return html.escape('' if x is None else str(x), quote=False)


def table(headers, rows, cls=None):
    h = '<tr>' + ''.join(f'<th>{esc(c)}</th>' for c in headers) + '</tr>'
    b = ''.join('<tr>' + ''.join(f'<td>{esc(c)}</td>' for c in r) + '</tr>' for r in rows)
    c = f' class="{cls}"' if cls else ''
    return f'<table{c}><thead>{h}</thead><tbody>{b}</tbody></table>'


def ordn(n):
    n = int(n)
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def fdate(s):
    """YYYY-MM-DD -> '11 Dec 1998' (anything else returned unchanged)."""
    try:
        d = D.date.fromisoformat(str(s)[:10])
        return f'{d.day} {MONTHS[d.month - 1]} {d.year}'
    except Exception:
        return '' if s is None else str(s)


def sidx(name):
    if not name: return None
    n = str(name).strip().lower()
    if n in SIGNS: return SIGNS.index(n)
    if n in SIGN_SA: return SIGNS.index(SIGN_SA[n].lower())
    return None


def deg_str(x):
    """degrees float -> 15°08'"""
    d = int(x); m = int(round((x - d) * 60))
    if m == 60: d, m = d + 1, 0
    return f"{d}°{m:02d}'"


def angdist(a, b):
    d = abs(a - b) % 360
    return min(d, 360 - d)


def rel(g, s):
    """Natural relation of planet g to the lord of sign index s: friend / neutral / enemy / own."""
    lord = SIGN_LORD[s]
    if lord == g: return 'own'
    if lord in FRIENDS.get(g, ()): return 'friend'
    if lord in ENEMIES.get(g, ()): return 'enemy'
    return 'neutral'


def varga_dignity(g, s):
    """Dignity in a divisional chart: exalted / debilitated / own / friend / neutral / enemy (no moolatrikona in vargas);
    nodes only exalted/debilitated (Taurus/Scorpio convention), else '-'."""
    if s is None: return '-'
    ex = DF.EXALT_SIGN.get(g)
    if g in ('Rahu', 'Ketu'):
        return 'Exalted' if s == ex else 'Debilitated' if s == (ex + 6) % 12 else '-'
    r = rel(g, s)
    if s == ex: return 'Exalted (own sign)' if r == 'own' else 'Exalted'
    if s == (ex + 6) % 12: return 'Debilitated'
    return {'own': 'Own sign', 'friend': "Friend's sign", 'enemy': "Enemy's sign", 'neutral': 'Neutral sign'}[r]


def first_sentences(t, cap=220):
    t = re.sub(r'\s+', ' ', str(t or '')).strip()
    if not t: return ''
    parts = re.split(r'(?<=[a-z0-9\)][a-z0-9\)][a-z0-9\)]\.)\s+(?=[A-Z])', t)
    out = parts[0]
    if len(out) < 40 and len(parts) > 1: out += ' ' + parts[1]
    if len(out) > cap: out = out[:cap].rsplit(' ', 1)[0] + '...'
    return out


def planets(chart):
    return {p['name']: p for p in chart.get('planets', []) if isinstance(p, dict) and p.get('name')}


def nb_yoga(chart, g):
    return next((y for y in chart.get('yogas_present', []) or [] if str(y.get('name', '')).startswith('Neecha Bhanga') and g in y['name']), None)


def dignity_text(chart, F, g):
    d = DIGNITY_WORDS.get((F[g].get('dignity') or 'other'), str(F[g].get('dignity') or '-').title())
    if nb_yoga(chart, g): d = 'Debilitated (cancelled)'
    return d


def houses_list(hs):
    hs = list(hs or [])
    if not hs: return 'none'
    if len(hs) == 1: return ordn(hs[0])
    return ', '.join(ordn(h) for h in hs[:-1]) + ' and ' + ordn(hs[-1])


# ---------- tables ----------
def t_d1(chart, F):
    P = planets(chart); lg = chart['lagna']
    rows = [['Lagna', lg.get('sign', '-'), lg.get('deg_in_sign', '-'), f"{lg.get('nakshatra', '-')} ({lg.get('pada', '-')})",
             lg.get('nak_lord') or DF.NAK_LORD.get(lg.get('nakshatra'), '-'), 1, '-',
             f"D9 {lg['vargas']['D9']}" if lg.get('vargas', {}).get('D9') else '-']]
    sun = P.get('Sun', {}).get('lon')
    wars = chart.get('graha_yuddha') or []
    for g in GRAHAS:
        if g not in P or g not in F: continue
        p, f = P[g], F[g]
        notes = []
        if f.get('vargottama'): notes.append(f"vargottama ({f['sign'].title()} in D9)")
        d9 = sidx(p.get('vargas', {}).get('D9'))
        if g not in ('Rahu', 'Ketu') and d9 is not None:
            if d9 == DF.EXALT_SIGN[g]: notes.append(f'exalted in D9 ({SIGN_EN[d9]})')
            elif d9 == (DF.EXALT_SIGN[g] + 6) % 12: notes.append(f'debilitated in D9 ({SIGN_EN[d9]})')
        if nb_yoga(chart, g): notes.append('debility cancelled (neecha bhanga)')
        if g in CV.ORB and sun is not None:
            dist = angdist(p['lon'], sun); orb = CV.ORB[g][1 if (p.get('speed') or 1) < 0 else 0]
            if p.get('combust'): notes.append(f"combust ({deg_str(dist)} from the Sun)")
            elif dist <= orb + 5: notes.append(f"not combust ({deg_str(dist)} from the Sun, limit {orb}°)")
        if p.get('retro') and g not in ('Rahu', 'Ketu'): notes.append('retrograde')
        if DIG_BALA.get(g) == f['house']: notes.append(f"directional strength (in the {ordn(f['house'])})")
        for w in wars:
            ps = w.get('planets') or []
            if g in ps:
                other = [q for q in ps if q != g]
                win = w.get('winner_by_latitude')
                notes.append(f"planetary war with {', '.join(other)}" + (f" ({'wins' if win == g else 'loses'})" if win else ''))
        dig = DIGNITY_WORDS.get(p.get('dignity') or 'other', str(p.get('dignity') or '-').title())
        if g in ('Rahu', 'Ketu') and dig != '-': dig += '*'
        rows.append([g, p.get('sign', '-'), p.get('deg_in_sign', '-'), f"{p.get('nakshatra', '-')} ({p.get('pada', '-')})",
                     p.get('nak_lord') or DF.NAK_LORD.get(p.get('nakshatra'), '-'), p.get('house', f['house']), dig,
                     '; '.join(notes) or '-'])
    gk = P.get('Gulika')
    if gk:
        rows.append(['Gulika', gk.get('sign', '-'), gk.get('deg_in_sign', '-'), '-', '-', gk.get('house', '-'), '-', '-'])
    node = chart.get('settings', {}).get('node_exalt')
    note = ('* Nodes: exalted/debilitated by the ' + node.replace('_', '/').title() + ' convention (authors differ).') if node else ''
    note += (' ' if note else '') + 'Directional strength: Jupiter and Mercury in the 1st, the Sun and Mars in the 10th, Saturn in the 7th, the Moon and Venus in the 4th.'
    return {'title': 'Planetary positions in the birth chart (D1)',
            'html': table(['Planet', 'Sign', 'Degree', 'Nakshatra (pada)', 'Nak. lord', 'House', 'Dignity', 'Notes'], rows),
            'note': note}


def t_houses(chart):
    rows = []
    for h in chart.get('houses') or []:
        rows.append([h.get('house'), h.get('sign'), h.get('lord'),
                     f"{ordn(h['lord_in_house'])} ({h.get('lord_in_sign', '-')}, {h.get('lord_dignity', '-')})" if h.get('lord_in_house') else '-',
                     ', '.join(h.get('occupants') or []) or '-', ', '.join(h.get('aspected_by') or []) or '-'])
    if not rows: return None
    return {'title': 'The twelve houses',
            'html': table(['House', 'Sign', 'Lord', 'Lord placed in', 'Occupants', 'Aspected by'], rows)}


def t_varga(chart, F, vk):
    P = planets(chart); lag = chart['lagna'].get('vargas', {}).get(vk)
    li = sidx(lag)
    if li is None: return None, None
    rows = []
    for g in GRAHAS:
        s = sidx(P.get(g, {}).get('vargas', {}).get(vk))
        if s is None: continue
        rows.append((g, s, (s - li) % 12 + 1, varga_dignity(g, s)))
    return lag, rows


def t_d9(chart, F):
    lag, rows = t_varga(chart, F, 'D9')
    if not rows: return None
    out = []
    for g, s, h, dig in rows:
        c = []
        if F.get(g, {}).get('vargottama'): c.append('vargottama (same sign as in D1)')
        if dig.startswith('Exalted'): c.append('exalted in D9')
        if dig == 'Debilitated': c.append('debilitated in D9')
        out.append([g, SIGN_EN[s], h, dig, '; '.join(c) or '-'])
    return {'title': f'Navamsa (D9) positions, {lag} lagna',
            'html': table(['Planet', 'D9 sign', 'D9 house', 'Dignity in D9', 'Comment'], out),
            'note': 'D9 houses are counted from the navamsa lagna.'}


def t_d10(chart, F):
    lag, rows = t_varga(chart, F, 'D10')
    if not rows: return None
    out = [[g, SIGN_EN[s], h, dig] for g, s, h, dig in rows]
    return {'title': f'Dashamsa (D10) positions, {lag} lagna',
            'html': table(['Planet', 'D10 sign', 'D10 house', 'Dignity'], out),
            'note': 'D10 houses are counted from the dashamsa lagna. The D10 is very sensitive to the birth time: a few minutes '
                    'can change its lagna and every house in it.'}


def functional_role(F, g):
    f = F[g]; r = f['rules']; role = f['role']
    if g in ('Rahu', 'Ketu'):
        return f"A node: gives the results of its sign lord {f['sign_lord']} and of the house it occupies"
    nat_ben = f.get('natural') == 'benefic'
    if 'yogakaraka' in role:
        return 'Yogakaraka (rules an angle and a trine): the most helpful planet for this lagna'
    if 'lagna_lord' in role:
        extra = [h for h in r if h != 1]
        return 'Lagna lord: helpful' + (f" (the 1st lordship outweighs the {ordn(extra[0])})" if extra and extra[0] in (6, 8, 12) else '')
    if 'trikona_lord' in role:
        tri = [h for h in r if h in (5, 9)]; oth = [h for h in r if h not in (5, 9)]
        return f"Lord of the {houses_list(tri)} (a trine): helpful" + (f"; the trine lordship outweighs the {houses_list(oth)}" if oth else '')
    if set(r) <= {2, 7} and r:
        return f"Lord of the {houses_list(r)}: mixed; carries money, partners and stress on health"
    if 'kendra_lord' in role and not any(h in (3, 6, 8, 11, 12) for h in r):
        return f"Lord of the {houses_list(r)} (an angle): " + ('neutral; a natural benefic ruling an angle gives mixed results' if nat_ben and g != 'Moon'
                                                               else 'generally helpful')
    if any(h in (3, 6, 8, 11, 12) for h in r):
        return f"Lord of the {houses_list(r)}: difficult for this lagna" + (' despite being a natural benefic' if nat_ben else '')
    return f"Lord of the {houses_list(r)}: neutral"


def t_roles(chart, F):
    rows = []
    for g in GRAHAS:
        if g not in F: continue
        f = F[g]
        here = f"{dignity_text(chart, F, g)}, in the {ordn(f['house'])} ({f['sign'].title()})"
        if f.get('karaka'): here += f"; {f['karaka']}"
        rows.append([g, ', '.join(map(str, f['rules'])) or '-', functional_role(F, g), here])
    lag = chart['lagna'].get('sign', '')
    return {'title': f'Functional roles of the planets for {lag} lagna',
            'html': table(['Planet', 'Houses ruled', 'Functional role', 'In this chart'], rows)}


PANCH_KEYS = [('vara', 'Weekday'), ('tithi', 'Tithi'), ('nitya_yoga', 'Nitya yoga'), ('karana', 'Karana')]
AVAK_LABELS = {'rashi': 'Rashi (Moon sign)', 'rashi_lord': 'Rashi lord', 'nakshatra': 'Nakshatra (pada)', 'nak_lord': 'Nakshatra lord',
               'gana': 'Gana', 'yoni': 'Yoni', 'nadi': 'Nadi', 'varna': 'Varna', 'vashya': 'Vashya', 'lagna': 'Lagna',
               'lagna_lord': 'Lagna lord', 'tatva': 'Tattva', 'tattva': 'Tattva', 'paya': 'Paya', 'yunja': 'Yunja', 'naam_akshar': 'Name syllable'}


def t_panchang(chart):
    pc = chart.get('panchang_at_birth') or {}; av = chart.get('avakhada') or {}
    if not pc and not av: return None
    rows = []
    for k, lab in PANCH_KEYS:
        v = pc.get(k)
        if not v: continue
        if k == 'tithi':
            v = f"{pc.get('paksha', '')} {v}".strip() + (f" ({pc['tithi_num']})" if pc.get('tithi_num') else '')
            if pc.get('paksha'): v += f", {'waxing' if str(pc['paksha']).lower().startswith('shukla') else 'waning'} Moon"
        rows.append([lab, v])
    if av.get('nakshatra'):
        rows.append(['Nakshatra (pada)', f"{av['nakshatra']} ({av['pada']})" if av.get('pada') else av['nakshatra']])
    else:
        mo = planets(chart).get('Moon')
        if mo: rows.append(['Nakshatra (pada)', f"{mo.get('nakshatra')} ({mo.get('pada')})"])
    for k, lab in (('sunrise', 'Sunrise'), ('sunset', 'Sunset')):
        v = pc.get(k)
        if v: rows.append([lab, str(v).split(' ')[-1]])
    for k, v in av.items():
        if k in ('nakshatra', 'pada') or v in (None, ''): continue
        lab = AVAK_LABELS.get(k, k.replace('_', ' ').capitalize())
        if k == 'rashi' and sidx(v) is not None: v = f"{v} ({SIGN_EN[sidx(v)]})"
        if k == 'lagna' and sidx(v) is not None: v = f"{v} ({SIGN_EN[sidx(v)]})"
        rows.append([lab, v])
    return {'title': 'Birth panchang and avakhada details',
            'html': table(['Item', 'Value'], rows, cls='kv'),
            'note': 'Sunrise and sunset are local times at the birth place on the birth date.'}


AVASTHA = [('Bala (infant)', 'quarter'), ('Kumara (youth)', 'half'), ('Yuva (adult)', 'full'), ('Vriddha (old)', 'little'),
           ('Mrita (dead)', 'none')]


def t_baladi(chart):
    P = planets(chart); rows = []
    for g in SEVEN:
        p = P.get(g)
        if not p or p.get('lon') is None: continue
        s = int(p['lon'] // 30) % 12; d = p['lon'] % 30
        band = min(int(d // 6), 4)
        if s % 2 == 1: band = 4 - band  # even signs (Taurus, Cancer...) run in reverse
        st, res = AVASTHA[band]
        rows.append([g, f"{SIGN_EN[s]} ({'odd' if s % 2 == 0 else 'even'})", deg_str(d), st, res])
    if not rows: return None
    return {'title': 'Baladi avasthas (age states of the planets)',
            'html': table(['Planet', 'Sign (odd/even)', 'Degree in sign', 'Avastha', 'Share of results'], rows),
            'note': 'Six-degree bands: Bala, Kumara, Yuva, Vriddha, Mrita in odd signs, reversed in even signs. Results: '
                    'Yuva full, Kumara half, Bala a quarter, Vriddha little, Mrita none.'}


def t_profession(chart, F, lib):
    P = planets(chart); L = chart['lagna']['sign_num'] - 1
    refs = [('10th from the lagna', L)]
    for g in ('Moon', 'Sun'):
        if g in F: refs.append((f'10th from the {g}', F[g]['_sign_num']))
    rows = []
    for lab, base in refs:
        s10 = (base + 9) % 12; lord = SIGN_LORD[s10]
        d9 = sidx(P.get(lord, {}).get('vargas', {}).get('D9'))
        if d9 is None: continue
        ind = SIGN_LORD[d9]
        e = lib.get(f'profession/{ind.lower()}') if isinstance(lib, dict) else None
        meaning = first_sentences(e.get('summary'), 260) if e and e.get('summary') else '-'
        rows.append([lab, SIGN_EN[s10], lord, SIGN_EN[d9], ind, meaning])
    if not rows: return None
    return {'title': 'Profession indicators (Phaladeepika ch. 5)',
            'html': table(['Counted from', '10th sign', 'Its lord', "Lord's D9 sign", 'Indicator (D9 sign lord)', 'Classical field'], rows),
            'note': 'Phaladeepika ch. 5: the source of livelihood is shown by the lord of the navamsa sign occupied by the 10th lord, '
                    'counted from the lagna, the Moon and the Sun; the strongest of the three prevails.'}


def t_manglik(chart):
    m = (chart.get('doshas') or {}).get('manglik')
    if not isinstance(m, dict): return None
    mh = m.get('mars_house') or {}; hits = m.get('hits') or {}
    rows = []
    for k, lab in (('lagna', 'Lagna'), ('moon', 'Moon'), ('venus', 'Venus')):
        if k not in mh: continue
        rows.append([lab, f"{ordn(mh[k])} house", 'Yes' if hits.get(k) else 'No'])
    flags = [k.replace('_', ' ') for k, v in (m.get('cancel_flags') or {}).items() if v]
    n = sum(1 for v in hits.values() if v)
    if m.get('is_manglik_any'):
        verdict = f"Present from {n} of {len(hits) or 3}"
        canc = (f"cancelled by the calculator's rules (met: {', '.join(flags)})" if m.get('cancelled_any') else 'no cancellation met')
        rows.append(['Result', verdict, canc[0].upper() + canc[1:]])
    else:
        rows.append(['Result', 'Absent from all three', '-'])
    return {'title': 'Manglik check',
            'html': table(['Reference', 'Mars counted from it', 'Manglik?'], rows),
            'note': f"Manglik houses used: {', '.join(map(str, m.get('houses_used', [])))}." if m.get('houses_used') else ''}


def _rules(F, g):
    return '/'.join(map(str, F[g]['rules'])) if g in F and F[g]['rules'] else ''


def yoga_how(chart, F, y):
    n = y.get('name', ''); c = y.get('conditions') or {}
    try:
        if 'pairs' in c:
            parts = []
            for pr in c['pairs']:
                a, b = pr.get('pair', ['?', '?'])[:2]
                own = pr.get('houses_owned') or {}
                ra = '/'.join(map(str, own.get(a, F.get(a, {}).get('rules', [])))); rb = '/'.join(map(str, own.get(b, F.get(b, {}).get('rules', []))))
                how = ', '.join(h.replace('_', ' ') for h in pr.get('how', []))
                parts.append(f"{a} (lord of {ra}) and {b} (lord of {rb}): {how}")
            return '; '.join(parts)
        if n == 'Yogakaraka present':
            return '; '.join(f"{g} rules the {houses_list(F[g]['rules'])}, placed in the {ordn(F[g]['house'])} ({F[g]['sign'].title()}, {F[g]['dignity']})"
                             for g in c.get('yogakaraka', []) if g in F)
        if n.startswith('Viparita'):
            g = c.get('lord'); want = {'Harsha': 6, 'Sarala': 8, 'Vimala': 12}
            h = next((v for k, v in want.items() if k in n), None)
            s = f"{ordn(h)} lord {g} in the {ordn(c.get('lord_house'))}" if h else f"{g} in the {ordn(c.get('lord_house'))}"
            if g in F and len(F[g]['rules']) > 1: s += f" ({g} also rules the {houses_list([x for x in F[g]['rules'] if x != h])})"
            if c.get('strict_fired') is False: s += '; popular form only (the strict form is not met)'
            return s
        if n.startswith('Neecha Bhanga'):
            g = n[n.find('(') + 1:n.find(')')] if '(' in n else '?'
            met = [k.split('_', 1)[1].replace('_', ' ') for k, v in c.items() if k[:1] == 'c' and k[1:2].isdigit() and v]
            lab = {'sign lord kendra': f"its sign lord {c.get('debilitation_lord', '')} in a kendra".replace('  ', ' '),
                   'exalt planet kendra': f"{c.get('exalt_planet', 'the planet exalted there')} in a kendra",
                   'D E mutual kendra': 'sign lord and exaltation planet in mutual kendras',
                   'exalted in D9': 'exalted in D9', 'with or aspected by D or E': 'joined or aspected by the sign lord or exaltation planet',
                   'lord of exalt sign kendra': 'the lord of its exaltation sign in a kendra'}
            s = f"{g} debilitated in {F[g]['sign'].title()} (house {F[g]['house']})" if g in F else n
            return s + f"; cancelled by: {', '.join(lab.get(x, x) for x in met)} ({len(met)} of 6 tests)"
        if n == 'Budhaditya':
            sep = c.get('sun_mercury_sep')
            return (f"Sun and Mercury together in {F['Sun']['sign'].title()} (house {F['Sun']['house']})"
                    + (f", {deg_str(sep)} apart" if sep is not None else '') + ('; Mercury combust' if c.get('mercury_combust') else '; Mercury not combust'))
        if n == 'Durudhara' or n in ('Sunapha', 'Anapha'):
            bits = []
            if c.get('second'): bits.append(f"{', '.join(c['second'])} in the 2nd from the Moon")
            if c.get('twelfth'): bits.append(f"{', '.join(c['twelfth'])} in the 12th from the Moon")
            return '; '.join(bits)
        if n == 'Shakata':
            return f"Moon in the {ordn(c.get('moon_from_jupiter'))} from Jupiter; " + ('cancelled' if c.get('cancelled') else 'not cancelled')
        if n == 'Grahan':
            out = []
            for combo in c.get('combos', []):
                a, b = (combo.split('+') + ['?'])[:2]
                h = F.get(a, {}).get('house')
                d = ''
                P = planets(chart)
                if a in P and b in P: d = f", {deg_str(angdist(P[a]['lon'], P[b]['lon']))} apart"
                out.append(f"{a} with {b}" + (f" in the {ordn(h)}" if h else '') + d)
            return '; '.join(out)
    except Exception:
        pass
    flat = []
    for k, v in c.items():
        if isinstance(v, (dict, list)): v = json.dumps(v, ensure_ascii=False)
        flat.append(f"{k.replace('_', ' ')}: {v}")
    return '; '.join(flat) or '-'


YOGA_LABEL = {'Raja (kendra-trikona lords)': 'Raja yoga (angle and trine lords)', 'Yogakaraka present': 'Yogakaraka',
              'Dhana (1/2/5/9/11 lords)': 'Dhana yoga (wealth-house lords)'}


def t_yogas(chart, F, lib):
    ys = chart.get('yogas_present') or []
    if not ys: return None
    rows = []
    for y in ys:
        slug = DF.yoga_slug(y.get('name', ''))
        e = lib.get(f'yoga/{slug}') if slug and isinstance(lib, dict) else None
        w = '-'
        if e:
            w = first_sentences(e.get('rarity_and_weight') or e.get('weight') or e.get('strength') or '', 220) or '-'
        rows.append([YOGA_LABEL.get(y['name'], y['name']), yoga_how(chart, F, y), w])
    return {'title': 'Yogas present, with their weight',
            'html': table(['Yoga', 'How it forms here', 'Weight (library)'], rows),
            'note': 'Formation from the calculator; weight from the library entry for each yoga.'}


DOSHA_NAME = {'manglik': 'Manglik (Kuja)', 'kaal_sarp': 'Kaal Sarp', 'pitra': 'Pitra (ancestral)', 'guru_chandal': 'Guru-Chandal',
              'shrapit': 'Shrapit', 'angarak': 'Angarak', 'ghata': 'Ghata', 'ganda_moola': 'Ganda Moola'}


def kaal_sarp_status(d):
    """Same rule as report_input.py's VERDICT."""
    modes = [v for v in d.values() if isinstance(v, dict)]
    full = any(v.get('degree_full') or v.get('sign_mode_full') for v in modes)
    part = any(v.get('degree_partial_one_out') for v in modes)
    outs = next((v.get('outside_planets') for v in modes if v.get('outside_planets')), [])
    if full: return 'Present', 'Full form: every planet lies on one side of the Rahu-Ketu axis'
    if part: return 'Partial', f"Partial form only: one planet outside the axis ({', '.join(outs)})"
    return 'Absent', (f"{len(outs)} planets lie outside the Rahu-Ketu axis ({', '.join(outs)}), so neither the full nor the partial form applies"
                      if outs else 'Neither the full nor the partial form applies')


def t_doshas(chart):
    ds = chart.get('doshas') or {}
    rows = []
    for k, d in ds.items():
        if k == 'sade_sati': continue
        name = DOSHA_NAME.get(k, k.replace('_', ' ').title())
        if d is False or d is None:
            rows.append([name, 'Absent', 'Not formed in this chart']); continue
        if d is True:
            rows.append([name, 'Present', 'Flag only; no reference points or cancellations computed']); continue
        if not isinstance(d, dict):
            rows.append([name, str(d), '-']); continue
        if k == 'manglik':
            hits = [h for h, v in (d.get('hits') or {}).items() if v]
            flags = [f.replace('_', ' ') for f, v in (d.get('cancel_flags') or {}).items() if v]
            mh = d.get('mars_house') or {}
            if not d.get('is_manglik_any'):
                rows.append([name, 'Absent', 'Mars is not in a Manglik house from the lagna, the Moon or Venus']); continue
            st = 'Cancelled' if d.get('cancelled_any') else 'Present'
            cm = (f"Counted from {', '.join(h.title() for h in hits)} only ({len(hits)} of 3; Mars "
                  + ', '.join(f"{ordn(v)} from {'the lagna' if r == 'lagna' else 'the Moon' if r == 'moon' else r.title()}" for r, v in mh.items()) + ')')
            if d.get('cancelled_any'): cm += f"; cancellation met: {', '.join(flags)}"
            rows.append([name, st, cm]); continue
        if k == 'kaal_sarp':
            st, cm = kaal_sarp_status(d)
            rows.append([name, st, cm]); continue
        fired = d.get('pyjhora_fired', d.get('present', d.get('fired')))
        flags = d.get('flags') if isinstance(d.get('flags'), dict) else {kk: vv for kk, vv in d.items() if kk not in ('pyjhora_fired', 'present', 'fired')}
        on = []
        for fk, fv in flags.items():
            if fv in (False, None, [], {}, ''): continue
            on.append(fk.replace('_', ' ') + ('' if fv is True else f": {', '.join(map(str, fv)) if isinstance(fv, list) else fv}"))
        st = 'Present' if fired else ('Partial' if on else 'Absent')
        rows.append([name, st, ('Flags met: ' + '; '.join(on)) if on else 'No flag met'])
    if not rows: return None
    return {'title': 'Dosha checks',
            'html': table(['Dosha', 'Status', 'Comment (from the calculator)'], rows),
            'note': 'Sade Sati and Dhaiya are dated in the Timeline.'}


def lord_role(chart, F, g):
    f = F[g]
    if g in ('Rahu', 'Ketu'):
        s = f"Node in the {ordn(f['house'])} ({f['sign'].title()}); acts for its sign lord {f['sign_lord']}"
        lag_nl = chart['lagna'].get('nak_lord') or DF.NAK_LORD.get(chart['lagna'].get('nakshatra'))
        if lag_nl == g: s += '; lord of the lagna nakshatra'
        return s
    words = {'yogakaraka': 'yogakaraka', 'lagna_lord': 'lagna lord'}
    tags = [words[r] for r in f['role'] if r in words]
    s = f"Lord of the {houses_list(f['rules'])}" + (f" ({', '.join(tags)})" if tags else '')
    s += f"; {dignity_text(chart, F, g).lower()} in the {ordn(f['house'])}"
    if f.get('retro'): s += ', retrograde'
    if f.get('with'): s += f"; with {', '.join(f['with'])}"
    if f.get('karaka') in ('Atmakaraka', 'Amatyakaraka'): s += f"; {f['karaka']}"
    return s


def age_at(birth, d):  # completed years, same rule as dasha_facts.build.age
    a = int(d[:4]) - int(birth[:4]) - (1 if d[5:10] < birth[5:10] else 0)
    return max(0, a)


def t_mahadashas(chart, F, now):
    v = chart.get('vimshottari') or {}; mds = v.get('mahadashas') or []
    birth = chart.get('birth', {}).get('date')
    if not mds or not birth: return None
    rows = []
    for m in mds:
        st = max(m['start'], birth)
        cur = m['start'] <= now < m['end']
        rows.append([m['md'] + (' (now)' if cur else ''), fdate(st) + (' (birth)' if st == birth and m['start'] < birth else ''),
                     fdate(m['end']), f"{age_at(birth, st)}-{age_at(birth, m['end'])}", lord_role(chart, F, m['md']) if m['md'] in F else '-'])
    bal = v.get('balance_at_birth') or {}
    note = (f"Balance at birth: {bal['lord']} {bal['years']:.2f} years. " if bal.get('lord') and isinstance(bal.get('years'), (int, float)) else '')
    note += 'Ages are completed years; Vimshottari years of 365.25 days.'
    return {'title': 'Vimshottari mahadashas',
            'html': table(['Mahadasha', 'From', 'To', 'Age', "Planet's role in this chart"], rows), 'note': note}


def short_tone(F, g):
    t = CV.role_tone(F, g)
    if g in ('Rahu', 'Ketu'):
        return f"node; acts through its sign lord {F[g]['sign_lord']}"
    m = re.match(r'^(.*) \(([^;)]*)', t)
    if not m: return t
    words, tone = m.group(1), m.group(2)
    return f"{words}; {tone}"


def t_antardashas(chart, F, now):
    md, _ = DF.dasha_at(chart, now)
    if not md: return None, None
    ads = (chart.get('vimshottari') or {}).get('antardashas_by_md', {}).get(md)
    if not ads:
        cur = (chart.get('vimshottari') or {}).get('current_md_antardashas')
        ads = cur or []
    if not ads: return md, None
    rows = []
    for a in ads:
        g = a['ad']
        now_ = a['start'] <= now < a['end']
        role = f"Rules {', '.join(map(str, F[g]['rules']))}, in the {ordn(F[g]['house'])}" if g in F and F[g]['rules'] else (f"In the {ordn(F[g]['house'])}" if g in F else '')
        rows.append([f"{md}-{g}" + (' (now)' if now_ else ''), fdate(a['start']), fdate(a['end']),
                     (role + ': ' if role else '') + (short_tone(F, g) if g in F else '-')])
    return md, {'title': f'Sub-periods (antardashas) within the {md} mahadasha',
                'html': table(['Sub-period', 'From', 'To', "Sub-lord's role and tone"], rows),
                'note': 'Tone is from the sub-lord\'s house rulership for this lagna; the mahadasha lord colours every sub-period.'}


def t_transits(chart, F, now):
    tk = next((k for k in chart if k.startswith('transits_')), None)
    tr = chart.get(tk) or {}
    if not tr: return None
    L = chart['lagna']['sign_num'] - 1; moon = F['Moon']['_sign_num'] if 'Moon' in F else None
    tr = dict(tr)
    if 'Ketu' not in tr and 'Rahu' in tr and sidx(tr['Rahu'].get('sign')) is not None:
        rs = sidx(tr['Rahu']['sign'])
        tr['Ketu'] = {'sign': SIGN_EN[(rs + 6) % 12], 'deg': tr['Rahu'].get('deg')}
    rows = []
    for g in GRAHAS:
        x = tr.get(g)
        if not x: continue
        s = sidx(x.get('sign'))
        if s is None: continue
        sign = SIGN_EN[s] + (f" {x['deg']:.1f}°" if isinstance(x.get('deg'), (int, float)) else '') + (' (R)' if x.get('retro') and g not in ('Rahu', 'Ketu') else '')
        hl = (s - L) % 12 + 1; hm = (s - moon) % 12 + 1 if moon is not None else '-'
        rows.append([g, sign, hl, hm])
    d = tk[len('transits_'):].replace('_', '-')
    return {'title': f'Current transits ({fdate(d)})',
            'html': table(['Planet', 'Sign (R = retrograde)', 'House from lagna', 'House from Moon'], rows),
            'note': 'Rahu and Ketu always move backwards; Ketu is opposite Rahu.'}


def t_ingresses(chart, F):
    L = chart['lagna']['sign_num'] - 1; moon = F['Moon']['_sign_num'] if 'Moon' in F else None
    ev = []
    for g, k in (('Jupiter', 'jupiter_ingresses_next_6y'), ('Saturn', 'saturn_ingresses_next_6y')):
        for item in chart.get(k) or []:
            try:
                d, sg = item[0], item[1]
            except Exception:
                continue
            s = sidx(sg)
            if s is None: continue
            ev.append((d, g, s))
    if not ev: return None
    ev.sort()
    rows = [[fdate(d), f"{g} enters {SIGN_EN[s]}", (s - L) % 12 + 1, (s - moon) % 12 + 1 if moon is not None else '-'] for d, g, s in ev]
    return {'title': 'Slow-planet sign changes (Jupiter and Saturn)',
            'html': table(['Date', 'Planet enters sign', 'House from lagna', 'House from Moon'], rows),
            'note': f"From the computed ephemeris to {fdate(ev[-1][0])}. A planet re-entering a sign it just left is a retrograde return."}


def t_chara(chart):
    ch = chart.get('chara_current_and_next') or []
    rows = []
    for c in ch:
        s = sidx(c.get('sign'))
        lab = c.get('sign', '-') + (f" ({SIGN_EN[s]})" if s is not None and c.get('sign', '').lower() not in SIGNS else '')
        rows.append([lab, fdate(c.get('start')), fdate(c.get('end'))])
    if not rows: return None
    return {'title': 'Chara (Jaimini sign) periods',
            'html': table(['Sign', 'From', 'To'], rows), 'note': 'Dates only; a secondary timer alongside the Vimshottari periods.'}


def build(chart, F=None, now=None, lib=None, sections_md=None):
    lib = lib or {}
    if F is None:
        F = DF.planet_facts(chart)
    if not now:
        tk = next((k for k in chart if k.startswith('transits_')), None)
        now = tk[len('transits_'):].replace('_', '-') if tk else D.date.today().isoformat()
    out = {}
    makers = [
        ('d1_positions', lambda: t_d1(chart, F)),
        ('houses', lambda: t_houses(chart)),
        ('d9_positions', lambda: t_d9(chart, F)),
        ('functional_roles', lambda: t_roles(chart, F)),
        ('panchang_avakhada', lambda: t_panchang(chart)),
        ('baladi_avasthas', lambda: t_baladi(chart)),
        ('profession_indicators', lambda: t_profession(chart, F, lib)),
        ('d10_positions', lambda: t_d10(chart, F)),
        ('manglik_check', lambda: t_manglik(chart)),
        ('yogas_present', lambda: t_yogas(chart, F, lib)),
        ('dosha_checks', lambda: t_doshas(chart)),
        ('mahadashas', lambda: t_mahadashas(chart, F, now)),
        ('antardashas', lambda: t_antardashas(chart, F, now)[1]),
        ('current_transits', lambda: t_transits(chart, F, now)),
        ('slow_ingresses', lambda: t_ingresses(chart, F)),
        ('chara_periods', lambda: t_chara(chart)),
    ]
    for key, fn in makers:
        try:
            r = fn()
        except Exception as e:  # never raise on missing or odd data; the key is skipped
            print(f'report_tables: skipped {key}: {type(e).__name__}: {e}', file=sys.stderr)
            r = None
        if r:
            if not r.get('note'): r.pop('note', None)
            out[key] = r
    return out


if __name__ == '__main__':
    import argparse
    sys.stdout.reconfigure(encoding='utf-8')
    ap = argparse.ArgumentParser(); ap.add_argument('--chart', required=True); ap.add_argument('--now'); ap.add_argument('--html')
    a = ap.parse_args()
    chart = json.load(open(a.chart, encoding='utf-8'))
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    lib = json.load(open(os.path.join(ROOT, 'library.json'), encoding='utf-8'))
    res = build(chart, DF.planet_facts(chart), a.now, lib, {})
    for k, v in res.items():
        print(f"{k:22s} {v['html'].count('<tr>') - 1:3d} rows  {v['title']}")
    if a.html:
        open(a.html, 'w', encoding='utf-8').write('<meta charset="utf-8"><style>td,th{border:1px solid #999;padding:2px 5px;font:12px sans-serif}table{border-collapse:collapse;margin:8px 0}</style>'
                                                  + ''.join(f"<h3>{esc(v['title'])}</h3>{v['html']}<p><i>{esc(v.get('note', ''))}</i></p>" for v in res.values()))
