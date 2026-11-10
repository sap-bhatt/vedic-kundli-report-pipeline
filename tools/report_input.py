"""Build the per-section inputs for the long kundli report (kundli-report skill), one compact Markdown file per section.

  python -I tools/report_input.py --chart chart_data.json --outdir report_inputs/

Writes <outdir>/<section>.md for every section in SECTIONS (the timeline input comes from tools/dasha_facts.py), plus
<outdir>/facts.json (shared chart facts) and <outdir>/selection.json (which entry ids each section received, for graders).
Each section input holds: the chart facts for its houses, the library entries that apply (trimmed to that section's
life area where the entry has a by_area field), checked conditions where entries carry them, and the rules for what the
section may say. Missing layers are reported in the file, never filled in.
"""
import argparse, json, os, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import dasha_facts as DF
import chart_verdicts as CV
try:
    import table_rows as TR  # v0.15 model-row tables: tells writers which hidden rows to fill
except ImportError:
    TR = None

GRAHAS = ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn', 'Rahu', 'Ketu']
ASP = {'Mars': [4, 7, 8], 'Jupiter': [5, 7, 9], 'Saturn': [3, 7, 10], 'Rahu': [5, 7, 9], 'Ketu': [5, 7, 9]}

# section -> houses, by_area key, planets of special interest, karaka roles, extra layers
SECTIONS = {
    'glance':        {'houses': [1], 'area': 'personality', 'planets': [], 'karakas': ['atmakaraka'], 'title': 'Chart at a glance'},
    'personality':   {'houses': [1], 'area': 'personality', 'planets': ['Sun'], 'karakas': ['atmakaraka'], 'title': 'Personality and temperament'},
    'mind':          {'houses': [4], 'area': 'personality', 'planets': ['Moon', 'Mercury'], 'karakas': [], 'title': 'Mind, emotions and inner life'},
    'career':        {'houses': [10, 6, 2, 11], 'area': 'career', 'planets': ['Sun', 'Saturn'], 'karakas': ['amatyakaraka'], 'title': 'Career and vocation'},
    'finance':       {'houses': [2, 11, 5, 9], 'area': 'finance', 'planets': ['Jupiter'], 'karakas': [], 'title': 'Finance and wealth'},
    'health':        {'houses': [1, 6, 8, 12], 'area': 'health', 'planets': ['Sun', 'Moon'], 'karakas': [], 'title': 'Health and vitality'},
    'relationships': {'houses': [7, 11], 'area': 'relationships', 'planets': ['Venus', 'Jupiter'], 'karakas': ['darakaraka'], 'title': 'Relationships, marriage and partner'},
    'family':        {'houses': [2, 3, 4, 5, 9], 'area': 'family', 'planets': ['Moon', 'Sun', 'Jupiter', 'Mars'],
                      'karakas': ['matrikaraka', 'putrakaraka', 'bhratrikaraka'], 'title': 'Family, home, siblings, children and education'},
    'spirituality':  {'houses': [8, 12, 9], 'area': 'spirituality', 'planets': ['Ketu', 'Jupiter'], 'karakas': ['atmakaraka'], 'title': 'Spirituality, the 8th and 12th houses, hidden talents and foreign links'},
    'yogas':         {'houses': [], 'area': None, 'planets': [], 'karakas': [], 'title': 'Yogas and doshas'},
    'guidance':      {'houses': [1], 'area': None, 'planets': [], 'karakas': [], 'title': 'Strengths, challenges, guidance and optional remedies'},
}
YOGA_SECTIONS = {  # which sections a present yoga is also mentioned in
    'raja_kendra_trikona': ['career'], 'yogakaraka': ['career'], 'dharma_karmadhipati': ['career'], 'dhana': ['finance'],
    'lakshmi': ['finance'], 'vasumati': ['finance'], 'saraswati': ['mind', 'family'], 'budhaditya': ['mind', 'career'],
    'gajakesari': ['mind', 'finance'], 'chandra_mangala': ['finance'], 'adhi': ['career'], 'amala': ['career'],
    'sunapha': ['mind', 'finance'], 'anapha': ['mind', 'personality'], 'durudhara': ['mind', 'finance'], 'kemadruma': ['mind'],
    'shakata': ['finance', 'mind'], 'viparita_harsha': ['health'], 'viparita_sarala': ['health', 'spirituality'],
    'viparita_vimala': ['finance', 'spirituality'], 'neecha_bhanga': ['career', 'personality'], 'parivartana': ['personality'],
    'ruchaka': ['personality', 'career'], 'bhadra': ['personality', 'career'], 'hamsa': ['personality', 'spirituality'],
    'malavya': ['personality', 'relationships'], 'sasa': ['personality', 'career'], 'grahan': ['personality', 'health'],
    'shubha_kartari': ['personality'], 'papa_kartari': ['personality', 'health'],
}
DOSHA_SECTIONS = {'manglik': ['relationships'], 'kaal_sarp': [], 'pitra': ['family'], 'guru_chandal': [], 'shrapit': [],
                  'angarak': [], 'ghata': [], 'ganda_moola': ['personality']}
ROWS_TABLE = {'finance': 'wealth_houses', 'health': 'body_correspondences', 'guidance': 'remedies'}  # timeline: timeline_rows.md
ENTRY_FIELDS = ['summary', 'common_outcomes', 'rare_outcomes', 'strengtheners', 'weakeners_or_cancellations', 'disagreements',
                'phrasing_guidance']


def slug(s):
    return s.lower().replace(' ', '_').replace('-', '_')


def entry_block(e, area, ctx='', owner=None):
    """One library entry as compact Markdown (v0.16 diet: an entry owned by another section gets only its "For this
    section" line, or its first sentences when it has none; generic varga (divisional-chart) notes get summary, results
    and phrasing; disagreements are cut at a sentence boundary near 450 characters)."""
    if not e: return None
    ba = (e.get('by_area') or {})
    if owner:  # the ownership note: use only the "For this section" line; the summary only when there is none
        if area and ba.get(area):
            return (f"- `{e['id']}` (explained in {CV.SECTION_TITLE[owner]}){' - ' + ctx if ctx else ''}\n"
                    f"  - For this section ({area}): {ba[area]}")
        return f"- `{e['id']}` (explained in {CV.SECTION_TITLE[owner]}){' - ' + ctx if ctx else ''}: {DF._first_sentences(e.get('summary'), 220, '')}"
    generic = e['id'].startswith('varga/')
    lines = [f"- `{e['id']}` ({e.get('confidence')}, {e.get('quality')}){' - ' + ctx if ctx else ''}: {e.get('summary', '')}"]
    if area and ba.get(area):
        lines.append(f"  - For this section ({area}): {ba[area]}")
    elif not area:
        oc = [x for x in (e.get('common_outcomes') or []) if x][:3 if generic else 4]
        if oc: lines.append('  - Results: ' + '; '.join(oc))
    if area and not ba.get(area):
        oc = [x for x in (e.get('common_outcomes') or []) if x][:3]
        if oc: lines.append('  - General results (not specific to this area; use only what fits): ' + '; '.join(oc))
    if not generic:
        for k, lab in (('strengtheners', 'Strengthened by'), ('weakeners_or_cancellations', 'Weakened by')):
            v = [x for x in (e.get(k) or []) if x][:3]
            if v: lines.append(f'  - {lab}: ' + '; '.join(v))
        if e.get('disagreements') and e['disagreements'] not in ('None.', 'None', ''):
            lines.append(f"  - Disagreements: {DF._first_sentences(e['disagreements'][:1500], 450)}")
    if e.get('phrasing_guidance'): lines.append(f"  - Tone guide for you (follow it, never copy its words): {e['phrasing_guidance']}")
    return '\n'.join(lines)


def build(chart, lib, now):
    verdict_txt, _ = CV.verdicts(chart, now)
    F = DF.planet_facts(chart)
    for g in F:
        F[g]['in_yogas'] = [y['name'] for y in chart.get('yogas_present', []) if f'"{g}"' in json.dumps(y.get('conditions'))]
    L = chart['lagna']['sign_num'] - 1
    houses = {h['house']: h for h in chart['houses']}
    P = {p['name']: p for p in chart['planets'] if p['name'] in GRAHAS}
    lagna_nak = chart['lagna']['nakshatra']; moon_nak = P['Moon']['nakshatra']
    karaka_of = {F[g]['karaka'].lower(): g for g in F if F[g].get('karaka')}
    md, ad = DF.dasha_at(chart, now)
    _m = next((m for m in chart['vimshottari']['mahadashas'] if m['md'] == md and m['start'] <= now < m['end']), None)
    md_span = f"{_m['start']} to {_m['end']}" if _m else '?'
    _a = next((a for a in chart['vimshottari'].get('antardashas_by_md', {}).get(md, []) if a['ad'] == ad and a['start'] <= now < a['end']), None)
    ad_span = f"{_a['start']} to {_a['end']}" if _a else '?'
    present_yogas = [(DF.yoga_slug(y['name']), y) for y in chart.get('yogas_present', [])]
    doshas = chart.get('doshas', {})
    row_keys = TR.row_keys(chart, F, now, lib) if TR else {}
    out, selection = {}, {}
    for sec, cfg in SECTIONS.items():
        ids, parts = [], []
        area = cfg['area']

        def add(eid, ctx=''):
            e = lib.get(eid)
            if eid in ids: return
            own = CV.entry_owner(eid, F, chart)
            b = entry_block(e, area, ctx, own if own and own != sec and sec != 'yogas' else None)
            if b:
                ids.append(eid); parts.append(b)
            else:
                parts.append(f'- `{eid}`: no library entry yet ({ctx}); do not interpret it.')

        # facts for the section's houses
        fact_lines = []
        for h in cfg['houses']:
            x = houses[h]
            fact_lines.append(f"- House {h}: {x['sign']}, lord {x['lord']} in house {x['lord_in_house']} ({x['lord_in_sign']}, "
                              f"{x['lord_dignity']}); occupants: {', '.join(x['occupants']) or 'none'}; aspected by: {', '.join(x['aspected_by']) or 'none'}")
        planets = []
        for h in cfg['houses']:
            planets += [o for o in houses[h]['occupants'] if o in GRAHAS]
            planets.append(houses[h]['lord'])
        planets += cfg['planets'] + [karaka_of[k] for k in cfg['karakas'] if k in karaka_of]
        planets = list(dict.fromkeys(planets))
        if sec in ('glance', 'yogas', 'guidance'):
            planets = GRAHAS[:]
        for g in planets:
            fact_lines.append(f"- {g}: {DF._lord_line(DF.lord_summary(F, g))}")
        # placement entries
        for h in cfg['houses']:
            for o in houses[h]['occupants']:
                if o in GRAHAS: add(f'planet_in_house/{o.lower()}/{h}', f'{o} occupies house {h}')
            lord = houses[h]['lord']
            add(f"lord_in_house/{h}/{houses[h]['lord_in_house']}", f"{h}th lord {lord} in house {houses[h]['lord_in_house']}")
        for g in planets:
            if sec in ('yogas',): break
            add(f"planet_in_sign/{g.lower()}/{F[g]['sign']}", f'{g} in {F[g]["sign"].title()}')
            if sec not in ('glance', 'guidance'):
                add(f"planet_in_house/{g.lower()}/{F[g]['house']}", f'{g} in house {F[g]["house"]}')
        # aspects on the section's houses, conjunctions in them
        for h in cfg['houses']:
            for a in houses[h]['aspected_by']:
                if a in GRAHAS: add(f'aspect/{a.lower()}/{h}', f'{a} aspects house {h}')
            occ = [o for o in houses[h]['occupants'] if o in GRAHAS]
            for i, a in enumerate(occ):
                for b in occ[i + 1:]:
                    pa, pb = sorted([a, b], key=GRAHAS.index)
                    add(f'conjunction/{pa.lower()}_{pb.lower()}', f'{pa} with {pb} in house {h}')
        # nakshatra, rising sign, karakas, vargas
        if sec in ('glance', 'personality'):
            add(f"rising_sign/{chart['lagna']['sign'].lower()}", 'rising sign')
            add(f'nakshatra/{slug(lagna_nak)}', f'lagna nakshatra {lagna_nak}: use its as_lagna notes')
        if sec in ('glance', 'personality', 'mind'):
            add(f'nakshatra/{slug(moon_nak)}', f'Moon nakshatra {moon_nak}: use its as_moon notes')
        if sec == 'personality':  # birth panchang and avakhada (minor factors; one short subsection at most)
            pc, av = chart.get('panchang_at_birth', {}), chart.get('avakhada', {})
            if pc.get('tithi_num'):
                n = pc['tithi_num'] + (15 if str(pc.get('paksha', '')).lower().startswith('krishna') and pc['tithi_num'] <= 15 else 0)
                add(f'panchang/tithi/{n}', f"birth tithi {pc.get('paksha')} {pc.get('tithi')}")
            if pc.get('vara'): add(f"panchang/vara/{pc['vara'].lower()}", f"born on {pc['vara']}")
            if pc.get('nitya_yoga'): add(f"panchang/nitya_yoga/{slug(pc['nitya_yoga'])}", f"nitya yoga {pc['nitya_yoga']}")
            if pc.get('karana'): add(f"panchang/karana/{slug(pc['karana'])}", f"karana {pc['karana']}")
            if av.get('gana'): add(f"panchang/gana/{slug(av['gana'])}", f"gana {av['gana']}")
            if av.get('nadi'): add(f"panchang/nadi/{slug(av['nadi'])}", f"nadi {av['nadi']}")
        for k in cfg['karakas']:
            if k in karaka_of: add(f'karaka/{k}', f'{karaka_of[k]} is the {k.title()}')
        if sec == 'spirituality' and 'atmakaraka' in karaka_of:
            ak = karaka_of['atmakaraka']; add(f"karaka/karakamsha_{F[ak]['d9_sign']}", f"karakamsha (AK {ak} in D9 {F[ak]['d9_sign'].title()})")
        if sec in ('relationships', 'glance'):
            for e in [v for k, v in lib.items() if k.startswith('varga/') and 'navamsa' in v.get('file', '')][:12]:
                ids.append(e['id']); parts.append(entry_block(e, None))
        if sec == 'career':
            for e in [v for k, v in lib.items() if k.startswith('varga/') and 'dashamsa' in v.get('file', '')][:10]:
                ids.append(e['id']); parts.append(entry_block(e, None))
            # Phaladeepika 5 / Brihat Jataka 10: lord of the navamsa sign held by the 10th lord (from lagna, Moon, Sun)
            add('profession/rule', 'the navamsa-lord rule for livelihood (the three indicators below)')
            for ref, s0 in (('lagna', chart['lagna']['sign_num'] - 1), ('Moon', DF.SIGNS.index(F['Moon']['sign'])),
                            ('Sun', DF.SIGNS.index(F['Sun']['sign']))):
                l10 = DF.SIGN_LORD[(s0 + 9) % 12]
                ind = DF.SIGN_LORD[DF.SIGNS.index(F[l10]['d9_sign'])]
                add(f'profession/{ind.lower()}', f"10th from the {ref}: lord {l10}, in navamsa {F[l10]['d9_sign'].title()}, whose lord {ind} is the indicator")
        # yogas and doshas
        for ys, y in present_yogas:
            if not ys: continue
            if sec == 'yogas' or sec in YOGA_SECTIONS.get(ys, []):
                add(f'yoga/{ys}', f"present: {y['name']} ({DF._flat(y.get('conditions'))})")
        for dname, d in doshas.items():
            if dname == 'sade_sati' or d is False or d is None: continue
            if d is True: d = {'present': True, 'note': 'flag only; no reference points or cancellations computed'}
            if sec == 'yogas' or sec in DOSHA_SECTIONS.get(dname, []):
                verdict = ''
                if dname == 'kaal_sarp' and isinstance(d, dict):
                    modes = [v for v in d.values() if isinstance(v, dict)]
                    full = any(v.get('degree_full') or v.get('sign_mode_full') for v in modes)
                    part = any(v.get('degree_partial_one_out') for v in modes)
                    outs = next((v.get('outside_planets') for v in modes if v.get('outside_planets')), [])
                    verdict = ('VERDICT: present (full form). ' if full else 'VERDICT: present only in the partial form (one planet outside). ' if part else
                               f"VERDICT: NOT present, neither full nor partial ({len(outs)} planets outside the Rahu-Ketu axis: {', '.join(outs)}). "
                               "The type name in the data (e.g. Kulik) only labels which form it would be from Rahu's house; never present it as a partial form. ")
                add(f'dosha/{dname}', verdict + f"calculator: {DF._flat(d)}")
        if sec == 'guidance':
            weak = [g for g in GRAHAS if F[g]['dignity'] in ('debilitated', 'enemy') or F[g]['house'] in (6, 8, 12) or F[g]['combust']]
            for g in weak: add(f'remedy/{g.lower()}', f'{g}: {F[g]["dignity"]}, house {F[g]["house"]}')
        head = [f"# {cfg['title']}: section input\n",
                f"Lagna {chart['lagna']['sign']} {chart['lagna']['deg_in_sign']} ({lagna_nak}); Moon {P['Moon']['sign']} in {moon_nak}; "
                f"running dasha {md}-{ad} (as of {now}): {md} mahadasha {md_span}; {ad} sub-period {ad_span}. "
                "Never give the sub-period's end as the end of the mahadasha.\n"
                + ({'female': "The native is a woman: call the spouse 'husband' or 'partner', never 'wife'.\n",
                    'male': "The native is a man: call the spouse 'wife' or 'partner', never 'husband'.\n"}
                   .get(str(chart['birth'].get('sex', '')).lower(), "Call the spouse 'partner'.\n")) + '\n', verdict_txt, '\n', CV.ownership_note(sec), '\n',
                CV.periods_ahead(chart, F, sec, now) if sec not in ('yogas', 'glance') else '', '\n', CV.must_cover(chart, F, sec),
                '\n## Chart facts for this section\n', '\n'.join(fact_lines), '\n\n## Library entries that apply\n', '\n'.join(parts), '\n']
        if TR and sec in ROWS_TABLE:
            head.append('\n' + TR.rows_prompt(ROWS_TABLE[sec], row_keys[ROWS_TABLE[sec]]))
        out[sec] = ''.join(head); selection[sec] = sorted(set(ids))
    facts = {'lagna': chart['lagna'], 'planets': {g: DF.lord_summary(F, g) for g in F}, 'houses': chart['houses'],
             'yogas_present': [y['name'] for y in chart.get('yogas_present', [])], 'running_dasha': f'{md}-{ad}'}
    return out, selection, facts


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--chart', required=True); ap.add_argument('--outdir', required=True)
    ap.add_argument('--now')
    a = ap.parse_args()
    chart = json.load(open(a.chart, encoding='utf-8'))
    tr_key = next((k for k in chart if k.startswith('transits_')), None)
    now = a.now or (tr_key[len('transits_'):].replace('_', '-') if tr_key else __import__('datetime').date.today().isoformat())
    lib = json.load(open(os.path.join(ROOT, 'library.json'), encoding='utf-8'))
    out, selection, facts = build(chart, lib, now)
    os.makedirs(a.outdir, exist_ok=True)
    for sec, txt in out.items():
        txt = DF.soften_health(txt)  # neutral words for classical health lists (see dasha_facts.soften_health)
        open(os.path.join(a.outdir, f'{sec}.md'), 'w', encoding='utf-8').write(txt)
        missing = txt.count('no library entry yet')
        print(f'{sec:14s} {len(txt)//4:6d} tokens, {len(selection[sec]):3d} entries, {missing} missing')
    if TR:  # the Timeline input comes from dasha_facts.py; its rows block to fill is written here
        _F = DF.planet_facts(chart)
        open(os.path.join(a.outdir, 'timeline_rows.md'), 'w', encoding='utf-8').write(
            '# Timeline: table rows to fill\n\n' + TR.rows_prompt('summary_10y', TR.row_keys(chart, _F, now, lib)['summary_10y']))
        print('timeline_rows.md written')
    open(os.path.join(a.outdir, 'ownership_map.md'), 'w', encoding='utf-8').write(CV.ownership_map(chart, DF.planet_facts(chart)))
    json.dump(selection, open(os.path.join(a.outdir, 'selection.json'), 'w', encoding='utf-8'), indent=1)
    json.dump(facts, open(os.path.join(a.outdir, 'facts.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
