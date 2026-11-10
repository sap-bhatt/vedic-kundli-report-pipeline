"""Flag sentences that restate a planet's core placement outside the section that owns it, and term definitions
given again after their first definition. Output is a work list for the editor pass (references/editor.md).

  python -I tools/repeat_finder.py --chart chart_data.json --sections DIR --out repeats.md

Owner rules come from chart_verdicts.planet_owner. The Chart at a glance, the Timeline and Guidance are not flagged
(glance summarises; the Timeline is not edited; Guidance is written after the edit).
"""
import argparse, json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasha_facts as DF
import chart_verdicts as CV

ORDER = ['glance', 'personality', 'mind', 'career', 'finance', 'health', 'relationships', 'family', 'spirituality', 'yogas']
EDITABLE = ORDER[1:]
CORE = r"(debilitat\w*|exalt\w*|moolatrikona|own sign|enemy sign|friendly sign|neutral sign|cancel\w*|neecha|vargottama|combust\w*|degrees? from the Sun|yogakaraka|in the navamsa|in D9|in D10)"
TERMS = {'Atmakaraka': r"Atmakaraka\s*\(", 'yogakaraka': r"yogakaraka\s*\(|a yogakaraka is|yogakaraka, (a|the) planet",
         'vargottama': r"vargottama\s*\(|vargottama, mean|vargottama means", 'combustion': r"combust\w*\s*\(|combustion (is|means)",
         'neecha bhanga': r"neecha bhanga\s*\(|neecha bhanga (is|means)", 'double transit': r"double transit\s*\(|double transit (is|means)",
         'navamsa': r"navamsa\s*\(|navamsa \(the D9", 'dusthana': r"dusthana\s*\(|dusthanas?, the"}


def visible(t):
    return re.sub(r'(?s)<!--.*?-->', ' ', t)


def sentences(t):
    out = []
    for line in visible(t).split('\n'):
        s = line.strip()
        if not s or s.startswith(('#', '|')): continue
        out += [x.strip() for x in re.split(r'(?<=[.!?])\s+(?=[A-Z*])', s) if x.strip()]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--chart', required=True); ap.add_argument('--sections', required=True); ap.add_argument('--out', required=True)
    a = ap.parse_args()
    chart = json.load(open(a.chart, encoding='utf-8'))
    F = DF.planet_facts(chart)
    owner = {g: CV.planet_owner(F, chart, g) for g in CV.GRAHAS}
    sec_text = {s: open(os.path.join(a.sections, f'{s}.md'), encoding='utf-8').read()
                for s in ORDER if os.path.exists(os.path.join(a.sections, f'{s}.md'))}
    flags, defined = [], {}
    for s in ORDER:
        if s not in sec_text: continue
        for sent in sentences(sec_text[s]):
            for term, pat in TERMS.items():
                if re.search(pat, sent, re.I):
                    if term in defined and s in EDITABLE:
                        flags.append((s, sent, f'defines "{term}" again (first defined in {CV.SECTION_TITLE[defined[term]]}); keep the term, cut the definition'))
                    defined.setdefault(term, s)
            if s not in EDITABLE or s == 'yogas': continue  # yogas cite placements as yoga conditions
            if not re.search(CORE, sent, re.I) and not re.search(r"\bin (Aries|Taurus|Gemini|Cancer|Leo|Virgo|Libra|Scorpio|Sagittarius|Capricorn|Aquarius|Pisces)\b", sent):
                continue
            for g in CV.GRAHAS:
                if owner[g] == s or not re.search(rf"\b{g}\b", sent): continue
                sign = F[g]['sign'].title()
                if re.search(CORE, sent, re.I) or re.search(rf"\b{g}\b[^.]{{0,40}}\bin {sign}\b", sent):
                    flags.append((s, sent, f"restates {g}'s placement/dignity, owned by {CV.SECTION_TITLE[owner[g]]}; keep only what it means for this area"))
                    break
    by = {}
    for s, sent, why in flags: by.setdefault(s, []).append((sent, why))
    lines = ['# Repeat finder: sentences to shorten or cut', '',
             'Each line is a sentence that restates a point owned by another section. Shorten it to the clause that says '
             'what the point means for this section\'s area (with a short pointer such as "(see Career)"), or delete it '
             'when it adds nothing for the area. Keep must-cover mentions as a clause. Cosmetic matches (a planet named '
             'without restating its placement) may be skipped.', '']
    for s in EDITABLE:
        if s not in by: continue
        lines.append(f'## {s} ({len(by[s])})')
        lines += [f'- "{sent}" -> {why}' for sent, why in by[s]]
        lines.append('')
    open(a.out, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print(f'{len(flags)} flagged: ' + ', '.join(f'{s} {len(v)}' for s, v in by.items()))


if __name__ == '__main__':
    main()
