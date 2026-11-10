# Dasha research rules (for research agents)

1. Read `docs/LIBRARY.md` (schema, "Dasha layers", condition vocabulary) first. Write ONLY your assigned file(s); scratch files
   only in a scratch folder outside the repository (delete at the end). Do not open any other file on this computer: no reports, charts or skills.
2. Research the dasha in general, never one person's chart. Nothing chart-specific goes into an entry.
3. Sources: at least THREE classical and THREE modern authorities per file where they speak to it, read in full.
   Classical: BPHS dasha and antardasha chapters (Santhanam vol. 2 and/or G.C. Sharma; enjoylearningsanskrit.com; archive.org),
   Phaladeepika dasha chapters (siva.sh, wisdomlib), Saravali dasha chapters, Uttara Kalamrita, Laghu Parashari / Jataka Chandrika,
   Jataka Parijata (Sastri, archive.org), Brihat Jataka. Modern: B.V. Raman (Hindu Predictive Astrology; How to Judge a Horoscope;
   archive.org), K.N. Rao, Sanjay Rath (Vimsottari and Udu Dasas), Hart de Fouw & Robert Svoboda (Light on Life), Komilla Sutton,
   James Braha, Andrew Foss. Use only what you can actually read; mark "(via summary)" honestly when you did not read the page itself.
4. Cite text + chapter/verse (confirm the numbers from the text, never guess) + URL. Paraphrase; no long quotations.
5. Conditional results: record each "good if / bad if" rule as one `conditional_results` item. Translate the condition into the
   vocabulary in docs/LIBRARY.md only when it maps exactly; otherwise use `manual: <the source's condition>`. Do not merge different
   reference points ("from the lagna" vs "from the dasha lord").
6. Death or maraka predictions: keep them faithful in `source_views` and write the effect as
   "[maraka: text predicts danger to life / death]" so the report skill can rephrase it. Never soften a source silently.
7. Unsourced content = empty field. Only `phrasing_guidance` may be your own. Fill `disagreements` where sources differ.
   Set `confidence` honestly (high / medium / low).
8. Valid UTF-8 JSON. Finish and save one file completely, then validate it with
   `python -I -c "import json;json.load(open('<file>',encoding='utf-8'))"` (full path in the agent prompt).
9. Reply in under 150 words: files written, sources per file (classical vs modern, full read vs summary), number of
   conditional results (checkable vs manual), and anything you could not verify.
