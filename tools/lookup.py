"""Look up the Astro Library entries that apply to one birth chart.

Input, either:
  --chart path.json        a kundli_maker.py --json output, or a chart_data.json with 'lagna' and 'planets'
  --date YYYY-MM-DD --time HH:MM --lat N --lon E [--tz 5.5]   (computes the chart with kundli_maker.py)
Options:
  --compact     trim each entry to the fields a small model needs (default: full entries)
  --out FILE    write JSON there (default: stdout)

Chart facts always come from the calculator, never from the library. Each returned entry carries the
chart context it was selected for (dignity, retrograde, combust, nakshatra) and the library's quality flag.
"""
import argparse, json, os, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KM_DIR = os.path.join(ROOT, 'tools', 'engine')  # the bundled calculator (tools/engine/kundli_maker.py)
SIGNS = ['aries', 'taurus', 'gemini', 'cancer', 'leo', 'virgo', 'libra', 'scorpio', 'sagittarius', 'capricorn', 'aquarius', 'pisces']
SIGN_LORD = ['Mars', 'Venus', 'Mercury', 'Moon', 'Sun', 'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn', 'Saturn', 'Jupiter']
GRAHAS = ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn', 'Rahu', 'Ketu']
COMPACT = ['id', 'summary', 'common_outcomes', 'rare_outcomes', 'by_area', 'strengtheners', 'weakeners_or_cancellations',
           'disagreements', 'confidence', 'quality', 'phrasing_guidance']


def load_chart(a):
    if a.chart:
        return json.load(open(a.chart, encoding='utf-8'))
    sys.path.insert(0, KM_DIR)
    import kundli_maker as K
    ns = argparse.Namespace(date=a.date, time=a.time, lat=a.lat, lon=a.lon, tz=a.tz, name='', ayanamsa='lahiri', node='mean',
                            year_days=365.25, gulika='begin', node_exalt='taurus_scorpio', node_aspects='7', manglik_houses='full',
                            yogini_ad='proportional', now=None, json=None, skip_sadesati=True)
    return K.compute(ns)


def select(chart, lib, compact=False):
    lagna = chart['lagna']['sign_num'] - 1
    P = {p['name']: p for p in chart['planets'] if p['name'] in GRAHAS}
    picks = []

    def add(eid, ctx):
        e = lib.get(eid)
        if not e:
            picks.append({'id': eid, 'missing': True, 'chart_context': ctx}); return
        body = {k: e.get(k) for k in COMPACT} if compact else dict(e)
        if compact:
            body['sources'] = [s.get('source', '') for s in e.get('source_views', [])]
        body['chart_context'] = ctx
        picks.append(body)

    for name in GRAHAS:
        p = P[name]; s = p['sign_num'] - 1; h = (s - lagna) % 12 + 1
        ctx = {'planet': name, 'sign': SIGNS[s].title(), 'house': h, 'degree_in_sign': p.get('deg_in_sign'),
               'nakshatra': f"{p.get('nakshatra')} {p.get('pada')}", 'dignity': p.get('dignity'),
               'retrograde': p.get('retro') if name not in ('Rahu', 'Ketu') else None, 'combust': p.get('combust')}
        add(f'planet_in_house/{name.lower()}/{h}', ctx)
        add(f'planet_in_sign/{name.lower()}/{SIGNS[s]}', ctx)
    for n in range(1, 13):
        lord = SIGN_LORD[(lagna + n - 1) % 12]; lp = P[lord]
        m = (lp['sign_num'] - 1 - lagna) % 12 + 1
        add(f'lord_in_house/{n}/{m}', {'lord_of': n, 'lord': lord, 'placed_in': m, 'lord_sign': SIGNS[lp['sign_num'] - 1].title(),
                                       'lord_dignity': lp.get('dignity')})
    return {'lagna': {'sign': SIGNS[lagna].title(), 'degree': chart['lagna'].get('deg_in_sign'), 'nakshatra': chart['lagna'].get('nakshatra')},
            'entries': picks, 'counts': {'selected': len(picks), 'missing': sum(1 for x in picks if x.get('missing')),
                                         'draft': sum(1 for x in picks if x.get('quality') == 'draft')}}


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--chart'); ap.add_argument('--date'); ap.add_argument('--time'); ap.add_argument('--lat', type=float)
    ap.add_argument('--lon', type=float); ap.add_argument('--tz', type=float, default=5.5)
    ap.add_argument('--compact', action='store_true'); ap.add_argument('--out')
    a = ap.parse_args()
    lib = json.load(open(os.path.join(ROOT, 'library.json'), encoding='utf-8'))
    res = select(load_chart(a), lib, a.compact)
    txt = json.dumps(res, ensure_ascii=False, indent=1)
    if a.out: open(a.out, 'w', encoding='utf-8').write(txt); print('wrote', a.out, res['counts'])
    else: print(txt)
