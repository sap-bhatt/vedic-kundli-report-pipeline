"""Compute the full chart_data.json for one person (the input format the kundli reports were written from).

Same calculator settings for every chart; birth details come from the command line.

  python -I tools/chart_data.py --date 1990-01-01 --time 10:00 --lat 28.6139 --lon 77.2090 \
      --place "New Delhi, India" --sex female --now 2026-11-11 --out chart_data.json

--now sets the reference date for "current" periods and transits (default: today).
Chart facts come from tools/engine/kundli_maker.py (Swiss Ephemeris, Lahiri, mean node, whole-sign houses).
"""
import sys, os, json, argparse, datetime as D
sys.stdout.reconfigure(encoding='utf-8')
TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(TOOLS, 'engine'))  # the bundled calculator (tools/engine/kundli_maker.py)
import kundli_maker as K, swisseph as swe

ASP = {'Mars': [4, 7, 8], 'Jupiter': [5, 7, 9], 'Saturn': [3, 7, 10], 'Rahu': [5, 7, 9], 'Ketu': [5, 7, 9]}


def fmt_coord(lat, lon):
    return f"{abs(lat):.2f}{'N' if lat >= 0 else 'S'}, {abs(lon):.2f}{'E' if lon >= 0 else 'W'}"


def build(date, time, lat, lon, tz, place, sex, now):
    a = argparse.Namespace(date=date, time=time, lat=lat, lon=lon, tz=tz, name='Native', ayanamsa='lahiri', node='mean',
                           year_days=365.25, gulika='middle', node_exalt='taurus_scorpio', node_aspects='7', manglik_houses='full',
                           yogini_ad='proportional', now=now, json=None, skip_sadesati=False)
    r = K.compute(a)
    L = r['lagna']['sign_num'] - 1
    P = {p['name']: p for p in r['planets']}
    houses = []
    for h in range(1, 13):
        s = (L + h - 1) % 12; lord = K.SIGN_LORD[s]
        occ = [n for n, p in P.items() if n != 'Gulika' and p['sign_num'] - 1 == s]
        asp = [n for n, p in P.items() if n != 'Gulika' and ((s - (p['sign_num'] - 1)) % 12 + 1) in ASP.get(n, [7])]
        houses.append({'house': h, 'sign': K.SIGNS[s], 'lord': lord, 'lord_in_house': P[lord]['house'], 'lord_in_sign': P[lord]['sign'],
                       'lord_dignity': P[lord].get('dignity'), 'occupants': occ, 'aspected_by': asp})
    y, m, d = map(int, now.split('-'))
    swe.set_sid_mode(swe.SIDM_LAHIRI); jd = swe.julday(y, m, d, 6.5)
    M = P['Moon']['sign_num'] - 1; tr = {}
    for n, i in K.SWE_ID.items():
        x = swe.calc_ut(jd, i, swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED)[0]
        tr[n] = {'sign': K.SIGNS[int(x[0] // 30)], 'deg': round(x[0] % 30, 1), 'retro': x[3] < 0,
                 'house_from_lagna': (int(x[0] // 30) - L) % 12 + 1, 'house_from_moon': (int(x[0] // 30) - M) % 12 + 1}
    rh = swe.calc_ut(jd, swe.MEAN_NODE, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)[0][0]
    tr['Rahu'] = {'sign': K.SIGNS[int(rh // 30)], 'house_from_lagna': (int(rh // 30) - L) % 12 + 1, 'house_from_moon': (int(rh // 30) - M) % 12 + 1}

    def ingress(body, years=6):
        t = jd; cur = int(swe.calc_ut(t, body, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)[0][0] // 30); evs = []
        while t < jd + years * 365.25:
            t += 2; s = int(swe.calc_ut(t, body, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)[0][0] // 30)
            if s != cur:
                yy, mm, dd, _ = swe.revjul(t); evs.append((f'{yy}-{mm:02d}-{dd:02d}', K.SIGNS[s], (s - L) % 12 + 1)); cur = s
        return evs

    md = next(m for m in r['dasha']['mahadashas'] if m['current'])
    res = {'birth': {'date': date, 'time': f'{time} IST' if tz == 5.5 else f'{time} (UTC{tz:+g})',
                     'place': f'{place} ({fmt_coord(lat, lon)})', 'sex': sex},
           'settings': r['settings'], 'lagna': r['lagna'], 'planets': r['planets'], 'houses': houses, 'panchang_at_birth': r['panchang'],
           'avakhada': r['avakhada'], 'graha_yuddha': r['wars'],
           'vimshottari': {'balance_at_birth': r['dasha']['balance_at_birth'],
                           'mahadashas': [{k: m[k] for k in ('md', 'start', 'end')} for m in r['dasha']['mahadashas'][:9]],
                           'current_md_antardashas': md['antardashas'],
                           # every sub-period of the first 9 mahadashas, from the calculator's exact-time arithmetic
                           'antardashas_by_md': {m['md']: [{k: x[k] for k in ('ad', 'start', 'end')} for x in m['antardashas']]
                                                 for m in r['dasha']['mahadashas'][:9]}},
           'yogini_current_and_next': [p for p in r['yogini']['periods'] if p['end'] >= f'{y}-01-01'][:3],
           'chara_current_and_next': [{k: p[k] for k in ('sign', 'years', 'start', 'end')} for p in r['chara']['periods'] if p['end'] >= f'{y}-01-01'][:3],
           'yogas_present': [yo for yo in r['yogas'] if yo['fired']], 'yogas_checked_absent': [yo['name'] for yo in r['yogas'] if not yo['fired']],
           'doshas': r['doshas'], f'transits_{now.replace("-", "_")}': tr,
           'jupiter_ingresses_next_6y': ingress(swe.JUPITER), 'saturn_ingresses_next_6y': ingress(swe.SATURN)}
    for yo in res['yogini_current_and_next']: yo.pop('antardashas', None)
    # kundli_maker builds some dosha flag lists from sets, so their order depends on the hash seed; fix it.
    for dosha in res['doshas'].values():
        for k, v in (dosha.get('flags') or {}).items() if isinstance(dosha, dict) else []:
            if isinstance(v, list) and all(isinstance(x, str) for x in v): dosha['flags'][k] = sorted(v, key=K.GRAHAS.index if all(x in K.GRAHAS for x in v) else str)
    birth_year = int(date[:4])
    res['doshas']['sade_sati']['intervals'] = [i for i in res['doshas']['sade_sati']['intervals'] if i['start'] >= f'{birth_year - 3}']
    return res


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', required=True); ap.add_argument('--time', required=True)
    ap.add_argument('--lat', type=float, required=True); ap.add_argument('--lon', type=float, required=True)
    ap.add_argument('--tz', type=float, default=5.5); ap.add_argument('--place', default='')
    ap.add_argument('--sex', default=''); ap.add_argument('--now', default=D.date.today().isoformat())
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    res = build(a.date, a.time, a.lat, a.lon, a.tz, a.place, a.sex, a.now)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(res, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
    print('saved', a.out, len(json.dumps(res, default=str)) // 1024, 'KB')
