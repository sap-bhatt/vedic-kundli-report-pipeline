"""Shared, code-computed chart verdicts for the long report (v0.9).

One block, identical in every section input, so sections cannot disagree about facts they all use:
per-planet net condition (dignity, neecha bhanga, distance from the Sun and combustion, natural vs functional nature,
D9/D10 dignity), the nature of every aspect between planets, Manglik status exactly as the calculator gives it,
chart shape (kendras, dusthanas, dispositors), D9 and D10 placements, and the dated periods ahead for each section.
Also the ownership map: which section explains each recurring point in full.
"""
import json
import dasha_facts as DF

GRAHAS = ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn', 'Rahu', 'Ketu']
SIGNS = DF.SIGNS
ORB = {'Moon': (12, 12), 'Mars': (17, 17), 'Mercury': (14, 12), 'Jupiter': (11, 11), 'Venus': (10, 8), 'Saturn': (15, 15)}
EXALT = DF.EXALT_SIGN
SIGN_LORD = DF.SIGN_LORD

# which section explains each house's matters in full (others refer to it in a clause)
HOUSE_OWNER = {1: 'personality', 2: 'finance', 3: 'family', 4: 'family', 5: 'family', 6: 'health', 7: 'relationships',
               8: 'spirituality', 9: 'spirituality', 10: 'career', 11: 'finance', 12: 'spirituality'}
SECTION_TITLE = {'glance': 'Chart at a glance', 'personality': 'Personality', 'mind': 'Mind', 'career': 'Career',
                 'finance': 'Finance', 'health': 'Health', 'relationships': 'Relationships', 'family': 'Family',
                 'spirituality': 'Spirituality', 'yogas': 'Yogas and doshas', 'timeline': 'Timeline', 'guidance': 'Guidance'}


def angdist(a, b):
    d = abs(a - b) % 360
    return min(d, 360 - d)


def planet_owner(F, chart, g):
    """Section that explains a planet's sign and house placement in full."""
    lagna_lord = SIGN_LORD[chart['lagna']['sign_num'] - 1]
    if g in ('Moon', 'Mercury'): return 'mind'
    if g in ('Sun', lagna_lord): return 'personality'
    return HOUSE_OWNER[F[g]['house']]


def entry_owner(eid, F, chart):
    """Owner section of a library entry id, or None when every section may use it fully."""
    parts = eid.split('/')
    lay = parts[0]
    if lay in ('yoga',): return 'yogas'
    if lay == 'dosha': return 'relationships' if parts[1] == 'manglik' else 'yogas'
    if lay in ('planet_in_sign',):
        return planet_owner(F, chart, parts[1].title())
    if lay == 'planet_in_house':
        g = parts[1].title()
        return planet_owner(F, chart, g)
    if lay == 'lord_in_house':
        return HOUSE_OWNER[int(parts[1])]
    if lay == 'aspect':
        return HOUSE_OWNER[int(parts[2])]
    if lay == 'conjunction':
        a = parts[1].split('_')[0].title()
        return planet_owner(F, chart, a) if a in F else None
    if lay in ('rising_sign',): return 'personality'
    if lay == 'nakshatra': return None
    return None


def d_house(sign, lagna_sign):
    return (SIGNS.index(sign.lower()) - SIGNS.index(lagna_sign.lower())) % 12 + 1


def verdicts(chart, now):
    F = DF.planet_facts(chart)
    P = {p['name']: p for p in chart['planets'] if p['name'] in GRAHAS}
    L = chart['lagna']['sign_num'] - 1
    sun = P['Sun']['lon']
    waxing = str(chart.get('panchang_at_birth', {}).get('paksha', '')).lower().startswith('shukla')
    nb = {y['name']: y for y in chart.get('yogas_present', []) if y['name'].startswith('Neecha Bhanga')}
    out = []
    out.append('## Chart verdicts (computed; identical in every section, use exactly these)\n')
    out.append('These settle points that several sections touch. They are reference facts, not content to restate: use a verdict only where it changes the reading of the area being written, in a clause, and then match it exactly. Never re-explain a verdict another section owns (see Ownership). '
               '"Natural" nature (benefic/malefic) decides the quality of a planet\'s aspect and company; its functional '
               'role for this lagna (houses ruled) decides which matters it carries. When the two differ, say both '
               '(for example: "a natural malefic, so its aspect is hard in manner, but as yogakaraka it carries the 4th and 5th").\n\n')
    md_ = angdist(P['Moon']['lon'], sun)
    strong = md_ >= 90
    out.append(f"Moon at birth: {'waxing' if waxing else 'waning'}, {md_:.0f} deg from the Sun, so the Moon counts as a natural "
               f"{'benefic' if strong else 'malefic'} in this chart (Parashara's rule: benefic from Shukla Ashtami to Krishna "
               f"Ashtami, i.e. 90 deg or more from the Sun{'; near full' if md_ >= 160 else ''}).\n\n")
    out.append('| Planet | Sign, house | Dignity (net) | Distance from Sun | Natural | Functional role | D9 | D10 |\n|---|---|---|---|---|---|---|---|\n')
    d10_lagna = chart['lagna']['vargas'].get('D10'); d9_lagna = chart['lagna']['vargas']['D9']
    for g in GRAHAS:
        f, p = F[g], P[g]
        dig = f['dignity']
        nbk = next((k for k in nb if g in k), None)
        if nbk:
            c = nb[nbk]['conditions']
            met = [k.split('_', 1)[1].replace('_', ' ') for k, v in c.items() if k[:1] == 'c' and k[1:2].isdigit() and v]
            dig = f"debilitated, cancelled (neecha bhanga: {len(met)} of 6 tests met: {'; '.join(met)})"
        if g == 'Sun' or g in ('Rahu', 'Ketu'):
            dist = '-'
        else:
            d = angdist(p['lon'], sun); orb = ORB[g][1 if p.get('speed', 1) < 0 else 0]
            dist = f"{d:.1f} deg: {'combust' if f['combust'] else 'not combust'} (limit {orb} deg)"
        rules = ', '.join(map(str, f['rules'])) or 'none'
        role = ', '.join(f['role']) or ('node: acts for its sign lord ' + f['sign_lord'] if g in ('Rahu', 'Ketu') else 'no special role')
        d10 = p['vargas'].get('D10', '')
        d10s = f"{d10} (h{d_house(d10, d10_lagna)}, {DF.sign_dignity(g, SIGNS.index(d10.lower())) if g not in ('Rahu', 'Ketu') else '-'})" if d10 else '-'
        d9 = p['vargas']['D9']
        d9s = f"{d9} (h{d_house(d9, d9_lagna)}, {DF.sign_dignity(g, SIGNS.index(d9.lower())) if g not in ('Rahu', 'Ketu') else '-'}{', vargottama' if f['vargottama'] else ''})"
        out.append(f"| {g} | {f['sign'].title()} {p['deg_in_sign']}, h{f['house']} | {dig}{', retrograde' if f['retro'] else ''} | {dist} | "
                   f"{f['natural']} | rules {rules}; {role} | {d9s} | {d10s} |\n")
    # aspects and conjunctions between planets with their nature
    out.append('\n**Aspects between planets (graha drishti; the aspect takes the aspecting planet\'s natural nature):**\n')
    seen = set()
    for g in GRAHAS:
        for a in F[g]['aspected_by']:
            mutual = g in F[a]['aspected_by']
            key = tuple(sorted([a, g]))
            if mutual and key in seen: continue
            seen.add(key)
            nat = F[a]['natural']
            txt = f"- {a} aspects {g}: {'benefic' if nat == 'benefic' else 'malefic'} aspect ({a}: natural {nat}; rules {', '.join(map(str, F[a]['rules'])) or 'no houses'})"
            if mutual:
                nat2 = F[g]['natural']
                txt = (f"- {a} and {g} aspect each other (mutual): {a}'s aspect is {nat} in nature, {g}'s is {nat2} "
                       f"({a} rules {', '.join(map(str, F[a]['rules'])) or 'no houses'}; {g} rules {', '.join(map(str, F[g]['rules'])) or 'no houses'})")
            n = (F[g]['house'] - F[a]['house']) % 12 + 1
            txt += (f"; {a} sits in house {F[a]['house']} and casts its aspect {n} houses ahead, onto house {F[g]['house']} "
                    + ('(a special aspect, full strength)' if n != 7 else '(the 7th aspect, full strength)'))
            if a in ('Rahu', 'Ketu'): txt += '; node aspects are accepted by some authors only'
            out.append(txt + '\n')
    out.append('Every aspect listed in these verdicts (planets and houses) is a full aspect: the 7th for all, and the special '
               '4th/8th of Mars, 5th/9th of Jupiter and 3rd/10th of Saturn. The fractional strengths (1/4, 1/2, 3/4) in some '
               'texts apply to other house distances, which are not counted here; never call a listed aspect partial.\n')
    conj = []
    for g in GRAHAS:
        for w in F[g]['with']:
            k = tuple(sorted([g, w], key=GRAHAS.index))
            if k not in conj: conj.append(k)
    for a, b in conj:
        d = angdist(P[a]['lon'], P[b]['lon'])
        out.append(f"- {a} and {b} together in {F[a]['sign'].title()} (house {F[a]['house']}), {d:.1f} deg apart\n")
    # houses aspected (for section use)
    # Manglik
    m = chart.get('doshas', {}).get('manglik')
    if isinstance(m, dict):
        hits = [k for k, v in (m.get('hits') or {}).items() if v]
        flags = [k.replace('_', ' ') for k, v in (m.get('cancel_flags') or {}).items() if v]
        mh = m.get('mars_house', {})
        status = 'present' if m.get('is_manglik_any') else 'absent'
        canc = m.get('cancelled_any')
        out.append(f"\n**Manglik (state exactly this):** Mars is in house {mh.get('lagna')} from the lagna, {mh.get('moon')} from the Moon, "
                   f"{mh.get('venus')} from Venus (Manglik houses {', '.join(map(str, m.get('houses_used', [])))}). "
                   f"Counted from: {', '.join(hits) or 'none'} -> Manglik {status} from {len(hits)} of 3 reference points"
                   + (f"; cancelled by the calculator's rules (met: {', '.join(flags)})." if status == 'present' and canc else
                      '; no cancellation met.' if status == 'present' else '.') + '\n')
    # chart shape
    occ = {h: [g for g in GRAHAS if F[g]['house'] == h] for h in range(1, 13)}
    kendra_empty = [h for h in (1, 4, 7, 10) if not occ[h]]
    dus = [g for g in GRAHAS if F[g]['house'] in (6, 8, 12)]
    d9dig = {g: DF.sign_dignity(g, SIGNS.index(P[g]['vargas']['D9'].lower())) for g in GRAHAS[:7]}
    d9ex = [g for g in GRAHAS[:7] if d9dig[g] in ('exalted', 'moolatrikona', 'own')]
    disp = {g: F[g]['sign_lord'] for g in GRAHAS[:7]}
    cycles, finals = [], []
    for g in disp:
        path, x = [], g
        while x not in path:
            path.append(x); x = disp[x]
        cyc = path[path.index(x):]
        c = tuple(sorted(cyc, key=GRAHAS.index))
        if c not in cycles: cycles.append(c)
        finals.append((g, c))
    def _feeds(c):  # planets outside the cycle whose dispositor chain ends in it
        return [g for g, cc in finals if cc == c and g not in c]
    def _chain(c):
        f = _feeds(c)
        if len(c) == 1:
            return (f'{c[0]} in its own sign is the final dispositor of {", ".join(f)}' if f else
                    f'{c[0]} in its own sign disposes only of itself (no other planet has its chain end there; do not call it the final dispositor of the chart)')
        return ' - '.join(c) + ' dispose of each other (a loop)' + (f'; the chains of {", ".join(f)} end in this loop' if f else '')
    chains = '; '.join(_chain(c) for c in cycles)
    occ_s = ', '.join('h%d %s' % (h, '/'.join(occ[h])) for h in (1, 4, 7, 10) if occ[h]) or 'none'
    dus_s = ', '.join('%s h%d' % (g, F[g]['house']) for g in dus)
    d9_s = ', '.join('%s (%s)' % (g, d9dig[g]) for g in d9ex) or 'none'
    vg_s = ', '.join(g for g in GRAHAS if F[g]['vargottama']) or 'none'
    out.append(f"\n**Chart shape:** kendras (1, 4, 7, 10) occupied: {occ_s}; empty kendras: {', '.join(map(str, kendra_empty)) or 'none'}. "
               f"Planets in the dusthanas (6, 8, 12): {len(dus)} ({dus_s}). Strong in D9 (exalted, moolatrikona or own): {d9_s}. "
               f"Vargottama: {vg_s}. Dispositor chains: {chains}.\n")
    # D9 7th house and D10 10th
    d9_occ = {}
    for g in GRAHAS:
        d9_occ.setdefault(d_house(P[g]['vargas']['D9'], d9_lagna), []).append(g)
    s7 = SIGNS[(SIGNS.index(d9_lagna.lower()) + 6) % 12]
    l7 = SIGN_LORD[SIGNS.index(s7)]
    out.append(f"\n**D9 (navamsa):** lagna {d9_lagna}; 7th house {s7.title()}, its lord {l7} in D9 {P[l7]['vargas']['D9']} "
               f"(h{d_house(P[l7]['vargas']['D9'], d9_lagna)}); occupants of the D9 7th: {', '.join(d9_occ.get(7, [])) or 'none'}. "
               f"Venus in D9 {P['Venus']['vargas']['D9']} (h{d_house(P['Venus']['vargas']['D9'], d9_lagna)}).\n")
    if d10_lagna:
        d10_occ = {}
        for g in GRAHAS: d10_occ.setdefault(d_house(P[g]['vargas']['D10'], d10_lagna), []).append(g)
        s10 = SIGNS[(SIGNS.index(d10_lagna.lower()) + 9) % 12]; l10 = SIGN_LORD[SIGNS.index(s10)]
        out.append(f"**D10 (dashamsa):** lagna {d10_lagna}; 10th house {s10.title()}, its lord {l10} in D10 {P[l10]['vargas']['D10']} "
                   f"(h{d_house(P[l10]['vargas']['D10'], d10_lagna)}); occupants of the D10 10th: {', '.join(d10_occ.get(10, [])) or 'none'}; "
                   f"D10 placements: {', '.join('%s h%d' % (g, d_house(P[g]['vargas']['D10'], d10_lagna)) for g in GRAHAS)}. "
                   "D10 depends closely on the birth time; say so when you use it.\n")
    # birth-time sensitivity
    def deg(p):
        return p['lon'] % 30
    lag = chart['lagna']['lon'] % 30
    d9pos = (chart['lagna']['lon'] % (30 / 9)) / (30 / 9)
    d10pos = (chart['lagna']['lon'] % 3) / 3
    out.append(f"**Birth-time sensitivity:** the lagna is at {lag:.1f} deg of its sign (a sign change needs the time off by about "
               f"{min(lag, 30 - lag) * 4:.0f} minutes); within its D9 division at {d9pos*100:.0f}% and its D10 division at {d10pos*100:.0f}% "
               "(near 0% or 100% means the varga lagna can change with a few minutes' error). The Moon moves about 0.5 deg an hour, "
               "so the Moon sign and nakshatra are far less time-sensitive than the lagna and the vargas.\n")
    return ''.join(out), F


SECTION_FOCUS = {  # houses and planets whose sub-periods and double transits matter for each section
    'glance': ([1, 10, 7], []), 'personality': ([1], ['Sun']), 'mind': ([4], ['Moon', 'Mercury']),
    'career': ([10, 6, 11], ['Sun', 'Saturn']), 'finance': ([2, 11, 9, 5], ['Jupiter']), 'health': ([1, 6, 8], ['Sun', 'Moon']),
    'relationships': ([7, 11], ['Venus', 'Jupiter']), 'family': ([4, 5, 3, 9], ['Moon', 'Jupiter', 'Mars']),
    'spirituality': ([8, 12, 9], ['Ketu', 'Jupiter']), 'yogas': ([], []), 'guidance': ([1, 10, 7, 2], []),
}


LIFE = ['personality', 'mind', 'career', 'finance', 'health', 'relationships', 'family', 'spirituality']


def _sub_reasons(F, g, houses, planets):
    """Reasons a sub-lord concerns a section, and a score: natural significator 5, each ruled house 3 (1 for a
    dusthana, which says little about the area by itself), occupied house 2."""
    why, score = [], 0
    rh = [h for h in F[g]['rules'] if h in houses]
    if rh: why.append(f"sub-lord {g} rules {'/'.join(map(str, rh))}"); score += sum(1 if h in (6, 8, 12) else 3 for h in rh)
    if F[g]['house'] in houses: why.append(f"sub-lord {g} sits in {F[g]['house']}"); score += 2
    if g in planets: why.append(f"{g} is a significator here"); score += 5
    return why, score


def period_assignment(chart, F, now, years=12, per_period=2):
    """Each upcoming sub-period goes to the (at most) two life sections it concerns most, judged by the SUB-lord only
    (the period lord is the same for every sub-period of a mahadasha, so it would tie a sub-period to every section).
    Returns {(md, ad): [sections]}."""
    end = DF.add_years(now, years)
    out = {}
    for md, ads in chart['vimshottari'].get('antardashas_by_md', {}).items():
        for a in ads:
            if a['end'] <= now or a['start'] >= end: continue
            sc = []
            for i, sec in enumerate(LIFE):
                why, score = _sub_reasons(F, a['ad'], *SECTION_FOCUS[sec])
                if score: sc.append((-score, i, sec))
            out[(md, a['ad'])] = [x[2] for x in sorted(sc)[:per_period]]
    return out


ROLE_WORDS = {'yogakaraka': 'yogakaraka', 'lagna_lord': 'lagna lord', 'trikona_lord': 'trikona lord',
              'kendra_lord': 'kendra lord', 'dusthana_lord': 'lord of a dusthana (6/8/12)',
              'trishadaya_lord': 'lord of 3/6/11'}


def role_tone(F, g):
    """Plain tone of a sub-lord's period for the dated-periods paragraph (never 'maraka' in visible text)."""
    if g in ('Rahu', 'Ketu'):
        return f"node, acts through its sign lord {F[g]['sign_lord']}; call it active for this area, not supportive by itself"
    r = F[g]['role']
    words = ', '.join(ROLE_WORDS[x] for x in r if x in ROLE_WORDS) or 'no special role'
    if any(x in r for x in ('yogakaraka', 'lagna_lord', 'trikona_lord')):
        return words + ' (supportive)'
    if 'trishadaya_lord' in r or ('dusthana_lord' in r and 'kendra_lord' not in r):
        return words + ' (mixed or demanding; call it active for this area, never the best time)'
    return words + ' (neutral)'


def periods_ahead(chart, F, sec, now, years=12):
    houses, planets = SECTION_FOCUS[sec]
    end = DF.add_years(now, years)
    assign = period_assignment(chart, F, now, years)
    rows = []
    for md, ads in chart['vimshottari'].get('antardashas_by_md', {}).items():
        for a in ads:
            if a['end'] <= now or a['start'] >= end: continue
            g = a['ad']
            if sec in LIFE and sec not in assign.get((md, g), []): continue
            why, _ = _sub_reasons(F, g, houses, planets)
            rh = [h for h in F[md]['rules'] if h in houses]
            if rh: why.append(f"period lord {md} rules {'/'.join(map(str, rh))}")
            why.append('tone: ' + role_tone(F, g))
            rows.append(f"- {md}-{g}: {a['start']} to {a['end']}{' (now)' if a['start'] <= now < a['end'] else ''}: "
                        + ('; '.join(dict.fromkeys(why)) or 'general'))
    out = ['## Periods ahead for this section (dates computed; detail is in the Timeline)\n'
           + ('Each sub-period and window is given to the one or two sections it concerns most, so other sections do not '
              'repeat it. Name at most three of the items below (fewer is fine); never add a period that is not listed '
              'here. If nothing is listed, end with one sentence pointing to the Timeline.\n' if sec in LIFE else
              'Name only the few most important items; the Timeline gives every period.\n')]
    out += [r + '\n' for r in rows] or ['- No sub-period is assigned to this section; point to the Timeline in one sentence.\n']
    win = DF.computed_windows(F, chart, now)
    own = (lambda h: HOUSE_OWNER.get(h) == sec) if sec in LIFE else (lambda h: h in houses)
    dt = [w for w in win['double_transit'] if own(w['house'])]
    if dt:
        out.append('\nDouble transit (Jupiter and Saturn both on the house, from the lagna; a classical timing marker for that house\'s matters; group back-to-back spells into one stretch):\n')
        for w in dt:
            out.append(f"- House {w['house']}: {w['from']} to {w['to']} (Jupiter {w['jupiter']}; Saturn {w['saturn']})\n")
    sat = [w for w in win['saturn_over_natal']
           if (planet_owner(F, chart, w['planet']) == sec if sec in LIFE else (w['natal_house'] in houses or w['planet'] in planets))]
    for w in sat:
        out.append(f"- Saturn over natal {w['planet']} (house {w['natal_house']}): {w['from']} to {w['to']}\n")
    ss = chart.get('doshas', {}).get('sade_sati', {})
    cur = [i for i in ss.get('intervals', []) if i['end'] > now][:3]
    if sec in ('mind', 'guidance') and cur:
        out.append('\nSade Sati / Dhaiya ahead: ' + '; '.join(f"{i['phase']} {i['start']} to {i['end']}" for i in cur) + '\n')
    ch = chart.get('chara_current_and_next') or []
    if sec in ('relationships',) and ch:
        out.append('Chara dasha (dates only; no meanings yet, so name them only as timing markers, or leave them out): '
                   + '; '.join(f"{c['sign']} {c['start']} to {c['end']}" for c in ch) + '\n')
    out.append(f'Data for transits runs to {win["data_until"]}.\n')
    return ''.join(out)


def must_cover(chart, F, sec):
    """Items tied to the lagna, the Moon and the section's houses that the section must at least name (coverage rule)."""
    P = {p['name']: p for p in chart['planets'] if p['name'] in GRAHAS}
    L = chart['lagna']['sign_num'] - 1
    ll = SIGN_LORD[L]
    houses = {h['house']: h for h in chart['houses']}
    nak_lord = lambda nak: DF.NAK_LORD.get(nak)
    lag_nak = chart['lagna']['nakshatra']
    yog = lambda g: [y['name'] for y in chart.get('yogas_present', []) if f'"{g}"' in json.dumps(y.get('conditions'))]
    items = []
    if sec in ('personality', 'glance'):
        items += [f"rising sign {chart['lagna']['sign']}", f"lagna nakshatra {lag_nak}" + (f" and its lord {nak_lord(lag_nak)} (in house {F[nak_lord(lag_nak)]['house']})" if nak_lord(lag_nak) else ''),
                  f"lagna lord {ll} in house {F[ll]['house']} ({F[ll]['dignity']})" + (f"; it forms {', '.join(yog(ll))}" if yog(ll) else ''),
                  'planets aspecting the lagna: ' + (', '.join(houses[1]['aspected_by']) or 'none'),
                  'vargottama planets: ' + (', '.join(g for g in GRAHAS if F[g]['vargottama']) or 'none'),
                  f"the Sun in {F['Sun']['sign'].title()}, house {F['Sun']['house']}" + (f", with {', '.join(F['Sun']['with'])}" if F['Sun']['with'] else '')]
        if sec == 'personality':
            pc = chart.get('panchang_at_birth', {})
            items.append(f"birth weekday {pc.get('vara')} and tithi {pc.get('paksha')} {pc.get('tithi')} (one short paragraph)")
    if sec in ('mind',):
        m = F['Moon']
        items += [f"Moon in {m['sign'].title()}, house {m['house']}, nakshatra {m['nakshatra']} (its lord {m['nak_lord']} in house {F[m['nak_lord']]['house']})",
                  'aspects on the Moon: ' + (', '.join(m['aspected_by']) or 'none'),
                  f"the Moon's dispositor {m['sign_lord']} in house {F[m['sign_lord']]['house']}", f"Moon in D9 {P['Moon']['vargas']['D9']}",
                  f"Mercury in {F['Mercury']['sign'].title()}, house {F['Mercury']['house']} (thinking style)"]
    if sec == 'career':
        l10 = houses[10]['lord']
        items += [f"10th lord {l10} in house {F[l10]['house']}", 'planets in the 10th: ' + (', '.join(houses[10]['occupants']) or 'none'),
                  'aspects on the 10th: ' + (', '.join(houses[10]['aspected_by']) or 'none'),
                  'the Amatyakaraka: ' + next((g for g in F if F[g].get('karaka') == 'Amatyakaraka'), '-'),
                  'the D10 10th house and lord (from the verdicts, with the birth-time caution)', 'yogakaraka: ' + (', '.join(g for g in F if 'yogakaraka' in F[g]['role']) or 'none')]
    if sec == 'relationships':
        l7 = houses[7]['lord']
        items += [f"7th lord {l7} in house {F[l7]['house']}", 'planets in the 7th: ' + (', '.join(houses[7]['occupants']) or 'none'),
                  'aspects on the 7th: ' + (', '.join(houses[7]['aspected_by']) or 'none'), f"Venus in house {F['Venus']['house']}",
                  'the Darakaraka: ' + next((g for g in F if F[g].get('karaka') == 'Darakaraka'), '-'),
                  'the D9 7th house and its lord (from the verdicts)', 'Manglik status exactly as in the verdicts, including the cancellation',
                  'the dated windows for the 7th from "Periods ahead"']
    if sec == 'finance':
        for h in (2, 11, 5, 9):
            items.append(f"house {h}: lord {houses[h]['lord']} in house {houses[h]['lord_in_house']}; occupants {', '.join(houses[h]['occupants']) or 'none'}")
        items.append(f"12th house (expenses): lord {houses[12]['lord']} in house {houses[12]['lord_in_house']}")
    if sec == 'family':
        for h, lab in ((2, 'family of origin'), (4, 'mother, home'), (9, 'father'), (3, 'siblings'), (5, 'children'), (4, 'education')):
            items.append(f"{lab}: house {h}, lord {houses[h]['lord']} in house {houses[h]['lord_in_house']}")
    if sec == 'spirituality':
        for h in (8, 9, 12):
            items.append(f"house {h}: lord {houses[h]['lord']} in house {houses[h]['lord_in_house']}; occupants {', '.join(houses[h]['occupants']) or 'none'}")
        items.append(f"Ketu in house {F['Ketu']['house']}; Rahu in house {F['Rahu']['house']} (foreign links only where entries mention them)")
    if sec == 'health':
        items.append(f"lagna lord {ll} in house {F[ll]['house']} ({F[ll]['dignity']}) and planets aspecting the lagna: {', '.join(houses[1]['aspected_by']) or 'none'}")
        items.append(f"the Sun in house {F['Sun']['house']} and the Moon in house {F['Moon']['house']} (vitality and mind)")
        for h in (6, 8, 12):
            items.append(f"house {h}: lord {houses[h]['lord']} in house {houses[h]['lord_in_house']}; occupants {', '.join(houses[h]['occupants']) or 'none'}")
    if sec == 'glance':
        items.append('chart shape from the verdicts: empty kendras, planets in dusthanas, strength in D9, dispositor chains')
        items.append('birth-time sensitivity exactly as in the verdicts (the lagna and vargas are the time-sensitive parts, not the Moon)')
    if not items: return ''
    return '## Must cover (name each at least briefly, even if another section explains it in full)\n' + ''.join(f'- {x}\n' for x in items)


def ownership_note(sec):
    rows = []
    for h, s in sorted(HOUSE_OWNER.items()):
        rows.append(f'{h}->{SECTION_TITLE[s]}')
    return ('## Ownership (to avoid repeating points across sections)\n'
            'Each recurring point is explained in full in one section only. Entries below marked "(explained in X)" belong to '
            'another section: use them here in one clause at most, and only for what they say about this section\'s area '
            '(the "For this section" line). Do not re-describe the planet\'s sign or house character. Owners: Moon and Mercury '
            '-> Mind; the Sun and the lagna lord -> Personality; other planets -> the section of the house they occupy; house '
            'matters by house: ' + ', '.join(rows) + '; yogas and doshas -> Yogas and doshas (Manglik -> Relationships).\n')


def ownership_map(chart, F):
    """Markdown map for the editor pass: which section owns each recurring point."""
    t = SECTION_TITLE
    lines = ['# Ownership map (for the editor pass)', '',
             'Each point is told in full by its owner. The Chart at a glance may name it in one short clause; the Timeline is not edited.', '',
             '| Point | Owner section |', '|---|---|']
    for g in GRAHAS:
        lines.append(f"| {g}: sign, house, dignity, cancellation, combustion, D9/D10 placement, character | {t[planet_owner(F, chart, g)]} |")
    for h in range(1, 13):
        lines.append(f"| House {h} and its lord's placement | {t[HOUSE_OWNER[h]]} |")
    lines += ['| Every yoga (meaning, strength, caveats, author quotes) and every dosha except Manglik | Yogas and doshas |',
              '| Manglik status and its cancellation | Relationships |',
              '| Birth-time sensitivity | Chart at a glance |',
              '| Chara karakas (Atmakaraka etc.): definition | the first section that defines it |',
              '| Terms (yogakaraka, combustion, vargottama, neecha bhanga, double transit): definition | the first section that defines it |',
              '| A dated sub-period or window | the section(s) whose "When this area is most active" paragraph names it, plus the Timeline |']
    return '\n'.join(lines) + '\n'
