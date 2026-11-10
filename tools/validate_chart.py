"""Check a chart_data.json before running the report pipeline on it.

  python tools/validate_chart.py chart_data.json [more.json ...] [--now YYYY-MM-DD] [--strict] [--schema] [--quiet]

Reports three kinds of finding (the format is documented in docs/CHART_DATA_FORMAT.md):

  ERROR    a required field is missing or malformed, or the data contradicts itself; the pipeline would stop or
           print wrong facts. Exit code 1.
  WARNING  an optional field is missing or unusual; the report still runs, but the feature it drives is skipped
           or reduced (the message says which).
  CHECK    sanity checks, each listed as ok or FAIL: 9 grahas, sign numbers 1-12, whole-sign houses 1-12,
           ISO dates, dasha periods in order and contiguous, lagna / planet / house / transit consistency.
           A failed check is also counted as an error or a warning.

--now      the "as of" date (default: the date in the transits_YYYY_MM_DD key, as the pipeline uses).
--strict   treat warnings as errors (exit code 1 if any).
--schema   also validate against docs/chart_data.schema.json with the jsonschema package, if it is installed.
--quiet    print only errors and warnings, not the list of sanity checks.

Standard library only. Exit code 0 = no errors, 1 = errors (or warnings with --strict), 2 = file not readable as JSON.
"""
import argparse, datetime as D, difflib, json, math, os, re, sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SIGNS = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces']
SIGN_LORD = ['Mars', 'Venus', 'Mercury', 'Moon', 'Sun', 'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn', 'Saturn', 'Jupiter']
SANSKRIT_SIGNS = {'mesha', 'vrishabha', 'vrishabh', 'mithuna', 'mithun', 'karka', 'karkata', 'simha', 'kanya', 'tula', 'vrischika',
                  'vrishchika', 'dhanu', 'dhanus', 'makara', 'kumbha', 'meena', 'mina'}
GRAHAS = ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn', 'Rahu', 'Ketu']
ORDER = ['Ketu', 'Venus', 'Sun', 'Moon', 'Mars', 'Rahu', 'Jupiter', 'Saturn', 'Mercury']
YEARS = {'Ketu': 7, 'Venus': 20, 'Sun': 6, 'Moon': 10, 'Mars': 7, 'Rahu': 18, 'Jupiter': 16, 'Saturn': 19, 'Mercury': 17}
NAKSHATRAS = ['Ashwini', 'Bharani', 'Krittika', 'Rohini', 'Mrigashira', 'Ardra', 'Punarvasu', 'Pushya', 'Ashlesha', 'Magha',
              'Purva Phalguni', 'Uttara Phalguni', 'Hasta', 'Chitra', 'Swati', 'Vishakha', 'Anuradha', 'Jyeshtha', 'Mula',
              'Purva Ashadha', 'Uttara Ashadha', 'Shravana', 'Dhanishta', 'Shatabhisha', 'Purva Bhadrapada', 'Uttara Bhadrapada', 'Revati']
EXALT = {'Sun': 0, 'Moon': 1, 'Mars': 9, 'Mercury': 5, 'Jupiter': 3, 'Venus': 11, 'Saturn': 6}
ASP = {'Mars': [4, 7, 8], 'Jupiter': [5, 7, 9], 'Saturn': [3, 7, 10], 'Rahu': [5, 7, 9], 'Ketu': [5, 7, 9]}
DIGNITIES = {'exalted', 'moolatrikona', 'own', 'friend', 'neutral', 'enemy', 'debilitated'}
YOGINIS = {'Mangala', 'Pingala', 'Dhanya', 'Bhramari', 'Bhadrika', 'Ulka', 'Siddha', 'Sankata'}
ISO = re.compile(r'^\d{4}-\d{2}-\d{2}$')
TRANSIT_KEY = re.compile(r'^transits_(\d{4})_(\d{2})_(\d{2})$')
TOP_KEYS = ['birth', 'settings', 'lagna', 'planets', 'houses', 'panchang_at_birth', 'avakhada', 'graha_yuddha', 'vimshottari',
            'yogini_current_and_next', 'chara_current_and_next', 'yogas_present', 'yogas_checked_absent', 'doshas',
            'jupiter_ingresses_next_6y', 'saturn_ingresses_next_6y']
PLANET_KEYS = ['name', 'lon', 'sign', 'sign_num', 'deg_in_sign', 'nakshatra', 'pada', 'nak_lord', 'house', 'vargas', 'retro', 'speed',
               'dignity', 'combust']
YOGA_MAP = {'Raja (kendra-trikona lords)': 'raja_kendra_trikona', 'Yogakaraka present': 'yogakaraka',
            'Dhana (1/2/5/9/11 lords)': 'dhana', 'Viparita Raja (Harsha)': 'viparita_harsha',
            'Viparita Raja (Sarala)': 'viparita_sarala', 'Viparita Raja (Vimala)': 'viparita_vimala',
            'Shubha Kartari (lagna)': 'shubha_kartari', 'Papa Kartari (lagna)': 'papa_kartari',
            'Dharma-Karmadhipati': 'dharma_karmadhipati', 'Chandra-Mangala': 'chandra_mangala', 'Guru-Chandal': None}


def yoga_slug(name):  # same rule as tools/dasha_facts.py yoga_slug
    if name in YOGA_MAP: return YOGA_MAP[name]
    if name.startswith('Neecha Bhanga'): return 'neecha_bhanga'
    return name.lower().replace('-', '_').replace(' ', '_')


def slug(s):
    return str(s).lower().replace(' ', '_').replace('-', '_')


class Report:
    def __init__(self):
        self.errors, self.warnings, self.checks = [], [], []

    def err(self, msg): self.errors.append(msg)

    def warn(self, msg): self.warnings.append(msg)

    def check(self, name, problems, severity='error'):
        """Record a sanity check. problems: list of strings (empty = ok)."""
        self.checks.append((name, problems, severity))
        for p in problems:
            (self.err if severity == 'error' else self.warn)(f'{name}: {p}')


def is_num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


def iso_ok(s):
    if not isinstance(s, str) or not ISO.match(s): return False
    try:
        D.date.fromisoformat(s); return True
    except ValueError:
        return False


def days(a, b):
    return (D.date.fromisoformat(b) - D.date.fromisoformat(a)).days


def validate(ch, now=None, lib=None):
    R = Report()
    if not isinstance(ch, dict):
        R.err('top level: the file must hold one JSON object'); return R, now
    for k in ch:  # unknown keys are ignored by the tools; a near miss is usually a typo or a renamed field
        if k not in TOP_KEYS and not TRANSIT_KEY.match(k):
            near = (['transits_' + k.split('_', 1)[1]] if k.lower().startswith('transit') and '_' in k else
                    difflib.get_close_matches(k, TOP_KEYS, 1, 0.75))
            R.warn(f"unknown top-level key {k!r} is ignored" + (f"; did you mean {near[0]!r}?" if near else ''))
    for p in ch.get('planets') or []:
        if isinstance(p, dict):
            for k in p:
                if k not in PLANET_KEYS:
                    alias = {'nakshatra_lord': 'nak_lord', 'longitude': 'lon', 'retrograde': 'retro', 'degree': 'deg_in_sign',
                             'planet': 'name', 'rashi': 'sign', 'varga': 'vargas', 'bhava': 'house'}
                    near = [alias[k]] if k in alias else difflib.get_close_matches(k, PLANET_KEYS, 1, 0.6)
                    R.warn(f"planets.{p.get('name')}: unknown field {k!r} is ignored" + (f"; did you mean {near[0]!r}?" if near else ''))

    # ---------------- birth, settings ----------------
    b = ch.get('birth')
    if not isinstance(b, dict):
        R.err('birth: missing (an object with date, time, place); needed for ages, dasha dates and the cover')
        b = {}
    else:
        if not iso_ok(b.get('date')): R.err(f"birth.date: must be an ISO date YYYY-MM-DD, got {b.get('date')!r}")
        for k in ('time', 'place'):
            if not isinstance(b.get(k), str): R.err(f'birth.{k}: missing or not a string (printed on the cover by assemble_report.py)')
        sex = b.get('sex')
        if sex in (None, ''):
            R.warn("birth.sex: missing; the writers call the spouse 'partner' (give 'female' or 'male' for husband/wife wording)")
        elif str(sex).lower() not in ('female', 'male'):
            R.warn(f"birth.sex: {sex!r} is neither 'female' nor 'male'; the writers call the spouse 'partner'")
    st = ch.get('settings')
    if not isinstance(st, dict):
        R.err('settings: missing (an object with at least ayanamsa_value, printed on the cover)'); st = {}
    else:
        if not isinstance(st.get('ayanamsa_value'), str):
            R.err('settings.ayanamsa_value: missing or not a string (for example "23°41\'31\""); printed on the cover')
        if st.get('ayanamsa') not in (None, 'lahiri'):
            R.warn(f"settings.ayanamsa is {st.get('ayanamsa')!r}: the library and tests assume Lahiri; the cover still says Lahiri")
        if st.get('houses') not in (None, 'whole sign'):
            R.warn(f"settings.houses is {st.get('houses')!r}: every tool counts houses whole-sign from the lagna sign")
        if 'node_exalt' not in st:
            R.warn('settings.node_exalt: missing; the D1 table leaves out its footnote on node dignity')

    # ---------------- lagna ----------------
    lg = ch.get('lagna')
    L = None
    if not isinstance(lg, dict):
        R.err('lagna: missing (an object with lon, sign, sign_num, deg_in_sign, nakshatra, vargas.D9)'); lg = {}
    else:
        if not is_num(lg.get('lon')) or not 0 <= lg['lon'] < 360: R.err(f"lagna.lon: must be a number 0 <= lon < 360 (sidereal), got {lg.get('lon')!r}")
        if lg.get('sign') not in SIGNS: R.err(f"lagna.sign: must be an English sign name in title case (Aries..Pisces), got {lg.get('sign')!r}")
        if not is_int(lg.get('sign_num')) or not 1 <= lg['sign_num'] <= 12: R.err(f"lagna.sign_num: must be an integer 1-12 (1 = Aries), got {lg.get('sign_num')!r}")
        else: L = lg['sign_num'] - 1
        if not isinstance(lg.get('deg_in_sign'), str): R.err('lagna.deg_in_sign: missing or not a string (display form, for example "21°58\'42\"")')
        if not isinstance(lg.get('nakshatra'), str): R.err('lagna.nakshatra: missing or not a string')
        v = lg.get('vargas')
        if not isinstance(v, dict) or v.get('D9') not in SIGNS:
            R.err(f"lagna.vargas.D9: missing or not an English sign name, got {(v or {}).get('D9') if isinstance(v, dict) else v!r}")
        if lg.get('pada') is None: R.warn("lagna.pada: missing; the D1 table shows '-' for the lagna pada")

    # ---------------- planets ----------------
    P = {}
    pl = ch.get('planets')
    if not isinstance(pl, list):
        R.err('planets: missing or not a list of planet objects'); pl = []
    names = [p.get('name') for p in pl if isinstance(p, dict)]
    probs = []
    for g in GRAHAS:
        n = names.count(g)
        if n == 0: probs.append(f'{g} is missing')
        elif n > 1: probs.append(f'{g} appears {n} times')
    if any(not isinstance(p, dict) or not isinstance(p.get('name'), str) for p in pl): probs.append('an entry has no string "name"')
    R.check('9 grahas (Sun..Saturn, Rahu, Ketu) each listed once in planets', probs)
    extra = [n for n in names if n not in GRAHAS + ['Gulika']]
    if extra: R.warn(f"planets: {', '.join(map(str, extra))} not used by any tool (only the 9 grahas and Gulika are read)")
    if 'Gulika' not in names: R.warn('planets: no Gulika; it is left out of the D1 table and the chart drawings (optional)')
    opt_missing = {'pada': [], 'retro': [], 'combust': [], 'speed': [], 'house': []}
    d10_have = []
    for p in pl:
        if not isinstance(p, dict): continue
        g = p.get('name')
        if g == 'Gulika':
            if p.get('sign') not in SIGNS: R.err(f"planets.Gulika.sign: must be an English sign name, got {p.get('sign')!r}")
            if not isinstance(p.get('vargas'), dict): R.err('planets.Gulika.vargas: missing; give an object (D9 sign, or {}), the chart drawing reads it')
            continue
        if g not in GRAHAS: continue
        P[g] = p
        pre = f'planets.{g}'
        if not is_num(p.get('lon')) or not 0 <= p['lon'] < 360: R.err(f"{pre}.lon: must be a number 0 <= lon < 360 (sidereal), got {p.get('lon')!r}")
        if p.get('sign') not in SIGNS: R.err(f"{pre}.sign: must be an English sign name in title case, got {p.get('sign')!r}")
        if not is_int(p.get('sign_num')) or not 1 <= p['sign_num'] <= 12: R.err(f"{pre}.sign_num: must be an integer 1-12, got {p.get('sign_num')!r}")
        if not isinstance(p.get('deg_in_sign'), str): R.err(f'{pre}.deg_in_sign: missing or not a string (display form)')
        if not isinstance(p.get('nakshatra'), str): R.err(f'{pre}.nakshatra: missing or not a string')
        if p.get('nak_lord') not in GRAHAS: R.err(f"{pre}.nak_lord: must be one of the 9 grahas, got {p.get('nak_lord')!r}")
        dg = p.get('dignity')
        if g in ('Rahu', 'Ketu'):
            if dg not in DIGNITIES | {'-'}: R.err(f"{pre}.dignity: must be a dignity word or '-' for a node, got {dg!r}")
        elif dg not in DIGNITIES: R.err(f"{pre}.dignity: must be one of {sorted(DIGNITIES)}, got {dg!r}")
        v = p.get('vargas')
        if not isinstance(v, dict) or v.get('D9') not in SIGNS:
            R.err(f'{pre}.vargas.D9: missing or not an English sign name')
        elif 'D10' in v:
            d10_have.append(g)
            if v['D10'] not in SIGNS: R.err(f"{pre}.vargas.D10: not an English sign name, got {v['D10']!r}")
        for k in opt_missing:
            if k not in p and not (k in ('retro', 'speed', 'combust') and g in ('Rahu', 'Ketu')): opt_missing[k].append(g)
        for k, ok in (('retro', isinstance(p.get('retro'), bool)), ('combust', isinstance(p.get('combust'), bool)),
                      ('speed', is_num(p.get('speed'))), ('pada', is_int(p.get('pada')) and 1 <= p['pada'] <= 4),
                      ('house', is_int(p.get('house')) and 1 <= p['house'] <= 12)):
            if k in p and p[k] is not None and not ok: R.err(f'{pre}.{k}: wrong type or range ({p[k]!r})')
    effects = {'pada': "the D1 table shows '-' for the pada", 'retro': 'treated as direct (no retrograde notes or conditions)',
               'combust': 'treated as not combust', 'speed': 'the combustion orb for direct motion is used',
               'house': 'computed from sign_num and the lagna (no effect)'}
    for k, gs in opt_missing.items():
        if gs and k != 'house': R.warn(f"planets.*.{k}: missing for {', '.join(gs)}; {effects[k]}")
    lag_d10 = isinstance(lg.get('vargas'), dict) and 'D10' in lg['vargas']
    if lag_d10 and lg['vargas']['D10'] not in SIGNS: R.err(f"lagna.vargas.D10: not an English sign name, got {lg['vargas']['D10']!r}")
    if lag_d10 or d10_have:
        miss = [g for g in GRAHAS if g in P and g not in d10_have]
        probs = (['lagna.vargas.D10 is missing while planets have D10'] if not lag_d10 else []) + \
                ([f"D10 missing for {', '.join(miss)}"] if miss else [])
        if probs: R.err('D10: give vargas.D10 for the lagna and all nine grahas, or for none (' + '; '.join(probs) + ')')
    else:
        R.warn('vargas.D10: not given; the D10 table, the D10 verdict line and the career D10 notes are skipped')

    # ---------------- sanity checks on positions ----------------
    probs = []
    for g, p in list(P.items()) + ([('lagna', lg)] if lg else []):
        if p.get('sign') in SIGNS and is_int(p.get('sign_num')) and SIGNS.index(p['sign']) + 1 != p['sign_num']:
            probs.append(f"{g}: sign {p['sign']} but sign_num {p['sign_num']} (Aries = 1 ... Pisces = 12)")
        if is_num(p.get('lon')) and is_int(p.get('sign_num')) and int(p['lon'] // 30) + 1 != p['sign_num']:
            probs.append(f"{g}: lon {p['lon']} lies in sign {int(p['lon'] // 30) + 1}, not sign_num {p['sign_num']}")
    R.check('sign numbers 1-12 agree with sign names and longitudes', probs)
    probs = []
    for g, p in list(P.items()) + ([('lagna', lg)] if lg else []):
        v = p.get('vargas') or {}
        if isinstance(v, dict) and 'D1' in v and v['D1'] != p.get('sign'): probs.append(f"{g}: vargas.D1 {v['D1']} differs from sign {p.get('sign')}")
        if is_num(p.get('lon')) and isinstance(v, dict) and v.get('D9') in SIGNS:
            d9 = int(p['lon'] // (10 / 3)) % 12
            if SIGNS[d9] != v['D9']: probs.append(f"{g}: D9 {v['D9']}, but the standard navamsa of lon {p['lon']} is {SIGNS[d9]}")
    R.check('vargas: D1 equals the sign, D9 matches the standard navamsa of the longitude', probs, 'warning')
    probs = []
    for g, p in list(P.items()) + ([('lagna', lg)] if lg else []):
        nk = p.get('nakshatra')
        if isinstance(nk, str) and nk not in NAKSHATRAS:
            probs.append(f"{g}: nakshatra {nk!r} is not one of the 27 spellings the library uses (e.g. 'Purva Phalguni', 'Dhanishta'); its entry will be missing")
        if is_num(p.get('lon')) and nk in NAKSHATRAS:
            i = int(p['lon'] // (40 / 3)) % 27
            if NAKSHATRAS[i] != nk: probs.append(f"{g}: nakshatra {nk}, but lon {p['lon']} falls in {NAKSHATRAS[i]}")
            elif is_int(p.get('pada')) and int((p['lon'] % (40 / 3)) // (10 / 3)) + 1 != p['pada']:
                probs.append(f"{g}: pada {p['pada']}, but lon {p['lon']} gives pada {int((p['lon'] % (40 / 3)) // (10 / 3)) + 1}")
        if g != 'lagna' and nk in NAKSHATRAS and p.get('nak_lord') in GRAHAS and ORDER[NAKSHATRAS.index(nk) % 9] != p['nak_lord']:
            probs.append(f"{g}: nak_lord {p['nak_lord']}, but the lord of {nk} is {ORDER[NAKSHATRAS.index(nk) % 9]}")
    R.check('nakshatra names, padas and lords agree with the longitudes', probs, 'warning')
    probs = []
    if 'Rahu' in P and 'Ketu' in P and is_int(P['Rahu'].get('sign_num')) and is_int(P['Ketu'].get('sign_num')):
        if (P['Rahu']['sign_num'] - P['Ketu']['sign_num']) % 12 != 6: probs.append('Rahu and Ketu are not in opposite signs')
        elif is_num(P['Rahu'].get('lon')) and is_num(P['Ketu'].get('lon')):
            d = abs((P['Rahu']['lon'] - P['Ketu']['lon']) % 360 - 180)
            if d > 1: probs.append(f'Rahu and Ketu are {180 - d:.1f} deg apart instead of 180')
    R.check('Ketu is exactly opposite Rahu', probs)
    probs = []
    for g, p in P.items():
        if g in EXALT and is_int(p.get('sign_num')) and p.get('dignity') in DIGNITIES:
            s = p['sign_num'] - 1; dg = p['dignity']
            if s == (EXALT[g] + 6) % 12 and dg != 'debilitated': probs.append(f'{g} in {SIGNS[s]} is debilitated, dignity says {dg}')
            if dg == 'debilitated' and s != (EXALT[g] + 6) % 12: probs.append(f'{g} dignity debilitated but {SIGNS[s]} is not its debilitation sign')
            if dg == 'exalted' and s != EXALT[g]: probs.append(f'{g} dignity exalted but {SIGNS[s]} is not its exaltation sign')
            if dg == 'own' and SIGN_LORD[s] != g and not (g == 'Mercury' and s == 5): probs.append(f'{g} dignity own but {SIGNS[s]} is ruled by {SIGN_LORD[s]}')
    R.check('dignity agrees with the sign (exaltation, debilitation, own sign)', probs, 'warning')

    # ---------------- houses ----------------
    hs = ch.get('houses')
    H = {}
    if not isinstance(hs, list):
        R.err('houses: missing; give a list of 12 house objects (house, sign, lord, lord_in_house, lord_in_sign, lord_dignity, occupants, aspected_by)')
        hs = []
    probs = []
    for x in hs:
        if not isinstance(x, dict) or not is_int(x.get('house')) or not 1 <= x['house'] <= 12:
            probs.append(f'an entry has no integer "house" 1-12: {str(x)[:60]}'); continue
        if x['house'] in H: probs.append(f"house {x['house']} appears twice")
        H[x['house']] = x
        for k, t in (('sign', str), ('lord', str), ('lord_in_house', int), ('lord_in_sign', str), ('occupants', list), ('aspected_by', list)):
            if not isinstance(x.get(k), t) or isinstance(x.get(k), bool): probs.append(f"house {x['house']}: {k} missing or not a {t.__name__}")
        if 'lord_dignity' not in x: probs.append(f"house {x['house']}: lord_dignity missing")
    if hs and sorted(H) != list(range(1, 13)): probs.append(f'houses present: {sorted(H)}; need exactly 1-12')
    R.check('houses: 12 entries numbered 1-12 with every field', probs)
    probs, wprobs = [], []
    if L is not None and len(H) == 12:
        if H[1].get('sign') != lg.get('sign'): probs.append(f"house 1 sign {H[1].get('sign')} differs from lagna sign {lg.get('sign')}")
        for h, x in H.items():
            s = (L + h - 1) % 12
            if x.get('sign') != SIGNS[s]: probs.append(f"house {h}: sign {x.get('sign')}, whole-sign from {SIGNS[L]} gives {SIGNS[s]}")
            if x.get('lord') != SIGN_LORD[s]: probs.append(f"house {h}: lord {x.get('lord')}, the lord of {SIGNS[s]} is {SIGN_LORD[s]}")
            lp = P.get(SIGN_LORD[s])
            if lp and is_int(lp.get('sign_num')):
                lh = (lp['sign_num'] - 1 - L) % 12 + 1
                if x.get('lord_in_house') != lh: probs.append(f"house {h}: lord_in_house {x.get('lord_in_house')}, but {SIGN_LORD[s]} is in house {lh}")
                if x.get('lord_in_sign') != lp.get('sign'): probs.append(f"house {h}: lord_in_sign {x.get('lord_in_sign')}, but {SIGN_LORD[s]} is in {lp.get('sign')}")
                if x.get('lord_dignity') != lp.get('dignity'): wprobs.append(f"house {h}: lord_dignity {x.get('lord_dignity')}, planet says {lp.get('dignity')}")
            occ = sorted((g for g, p in P.items() if p.get('sign_num') == s + 1), key=GRAHAS.index)
            got = sorted((o for o in x.get('occupants') or [] if o in GRAHAS), key=GRAHAS.index)
            if occ != got: probs.append(f"house {h}: occupants {got}, planets in {SIGNS[s]} are {occ}")
            asp = sorted((g for g, p in P.items() if is_int(p.get('sign_num')) and ((s - (p['sign_num'] - 1)) % 12 + 1) in ASP.get(g, [7])), key=GRAHAS.index)
            got = sorted((o for o in x.get('aspected_by') or [] if o in GRAHAS), key=GRAHAS.index)
            if asp != got: wprobs.append(f"house {h}: aspected_by {got}; the pipeline's rule (all 7th; Mars 4/8, Jupiter 5/9, Saturn 3/10, nodes 5/9) gives {asp}")
        for g, p in P.items():
            if is_int(p.get('house')) and is_int(p.get('sign_num')) and p['house'] != (p['sign_num'] - 1 - L) % 12 + 1:
                probs.append(f"{g}: house {p['house']}, whole-sign from the lagna gives {(p['sign_num'] - 1 - L) % 12 + 1}")
    R.check('whole-sign houses agree with the lagna and the planets (signs, lords, lord placements, occupants)', probs)
    R.check('house aspects and lord dignities match the pipeline rules', wprobs, 'warning')

    # ---------------- vimshottari ----------------
    vm = ch.get('vimshottari')
    mds = []
    if not isinstance(vm, dict):
        R.err('vimshottari: missing (an object with balance_at_birth and mahadashas; antardashas_by_md strongly recommended)'); vm = {}
    else:
        bal = vm.get('balance_at_birth')
        if not isinstance(bal, dict) or bal.get('lord') not in GRAHAS or not is_num(bal.get('years')):
            R.err('vimshottari.balance_at_birth: must be {"lord": <graha>, "years": <number>}')
        mds = vm.get('mahadashas')
        if not isinstance(mds, list) or not mds:
            R.err('vimshottari.mahadashas: missing or empty (list of {md, start, end})'); mds = []
    probs, wprobs = [], []
    good = []
    for i, m in enumerate(mds):
        if not isinstance(m, dict) or m.get('md') not in GRAHAS or not iso_ok(m.get('start')) or not iso_ok(m.get('end')):
            probs.append(f'mahadasha #{i + 1} must be {{"md": <graha>, "start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}}, got {str(m)[:80]}'); continue
        if m['start'] >= m['end']: probs.append(f"{m['md']} mahadasha starts {m['start']} but ends {m['end']}")
        good.append(m)
    if len(good) == len(mds) and good:
        for a, c in zip(good, good[1:]):
            if ORDER[(ORDER.index(a['md']) + 1) % 9] != c['md']: probs.append(f"{c['md']} follows {a['md']}; Vimshottari order is {' > '.join(ORDER)}")
            if a['end'] != c['start']:
                n = abs(days(a['end'], c['start']))
                (wprobs if n <= 1 else probs).append(f"{a['md']} ends {a['end']} but {c['md']} starts {c['start']} ({'gap' if c['start'] > a['end'] else 'overlap'} of {n} day(s))")
        for m in good[1:]:
            exp = YEARS[m['md']] * 365.25; got = days(m['start'], m['end'])
            if abs(got - exp) > 3: wprobs.append(f"{m['md']} mahadasha lasts {got} days; {YEARS[m['md']]} years of 365.25 days is {exp:.0f}")
        bd = b.get('date') if iso_ok(b.get('date')) else None
        bal = vm.get('balance_at_birth') or {}
        if bd:
            if not good[0]['start'] <= bd < good[0]['end']: probs.append(f"birth date {bd} is not inside the first mahadasha ({good[0]['start']} to {good[0]['end']})")
            elif is_num(bal.get('years')) and abs(days(bd, good[0]['end']) / 365.25 - bal['years']) > 0.02:
                wprobs.append(f"balance_at_birth {bal['years']} years, but birth to the end of the first mahadasha is {days(bd, good[0]['end']) / 365.25:.3f}")
        if bal.get('lord') in GRAHAS and bal.get('lord') != good[0]['md']: probs.append(f"balance_at_birth lord {bal['lord']} is not the first mahadasha lord {good[0]['md']}")
        if len(good) < 9: wprobs.append(f'only {len(good)} mahadashas; the mahadasha table shows these only')
    R.check('mahadashas: ISO dates, Vimshottari order, contiguous, birth inside the first', probs)
    R.check('mahadasha lengths and balance at birth', wprobs, 'warning')
    abm = vm.get('antardashas_by_md')
    probs, wprobs = [], []
    if not abm:
        R.warn('vimshottari.antardashas_by_md: missing; the timeline falls back to date-level sub-periods (can be a day off), '
               'the "Periods ahead" lists in every section and the 10-year summary rows for sub-periods are left out, and the running '
               'sub-period in each section header reads "None"')
        if not vm.get('current_md_antardashas'): R.warn('vimshottari.current_md_antardashas: also missing; the sub-period table is skipped')
    elif not isinstance(abm, dict):
        probs.append('antardashas_by_md must be an object {mahadasha lord: [ {ad, start, end} x 9 ]}')
    else:
        byname = {m['md']: m for m in good}
        for md, ads in abm.items():
            if md not in GRAHAS: probs.append(f'key {md!r} is not a graha'); continue
            if not isinstance(ads, list) or any(not isinstance(a, dict) or a.get('ad') not in GRAHAS or not iso_ok(a.get('start')) or not iso_ok(a.get('end')) for a in ads):
                probs.append(f'{md}: every sub-period must be {{"ad": <graha>, "start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}}'); continue
            want = [ORDER[(ORDER.index(md) + k) % 9] for k in range(9)]
            if [a['ad'] for a in ads] != want: probs.append(f"{md}: sub-periods {[a['ad'] for a in ads]}, expected {want}")
            for a, c in zip(ads, ads[1:]):
                if a['end'] != c['start']:
                    n = abs(days(a['end'], c['start']))
                    (wprobs if n <= 1 else probs).append(f"{md}-{a['ad']} ends {a['end']} but {md}-{c['ad']} starts {c['start']}")
            m = byname.get(md)
            if not m: probs.append(f'{md}: no matching mahadasha in mahadashas'); continue
            for lab, x, y in (('first sub-period start', ads[0]['start'], m['start']), ('last sub-period end', ads[-1]['end'], m['end'])):
                if x != y:
                    (wprobs if abs(days(x, y)) <= 1 else probs).append(f'{md}: {lab} {x} differs from the mahadasha date {y}')
        miss = [m['md'] for m in good if m['md'] not in abm]
        if miss: wprobs.append(f"no sub-periods for the {', '.join(miss)} mahadasha(s); the timeline computes them at date level")
    R.check('sub-periods (antardashas_by_md): 9 per mahadasha, in order, contiguous, matching the mahadasha dates', probs)
    if wprobs: R.check('sub-period dates within one day', wprobs, 'warning')
    cur = vm.get('current_md_antardashas')
    if cur is not None and (not isinstance(cur, list) or any(not isinstance(a, dict) or a.get('ad') not in GRAHAS or not iso_ok(a.get('start')) or not iso_ok(a.get('end')) for a in cur)):
        R.err('vimshottari.current_md_antardashas: must be a list of {ad, start, end} with ISO dates')

    # ---------------- transits, "now" ----------------
    tks = [k for k in ch if k.startswith('transits_')]
    tr = None
    if not tks:
        R.err('transits_YYYY_MM_DD: missing; give the sidereal positions on the "as of" date under a key such as transits_2026_11_11 '
              '(Jupiter and Saturn required); its date is the default "now" of the whole pipeline')
    else:
        if len(tks) > 1: R.warn(f"several transits_ keys ({', '.join(tks)}); only the first, {tks[0]}, is used")
        m = TRANSIT_KEY.match(tks[0])
        if not m or not iso_ok(f'{m.group(1)}-{m.group(2)}-{m.group(3)}'):
            R.err(f'{tks[0]}: the key must be transits_YYYY_MM_DD with a valid date')
        else:
            now = now or f'{m.group(1)}-{m.group(2)}-{m.group(3)}'
        tr = ch[tks[0]]
        if not isinstance(tr, dict):
            R.err(f'{tks[0]}: must be an object {{planet: {{sign, house_from_lagna, house_from_moon, deg?, retro?}}}}'); tr = None
    now = now or D.date.today().isoformat()
    if tr is not None:
        for g in ('Jupiter', 'Saturn'):
            if g not in tr: R.err(f'{tks[0]}.{g}: missing; the slow-transit, double-transit and Sade Sati timing needs it')
        miss = [g for g in GRAHAS if g not in tr and not (g == 'Ketu' and 'Rahu' in tr)]
        if miss: R.warn(f"{tks[0]}: no entry for {', '.join(miss)}; those rows are left out of the current-transits table and of the vedha check")
        probs = []
        moon_s = P.get('Moon', {}).get('sign_num')
        for g, x in tr.items():
            if not isinstance(x, dict) or x.get('sign') not in SIGNS or not is_int(x.get('house_from_lagna')) or not is_int(x.get('house_from_moon')):
                R.err(f'{tks[0]}.{g}: needs sign (English), house_from_lagna and house_from_moon (integers 1-12)'); continue
            s = SIGNS.index(x['sign'])
            if L is not None and x['house_from_lagna'] != (s - L) % 12 + 1: probs.append(f"{g} in {x['sign']}: house_from_lagna {x['house_from_lagna']}, expected {(s - L) % 12 + 1}")
            if is_int(moon_s) and x['house_from_moon'] != (s - moon_s + 1) % 12 + 1: probs.append(f"{g} in {x['sign']}: house_from_moon {x['house_from_moon']}, expected {(s - moon_s + 1) % 12 + 1}")
            if 'deg' in x and x['deg'] is not None and (not is_num(x['deg']) or not 0 <= x['deg'] < 30): probs.append(f"{g}: deg must be degrees within the sign (0-30), got {x['deg']!r}")
        R.check('transits: houses counted from the lagna and the Moon agree with the signs', probs)
    for key, g in (('jupiter_ingresses_next_6y', 'Jupiter'), ('saturn_ingresses_next_6y', 'Saturn')):
        ev = ch.get(key)
        if ev is None:
            R.warn(f'{key}: missing; the slow-planet sign-change table is skipped, {g} is assumed to stay in its present sign for the next year only, '
                   'and the double-transit windows and transit stretches end after one year')
            continue
        probs = []
        if not isinstance(ev, list): probs.append('must be a list of [date, sign, house_from_lagna]')
        else:
            for i, e in enumerate(ev):
                if not isinstance(e, list) or len(e) != 3 or not iso_ok(e[0]) or e[1] not in SIGNS or not is_int(e[2]):
                    probs.append(f'item {i + 1} must be ["YYYY-MM-DD", "<Sign>", <house from lagna 1-12>], got {e!r}'); continue
                if L is not None and e[2] != (SIGNS.index(e[1]) - L) % 12 + 1: probs.append(f'item {i + 1}: {e[1]} is house {(SIGNS.index(e[1]) - L) % 12 + 1} from the lagna, not {e[2]}')
            ds = [e[0] for e in ev if isinstance(e, list) and e and iso_ok(e[0])]
            if ds != sorted(ds): probs.append('dates are not in ascending order')
            if ds and ds[0] < now: probs.append(f'first date {ds[0]} is before the "as of" date {now}')
        R.check(f'{key}: [ISO date, sign, house] items in date order after the "as of" date', probs)
    probs = []
    if good:
        if not good[0]['start'] <= now < good[-1]['end']: probs.append(f'"as of" date {now} is outside the mahadashas ({good[0]["start"]} to {good[-1]["end"]})')
        if isinstance(abm, dict) and abm and not any(isinstance(a, dict) and iso_ok(a.get('start')) and iso_ok(a.get('end')) and a['start'] <= now < a['end']
                                                     for ads in abm.values() if isinstance(ads, list) for a in ads):
            probs.append(f'no sub-period in antardashas_by_md covers the "as of" date {now}')
    R.check(f'the "as of" date {now} falls inside the dasha data', probs)

    # ---------------- optional blocks ----------------
    pc = ch.get('panchang_at_birth')
    if not isinstance(pc, dict) or not pc:
        R.warn('panchang_at_birth: missing; the Moon counts as waning in dasha conditions (moon_waxing false), the birth tithi, weekday, '
               'nitya yoga and karana entries are left out of Personality, and the panchang table loses those rows')
    else:
        if str(pc.get('paksha', '')).split(' ')[0].lower() not in ('shukla', 'krishna'):
            R.warn(f"panchang_at_birth.paksha: {pc.get('paksha')!r} is not 'Shukla' or 'Krishna'; the Moon counts as waning in dasha conditions")
        if 'tithi_num' in pc and not (is_int(pc['tithi_num']) and 1 <= pc['tithi_num'] <= 30): R.err(f"panchang_at_birth.tithi_num: must be 1-30, got {pc['tithi_num']!r}")
        for k in ('tithi_num', 'vara', 'nitya_yoga', 'karana'):
            if not pc.get(k): R.warn(f'panchang_at_birth.{k}: missing; its library entry is left out of Personality')
        if lib is not None:
            for k, pre in (('vara', 'panchang/vara/'), ('nitya_yoga', 'panchang/nitya_yoga/'), ('karana', 'panchang/karana/')):
                if pc.get(k) and f'{pre}{slug(pc[k])}' not in lib: R.warn(f"panchang_at_birth.{k}: {pc[k]!r} has no library entry {pre}{slug(pc[k])} (spelling?)")
    av = ch.get('avakhada')
    if not isinstance(av, dict) or not av:
        R.warn('avakhada: missing; the gana and nadi entries are left out of Personality and the avakhada rows of the panchang table are skipped')
    elif lib is not None:
        for k in ('gana', 'nadi'):
            if av.get(k) and f'panchang/{k}/{slug(av[k])}' not in lib: R.warn(f"avakhada.{k}: {av[k]!r} has no library entry panchang/{k}/{slug(av[k])}")
    gy = ch.get('graha_yuddha')
    if gy is None: R.warn('graha_yuddha: missing; no planetary-war notes in the D1 table (give [] when there is none)')
    elif not isinstance(gy, list) or any(not isinstance(w, dict) or not isinstance(w.get('planets'), list) for w in gy):
        R.err('graha_yuddha: must be a list of {"planets": [p, q], "winner_by_latitude": p}')
    yg = ch.get('yogini_current_and_next')
    if not yg: R.warn('yogini_current_and_next: missing; the Yogini periods are left out of the timeline')
    else:
        probs = []
        for y in yg if isinstance(yg, list) else [yg]:
            if not isinstance(y, dict) or y.get('planet') not in GRAHAS or not iso_ok(y.get('start')) or not iso_ok(y.get('end')) or not isinstance(y.get('yogini'), str):
                probs.append(f'each item needs yogini, planet (a graha), start, end (ISO); got {str(y)[:80]}')
            elif y['yogini'] not in YOGINIS: R.warn(f"yogini {y['yogini']!r}: no library entry (names: {', '.join(sorted(YOGINIS))})")
        R.check('yogini_current_and_next items', probs)
    cr = ch.get('chara_current_and_next')
    if not cr: R.warn('chara_current_and_next: missing; the Chara periods table and the Chara line in Relationships are skipped')
    else:
        probs = [f'each item needs sign, start, end (ISO); got {str(c)[:80]}' for c in (cr if isinstance(cr, list) else [cr])
                 if not isinstance(c, dict) or not isinstance(c.get('sign'), str) or not iso_ok(c.get('start')) or not iso_ok(c.get('end'))]
        for c in cr if isinstance(cr, list) else []:
            if isinstance(c, dict) and isinstance(c.get('sign'), str) and c['sign'] not in SIGNS and c['sign'].lower() not in SANSKRIT_SIGNS:
                probs.append(f"sign {c['sign']!r} is neither an English nor a Sanskrit sign name")
        R.check('chara_current_and_next items', probs)
    yp = ch.get('yogas_present')
    if yp is None: R.warn('yogas_present: missing; the yoga table and every yoga entry are left out (give [] when none formed)')
    elif not isinstance(yp, list): R.err('yogas_present: must be a list of {name, conditions}')
    else:
        if not yp: R.warn('yogas_present: empty; the yoga table is skipped')
        for y in yp:
            if not isinstance(y, dict) or not isinstance(y.get('name'), str):
                R.err(f'yogas_present: each item needs a string name, got {str(y)[:80]}'); continue
            if 'conditions' in y and not isinstance(y['conditions'], dict): R.err(f"yogas_present {y['name']!r}: conditions must be an object")
            if y['name'].startswith('Neecha Bhanga'):
                g = y['name'][y['name'].find('(') + 1:y['name'].find(')')] if '(' in y['name'] else ''
                if g not in GRAHAS: R.err(f"yogas_present {y['name']!r}: name must be 'Neecha Bhanga (<Planet>)'")
                if not isinstance(y.get('conditions'), dict): R.err(f"yogas_present {y['name']!r}: needs a conditions object with c1_..c6_ flags")
            s = yoga_slug(y['name'])
            if lib is not None and s and f'yoga/{s}' not in lib:
                R.warn(f"yogas_present {y['name']!r}: no library entry yoga/{s}; it is named as a fact only (see the name list in docs/CHART_DATA_FORMAT.md)")
    if 'yogas_checked_absent' not in ch: R.warn('yogas_checked_absent: missing (informational only; no tool reads it yet)')
    ds = ch.get('doshas')
    if not isinstance(ds, dict) or not ds:
        R.warn('doshas: missing; the Manglik check, the dosha table, every dosha entry and the Sade Sati phases are left out')
    else:
        m = ds.get('manglik')
        if m is None: R.warn('doshas.manglik: missing; the Manglik check table and the Manglik verdict are left out')
        elif isinstance(m, dict):
            for k in ('mars_house', 'hits', 'is_manglik_any'):
                if k not in m: R.warn(f'doshas.manglik.{k}: missing; the Manglik verdict is incomplete')
            mh = (m.get('mars_house') or {}).get('lagna')
            if is_int(mh) and 'Mars' in P and L is not None and is_int(P['Mars'].get('sign_num')) and mh != (P['Mars']['sign_num'] - 1 - L) % 12 + 1:
                R.err(f"doshas.manglik.mars_house.lagna is {mh}, but Mars is in house {(P['Mars']['sign_num'] - 1 - L) % 12 + 1}")
        elif m is not False:
            R.warn('doshas.manglik: use the object form (see the format doc); a bare flag gives no Manglik verdict')
        ks = ds.get('kaal_sarp')
        if ks is True:
            R.warn('doshas.kaal_sarp: true as a bare flag; the dosha table says Present but the section input reads it as NOT present. Use the object form ({"mean": {...}})')
        for k, d in ds.items():
            if k == 'sade_sati': continue
            if lib is not None and d not in (False, None) and f'dosha/{k}' not in lib: R.warn(f'doshas.{k}: no library entry dosha/{k}; it is named as a fact only')
        ss = ds.get('sade_sati')
        if ss is None: R.warn('doshas.sade_sati: missing; the Sade Sati and Dhaiya phases are left out of the timeline, Mind, Guidance and the 10-year summary')
        else:
            probs = []
            iv = ss.get('intervals') if isinstance(ss, dict) else None
            if not isinstance(iv, list): probs.append('needs "intervals": a list of {phase, saturn_in, start, end, current}')
            else:
                for i in iv:
                    if not isinstance(i, dict) or not isinstance(i.get('phase'), str) or i.get('saturn_in') not in SIGNS or not iso_ok(i.get('start')) or not iso_ok(i.get('end')):
                        probs.append(f'interval needs phase, saturn_in (English sign), start, end (ISO): {str(i)[:80]}'); continue
                    if not any(w in i['phase'].lower() for w in ('rising', 'peak', 'setting', 'kantaka', 'ashtama')):
                        probs.append(f"phase {i['phase']!r} names none of rising/peak/setting/kantaka/ashtama, so it gets no library entry")
                st_ = [i['start'] for i in iv if isinstance(i, dict) and iso_ok(i.get('start'))]
                if st_ != sorted(st_): probs.append('intervals are not in date order')
            if isinstance(ss, dict) and 'Moon' in P and ss.get('moon_sign') not in (None, P['Moon'].get('sign')):
                probs.append(f"moon_sign {ss.get('moon_sign')} differs from the Moon's sign {P['Moon'].get('sign')}")
            R.check('doshas.sade_sati intervals', probs)
    if lib is not None:
        if lg.get('sign') in SIGNS and f"rising_sign/{lg['sign'].lower()}" not in lib: R.warn('library: no rising_sign entry for the lagna')
    return R, now


def print_report(path, R, now, quiet=False):
    print(f'{path}  (as of {now})')
    if R.errors:
        print(f'\nERRORS ({len(R.errors)}): the pipeline would stop or print wrong facts')
        for e in R.errors: print(f'  - {e}')
    if R.warnings:
        print(f'\nWARNINGS ({len(R.warnings)}): the report runs, but these features are skipped or reduced')
        for w in R.warnings: print(f'  - {w}')
    if not quiet:
        print('\nSANITY CHECKS')
        for name, probs, sev in R.checks:
            print(f"  {'ok  ' if not probs else 'FAIL' if sev == 'error' else 'warn'}  {name}" + (f' ({len(probs)} problem(s), listed above)' if probs else ''))
    print(f"\nRESULT: {'FAILED' if R.errors else 'passed'} with {len(R.errors)} error(s) and {len(R.warnings)} warning(s)\n")


def schema_errors(ch):
    try:
        import jsonschema
    except ImportError:
        return None
    schema = json.load(open(os.path.join(ROOT, 'docs', 'chart_data.schema.json'), encoding='utf-8'))
    v = jsonschema.Draft202012Validator(schema)
    msg = lambda e: ('needs ' + e.schema.get('description', 'a different shape') if e.validator in ('not', 'allOf') and isinstance(e.schema, dict)
                     else e.message[:200])
    return [f"schema: {'/'.join(map(str, e.absolute_path)) or '(top)'}: {msg(e)}" for e in sorted(v.iter_errors(ch), key=lambda e: list(map(str, e.absolute_path)))]


def main():
    ap = argparse.ArgumentParser(description='Check a chart_data.json before running the report pipeline.')
    ap.add_argument('charts', nargs='+'); ap.add_argument('--now', help='as-of date YYYY-MM-DD (default: the transits_ key date)')
    ap.add_argument('--strict', action='store_true'); ap.add_argument('--schema', action='store_true'); ap.add_argument('--quiet', action='store_true')
    a = ap.parse_args()
    if a.now and not iso_ok(a.now): ap.error('--now must be YYYY-MM-DD')
    lib_path = os.path.join(ROOT, 'library.json')
    lib = json.load(open(lib_path, encoding='utf-8')) if os.path.exists(lib_path) else None
    code = 0
    for path in a.charts:
        try:
            ch = json.load(open(path, encoding='utf-8'))
        except (OSError, ValueError) as e:
            print(f'{path}: cannot read as JSON ({e})\n'); code = max(code, 2); continue
        R, now = validate(ch, a.now, lib)
        if a.schema:
            se = schema_errors(ch)
            if se is None: R.warn('--schema: the jsonschema package is not installed; schema check skipped')
            else: R.errors += se
        print_report(path, R, now, a.quiet)
        if R.errors or (a.strict and R.warnings): code = max(code, 1)
    sys.exit(code)


if __name__ == '__main__':
    main()
