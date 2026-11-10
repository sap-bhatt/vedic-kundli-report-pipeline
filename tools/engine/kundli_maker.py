"""Vedic kundli calculator (Swiss Ephemeris): positions, whole-sign houses, dignity, nakshatras, vargas,
Vimshottari / Yogini / Chara dashas, panchang, yogas, doshas and Sade Sati.  Parashari conventions throughout.

Usage:
  python -I tools/engine/kundli_maker.py --date 1990-01-01 --time 10:00 --lat 28.6139 --lon 77.2090 \
      [--tz 5.5] [--name X] [--ayanamsa lahiri|true_citra|icrc] [--node mean|true] \
      [--year-days 365.25] [--gulika begin|middle] [--json out.json] [--now 2026-11-03]

Every yoga/dosha reports its individual condition flags plus the variant used, so a
difference against another calculator can be read as "which variant matches" rather than "bug".
Outer planets are never used.
"""
import argparse, json, math, sys, datetime as D
import swisseph as swe

sys.stdout.reconfigure(encoding='utf-8')

SIGNS = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra', 'Scorpio',
         'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces']
RASHI = ['Mesha', 'Vrishabha', 'Mithuna', 'Karka', 'Simha', 'Kanya', 'Tula', 'Vrischika',
         'Dhanu', 'Makara', 'Kumbha', 'Meena']
NAK = ['Ashwini', 'Bharani', 'Krittika', 'Rohini', 'Mrigashira', 'Ardra', 'Punarvasu', 'Pushya',
       'Ashlesha', 'Magha', 'Purva Phalguni', 'Uttara Phalguni', 'Hasta', 'Chitra', 'Swati',
       'Vishakha', 'Anuradha', 'Jyeshtha', 'Mula', 'Purva Ashadha', 'Uttara Ashadha', 'Shravana',
       'Dhanishta', 'Shatabhisha', 'Purva Bhadrapada', 'Uttara Bhadrapada', 'Revati']
DASHA_LORDS = ['Ketu', 'Venus', 'Sun', 'Moon', 'Mars', 'Rahu', 'Jupiter', 'Saturn', 'Mercury']
DASHA_YEARS = {'Ketu': 7, 'Venus': 20, 'Sun': 6, 'Moon': 10, 'Mars': 7, 'Rahu': 18,
               'Jupiter': 16, 'Saturn': 19, 'Mercury': 17}
GRAHAS = ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn']
ALL = GRAHAS + ['Rahu', 'Ketu']
SWE_ID = {'Sun': swe.SUN, 'Moon': swe.MOON, 'Mars': swe.MARS, 'Mercury': swe.MERCURY,
          'Jupiter': swe.JUPITER, 'Venus': swe.VENUS, 'Saturn': swe.SATURN}
SIGN_LORD = ['Mars', 'Venus', 'Mercury', 'Moon', 'Sun', 'Mercury', 'Venus', 'Mars', 'Jupiter',
             'Saturn', 'Saturn', 'Jupiter']
OWN = {'Sun': [4], 'Moon': [3], 'Mars': [0, 7], 'Mercury': [2, 5], 'Jupiter': [8, 11],
       'Venus': [1, 6], 'Saturn': [9, 10]}
EXALT = {'Sun': (0, 10), 'Moon': (1, 3), 'Mars': (9, 28), 'Mercury': (5, 15), 'Jupiter': (3, 5),
         'Venus': (11, 27), 'Saturn': (6, 20)}
MOOLA = {'Sun': (4, 0, 20), 'Moon': (1, 3, 30), 'Mars': (0, 0, 12), 'Mercury': (5, 15, 20),
         'Jupiter': (8, 0, 10), 'Venus': (6, 0, 15), 'Saturn': (10, 0, 20)}
NODE_EXALT = {'taurus_scorpio': {'Rahu': 1, 'Ketu': 7}, 'gemini_sagittarius': {'Rahu': 2, 'Ketu': 8}}
FRIENDS = {'Sun': ({'Moon', 'Mars', 'Jupiter'}, {'Mercury'}, {'Venus', 'Saturn'}),
           'Moon': ({'Sun', 'Mercury'}, {'Mars', 'Jupiter', 'Venus', 'Saturn'}, set()),
           'Mars': ({'Sun', 'Moon', 'Jupiter'}, {'Venus', 'Saturn'}, {'Mercury'}),
           'Mercury': ({'Sun', 'Venus'}, {'Mars', 'Jupiter', 'Saturn'}, {'Moon'}),
           'Jupiter': ({'Sun', 'Moon', 'Mars'}, {'Saturn'}, {'Mercury', 'Venus'}),
           'Venus': ({'Mercury', 'Saturn'}, {'Mars', 'Jupiter'}, {'Sun', 'Moon'}),
           'Saturn': ({'Mercury', 'Venus'}, {'Jupiter'}, {'Sun', 'Moon', 'Mars'})}
COMBUST = {'Moon': (12, 12), 'Mars': (17, 17), 'Mercury': (14, 12), 'Jupiter': (11, 11),
           'Venus': (10, 8), 'Saturn': (15, 15)}
ASPECTS = {'Sun': [7], 'Moon': [7], 'Mercury': [7], 'Venus': [7], 'Mars': [4, 7, 8],
           'Jupiter': [5, 7, 9], 'Saturn': [3, 7, 10]}
KENDRA, TRIKONA, DUSTHANA, UPACHAYA = {1, 4, 7, 10}, {1, 5, 9}, {6, 8, 12}, {3, 6, 10, 11}
GANA = {i: 'Deva' for i in (0, 4, 6, 7, 12, 14, 16, 21, 26)}
GANA.update({i: 'Manushya' for i in (1, 3, 5, 10, 11, 19, 20, 24, 25)})
YONI = ['Horse', 'Elephant', 'Goat', 'Serpent', 'Serpent', 'Dog', 'Cat', 'Goat', 'Cat', 'Rat',
        'Rat', 'Cow', 'Buffalo', 'Tiger', 'Buffalo', 'Tiger', 'Deer', 'Deer', 'Dog', 'Monkey',
        'Mongoose', 'Monkey', 'Lion', 'Horse', 'Lion', 'Cow', 'Elephant']
YONI_SEX = 'MMFMFFFMMMFMFFMMFMFMMFFFMFF'
VARNA = {0: 'Kshatriya', 4: 'Kshatriya', 8: 'Kshatriya', 3: 'Brahmin', 7: 'Brahmin', 11: 'Brahmin',
         1: 'Vaishya', 5: 'Vaishya', 9: 'Vaishya', 2: 'Shudra', 6: 'Shudra', 10: 'Shudra'}
KARANA_MOVABLE = ['Bava', 'Balava', 'Kaulava', 'Taitila', 'Garaja', 'Vanija', 'Vishti']
NITYA_YOGA = ['Vishkambha', 'Priti', 'Ayushman', 'Saubhagya', 'Shobhana', 'Atiganda', 'Sukarma',
              'Dhriti', 'Shula', 'Ganda', 'Vriddhi', 'Dhruva', 'Vyaghata', 'Harshana', 'Vajra',
              'Siddhi', 'Vyatipata', 'Variyana', 'Parigha', 'Shiva', 'Siddha', 'Sadhya', 'Shubha',
              'Shukla', 'Brahma', 'Indra', 'Vaidhriti']
TITHI = ['Pratipada', 'Dwitiya', 'Tritiya', 'Chaturthi', 'Panchami', 'Shashthi', 'Saptami',
         'Ashtami', 'Navami', 'Dashami', 'Ekadashi', 'Dwadashi', 'Trayodashi', 'Chaturdashi']
WEEKDAY = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
WEEKDAY_LORD = ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn']
KAAL_SARP_NAMES = ['Anant', 'Kulik', 'Vasuki', 'Shankhpal', 'Padma', 'Mahapadma', 'Takshak',
                   'Karkotak', 'Shankhachood', 'Ghatak', 'Vishdhar', 'Sheshnag']
# true_citra needs the sefstars.txt star catalogue, which is not installed, so it is left out.
# Yogini: name, planet, years, Moon nakshatras (1-based) that start it (PyJHora yogini.py)
YOGINI = [('Mangala', 'Moon', 1, {6, 14, 22}), ('Pingala', 'Sun', 2, {7, 15, 23}),
          ('Dhanya', 'Jupiter', 3, {8, 16, 24}), ('Bhramari', 'Mars', 4, {1, 9, 17, 25}),
          ('Bhadrika', 'Mercury', 5, {2, 10, 18, 26}), ('Ulka', 'Saturn', 6, {3, 11, 19, 27}),
          ('Siddha', 'Venus', 7, {4, 12, 20}), ('Sankata', 'Rahu', 8, {5, 13, 21})]
AYAN = {'lahiri': swe.SIDM_LAHIRI, 'icrc': getattr(swe, 'SIDM_LAHIRI_ICRC', 46),
        'raman': swe.SIDM_RAMAN, 'kp': swe.SIDM_KRISHNAMURTI}


def norm(x): return x % 360.0
def sign_of(lon): return int(norm(lon) // 30)
def dms(x):
    x = norm(x) % 30; d = int(x); m = int((x - d) * 60); s = int(round(((x - d) * 60 - m) * 60))
    if s == 60: m, s = m + 1, 0
    return f"{d}°{m:02d}'{s:02d}\""
def nak_of(lon):
    i = int(norm(lon) // (360 / 27)); pada = int((norm(lon) % (360 / 27)) // (360 / 108)) + 1
    return i, pada
def house_from(ref_sign, sign): return (sign - ref_sign) % 12 + 1
def angdist(a, b): return abs(((a - b + 180) % 360) - 180)


def vargas(lon):
    s, deg = sign_of(lon), norm(lon) % 30
    odd = s % 2 == 0  # Aries (0) is an odd sign
    d2 = (4 if deg < 15 else 3) if odd else (3 if deg < 15 else 4)
    d3 = (s + 4 * int(deg // 10)) % 12
    i7 = int(deg // (30 / 7)); d7 = (s + i7) % 12 if odd else (s + 6 + i7) % 12
    d9 = int(norm(lon) // (10 / 3)) % 12
    i10 = int(deg // 3); d10 = (s + i10) % 12 if odd else (s + 8 + i10) % 12
    d12 = (s + int(deg // 2.5)) % 12
    return {'D1': s, 'D2': d2, 'D3': d3, 'D7': d7, 'D9': d9, 'D10': d10, 'D12': d12}


def dignity(p, lon, node_exalt):
    s, deg = sign_of(lon), norm(lon) % 30
    if p in ('Rahu', 'Ketu'):
        ex = NODE_EXALT[node_exalt][p]
        return 'exalted' if s == ex else 'debilitated' if s == (ex + 6) % 12 else '-'
    ex_s = EXALT[p][0]
    if s == (ex_s + 6) % 12: return 'debilitated'
    if s == ex_s and not (p == 'Mercury' and deg >= 15): return 'exalted'
    ms, a, b = MOOLA[p]
    if s == ms and a <= deg < b: return 'moolatrikona'
    if s in OWN[p]: return 'own'
    lord = SIGN_LORD[s]
    if lord == p: return 'own'
    f, n, e = FRIENDS[p]
    return 'friend' if lord in f else 'neutral' if lord in n else 'enemy'


def compute(a):
    swe.set_sid_mode(AYAN[a.ayanamsa])
    y, mo, d = map(int, a.date.split('-'))
    hh, mm = map(int, a.time.split(':')[:2]); ss = int(a.time.split(':')[2]) if a.time.count(':') == 2 else 0
    local = D.datetime(y, mo, d, hh, mm, ss)
    ut = local - D.timedelta(hours=a.tz)
    jd = swe.julday(ut.year, ut.month, ut.day, ut.hour + ut.minute / 60 + ut.second / 3600)
    flg = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
    ayan = swe.get_ayanamsa_ex_ut(jd, swe.FLG_SWIEPH)[1]  # true ayanamsa (with nutation), as sites print it

    def calc(t):
        out = {}
        for p in GRAHAS:
            x = swe.calc_ut(t, SWE_ID[p], flg)[0]
            out[p] = {'lon': x[0], 'lat': x[1], 'speed': x[3]}
        for kind, body in (('mean', swe.MEAN_NODE), ('true', swe.TRUE_NODE)):
            x = swe.calc_ut(t, body, flg)[0]
            out['Rahu_' + kind] = x[0]
        return out

    raw = calc(jd)
    rahu = raw['Rahu_' + a.node]; ketu = norm(rahu + 180)
    lon = {p: raw[p]['lon'] for p in GRAHAS}; lon['Rahu'] = rahu; lon['Ketu'] = ketu
    asc = swe.houses_ex(jd, a.lat, a.lon, b'W', swe.FLG_SIDEREAL)[1][0]
    L = sign_of(asc); M = sign_of(lon['Moon'])
    sg = {p: sign_of(lon[p]) for p in ALL}

    # sunrise / sunset (Hindu: disc centre, no refraction) for the local civil day
    jd_mid = swe.julday(y, mo, d, 0) - a.tz / 24
    rs = swe.CALC_RISE | getattr(swe, 'BIT_HINDU_RISING', 0)
    st = swe.CALC_SET | getattr(swe, 'BIT_HINDU_RISING', 0)
    geo = (a.lon, a.lat, 0)
    def rise(t0, flag): return swe.rise_trans(t0, swe.SUN, flag, geo)[1][0]
    sunrise = rise(jd_mid, rs); sunset = rise(sunrise, st)
    wd = (local.weekday() + 1) % 7  # Sunday = 0 for the civil date
    if jd < sunrise:   # before sunrise: previous weekday, night segment
        vara = (wd - 1) % 7; prev_rise = rise(jd_mid - 1, rs); seg_start = rise(prev_rise, st); seg_end = sunrise; day = False
    elif jd < sunset:
        vara = wd; seg_start, seg_end, day = sunrise, sunset, True
    else:
        vara = wd; seg_start, seg_end, day = sunset, rise(sunset, rs), False
    part = (seg_end - seg_start) / 8
    gidx = (6 - vara) % 7 if day else (6 - (vara + 4)) % 7
    gt = seg_start + part * (gidx + (0.5 if a.gulika == 'middle' else 0))
    lon['Gulika'] = swe.houses_ex(gt, a.lat, a.lon, b'W', swe.FLG_SIDEREAL)[1][0]

    def jd2local(t):
        yy, m2, dd, h = swe.revjul(t)
        return (D.datetime(yy, m2, dd) + D.timedelta(hours=h + a.tz)).strftime('%Y-%m-%d %H:%M')

    # ---------- relationships ----------
    def aspects_sign(p, target_sign):
        offs = ASPECTS.get(p, [7] if a.node_aspects == '7' else [5, 7, 9])
        return house_from(sg[p], target_sign) in offs
    def conj(p, q): return sg[p] == sg[q]
    def mutual_aspect(p, q): return aspects_sign(p, sg[q]) and aspects_sign(q, sg[p])
    def exchange(p, q): return p != q and SIGN_LORD[sg[p]] == q and SIGN_LORD[sg[q]] == p
    def assoc(p, q):
        r = []
        if conj(p, q): r.append('conjunct')
        if mutual_aspect(p, q): r.append('mutual_aspect')
        if exchange(p, q): r.append('exchange')
        return r
    def lord_of_house(h): return SIGN_LORD[(L + h - 1) % 12]
    def hL(p): return house_from(L, sg[p])
    def hM(p): return house_from(M, sg[p])
    dig = {p: dignity(p, lon[p], a.node_exalt) for p in ALL}
    sun = lon['Sun']
    combust = {}
    for p in GRAHAS[1:]:
        orb = COMBUST[p][1 if raw[p]['speed'] < 0 else 0]
        combust[p] = angdist(lon[p], sun) <= orb
    retro = {p: raw[p]['speed'] < 0 for p in GRAHAS}
    wars = []
    star = ['Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn']
    for i, p in enumerate(star):
        for q in star[i + 1:]:
            if angdist(lon[p], lon[q]) <= 1:
                win = p if raw[p]['lat'] > raw[q]['lat'] else q
                wars.append({'planets': [p, q], 'sep_deg': round(angdist(lon[p], lon[q]), 3), 'winner_by_latitude': win})
    malefic_set = {'Sun', 'Mars', 'Saturn', 'Rahu', 'Ketu'}
    merc_afflicted = any(conj('Mercury', m) for m in malefic_set)
    benefics = ['Jupiter', 'Venus'] + ([] if merc_afflicted else ['Mercury'])

    # ---------- planets table ----------
    planets = []
    for p in ALL + ['Gulika']:
        l = lon[p]; ni, pada = nak_of(l)
        row = {'name': p, 'lon': round(l, 4), 'sign': SIGNS[sign_of(l)], 'sign_num': sign_of(l) + 1,
               'deg_in_sign': dms(l), 'nakshatra': NAK[ni], 'pada': pada, 'nak_lord': DASHA_LORDS[ni % 9],
               'house': house_from(L, sign_of(l)), 'vargas': {k: SIGNS[v] for k, v in vargas(l).items()}}
        if p in GRAHAS:
            row.update(retro=retro[p], speed=round(raw[p]['speed'], 4), dignity=dig[p],
                       combust=combust.get(p, False))
        elif p in ('Rahu', 'Ketu'):
            row.update(retro=True, dignity=dig[p])
        planets.append(row)
    ani, apada = nak_of(asc)
    lagna = {'lon': round(asc, 4), 'sign': SIGNS[L], 'sign_num': L + 1, 'deg_in_sign': dms(asc),
             'nakshatra': NAK[ani], 'pada': apada, 'vargas': {k: SIGNS[v] for k, v in vargas(asc).items()}}

    # ---------- panchang / avakhada ----------
    elong = norm(lon['Moon'] - sun)
    t = int(elong // 12)
    k = int(elong // 6)
    karana = 'Kimstughna' if k == 0 else {57: 'Shakuni', 58: 'Chatushpada', 59: 'Naga'}.get(k, KARANA_MOVABLE[(k - 1) % 7])
    mni, mpada = nak_of(lon['Moon'])
    vashya = ['Chatushpada', 'Chatushpada', 'Manava', 'Jalachara', 'Vanachara', 'Manava', 'Manava', 'Keeta',
              'Manava' if norm(lon['Moon']) % 30 < 15 else 'Chatushpada',
              'Chatushpada' if norm(lon['Moon']) % 30 < 15 else 'Jalachara', 'Manava', 'Jalachara'][M]
    nadi = ['Adi', 'Madhya', 'Antya'][[0, 1, 2, 2, 1, 0][mni % 6]]
    panchang = {
        'tithi': f"{TITHI[t % 15] if t % 15 < 14 else ('Purnima' if t < 15 else 'Amavasya')}",
        'paksha': 'Shukla' if t < 15 else 'Krishna', 'tithi_num': t + 1,
        'nitya_yoga': NITYA_YOGA[int(norm(sun + lon['Moon']) // (360 / 27))], 'karana': karana,
        'vara': WEEKDAY[vara], 'sunrise': jd2local(sunrise), 'sunset': jd2local(sunset)}
    avakhada = {'rashi': RASHI[M], 'rashi_lord': SIGN_LORD[M], 'nakshatra': NAK[mni], 'pada': mpada,
                'nak_lord': DASHA_LORDS[mni % 9], 'gana': GANA.get(mni, 'Rakshasa'),
                'yoni': f"{YONI[mni]} ({'Male' if YONI_SEX[mni] == 'M' else 'Female'})",
                'nadi': nadi, 'varna': VARNA[M], 'vashya': vashya, 'lagna': RASHI[L], 'lagna_lord': SIGN_LORD[L]}

    # ---------- Vimshottari ----------
    span = 360 / 27; frac = (norm(lon['Moon']) % span) / span
    lord0 = DASHA_LORDS[mni % 9]
    yd = a.year_days
    md_start = local - D.timedelta(days=frac * DASHA_YEARS[lord0] * yd)
    order = DASHA_LORDS[DASHA_LORDS.index(lord0):] + DASHA_LORDS[:DASHA_LORDS.index(lord0)]
    now = D.datetime.fromisoformat(a.now) if a.now else D.datetime.now()
    dasha = []; t0 = md_start
    for md in order + order:
        md_len = DASHA_YEARS[md] * yd; md_end = t0 + D.timedelta(days=md_len)
        ads = []; a0 = t0
        o2 = DASHA_LORDS[DASHA_LORDS.index(md):] + DASHA_LORDS[:DASHA_LORDS.index(md)]
        for ad in o2:
            a1 = a0 + D.timedelta(days=md_len * DASHA_YEARS[ad] / 120)
            ads.append({'ad': ad, 'start': a0.strftime('%Y-%m-%d'), 'end': a1.strftime('%Y-%m-%d'),
                        'current': a0 <= now < a1}); a0 = a1
        dasha.append({'md': md, 'start': t0.strftime('%Y-%m-%d'), 'end': md_end.strftime('%Y-%m-%d'),
                      'current': t0 <= now < md_end, 'antardashas': ads})
        t0 = md_end
        if t0.year > local.year + 110: break
    balance = {'lord': lord0, 'years': round((1 - frac) * DASHA_YEARS[lord0], 4)}

    # ---------- Yogini (PyJHora yogini.py star lists; 36-year cycle) ----------
    nak1 = mni + 1
    y_idx = next(i for i, (_, _, _, stars) in enumerate(YOGINI) if nak1 in stars)
    y_start = local - D.timedelta(days=frac * YOGINI[y_idx][2] * yd)
    yogini = []; t0 = y_start
    for k in range(3 * 8):
        nm, pl, yrs, _ = YOGINI[(y_idx + k) % 8]
        t1 = t0 + D.timedelta(days=yrs * yd)
        ads = []; a0 = t0
        for j in range(8):
            anm, apl, ayrs, _ = YOGINI[(y_idx + k + j) % 8]
            dur = yrs * ayrs / 36 if a.yogini_ad == 'proportional' else yrs / 8
            a1 = a0 + D.timedelta(days=dur * yd)
            ads.append({'ad': f'{anm} ({apl})', 'start': a0.strftime('%Y-%m-%d'), 'end': a1.strftime('%Y-%m-%d'), 'current': a0 <= now < a1}); a0 = a1
        yogini.append({'yogini': nm, 'planet': pl, 'years': yrs, 'start': t0.strftime('%Y-%m-%d'), 'end': t1.strftime('%Y-%m-%d'),
                       'current': t0 <= now < t1, 'antardashas': ads})
        t0 = t1
        if t0.year > local.year + 110: break

    # ---------- Jaimini Chara dasha, K.N. Rao method (PyJHora default) ----------
    EVEN_FOOTED = {3, 4, 5, 9, 10, 11}
    def is_exalted(p):
        return sg[p] == (NODE_EXALT[a.node_exalt][p] if p in ('Rahu', 'Ketu') else EXALT[p][0])
    def is_debil(p):
        ex = NODE_EXALT[a.node_exalt][p] if p in ('Rahu', 'Ketu') else EXALT[p][0]
        return sg[p] == (ex + 6) % 12
    def stronger(p1, p2, sign):  # PyJHora _stronger_planet_new, rules a,b,d,e,g (rule 2 aspects omitted)
        why = []
        in1, in2 = sg[p1] == sign, sg[p2] == sign
        if in1 and not in2: return p2, 'basic: other lord outside the sign'
        if in2 and not in1: return p1, 'basic: other lord outside the sign'
        c1 = sum(sg[q] == sg[p1] for q in ALL if q != p1); c2 = sum(sg[q] == sg[p2] for q in ALL if q != p2)
        if c1 != c2: return (p1 if c1 > c2 else p2), f'rule1: co-planets {c1} vs {c2}'
        e1, e2 = is_exalted(p1), is_exalted(p2)
        if e1 != e2: return (p1 if e1 else p2), 'rule3: exalted'
        mod = lambda s: 3 if s in (2, 5, 8, 11) else 2 if s in (1, 4, 7, 10) else 1
        if mod(sg[p1]) != mod(sg[p2]): return (p1 if mod(sg[p1]) > mod(sg[p2]) else p2), 'rule4: sign modality'
        return (p1 if norm(lon[p1]) % 30 > norm(lon[p2]) % 30 else p2), 'rule5b: higher degree in sign'
    def chara_lord(sign):
        if sign == 7: return stronger('Mars', 'Ketu', 7)
        if sign == 10: return stronger('Saturn', 'Rahu', 10)
        return SIGN_LORD[sign], ''
    ninth = (L + 8) % 12
    step = -1 if ninth in EVEN_FOOTED else 1
    chara = []; t0 = local
    order12 = [(L + step * i) % 12 for i in range(12)]
    for cyc in range(2):
        for s in order12:
            lord, why = chara_lord(s)
            ls = sg[lord]
            yrs = (s - ls) % 12 if s in EVEN_FOOTED else (ls - s) % 12
            if yrs == 0: yrs = 12
            adj = ''
            if is_exalted(lord): yrs += 1; adj = '+1 exalted'
            elif is_debil(lord): yrs -= 1; adj = '-1 debilitated'
            t1 = t0 + D.timedelta(days=yrs * yd)
            fwd = s in (0, 4, 5, 6, 10, 11)
            ad_signs = [(s + 1 + h) % 12 if fwd else (s - 1 - h) % 12 for h in range(12)]
            ads = []; a0 = t0
            for asg in ad_signs:
                a1 = a0 + D.timedelta(days=yrs / 12 * yd)
                ads.append({'ad': RASHI[asg], 'start': a0.strftime('%Y-%m-%d'), 'end': a1.strftime('%Y-%m-%d'), 'current': a0 <= now < a1}); a0 = a1
            chara.append({'sign': RASHI[s], 'years': yrs, 'lord': lord, 'lord_in': RASHI[ls], 'lord_rule': why, 'adjust': adj,
                          'start': t0.strftime('%Y-%m-%d'), 'end': t1.strftime('%Y-%m-%d'), 'current': t0 <= now < t1, 'antardashas': ads})
            t0 = t1
        if t0.year > local.year + 110: break
    chara_meta = {'method': 'K.N. Rao (PyJHora default)', 'direction': 'zodiacal' if step == 1 else 'anti-zodiacal',
                  'ninth_sign': RASHI[ninth], 'note': 'one pass of 12 signs then repeated with the same lengths (KN Rao has no 12-minus rule)'}

    # ---------- yogas ----------
    yogas = []
    def Y(name, fired, variant='', **cond): yogas.append({'name': name, 'fired': bool(fired), 'variant': variant, 'conditions': cond})

    jup_k_moon = hM('Jupiter') in KENDRA
    ben_on_jup = [b for b in ('Venus', 'Mercury') if b in benefics and (conj(b, 'Jupiter') or aspects_sign(b, sg['Jupiter']))]
    jup_ok = dig['Jupiter'] not in ('debilitated', 'enemy') and not combust['Jupiter']
    Y('Gajakesari', jup_k_moon, 'loose: Jupiter in kendra from Moon', jupiter_house_from_moon=hM('Jupiter'),
      strict_fired=jup_k_moon and bool(ben_on_jup) and jup_ok, benefic_on_jupiter=ben_on_jup,
      jupiter_dignity=dig['Jupiter'], jupiter_combust=combust['Jupiter'],
      jupiter_kendra_from_lagna=hL('Jupiter') in KENDRA)
    MP = {'Ruchaka': ('Mars', {0, 7, 9}), 'Bhadra': ('Mercury', {2, 5}), 'Hamsa': ('Jupiter', {8, 11, 3}),
          'Malavya': ('Venus', {1, 6, 11}), 'Sasa': ('Saturn', {9, 10, 6})}
    for n, (p, ss_) in MP.items():
        Y(n, sg[p] in ss_ and hL(p) in KENDRA, 'own/exalted sign in kendra from Lagna', planet=p,
          sign=SIGNS[sg[p]], house=hL(p), from_moon_kendra=hM(p) in KENDRA, combust=combust[p])
    klords = {lord_of_house(h) for h in KENDRA}; tlords = {lord_of_house(h) for h in TRIKONA}
    pairs = []
    for kp in sorted(klords):
        for tp in sorted(tlords):
            if kp == tp: continue
            key = tuple(sorted((kp, tp)))
            if any(x['pair'] == list(key) for x in pairs): continue
            r = assoc(kp, tp)
            if r:
                owns = lambda p: [h for h in range(1, 13) if lord_of_house(h) == p]
                pairs.append({'pair': list(key), 'how': r, 'houses_owned': {key[0]: owns(key[0]), key[1]: owns(key[1])}})
    Y('Raja (kendra-trikona lords)', pairs, 'PyJHora/BVR: any association, no strength filter', pairs=pairs)
    yk = [p for p in GRAHAS if any(lord_of_house(h) == p for h in (4, 7, 10)) and any(lord_of_house(h) == p for h in (5, 9))]
    Y('Yogakaraka present', yk, '', yogakaraka=yk, yogakaraka_house={p: hL(p) for p in yk})
    l9, l10 = lord_of_house(9), lord_of_house(10)
    Y('Dharma-Karmadhipati', l9 != l10 and assoc(l9, l10), '9L+10L association', lord9=l9, lord10=l10, how=assoc(l9, l10) if l9 != l10 else [])
    for n, h in (('Harsha', 6), ('Sarala', 8), ('Vimala', 12)):
        p = lord_of_house(h)
        Y(f'Viparita Raja ({n})', hL(p) in DUSTHANA, 'popular: lord in any dusthana', lord=p, lord_house=hL(p), strict_fired=hL(p) == h)
    for p in GRAHAS:
        if dig[p] != 'debilitated': continue
        S = sg[p]; Dl = SIGN_LORD[S]; E = next((q for q in GRAHAS if EXALT[q][0] == S), None)
        kend = lambda q: q is not None and (hL(q) in KENDRA or hM(q) in KENDRA)
        c = {'c1_sign_lord_kendra': kend(Dl), 'c2_exalt_planet_kendra': kend(E),
             'c3_D_E_mutual_kendra': E is not None and house_from(sg[Dl], sg[E]) in KENDRA,
             'c4_exalted_in_D9': vargas(lon[p])['D9'] == EXALT[p][0],
             'c5_with_or_aspected_by_D_or_E': conj(p, Dl) or aspects_sign(Dl, S) or (E is not None and (conj(p, E) or aspects_sign(E, S))),
             'c6_lord_of_exalt_sign_kendra': kend(SIGN_LORD[EXALT[p][0]]), 'P_in_kendra': hL(p) in KENDRA}
        Y(f'Neecha Bhanga ({p})', any(v for k2, v in c.items() if k2.startswith('c')), 'any of c1-c6',
          debilitation_lord=Dl, exalt_planet=E, grade=sum(c.values()), **c)
    mc = combust['Mercury']
    Y('Budhaditya', conj('Sun', 'Mercury'), 'same sign', mercury_combust=mc, sun_mercury_sep=round(angdist(lon['Sun'], lon['Mercury']), 2))
    Y('Chandra-Mangala', conj('Moon', 'Mars'), 'same sign')
    adhi = [b for b in benefics if hM(b) in (6, 7, 8)]
    Y('Adhi', len(adhi) == len(benefics), 'all benefics in 6/7/8 from Moon', in_678=adhi, benefics=benefics)
    am = [b for b in benefics if hL(b) == 10 or hM(b) == 10]
    Y('Amala', am, 'benefic in 10th from Lagna or Moon', planets=am)
    vL = [b for b in benefics if hL(b) in UPACHAYA]; vM = [b for b in benefics if hM(b) in UPACHAYA]
    Y('Vasumati', len(vL) == len(benefics) or len(vM) == len(benefics), 'all benefics in upachaya from Lagna or Moon',
      from_lagna=vL, from_moon=vM, popular_2plus=max(len(vL), len(vM)) >= 2)
    moonset = ['Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn']
    s2 = [p for p in moonset if hM(p) == 2]; s12 = [p for p in moonset if hM(p) == 12]
    Y('Sunapha', s2 and not s12, 'Mars..Saturn in 2nd from Moon', planets=s2)
    Y('Anapha', s12 and not s2, 'Mars..Saturn in 12th from Moon', planets=s12)
    Y('Durudhara', s2 and s12, 'both', second=s2, twelfth=s12)
    kc = {'planet_kendra_from_moon': [p for p in moonset if hM(p) in KENDRA - {1}],
          'planet_kendra_from_lagna': [p for p in moonset if hL(p) in KENDRA],
          'moon_in_kendra_from_lagna': hL('Moon') in KENDRA,
          'jupiter_aspects_moon': aspects_sign('Jupiter', M) or conj('Jupiter', 'Moon')}
    kem = not s2 and not s12
    Y('Kemadruma', kem, 'no planet (ex Sun/nodes) in 2nd/12th from Moon',
      cancelled=kem and any(bool(v) for v in kc.values()), **kc)
    l9p = lord_of_house(9); l1p = lord_of_house(1)
    l1_strong = dig[l1p] in ('exalted', 'moolatrikona', 'own') or (hL(l1p) in KENDRA | TRIKONA and dig[l1p] != 'debilitated')
    Y('Lakshmi', dig[l9p] in ('exalted', 'moolatrikona', 'own') and hL(l9p) in KENDRA | TRIKONA and l1_strong,
      '9L own/exalted in kendra/trikona + strong lagna lord', lord9=l9p, lord9_dignity=dig[l9p], lord9_house=hL(l9p), lagna_lord=l1p, lagna_lord_strong=l1_strong)
    good = {1, 2, 4, 5, 7, 9, 10}
    Y('Saraswati', all(hL(p) in good for p in ('Mercury', 'Jupiter', 'Venus')) and dig['Jupiter'] in ('exalted', 'moolatrikona', 'own', 'friend'),
      'Mer/Jup/Ven in kendra/trikona/2nd, Jupiter strong', houses={p: hL(p) for p in ('Mercury', 'Jupiter', 'Venus')})
    dl = sorted({lord_of_house(h) for h in (1, 2, 5, 9, 11)})
    dp = [{'pair': [p, q], 'how': assoc(p, q)} for i, p in enumerate(dl) for q in dl[i + 1:] if assoc(p, q)]
    Y('Dhana (1/2/5/9/11 lords)', dp, 'any association between wealth-house lords', pairs=dp)
    pv = []
    for i, p in enumerate(GRAHAS):
        for q in GRAHAS[i + 1:]:
            if exchange(p, q):
                h1, h2 = hL(p), hL(q)
                kind = 'Dainya' if {h1, h2} & DUSTHANA else 'Khala' if 3 in (h1, h2) else 'Maha'
                pv.append({'planets': [p, q], 'houses': [h1, h2], 'type': kind})
    Y('Parivartana', pv, 'sign exchange', exchanges=pv)
    sh = house_from(sg['Jupiter'], M)
    Y('Shakata', sh in (6, 8, 12), 'popular: Moon 6/8/12 from Jupiter', moon_from_jupiter=sh, cancelled=hL('Moon') in KENDRA)
    Y('Guru-Chandal', conj('Jupiter', 'Rahu'), 'Jupiter with Rahu', with_ketu=conj('Jupiter', 'Ketu'))
    Y('Grahan', any(conj(x, n) for x in ('Sun', 'Moon') for n in ('Rahu', 'Ketu')), 'Sun/Moon with a node',
      combos=[f'{x}+{n}' for x in ('Sun', 'Moon') for n in ('Rahu', 'Ketu') if conj(x, n)])
    occ = lambda h: [p for p in ALL if hL(p) == h]
    o12, o2 = occ(12), occ(2)
    Y('Shubha Kartari (lagna)', o12 and o2 and all(p in benefics for p in o12 + o2), '', h12=o12, h2=o2)
    Y('Papa Kartari (lagna)', o12 and o2 and all(p in malefic_set for p in o12 + o2), '', h12=o12, h2=o2)

    # ---------- doshas ----------
    doshas = {}
    HSETS = {'full': {1, 2, 4, 7, 8, 12}, 'south': {2, 4, 7, 8, 12}, 'no2': {1, 4, 7, 8, 12}}
    hs = HSETS[a.manglik_houses]
    mh = {'lagna': hL('Mars'), 'moon': hM('Mars'), 'venus': house_from(sg['Venus'], sg['Mars'])}
    hits = {r: h in hs for r, h in mh.items()}
    base = {12: 50, 1: 60, 2: 80, 4: 80, 7: 100, 8: 100}
    cos = [p for p in ('Saturn', 'Rahu', 'Ketu', 'Sun') if conj(p, 'Mars')]
    drik = base.get(mh['lagna'], 0)
    if drik and cos:
        drik = (200 if len(cos) == 1 else 250) if mh['lagna'] in (7, 8) else (150 if len(cos) == 1 else 200)
    hsign = {2: {2, 5}, 4: {0, 7}, 7: {3, 9}, 8: {8, 11}, 12: {1, 6}}
    cancel = {'mars_own_or_exalted': sg['Mars'] in (0, 7, 9), 'mars_in_leo_aquarius': sg['Mars'] in (4, 10),
              'house_specific_sign': sg['Mars'] in hsign.get(mh['lagna'], set()),
              'with_jupiter_or_venus': conj('Mars', 'Jupiter') or conj('Mars', 'Venus'),
              'aspected_by_jupiter': aspects_sign('Jupiter', sg['Mars']), 'mars_retro': retro['Mars'],
              'mars_movable_sign': sg['Mars'] in (0, 3, 6, 9), 'lagna_cancer_or_leo': L in (3, 4),
              'mars_is_lagna_lord': SIGN_LORD[L] == 'Mars', 'mars_debilitated': dig['Mars'] == 'debilitated'}
    doshas['manglik'] = {'houses_used': sorted(hs), 'mars_house': mh, 'hits': hits, 'is_manglik_any': any(hits.values()),
                         'count_refs': sum(hits.values()), 'drik_pct_from_lagna': drik, 'malefics_with_mars': cos,
                         'cancel_flags': cancel, 'cancelled_any': any(cancel.values())}
    ks = {}
    for kind in ('mean', 'true'):
        r = raw['Rahu_' + kind]
        inside = [norm(lon[p] - r) < 180 for p in GRAHAS]; n = sum(inside)
        rs_ = sign_of(r)
        sign_rk = all(house_from(rs_, sg[p]) <= 7 for p in GRAHAS)
        sign_kr = all(house_from((rs_ + 6) % 12, sg[p]) <= 7 for p in GRAHAS)
        ks[kind] = {'degree_full': n in (0, 7), 'direction': 'Rahu->Ketu' if n == 7 else 'Ketu->Rahu' if n == 0 else None,
                    'degree_partial_one_out': n in (1, 6),
                    'outside_planets': [p for p, i in zip(GRAHAS, inside) if i != (n >= 4)],
                    'sign_mode_full': sign_rk or sign_kr, 'rahu_house': house_from(L, rs_),
                    'name': KAAL_SARP_NAMES[house_from(L, rs_) - 1]}
    doshas['kaal_sarp'] = ks
    pit = {'sun_moon_rahu_in_9th': [p for p in ('Sun', 'Moon', 'Rahu') if hL(p) == 9],
           'ketu_in_4th': hL('Ketu') == 4,
           'lights_or_nodes_with_mars_saturn': [f'{x}+{y}' for x in ('Sun', 'Moon', 'Rahu', 'Ketu') for y in ('Mars', 'Saturn') if conj(x, y)],
           'mer_ven_rahu_pair_in_2_5_9_12': [h for h in (2, 5, 9, 12) if sum(hL(p) == h for p in ('Mercury', 'Venus', 'Rahu')) >= 2],
           'sun_or_moon_with_node': [f'{x}+{n}' for x in ('Sun', 'Moon') for n in ('Rahu', 'Ketu') if conj(x, n)],
           'sun_with_saturn': conj('Sun', 'Saturn'),
           'ninth_lord_with_malefic': [m for m in malefic_set if m != lord_of_house(9) and conj(lord_of_house(9), m)]}
    doshas['pitra'] = {'flags': pit, 'pyjhora_fired': any(bool(v) for k2, v in pit.items() if k2 not in ('sun_with_saturn', 'ninth_lord_with_malefic'))}
    doshas['guru_chandal'] = conj('Jupiter', 'Rahu') or conj('Jupiter', 'Ketu')
    doshas['shrapit'] = conj('Saturn', 'Rahu'); doshas['angarak'] = conj('Mars', 'Rahu')
    doshas['ghata'] = conj('Mars', 'Saturn'); doshas['ganda_moola'] = mni in (0, 8, 9, 17, 18, 26)

    # Sade Sati / Dhaiya from the real Saturn transit
    sat_f = swe.FLG_SWIEPH | swe.FLG_SIDEREAL
    def sat_sign(t): return sign_of(swe.calc_ut(t, swe.SATURN, sat_f)[0][0])
    # 5-day steps: Saturn never stays in a sign (even on a retrograde re-entry) for less than ~5 days;
    # every sign change is then bisected to ~minutes.
    t = jd - 3 * 365.25; end = jd + (0 if getattr(a, 'skip_sadesati', False) else 100 * 365.25); cur = sat_sign(t); changes = [(t, cur)]
    while t < end:
        t2 = t + 5; s2_ = sat_sign(t2)
        if s2_ != cur:
            lo, hi = t, t2
            for _ in range(20):
                mid = (lo + hi) / 2
                if sat_sign(mid) == cur: lo = mid
                else: hi = mid
            changes.append((hi, s2_)); cur = s2_
        t = t2
    changes.append((end, None))
    label = {(M - 1) % 12: 'Sade Sati - rising (12th)', M: 'Sade Sati - peak (1st)', (M + 1) % 12: 'Sade Sati - setting (2nd)',
             (M + 3) % 12: 'Dhaiya - Kantaka (4th)', (M + 7) % 12: 'Dhaiya - Ashtama (8th)'}
    jd_now = swe.julday(now.year, now.month, now.day, 12)
    intervals = []
    for (ta, s_), (tb, _) in zip(changes[:-1], changes[1:]):
        if s_ in label:
            intervals.append({'phase': label[s_], 'saturn_in': SIGNS[s_], 'start': jd2local(ta)[:10], 'end': jd2local(tb)[:10], 'current': ta <= jd_now < tb})
    curr = [i['phase'] for i in intervals if i['current']]
    doshas['sade_sati'] = {'moon_sign': SIGNS[M], 'saturn_now': SIGNS[sat_sign(jd_now)], 'current': curr or ['none'], 'intervals': intervals}

    return {'input': {'name': a.name, 'date': a.date, 'time': a.time, 'tz': a.tz, 'lat': a.lat, 'lon': a.lon},
            'settings': {'ayanamsa': a.ayanamsa, 'ayanamsa_value': f"{int(ayan)}°{dms(ayan)[3:] if ayan >= 10 else dms(ayan)}", 'ayanamsa_deg': round(ayan, 6),
                         'node': a.node, 'dasha_year_days': yd, 'houses': 'whole sign', 'sunrise': 'hindu (disc centre, no refraction)',
                         'gulika': a.gulika, 'node_exalt': a.node_exalt, 'node_aspects': a.node_aspects,
                         'manglik_houses': a.manglik_houses, 'benefics': benefics},
            'lagna': lagna, 'planets': planets, 'rahu_mean_vs_true': {'mean': round(raw['Rahu_mean'], 4), 'true': round(raw['Rahu_true'], 4)},
            'panchang': panchang, 'avakhada': avakhada, 'wars': wars,
            'dasha': {'balance_at_birth': balance, 'mahadashas': dasha},
            'yogini': {'start': YOGINI[y_idx][0], 'ad_split': a.yogini_ad, 'periods': yogini},
            'chara': {**chara_meta, 'periods': chara}, 'yogas': yogas, 'doshas': doshas}


# ---------- Ashtakoota (North Indian guna milan), tables from PyJHora compatibility.py ----------
VARNA_PYJHORA = [1, 3, 2, 0, 1, 3, 2, 0, 1, 3, 2, 0]   # 0 Brahmin 1 Kshatriya 2 Vaishya 3 Shudra (earth=Shudra, air=Vaishya)
VARNA_NORTH = [1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0]     # common North table (earth=Vaishya, air=Shudra)
VARNA_ARR = [[1, 0, 0, 0], [1, 1, 0, 0], [1, 1, 1, 0], [1, 1, 1, 1]]  # [girl][boy]
VASHYA_SARAVALI = [[2, .5, 1, 0, 2], [.5, 2, 0, 0, 0], [1, 0, 2, 2, 2], [0, 0, 2, 2, 0], [1, 0, 1, 0, 2]]
VASHYA_ASTROYOGI = [[2, 1, 1, 1.5, 1], [1, 2, 1.5, 0, 1], [1, 1.5, 2, 1, 1], [0, 0, 0, 2, 0], [1, 1, 1, 0, 2]]
YONI_MAP = [0, 1, 2, 3, 3, 4, 5, 2, 5, 6, 6, 7, 8, 9, 8, 9, 10, 10, 4, 11, 12, 11, 13, 0, 13, 7, 1]
YONI_NAMES = ['Horse', 'Elephant', 'Sheep', 'Serpent', 'Dog', 'Cat', 'Rat', 'Cow', 'Buffalo', 'Tiger', 'Deer', 'Monkey', 'Mongoose', 'Lion']
YONI_ARR = [[4,2,2,3,2,2,2,1,0,1,1,3,2,1],[2,4,3,3,2,2,2,2,3,1,2,3,2,0],[2,3,4,2,1,2,1,3,3,1,2,0,3,1],[3,3,2,4,2,1,1,1,1,2,2,2,0,2],
            [2,2,1,2,4,2,1,2,2,1,0,2,1,1],[2,2,2,1,2,4,0,2,2,1,3,3,2,1],[2,2,1,1,1,0,4,2,2,2,2,2,1,2],[1,2,3,1,2,2,2,4,3,0,3,2,2,1],
            [0,3,3,1,2,2,2,3,4,1,2,2,2,1],[1,1,1,2,1,1,2,0,1,4,1,1,2,1],[1,2,2,2,0,3,2,3,2,1,4,2,2,1],[3,3,0,2,2,3,2,2,2,1,2,4,3,2],
            [2,2,3,0,1,2,1,2,2,2,2,3,4,2],[1,0,1,2,1,1,2,1,1,1,1,2,2,4]]
MAITRI_MAP = [2, 5, 3, 1, 0, 3, 5, 2, 4, 6, 6, 4]  # sign -> Sun0 Moon1 Mars2 Mer3 Jup4 Ven5 Sat6
MAITRI_ARR = [[5,5,5,4,5,0,0],[5,5,4,1,4,.5,.5],[5,4,5,.5,5,3,.5],[4,1,.5,5,.5,5,4],[5,4,5,.5,5,.5,3],[0,.5,3,5,.5,5,5],[0,.5,.5,4,3,5,5]]
GANA_ARR = [[6, 6, 0], [5, 6, 0], [1, 0, 6]]  # [girl][boy], 0 Deva 1 Manushya 2 Rakshasa
NADI_OF = [0, 1, 2, 2, 1, 0] * 4 + [0, 1, 2]


def vashya_class(moon_lon):
    s, deg = sign_of(moon_lon), norm(moon_lon) % 30
    if s in (0, 1): return 0
    if s in (2, 5, 6, 10): return 1
    if s in (3, 11): return 2
    if s == 4: return 3
    if s == 7: return 4
    if s == 8: return 1 if deg < 15 else 0
    return 0 if deg < 15 else 2  # Capricorn


def ashtakoota(boy_moon, girl_moon):
    bn, bp = nak_of(boy_moon); gn, gp = nak_of(girl_moon); bs, gs = sign_of(boy_moon), sign_of(girl_moon)
    gana = lambda n: 0 if n in (0, 4, 6, 7, 12, 14, 16, 21, 26) else 1 if n in (1, 3, 5, 10, 11, 19, 20, 24, 25) else 2
    def tara_one(frm, to):
        c = (to - frm) % 27 + 1; return 0 if c % 9 in (3, 5, 7) else 1.5
    rel = (bs - gs) % 12 + 1  # boy's sign counted from girl's
    bhak_bad = rel in (2, 12, 5, 9, 6, 8)
    k = {'varna': VARNA_ARR[VARNA_PYJHORA[gs]][VARNA_PYJHORA[bs]], 'varna_north': VARNA_ARR[VARNA_NORTH[gs]][VARNA_NORTH[bs]],
         'vashya': VASHYA_SARAVALI[vashya_class(girl_moon)][vashya_class(boy_moon)],
         'vashya_astroyogi': VASHYA_ASTROYOGI[vashya_class(girl_moon)][vashya_class(boy_moon)],
         'tara': tara_one(gn, bn) + tara_one(bn, gn), 'yoni': YONI_ARR[YONI_MAP[gn]][YONI_MAP[bn]],
         'maitri': MAITRI_ARR[MAITRI_MAP[gs]][MAITRI_MAP[bs]], 'gana': GANA_ARR[gana(gn)][gana(bn)],
         'bhakoot': 0 if bhak_bad else 7, 'nadi': 0 if NADI_OF[bn] == NADI_OF[gn] else 8}
    nadi_dosha = NADI_OF[bn] == NADI_OF[gn]
    friends = lambda a, b: b in FRIENDS[a][0] and a in FRIENDS[b][0]
    lb, lg = SIGN_LORD[bs], SIGN_LORD[gs]
    return {'boy': {'nakshatra': bn, 'pada': bp, 'rashi': bs, 'yoni': YONI_NAMES[YONI_MAP[bn]]},
            'girl': {'nakshatra': gn, 'pada': gp, 'rashi': gs, 'yoni': YONI_NAMES[YONI_MAP[gn]]},
            'kootas': k, 'total': sum(k[x] for x in ('varna', 'vashya', 'tara', 'yoni', 'maitri', 'gana', 'bhakoot', 'nadi')),
            'nadi_dosha': nadi_dosha, 'bhakoot_dosha': bhak_bad,
            'nadi_cancel': nadi_dosha and ((bs == gs and bn != gn) or (bn == gn and bs != gs) or (bn == gn and bp != gp)),
            'bhakoot_cancel': bhak_bad and (lb == lg or friends(lb, lg))}


def print_summary(r):
    i = r['input']; s = r['settings']
    print(f"== {i['name']}  {i['date']} {i['time']} (UTC{'+' if i['tz'] >= 0 else ''}{i['tz']})  lat {i['lat']} lon {i['lon']}")
    print(f"   ayanamsa {s['ayanamsa']} {s['ayanamsa_deg']:.4f}  node {s['node']}  dasha year {s['dasha_year_days']}")
    l = r['lagna']
    print(f"\nLagna  {l['sign']} {l['deg_in_sign']}  {l['nakshatra']} {l['pada']}   D9 {l['vargas']['D9']}")
    print(f"{'Planet':<8}{'Sign':<12}{'Deg':<12}{'H':<3}{'Nakshatra':<20}{'D9':<12}{'Dignity':<13}flags")
    for p in r['planets']:
        fl = ' '.join(x for x, on in (('R', p.get('retro') and p['name'] not in ('Rahu', 'Ketu')), ('combust', p.get('combust'))) if on)
        print(f"{p['name']:<8}{p['sign']:<12}{p['deg_in_sign']:<12}{p['house']:<3}{p['nakshatra'] + ' ' + str(p['pada']):<20}{p['vargas']['D9']:<12}{p.get('dignity', ''):<13}{fl}")
    print(f"Rahu mean {r['rahu_mean_vs_true']['mean']}  true {r['rahu_mean_vs_true']['true']}")
    print('\nPanchang:', ', '.join(f'{k}={v}' for k, v in r['panchang'].items()))
    print('Avakhada:', ', '.join(f'{k}={v}' for k, v in r['avakhada'].items()))
    if r['wars']: print('Graha yuddha:', r['wars'])
    b = r['dasha']['balance_at_birth']; print(f"\nDasha balance at birth: {b['lord']} {b['years']} y")
    for m in r['dasha']['mahadashas']:
        cur = '  <== NOW' if m['current'] else ''
        print(f"  {m['md']:<8}{m['start']} -> {m['end']}{cur}")
        if m['current']:
            for ad in m['antardashas']:
                print(f"      {m['md']}/{ad['ad']:<8}{ad['start']} -> {ad['end']}{'  <== NOW' if ad['current'] else ''}")
    yg = r['yogini']; print(f"\nYogini (starts {yg['start']}, antardasha split {yg['ad_split']}):")
    for m in yg['periods'][:12]:
        print(f"  {m['yogini'] + ' (' + m['planet'] + ')':<20}{m['years']}y  {m['start']} -> {m['end']}{'  <== NOW' if m['current'] else ''}")
    ch = r['chara']; print(f"\nChara dasha ({ch['method']}, {ch['direction']}, 9th sign {ch['ninth_sign']}):")
    for m in ch['periods'][:12]:
        print(f"  {m['sign']:<10}{m['years']:>2}y  lord {m['lord']} in {m['lord_in']:<10}{m['adjust']:<15}{m['start']} -> {m['end']}{'  <== NOW' if m['current'] else ''}  {m['lord_rule']}")
    print('\nYogas fired:')
    for y in r['yogas']:
        if y['fired']:
            c = {k: v for k, v in y['conditions'].items() if v not in ([], {}, None, False)}
            print(f"  + {y['name']}  [{y['variant']}]  {json.dumps(c, ensure_ascii=False)[:300]}")
    print('Not fired:', ', '.join(y['name'] for y in r['yogas'] if not y['fired']))
    d = r['doshas']; m = d['manglik']
    print(f"\nManglik: any={m['is_manglik_any']} refs={m['hits']} mars_house={m['mars_house']} drik%={m['drik_pct_from_lagna']} cancelled_any={m['cancelled_any']} "
          f"cancel={[k for k, v in m['cancel_flags'].items() if v]}")
    for k, v in d['kaal_sarp'].items():
        print(f"Kaal Sarp ({k} node): full_by_degree={v['degree_full']} partial={v['degree_partial_one_out']} sign_mode_full={v['sign_mode_full']} "
              f"outside={v['outside_planets']} name_if_any={v['name']}")
    print(f"Pitra (PyJHora any): {d['pitra']['pyjhora_fired']}  {json.dumps({k: v for k, v in d['pitra']['flags'].items() if v}, ensure_ascii=False)}")
    print(f"Guru-Chandal {d['guru_chandal']}  Shrapit {d['shrapit']}  Angarak {d['angarak']}  Ghata {d['ghata']}  Ganda Moola {d['ganda_moola']}")
    ss = d['sade_sati']
    print(f"Sade Sati: Moon {ss['moon_sign']}, Saturn now {ss['saturn_now']} -> {ss['current']}")
    for iv in ss['intervals']:
        print(f"   {iv['phase']:<28}{iv['start']} -> {iv['end']}{'  <== NOW' if iv['current'] else ''}")


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', required=True); ap.add_argument('--time', required=True)
    ap.add_argument('--lat', type=float, required=True); ap.add_argument('--lon', type=float, required=True)
    ap.add_argument('--tz', type=float, default=5.5); ap.add_argument('--name', default='')
    ap.add_argument('--ayanamsa', default='lahiri', choices=list(AYAN)); ap.add_argument('--node', default='mean', choices=['mean', 'true'])
    ap.add_argument('--year-days', dest='year_days', type=float, default=365.25)
    ap.add_argument('--gulika', default='begin', choices=['begin', 'middle'])
    ap.add_argument('--node-exalt', dest='node_exalt', default='taurus_scorpio', choices=list(NODE_EXALT))
    ap.add_argument('--node-aspects', dest='node_aspects', default='7', choices=['7', '579'])
    ap.add_argument('--manglik-houses', dest='manglik_houses', default='full', choices=['full', 'south', 'no2'])
    ap.add_argument('--yogini-ad', dest='yogini_ad', default='proportional', choices=['proportional', 'equal'])
    ap.add_argument('--now', default=None); ap.add_argument('--json', default=None)
    a = ap.parse_args()
    r = compute(a)
    print_summary(r)
    if a.json:
        json.dump(r, open(a.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
        print('\njson ->', a.json)
