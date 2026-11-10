"""Build the Astro Library: validate every layer file, assemble library.json (id -> entry),
index.json (coverage + quality), and readable Markdown under md/.

Run: python -I tools/build_library.py            (from anywhere; paths are relative to this file)
Re-run after any layer file changes. Output files are generated - edit the layer JSON, not these.
"""
import json, glob, os, sys, collections, datetime as D
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAYERS = ['planet_in_house', 'planet_in_sign', 'lord_in_house', 'dasha_principle', 'dasha_md', 'dasha_ad', 'transit', 'sade_sati', 'yogini', 'yoga', 'dosha', 'nakshatra', 'rising_sign', 'karaka', 'varga', 'aspect', 'conjunction', 'panchang', 'remedy', 'profession']
NAKSHATRA_SLUGS = ['ashwini', 'bharani', 'krittika', 'rohini', 'mrigashira', 'ardra', 'punarvasu', 'pushya', 'ashlesha', 'magha',
                   'purva_phalguni', 'uttara_phalguni', 'hasta', 'chitra', 'swati', 'vishakha', 'anuradha', 'jyeshtha', 'mula',
                   'purva_ashadha', 'uttara_ashadha', 'shravana', 'dhanishta', 'shatabhisha', 'purva_bhadrapada', 'uttara_bhadrapada', 'revati']
YOGA_SLUGS = ['ruchaka', 'bhadra', 'hamsa', 'malavya', 'sasa', 'gajakesari', 'budhaditya', 'chandra_mangala', 'adhi', 'amala',
              'raja_kendra_trikona', 'yogakaraka', 'dharma_karmadhipati', 'parivartana', 'dhana', 'lakshmi', 'saraswati', 'vasumati',
              'viparita_harsha', 'viparita_sarala', 'viparita_vimala', 'neecha_bhanga',
              'sunapha', 'anapha', 'durudhara', 'kemadruma', 'shakata', 'shubha_kartari', 'papa_kartari', 'grahan']
DOSHA_SLUGS = ['manglik', 'kaal_sarp', 'pitra', 'guru_chandal', 'shrapit', 'angarak', 'ghata', 'ganda_moola']
DASHA_ORDER = ['ketu', 'venus', 'sun', 'moon', 'mars', 'rahu', 'jupiter', 'saturn', 'mercury']
FIELDS = ['id', 'layer', 'key', 'summary', 'themes', 'common_outcomes', 'rare_outcomes', 'by_area', 'strengtheners',
          'weakeners_or_cancellations', 'lagna_or_context_notes', 'source_views', 'disagreements', 'confidence', 'phrasing_guidance']
PLANETS = ['sun', 'moon', 'mars', 'mercury', 'jupiter', 'venus', 'saturn', 'rahu', 'ketu']
SIGNS = ['aries', 'taurus', 'gemini', 'cancer', 'leo', 'virgo', 'libra', 'scorpio', 'sagittarius', 'capricorn', 'aquarius', 'pisces']
# Files whose content is a known draft; quality "draft" until replaced.
DRAFT_FILES = set()  # e.g. {'planet_in_house/saturn.json'}; filled from QUALITY below
QUALITY_PATH = os.path.join(ROOT, 'quality.json')


def expected_ids(layer):
    if layer == 'planet_in_house':
        return [f'{layer}/{p}/{h}' for p in PLANETS for h in range(1, 13)]
    if layer == 'planet_in_sign':
        return [f'{layer}/{p}/{s}' for p in PLANETS for s in SIGNS]
    if layer == 'dasha_principle':
        return None  # open-ended rule list
    if layer == 'dasha_md':
        return [f'{layer}/{p}' for p in PLANETS]
    if layer == 'nakshatra':
        return [f'nakshatra/{x}' for x in NAKSHATRA_SLUGS]
    if layer == 'rising_sign':
        return [f'rising_sign/{x}' for x in SIGNS]
    if layer == 'karaka':
        return [f'karaka/{x}' for x in ('atmakaraka', 'amatyakaraka', 'bhratrikaraka', 'matrikaraka', 'putrakaraka', 'gnatikaraka',
                                       'darakaraka')] + [f'karaka/karakamsha_{x}' for x in SIGNS]
    if layer == 'aspect':
        return [f'aspect/{p}/{h}' for p in PLANETS for h in range(1, 13)]
    if layer == 'conjunction':
        return [f'conjunction/{a}_{b}' for i, a in enumerate(PLANETS) for b in PLANETS[i + 1:]]
    if layer == 'remedy':
        return [f'remedy/{p}' for p in PLANETS]
    if layer == 'profession':
        return ['profession/rule'] + [f'profession/{p}' for p in PLANETS[:7]]  # nodes own no navamsa sign: never the indicator
    if layer in ('varga', 'panchang'):
        return None
    if layer == 'yoga':
        return [f'yoga/{x}' for x in YOGA_SLUGS]
    if layer == 'dosha':
        return [f'dosha/{x}' for x in DOSHA_SLUGS]
    if layer == 'transit':
        return [f'{layer}/{p}/{h}' for p in ('saturn', 'jupiter') for h in range(1, 13)]
    if layer == 'sade_sati':
        return [f'{layer}/{x}' for x in ('rising', 'peak', 'setting', 'kantaka_dhaiya', 'ashtama_dhaiya')]
    if layer == 'yogini':
        return [f'{layer}/{x}' for x in ('mangala', 'pingala', 'dhanya', 'bhramari', 'bhadrika', 'ulka', 'siddha', 'sankata')]
    if layer == 'dasha_ad':
        return [f'{layer}/{m}/{DASHA_ORDER[(DASHA_ORDER.index(m) + k) % 9]}' for m in DASHA_ORDER for k in range(9)]
    return [f'{layer}/{n}/{m}' for n in range(1, 13) for m in range(1, 13)]


def main():
    quality = json.load(open(QUALITY_PATH, encoding='utf-8')) if os.path.exists(QUALITY_PATH) else {}
    lib, problems, files = {}, [], {}
    for layer in LAYERS:
        for f in sorted(glob.glob(os.path.join(ROOT, layer, '*.json'))):
            rel = f'{layer}/{os.path.basename(f)}'
            try:
                entries = json.load(open(f, encoding='utf-8'))
            except Exception as e:
                problems.append(f'{rel}: invalid JSON ({e})'); continue
            q = quality.get(rel, {'status': 'unreviewed'})
            files[rel] = {'entries': len(entries), **q}
            for e in entries:
                miss = [k for k in FIELDS if k not in e]
                if miss: problems.append(f"{e.get('id', rel)}: missing {miss}")
                eid = str(e.get('id', '')).lower()
                if eid in lib: problems.append(f'{eid}: duplicate')
                e['id'] = eid
                conf = str(e.get('confidence', '')).strip().split()
                e['confidence'] = conf[0].lower().strip('.,;:') if conf else ''
                e['quality'] = q.get('status', 'unreviewed')
                e['file'] = rel
                lib[eid] = e
    coverage = {}
    for layer in LAYERS:
        exp = expected_ids(layer)
        if exp is None:
            exp = sorted(i for i in lib if i.startswith(layer + '/'))
        have = [i for i in exp if i in lib]
        coverage[layer] = {'expected': len(exp), 'present': len(have), 'missing': [i for i in exp if i not in lib]}
    json.dump(lib, open(os.path.join(ROOT, 'library.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    idx = {'built': D.datetime.now().isoformat(timespec='seconds'), 'entries': len(lib), 'coverage': coverage, 'files': files,
           'confidence': dict(collections.Counter(e['confidence'] for e in lib.values())),
           'quality': dict(collections.Counter(e['quality'] for e in lib.values())), 'problems': problems}
    json.dump(idx, open(os.path.join(ROOT, 'index.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    write_markdown(lib)
    print(f"entries {len(lib)}; coverage " + ', '.join(f"{k} {v['present']}/{v['expected']}" for k, v in coverage.items()))
    print('quality', idx['quality'], 'confidence', idx['confidence'])
    print('problems', len(problems), problems[:10])


def bullet(items):
    return ''.join(f'- {x}\n' for x in items if x) if isinstance(items, list) else (f'{items}\n' if items else '')


def write_markdown(lib):
    md = os.path.join(ROOT, 'md'); os.makedirs(md, exist_ok=True)
    groups = collections.defaultdict(list)
    for e in lib.values():
        groups[e['file']].append(e)
    for rel, entries in groups.items():
        title = rel.replace('.json', '').replace('/', ' / ').replace('_', ' ')
        out = [f'# {title}\n', f'_Quality: {entries[0]["quality"]}. Generated from `{rel}`; edit the JSON, not this file._\n']
        for e in entries:
            out.append(f"\n## {e['id']}  ·  confidence: {e['confidence']}\n\n{e['summary']}\n")
            if e.get('themes'): out.append(f"\n**Themes:** {', '.join(e['themes'])}\n")
            for lab, k in (('Common outcomes', 'common_outcomes'), ('Rarer outcomes', 'rare_outcomes'), ('Strengthened by', 'strengtheners'),
                           ('Weakened or cancelled by', 'weakeners_or_cancellations')):
                if e.get(k): out.append(f'\n**{lab}**\n\n{bullet(e[k])}')
            ba = {k: v for k, v in (e.get('by_area') or {}).items() if v}
            if ba: out.append('\n**By life area**\n\n' + ''.join(f'- *{k}:* {v}\n' for k, v in ba.items()))
            for lab, k in (('Lagna / context', 'lagna_or_context_notes'), ('Where sources disagree', 'disagreements'), ('How to say it', 'phrasing_guidance')):
                if e.get(k): out.append(f'\n**{lab}:** {e[k]}\n')
            if e.get('source_views'):
                out.append('\n**Sources**\n\n' + ''.join(f"- {s.get('source', '')}: {s.get('view', '')} {s.get('url', '')}\n" for s in e['source_views']))
        open(os.path.join(md, rel.replace('/', '__').replace('.json', '.md')), 'w', encoding='utf-8').write(''.join(out))


if __name__ == '__main__':
    main()
