"""Guardrail lint for report sections written by the small model. Checks the VISIBLE text (trace blocks removed).

  python -I tools/eval/lint_report.py section.md [more.md ...]      exit code 1 if any finding

Findings are phrases the shared rules forbid in visible text: fatalistic hard results, death/maraka wording, machinery
words, copied phrasing instructions, entry ids. A clean lint is necessary, not sufficient: graders still read for
past-as-fact and softer fear language.
"""
import re, sys
sys.stdout.reconfigure(encoding='utf-8')

PATTERNS = [
    ('fatalistic', r"\b(brings?|bringing|causes?|gives?)\b[^.]{0,90}\b(illness|disease|losses?|separation|death|accident|divorce|ruin|misfortune|suffering)\b"),
    ('fatalistic', r"\bwill (suffer|fall ill|lose|die|be ruined|divorce)\b"),
    ('death_wording', r"\b(danger (to|from|of)|sudden hazards?|death|longevity|maraka|life[- ]span|fatal)\b"),
    ('marriage_calamity', r"\b(more than one (marriage|union|spouse)|second marriage|multiple marriages|outside (the )?marriage|infidelity|extra-?marital|divorce|loss of (the |a )?(spouse|partner)|widow\w*|early separation)\b"),
    ('health_list', r"\b(fevers?|weapons?|poison\w*|wounds?|injur(y|ies)|illness(es)?|diseases?|burns|accidents?|sharp tools|(around|near|from|with) fire)\b"),
    ('machinery', r"\b(the code|library|the input|input file|entr(y|ies)|conditions? (that )?(hold|holds|held|checked)|could not be checked|not checkable|horizon|ten-year window|marked as|this section|the verdicts?|chart verdicts|must cover|(is|are) recorded|not reported as met|nothing more is said|keep to one general note|keep to care with|no source( here)? gives|(is|are) recorded here|none is claimed|not (part of|covered (in|by)) this reading|no reading (is )?given|one clause( here)?( at most)?|(named|mentioned|given) (here )?only as a placement|lead with the strengths|(run|runs) only (to|until)|named here|data (runs|range)|\(explained in [A-Z][^)]*\)|calculator)\b"),
    ('copied_instruction', r"\b(keep (it|the reading) (encouraging|balanced|positive)|present (it|this) as|do not promise|(this|it) is not a promise|speak of [a-z]+ and|avoid (fear|promising))\b"),
    ('imperative_to_writer', r"(?:^|[.!?]\s+|\*\*\s*)(Lead with (the|its|this)|Speak of|Describe (it|this|the)|Call (it|this)|Frame (it|this|the)|Present (it|this|the)|Emphasi[sz]e (the|that)|Stress (the|that)|Do not (copy|say|mention|frame|present|tell|call|describe|use|write|promise)|[Aa]void any reading)\b"),
    ('entry_id', r"\b(planet_in_house|planet_in_sign|lord_in_house|dasha_md|dasha_ad|dasha_principle|transit|sade_sati|yogini|yoga|dosha|nakshatra|karaka|aspect|conjunction|remedy)/[a-z0-9_/]+"),
    ('gemstone_push', r"\b(must|should) (wear|buy)\b[^.]{0,30}\b(gem|stone|ruby|sapphire|emerald|diamond|pearl|coral|hessonite|cat'?s eye)\b"),
]


def visible(t):
    return re.sub(r'(?s)<!--.*?-->', ' ', t)


def lint(text):
    out = []
    for i, line in enumerate(visible(text).split('\n'), 1):
        for kind, pat in PATTERNS:
            for m in re.finditer(pat, line, flags=re.I):
                out.append((i, kind, m.group(0), line.strip()[:160]))
    return out


if __name__ == '__main__':
    bad = 0
    for path in sys.argv[1:]:
        f = lint(open(path, encoding='utf-8').read())
        bad += len(f)
        print(f'{path}: {len(f)} finding(s)')
        for i, kind, hit, ctx in f:
            print(f'  line {i} [{kind}] "{hit}" | {ctx}')
    sys.exit(1 if bad else 0)
