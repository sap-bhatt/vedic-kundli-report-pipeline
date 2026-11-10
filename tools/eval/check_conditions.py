"""Evaluate every checkable condition in the dasha/timing layers against one or more charts and report errors.

  python -I tools/eval/check_conditions.py chart_data.json [chart_data2.json ...]

For each chart, every dasha_md entry is checked with the mahadasha env, every dasha_ad entry with the md+ad env, and every
transit / sade_sati / yogini entry with a timing env. An `error:` status means the condition uses an unknown fact or bad
syntax; fix the entry (or add the fact to dasha_facts.py and the vocabulary in docs/LIBRARY.md).
"""
import json, os, sys, collections
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import dasha_facts as DF

lib = json.load(open(os.path.join(ROOT, 'library.json'), encoding='utf-8'))
for path in sys.argv[1:]:
    chart = json.load(open(path, encoding='utf-8'))
    F = DF.planet_facts(chart)
    waxing = str(chart.get('panchang_at_birth', {}).get('paksha', '')).lower().startswith('shukla')
    stats = collections.Counter(); errors = collections.defaultdict(set)
    for eid, e in lib.items():
        layer = e.get('layer')
        envs = []
        if layer == 'dasha_md':
            envs = [DF.env_for(F, e['key']['md'], None, waxing)]
        elif layer == 'dasha_ad':
            envs = [DF.env_for(F, e['key']['md'], e['key']['ad'], waxing)]
        elif layer == 'dasha_principle':
            envs = [DF.env_for(F, 'Rahu', None, waxing), DF.env_for(F, 'Saturn', 'Venus', waxing)]
        elif layer in ('transit', 'sade_sati'):
            planet = e['key'].get('planet', 'Saturn')
            h = e['key'].get('house_from_moon') or {'rising': 12, 'peak': 1, 'setting': 2, 'kantaka_dhaiya': 4, 'ashtama_dhaiya': 8}[e['key']['phase']]
            sign = (F['Moon']['_sign_num'] + h - 1) % 12
            envs = [DF.timing_env(F, chart, planet, sign, chart['birth']['date'][:4] + '-06-01', waxing, vedha=[3, 5])[0]]
        elif layer == 'yogini':
            env = DF.env_for(F, 'Rahu', 'Saturn', waxing)
            for k, v in F[e['key']['planet']].items():
                if not k.startswith('_'): env[f'yl_{k}'] = v
            envs = [env]
        for env in envs:
            for c in e.get('conditional_results') or []:
                st = DF.evaluate(c.get('when'), env)
                stats[st.split(':')[0]] += 1
                if st.startswith('error'): errors[eid].add(f"{c.get('when')} -> {st}")
    print(os.path.basename(os.path.dirname(path)) or path, dict(stats))
    for eid, es in sorted(errors.items()):
        for x in sorted(es): print('  ERROR', eid, '|', x)
