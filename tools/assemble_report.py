"""Assemble the long kundli report: model-written sections + code-built tables, charts and sources -> HTML (+ PDF).

  python -I tools/assemble_report.py --chart chart_data.json --sections DIR --name "Name" --out report.html
         [--pdf report.pdf] [--chart-style north|south] [--prepared "3 November 2026"]

DIR holds the model's section files: glance.md, personality.md, mind.md, career.md, finance.md, health.md,
relationships.md, family.md, spirituality.md, yogas.md, timeline.md, guidance.md (any missing one is skipped and listed).
Code adds: the cover, contents (with a fixed subtitle per section), the D1 and D9 charts (North Indian, or South Indian
with --chart-style south), every numbered table from tools/report_tables.py and tools/table_rows.py (each optional: a
module that is missing or fails is skipped with a note), and the Sources section built from the ids in every section's
hidden trace block (via library.json source_views). Hidden trace and rows blocks are removed from the visible report.

Tables: each module's build(chart, F, now, lib, sections_md) returns {key: {"title", "html", "note"?}}; SLOTS below says
which section and subsection each key goes into. Captions "Table N. <title>" are numbered in document order. Where a code
table lands in a subsection that still holds the model's own Markdown table (older timeline sections), the code table
replaces it. An entry with "replace": true replaces the first list in its subsection instead (used for summary_10y).

Styling: tools/report_assets/report.css; fonts (OFL) in tools/report_assets/fonts are embedded into the HTML as data
URIs, so the HTML is self-contained and the PDF needs no network. PDF: Playwright Chromium (bundled browser, else the
installed Edge/Chrome via Playwright channels), else headless Edge/Chrome/Chromium on the command line. Page numbers and
the running header come from CSS @page margin boxes (Chromium 131+).
"""
import argparse, base64, html, importlib, json, os, re, shutil, subprocess, sys, datetime as D
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, 'tools', 'report_assets')
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import dasha_facts as DF

ORDER = [('glance', 'Chart at a glance'), ('personality', 'Personality and temperament'), ('mind', 'Mind, emotions and inner life'),
         ('career', 'Career and vocation'), ('finance', 'Finance and wealth'), ('health', 'Health and vitality'),
         ('relationships', 'Relationships, marriage and partner'), ('family', 'Family, home, siblings, children and education'),
         ('spirituality', 'Spirituality, hidden talents and foreign links'), ('yogas', 'Yogas and doshas'),
         ('timeline', 'Timeline'), ('guidance', 'Strengths, challenges and guidance')]
SUBTITLE = {'glance': 'charts, positions, defining themes', 'personality': 'lagna, lagna lord, Sun, birth day',
            'mind': 'the Moon and Mercury', 'career': '10th house, D10, profession indicators',
            'finance': '2nd, 11th, 5th, 9th and 12th houses', 'health': 'traditional indicators',
            'relationships': '7th house, Venus, D9, Manglik', 'family': '4th, 3rd, 5th and 9th houses',
            'spirituality': '8th, 9th and 12th houses, karakamsha', 'yogas': 'what formed, and how much it weighs',
            'timeline': 'dashas, transits, Yogini and Chara', 'guidance': 'strengths, challenges, optional remedies',
            'sources': 'classical texts and modern authors'}
ABBR = {'Sun': 'Su', 'Moon': 'Mo', 'Mars': 'Ma', 'Mercury': 'Me', 'Jupiter': 'Ju', 'Venus': 'Ve', 'Saturn': 'Sa', 'Rahu': 'Ra',
        'Ketu': 'Ke', 'Gulika': 'Gk'}
NODES = ('Rahu', 'Ketu', 'Gulika')
SIGN_NAMES = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces']
SIGN_SHORT = ['Ari', 'Tau', 'Gem', 'Can', 'Leo', 'Vir', 'Lib', 'Sco', 'Sag', 'Cap', 'Aqu', 'Pis']
UP, DOWN = '\u2191', '\u2193'
# North Indian layout (house -> sign-number position, planet-label position), from the benchmark chart
SIGN_POS = {1: (200, 186), 2: (100, 88), 3: (84, 104), 4: (184, 204), 5: (84, 304), 6: (100, 324), 7: (200, 226), 8: (300, 324),
            9: (318, 304), 10: (218, 204), 11: (318, 104), 12: (300, 88)}
PL_POS = {1: (200, 92), 2: (100, 42), 3: (38, 104), 4: (88, 204), 5: (38, 304), 6: (100, 372), 7: (200, 308), 8: (300, 360),
          9: (362, 304), 10: (312, 204), 11: (362, 104), 12: (300, 42)}
# South Indian layout: fixed sign boxes (sign index -> column, row) on a 4x4 grid, Pisces top left, running clockwise
SOUTH_CELL = {11: (0, 0), 0: (1, 0), 1: (2, 0), 2: (3, 0), 3: (3, 1), 4: (3, 2), 5: (3, 3), 6: (2, 3), 7: (1, 3), 8: (0, 3),
              9: (0, 2), 10: (0, 1)}

# Where each code table goes: (key, section, [anchor options tried in order]).
#   ('charts',)            glance: after the intro paragraph(s), following the charts
#   ('head', [needles])    after the first h3/h4 whose text contains a needle (needles tried in order); a fallback needle
#                          (not the first) places the table after that subsection's first paragraph instead
#   ('start', [needles])   same, but the heading text must start with the needle
#   ('first_para',)        after the section's first paragraph
#   ('after', key)         right after another table that has been placed
#   ('end',)               end of the section
SLOTS = [
    ('d1_positions', 'glance', [('charts',)]),
    ('houses', 'glance', [('charts',)]),
    ('d9_positions', 'glance', [('charts',)]),
    ('functional_roles', 'glance', [('charts',)]),
    ('panchang_avakhada', 'personality', [('head', ['weekday', 'birth']), ('end',)]),
    ('baladi_avasthas', 'personality', [('end',)]),
    ('profession_indicators', 'career', [('head', ['field', 'suit']), ('end',)]),
    ('d10_positions', 'career', [('head', ['D10']), ('end',)]),
    ('wealth_houses', 'finance', [('first_para',)]),
    ('body_correspondences', 'health', [('first_para',)]),
    ('manglik_check', 'relationships', [('head', ['manglik']), ('end',)]),
    ('yogas_present', 'yogas', [('first_para',)]),
    ('dosha_checks', 'yogas', [('start', ['dosha']), ('end',)]),
    ('mahadashas', 'timeline', [('head', ['mahadasha table', 'how timing works']), ('end',)]),
    ('antardashas', 'timeline', [('head', ['sub-period']), ('end',)]),
    ('current_transits', 'timeline', [('head', ['transit']), ('end',)]),
    ('slow_ingresses', 'timeline', [('after', 'current_transits'), ('head', ['transit']), ('end',)]),
    ('summary_10y', 'timeline', [('head', ['next ten years']), ('end',)]),
    ('chara_periods', 'timeline', [('end',)]),
    ('remedies', 'guidance', [('head', ['remed']), ('end',)]),
]
REPLACES_MODEL_TABLE = {'mahadashas', 'antardashas'}
TABLE_MODULES = ('report_tables', 'table_rows')


# ---------- minimal Markdown -> HTML ----------
def inline(t):
    t = html.escape(t, quote=False)
    t = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', t)
    t = re.sub(r'(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])', r'<em>\1</em>', t)
    t = re.sub(r'`([^`]+)`', r'\1', t)
    return t


def strip_hidden(md):
    """Remove trace blocks, rows blocks and any other HTML comment from the visible text."""
    md = re.sub(r'(?s)<!--\s*rows:.*?-->', '', md)
    md = re.sub(r'(?s)<!--\s*trace.*?-->', '', md)
    return re.sub(r'(?s)<!--.*?-->', '', md)


def md_blocks(md, num=None):
    out, para, lst, table = [], [], None, []

    def flush():
        nonlocal para, lst, table
        if para: out.append('<p>' + inline(' '.join(para)) + '</p>'); para = []
        if lst: out.append(f'<{lst[0]}>' + ''.join(f'<li>{inline(x)}</li>' for x in lst[1]) + f'</{lst[0]}>'); lst = None
        if table:
            cells = [[c.strip() for c in r.strip().strip('|').split('|')] for r in table if not re.fullmatch(r'[\s|:\-]+', r)]
            if cells:
                h = '<tr>' + ''.join(f'<th>{inline(c)}</th>' for c in cells[0]) + '</tr>'
                b = ''.join('<tr>' + ''.join(f'<td>{inline(c)}</td>' for c in r) + '</tr>' for r in cells[1:])
                out.append(f'<table class="long"><thead>{h}</thead><tbody>{b}</tbody></table>')
            table = []
    for line in md.split('\n'):
        s = line.rstrip()
        if not s.strip(): flush(); continue
        if s.startswith('|'): para and flush(); table.append(s); continue
        elif table: flush()
        m = re.match(r'^(#{2,4})\s+(.*)', s)
        if m:
            flush(); lvl = len(m.group(1)); text = m.group(2)
            if lvl == 2:
                clean = inline(re.sub(r'^\d+\s*', '', text))
                out.append(f'<h2><span class="num">{num}</span>{clean}</h2>' if num else f'<h2>{clean}</h2>')
            else:
                out.append(f'<h{lvl}>{inline(text)}</h{lvl}>')
            continue
        m = re.match(r'^\s*([-*]|\d+[.)])\s+(.*)', s)
        if m:
            kind = 'ol' if m.group(1)[0].isdigit() else 'ul'
            if para: flush()
            if lst and lst[0] != kind: flush()
            if not lst: lst = (kind, [])
            lst[1].append(m.group(2)); continue
        if lst and line.startswith('  '): lst[1][-1] += ' ' + s.strip(); continue
        if lst: flush()
        para.append(s.strip())
    flush()
    return out


def md_to_html(md, num=None):
    return '\n'.join(md_blocks(md, num))


# ---------- charts ----------
def _deg(s):
    return s.split("'")[0] + "'" if "'" in s else s


def chart_points(chart, varga):
    """[(label, sign index)] for the 9 grahas + Gulika in D1 or D9, with the report's markers."""
    pts = []
    for p in chart['planets']:
        g = p['name']
        if g not in ABBR: continue
        sign = p['vargas'].get(varga) if varga != 'D1' else p['sign']
        if sign not in SIGN_NAMES: continue
        s = SIGN_NAMES.index(sign); lab = ABBR[g]
        if g not in NODES:
            dig = p.get('dignity') if varga == 'D1' else DF.sign_dignity(g, s)
            lab += UP if dig == 'exalted' else DOWN if dig == 'debilitated' else ''
            if varga == 'D1' and p.get('retro'): lab += '(R)'
        pts.append((lab, s, g))
    return pts


def north_svg(pts, lagna_sign, title, asc_label=''):
    by_house = {h: [] for h in range(1, 13)}
    for lab, s, _ in pts: by_house[(s - lagna_sign) % 12 + 1].append(lab)
    p = [f'<svg viewBox="-4 -4 408 408" width="300" height="300" role="img" aria-label="{html.escape(title)}">',
         '<rect x="0" y="0" width="400" height="400" fill="#fffaf0" stroke="#6e1f1f" stroke-width="2"/>',
         '<line x1="0" y1="0" x2="400" y2="400" stroke="#6e1f1f" stroke-width="1.3"/>',
         '<line x1="400" y1="0" x2="0" y2="400" stroke="#6e1f1f" stroke-width="1.3"/>',
         '<polygon points="200,0 400,200 200,400 0,200" fill="none" stroke="#6e1f1f" stroke-width="1.3"/>']
    for h in range(1, 13):
        x, y = SIGN_POS[h]; sign = (lagna_sign + h - 1) % 12 + 1
        p.append(f'<text class="sg" x="{x}" y="{y}" text-anchor="middle">{sign}</text>')
    if asc_label:
        x, y = PL_POS[1]; p.append(f'<text class="asc" x="{x}" y="{y - 22}" text-anchor="middle">{html.escape(asc_label)}</text>')
    for h, names in by_house.items():
        if not names: continue
        x, y = PL_POS[h]
        rows = [names[i:i + 2] for i in range(0, len(names), 2)]
        y0 = y - 9 * (len(rows) - 1) if h not in (1, 7) else y
        for k, row in enumerate(rows):
            p.append(f'<text class="pl" x="{x}" y="{y0 + 18 * k}" text-anchor="middle">{html.escape(" ".join(row))}</text>')
    p.append('</svg>')
    return '\n'.join(p)


def south_svg(pts, lagna_sign, title, asc_label='Asc'):
    by_sign = {s: [] for s in range(12)}
    for lab, s, _ in pts: by_sign[s].append(lab)
    p = [f'<svg viewBox="-4 -4 408 408" width="300" height="300" role="img" aria-label="{html.escape(title)}">',
         '<rect x="0" y="0" width="400" height="400" fill="#fffaf0" stroke="#6e1f1f" stroke-width="2"/>']
    for s, (c, r) in SOUTH_CELL.items():
        x, y = c * 100, r * 100
        p.append(f'<rect x="{x}" y="{y}" width="100" height="100" fill="none" stroke="#6e1f1f" stroke-width="1.3"/>')
        p.append(f'<text class="sg" x="{x + 94}" y="{y + 94}" text-anchor="end">{SIGN_SHORT[s]}</text>')
        if s == lagna_sign:
            p.append(f'<line x1="{x}" y1="{y + 26}" x2="{x + 26}" y2="{y}" stroke="#6e1f1f" stroke-width="1.3"/>')
            p.append(f'<text class="asc" x="{x + 30}" y="{y + 15}">{html.escape(asc_label)}</text>')
        labs = by_sign[s]
        rows = [labs[i:i + 2] for i in range(0, len(labs), 2)]
        for k, row in enumerate(rows):
            yy = y + 54 - 9 * (len(rows) - 1) + 18 * k
            p.append(f'<text class="pl" x="{x + 50}" y="{yy}" text-anchor="middle">{html.escape(" ".join(row))}</text>')
    p.append(f'<text class="ctitle" x="200" y="196" text-anchor="middle">{html.escape(title.split(",")[0])}</text>')
    p.append('</svg>')
    return '\n'.join(p)


def _join(xs):
    return xs[0] if len(xs) == 1 else ', '.join(xs[:-1]) + ' and ' + xs[-1]


def charts_html(chart, style='north'):
    L = chart['lagna']['sign_num'] - 1
    l9 = SIGN_NAMES.index(chart['lagna']['vargas']['D9'])
    d1, d9 = chart_points(chart, 'D1'), chart_points(chart, 'D9')
    asc = f"Asc {_deg(chart['lagna']['deg_in_sign'])}"
    marks = f'{UP} exalted, {DOWN} debilitated, (R) retrograde, Gk = Gulika.'
    if style == 'south':
        svg1 = south_svg(d1, L, 'Rashi (D1), South Indian chart', asc)
        svg9 = south_svg(d9, l9, 'Navamsa (D9), South Indian chart', 'Asc')
        cap1 = ('Rashi chart (D1), South Indian style. The signs are fixed (Aries second from the left on the top row, then '
                f'clockwise); the slanted line marks the lagna, and houses are counted from it. {marks}')
    else:
        svg1 = north_svg(d1, L, 'North Indian D1 chart', asc)
        svg9 = north_svg(d9, l9, 'North Indian D9 chart', 'Asc')
        cap1 = ('Rashi chart (D1), North Indian style. The houses are fixed (the 1st is the top centre diamond, then '
                f'anticlockwise); the numbers are signs (1 = Aries to 12 = Pisces). {marks}')
    ex = [g for lab, _, g in d9 if lab.endswith(UP)]; db = [g for lab, _, g in d9 if lab.endswith(DOWN)]
    cap9 = f"Navamsa chart (D9), {SIGN_NAMES[l9]} rising."
    if ex: cap9 += f" Exalted here: {_join(ex)}."
    if db: cap9 += f" Debilitated here: {_join(db)}."
    return (f'<div class="charts"><figure>{svg1}<figcaption>{html.escape(cap1)}</figcaption></figure>'
            f'<figure>{svg9}<figcaption>{html.escape(cap9)}</figcaption></figure></div>')


# ---------- code tables ----------
def load_tables(chart, F, now, lib, sections_md, log):
    entries = {}
    for name in TABLE_MODULES:
        try:
            mod = importlib.import_module(name)
        except Exception as e:  # missing (ImportError) or broken module: skip its tables, never stop the report
            log.append(f'tables: {name} not loaded ({type(e).__name__}: {e}); its tables are skipped'); continue
        try:
            res = mod.build(chart, F, now, lib, sections_md) or {}
        except Exception as e:
            log.append(f'tables: {name}.build failed ({type(e).__name__}: {e}); its tables are skipped'); continue
        for k, v in res.items():
            if isinstance(v, dict) and (v.get('html') or '').strip(): entries[k] = v
    return entries


def _txt(s):
    return html.escape(html.unescape(str(s)), quote=False)


def table_block(entry):
    h = entry['html'].strip()
    h = re.sub(r'(?s)<caption\b.*?</caption>', '', h)
    nrows = len(re.findall(r'<tr\b', h))
    cls = 'ct split' if nrows > 9 else 'ct'
    cap = f'<caption>Table \x00. {_txt(entry.get("title", ""))}</caption>'

    def tag(m):
        attrs = m.group(1)
        if re.search(r'\bclass="', attrs): attrs = re.sub(r'\bclass="', f'class="{cls} ', attrs, 1)
        else: attrs += f' class="{cls}"'
        return f'<table{attrs}>{cap}'
    h, n = re.subn(r'<table\b([^>]*)>', tag, h, 1)
    if not n: h = f'<table class="{cls}">{cap}<tbody><tr><td>{h}</td></tr></tbody></table>'
    h = re.sub(r'(?s)<tr(\s[^>]*)?>((?:(?!</tr>).)*?\(now\).*?</tr>)',
               lambda m: f'<tr class="now"{m.group(1) or ""}>{m.group(2)}', h)
    note = f'<p class="tnote">{_txt(entry["note"])}</p>' if entry.get('note') else ''
    return f'<div class="tblock{" split" if "split" in cls else ""}">{h}{note}</div>'


def _htext(b):
    m = re.match(r'(?s)<h([34])>(.*)</h\1>$', b)
    return re.sub(r'<[^>]+>', '', html.unescape(m.group(2))).strip().lower() if m else None


def _sub_end(blocks, i):
    lvl = blocks[i][2] if blocks[i].startswith('<h') else '3'
    j = i + 1
    while j < len(blocks) and not (re.match(r'<h([2-4])', blocks[j]) and blocks[j][2] <= lvl): j += 1
    return j


def place_tables(key, blocks, entries, charts, placed, log):
    """Return the section's blocks with charts (glance) and its code tables inserted."""
    inserts = {}

    def put(pos, item):
        inserts.setdefault(pos, []).append(item)

    if key == 'glance' and charts:
        first_h = next((i for i, b in enumerate(blocks) if i > 0 and re.match(r'<h[34]', b)), len(blocks))
        put(first_h - 1, charts)
    for tkey, sec, anchors in SLOTS:
        if sec != key or tkey not in entries: continue
        entry, pos = entries[tkey], None
        for a in anchors:
            kind = a[0]
            if kind == 'charts':
                pos = next((i for i, b in enumerate(blocks) if i > 0 and re.match(r'<h[34]', b)), len(blocks)) - 1
            elif kind in ('head', 'start'):
                for ni, needle in enumerate(a[1]):
                    i = next((i for i, b in enumerate(blocks) if _htext(b) is not None and
                              (_htext(b).startswith(needle.lower()) if kind == 'start' else needle.lower() in _htext(b))), None)
                    if i is None: continue
                    end, pos = _sub_end(blocks, i), i
                    if ni > 0 and i + 1 < end and blocks[i + 1].startswith('<p'): pos = i + 1
                    want = ('<table class="long"',) if tkey in REPLACES_MODEL_TABLE else ('<ul', '<ol') if entry.get('replace') else ()
                    j = next((j for j in range(i + 1, end) if want and blocks[j].startswith(want)), None)
                    if j is not None:
                        blocks[j] = ''; pos = j; log.append(f'tables: {tkey} replaces the model-written block in "{_htext(blocks[i])}"')
                    break
            elif kind == 'first_para':
                h2 = next((i for i, b in enumerate(blocks) if b.startswith('<h2')), -1)
                pos = h2 + 1 if h2 + 1 < len(blocks) and blocks[h2 + 1].startswith('<p') else max(h2, 0)
            elif kind == 'after':
                pos = placed.get(a[1])
            elif kind == 'end':
                pos = len(blocks) - 1
            if pos is not None: break
        put(pos, table_block(entry)); placed[tkey] = pos
    out = []
    for i, b in enumerate(blocks):
        if b: out.append(b)
        out += inserts.get(i, [])
    return out


# ---------- sources ----------
def sources(trace_ids, lib):
    seen, items = set(), []
    for eid in trace_ids:
        e = lib.get(eid)
        for s in (e or {}).get('source_views', []):
            key = re.sub(r'\s+', ' ', s.get('source', '')).strip()
            base = re.split(r'[,;(]| \d', key)[0].strip()
            if base and base not in seen:
                seen.add(base); items.append((base, s.get('url', '')))
    items.sort(key=lambda x: x[0].lower())
    lis = ''.join(f'<li>{html.escape(n)}' + (f' <span class="cite">{html.escape(u)}</span>' if u else '') + '</li>' for n, u in items)
    return f'<ol>{lis}</ol>', len(items)


# ---------- page assets ----------
def css_with_fonts():
    css = open(os.path.join(ASSETS, 'report.css'), encoding='utf-8').read()

    def embed(m):
        f = os.path.join(ASSETS, m.group(1).replace('/', os.sep))
        if not os.path.exists(f): return m.group(0)
        return 'url(data:font/woff2;base64,' + base64.b64encode(open(f, 'rb').read()).decode('ascii') + ')'
    return re.sub(r'url\(["\']?(fonts/[^"\')]+)["\']?\)', embed, css)


def _css_str(s):
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ') + '"'


def transit_date(chart):
    k = next((k for k in chart if k.startswith('transits_')), None)
    return k[len('transits_'):].replace('_', '-') if k else D.date.today().isoformat()


def build(chart, secdir, name, prepared, chart_style='north', log=None):
    log = [] if log is None else log
    lib = json.load(open(os.path.join(ROOT, 'library.json'), encoding='utf-8'))
    F = DF.planet_facts(chart)
    raw = {k: open(os.path.join(secdir, f'{k}.md'), encoding='utf-8').read()
           for k, _ in ORDER if os.path.exists(os.path.join(secdir, f'{k}.md'))}
    entries = load_tables(chart, F, transit_date(chart), lib, raw, log)
    charts = charts_html(chart, chart_style)
    body, toc, trace_ids, missing, placed = [], [], [], [], {}
    n = 0
    for key, title in ORDER:
        if key not in raw: missing.append(key); continue
        md = raw[key]
        for blk in re.findall(r'(?s)<!--\s*trace(.*?)-->', md):
            trace_ids += re.findall(r'[a-z_]+/[a-z0-9_/]+', blk)
        n += 1
        blocks = place_tables(key, md_blocks(strip_hidden(md), n), entries, charts, placed, log)
        body.append(f'<section class="sec-{key}">' + '\n'.join(blocks) + '</section>'); toc.append((n, title, SUBTITLE.get(key, '')))
    unplaced = [k for k in entries if k not in placed]
    if unplaced: log.append(f'tables: no slot or section for {unplaced}; not shown')
    src_html, n_src = sources(list(dict.fromkeys(trace_ids)), lib)
    n += 1; toc.append((n, 'Sources', SUBTITLE['sources']))
    body.append(f'<section><h2><span class="num">{n}</span>Sources</h2><p class="small">Classical texts and modern authors behind '
                f'the interpretations in this report ({n_src}).</p>{src_html}</section>')
    counter = iter(range(1, 1000))
    body_html = re.sub('\x00', lambda m: str(next(counter)), ''.join(body))
    n_tables = len(placed)
    P = {p['name']: p for p in chart['planets']}
    bdate = D.date.fromisoformat(chart['birth']['date'])
    cover = (f'<section class="cover"><div class="om">&#2384;</div><h1>Janma Kundli Report</h1><div class="sub">A Parashari reading of the birth chart</div>'
             f'<div class="name">{html.escape(name)}</div><div class="orn"></div><div class="details">Born {bdate.strftime("%A, %d %B %Y")}, '
             f"{html.escape(chart['birth']['time'])}<br>{html.escape(chart['birth']['place'])}{' &middot; ' + html.escape(chart['birth']['sex'].title()) if chart['birth'].get('sex') else ''}<br>"
             f"{chart['lagna']['sign']} Lagna &middot; {P['Moon']['sign']} Rashi &middot; {P['Moon']['nakshatra']} Nakshatra</div><div class=\"orn\"></div>"
             f"<div class=\"calc\">Computed with Swiss Ephemeris, Lahiri ayanamsa ({chart['settings']['ayanamsa_value']}), mean lunar nodes, whole-sign houses, "
             f"Vimshottari years of 365.25 days. Reading prepared {prepared}.</div></section>")
    toc_html = ('<section class="toc"><div class="tt">Contents</div><ol>' +
                ''.join(f'<li><span class="n">{i}</span><span class="d">{html.escape(t)}</span><span class="s">{html.escape(s)}</span></li>'
                        for i, t, s in toc) +
                '</ol><div class="box note" style="margin-top:10mm"><h4>How to read this report</h4><p>Jyotish describes tendencies and timing, '
                'not certainties. The classical texts state their results bluntly; this report gives their sense, weighs each factor against the '
                'rest of the chart, and says where sources differ. The planetary positions come from one computation and are treated as correct; '
                'the reading is an interpretation and can be wrong. Nothing here is medical, financial or legal advice.</p></div></section>')
    running = f'@page{{ @top-center{{ content:{_css_str(name + "  ·  Janma Kundli Report")}; }} }}'
    doc = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
           f'<title>{html.escape(name)} - Janma Kundli Report</title>'
           f'<style>{css_with_fonts()}\n{running}</style></head><body><div class="wrap">{cover}{toc_html}{body_html}</div></body></html>')
    log.append(f'tables: {n_tables} placed: ' + ', '.join(f'{k}' for k in placed))
    return doc, missing, n_src


# ---------- PDF ----------
def _browser_paths():
    c = [r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe', r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
         r'C:\Program Files\Google\Chrome\Application\chrome.exe']
    c += [shutil.which(x) for x in ('chromium', 'chromium-browser', 'google-chrome', 'google-chrome-stable', 'microsoft-edge', 'msedge')]
    return [x for x in c if x and os.path.exists(x)]


def to_pdf(html_path, pdf_path):
    """Return the renderer used ('playwright:chromium', 'playwright:msedge', 'cli:<exe>') or None on failure."""
    url = 'file:///' + os.path.abspath(html_path).replace('\\', '/').lstrip('/')
    pdf_path = os.path.abspath(pdf_path)
    if os.path.exists(pdf_path): os.remove(pdf_path)
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            # Prefer a browser that draws @page margin boxes (Chromium 131+): the bundled one first, then installed
            # Edge/Chrome. An older one still renders, with page numbers from Playwright's footer template instead.
            chosen = None
            for ch in (None, 'msedge', 'chrome'):
                try:
                    b = pw.chromium.launch(channel=ch) if ch else pw.chromium.launch()
                except Exception:
                    continue
                major = int(re.match(r'\d+', b.version).group(0))
                if major >= 131:
                    if chosen: chosen[0].close()
                    chosen = (b, ch, major); break
                if chosen: b.close()
                else: chosen = (b, ch, major)
            if chosen:
                b, ch, major = chosen
                try:
                    pg = b.new_page()
                    pg.goto(url, wait_until='load', timeout=120000)
                    pg.evaluate('document.fonts.ready.then(() => true)')
                    pg.emulate_media(media='print')
                    opts = dict(path=pdf_path, format='A4', print_background=True, prefer_css_page_size=True)
                    if major < 131:
                        style = 'font-family:Georgia,serif;font-size:8px;color:#8a7a6a;width:100%;text-align:center;'
                        opts.update(display_header_footer=True, header_template=f'<div style="{style}">{html.escape(pg.title())}</div>',
                                    footer_template=f'<div style="{style}"><span class="pageNumber"></span></div>')
                    pg.pdf(**opts)
                finally:
                    b.close()
                if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0: return f'playwright:{ch or "chromium"} {major}'
    except ImportError:
        pass
    for exe in _browser_paths():
        subprocess.run([exe, '--headless', '--disable-gpu', '--no-pdf-header-footer', f'--print-to-pdf={pdf_path}', url],
                       capture_output=True, timeout=180)
        if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0: return f'cli:{os.path.basename(exe)}'
    return None


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--chart', required=True); ap.add_argument('--sections', required=True); ap.add_argument('--name', required=True)
    ap.add_argument('--out', required=True); ap.add_argument('--pdf'); ap.add_argument('--prepared', default=D.date.today().strftime('%d %B %Y'))
    ap.add_argument('--chart-style', choices=['north', 'south'], default='north')
    a = ap.parse_args()
    chart = json.load(open(a.chart, encoding='utf-8'))
    sys.path.insert(0, os.path.join(ROOT, 'tools', 'eval'))
    from lint_report import lint
    findings = {k: lint(open(os.path.join(a.sections, f'{k}.md'), encoding='utf-8').read())
                for k, _ in ORDER if os.path.exists(os.path.join(a.sections, f'{k}.md'))}
    for k, f in findings.items():
        for i, kind, hit, ctx in f: print(f'LINT {k} line {i} [{kind}] "{hit}"')
    log = []
    doc, missing, n_src = build(chart, a.sections, a.name, a.prepared, a.chart_style, log)
    for line in log: print(line)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    open(a.out, 'w', encoding='utf-8').write(doc)
    words = len(re.sub(r'<[^>]+>', ' ', re.sub(r'(?s)<style>.*?</style>', '', doc)).split())
    print(f'wrote {a.out}: ~{words} words, {n_src} sources; missing sections: {missing or "none"}')
    if a.pdf:
        r = to_pdf(a.out, a.pdf)
        print('pdf', f'written with {r}' if r else 'FAILED', a.pdf)
