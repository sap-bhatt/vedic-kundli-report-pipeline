# Third-party notices

This repository is under the MIT licence (`LICENSE`). It ships the fonts below, each with its own licence text, and
its interpretation library summarises published works, credited below.

## Fonts (SIL Open Font License 1.1)

Embedded into the HTML report by `tools/assemble_report.py`; licence texts sit next to the font files in
`tools/report_assets/fonts/`.

| Font | Files | Licence file |
|---|---|---|
| Cormorant Garamond (the Cormorant Project Authors) | `CormorantGaramond*.woff2` | `OFL-CormorantGaramond.txt` |
| EB Garamond (the EB Garamond Project Authors) | `EBGaramond*.woff2` | `OFL-EBGaramond.txt` |
| Noto Serif Devanagari (the Noto Project Authors), subset | `NotoSerifDevanagari-Om.woff2` | `OFL-NotoSerifDevanagari.txt` |

## Playwright (optional)

`tools/assemble_report.py --pdf` uses [Playwright for Python](https://github.com/microsoft/playwright-python) to print
the HTML with Chromium when it is installed. Without it, the tool falls back to a locally installed Chrome, Chromium
or Edge in headless mode, and the HTML report needs neither.

## The interpretation library (classical texts and modern authors)

The layer folders (`planet_in_house/`, `dasha_ad/`, `yoga/` ...) and the generated `library.json` hold paraphrases
of classical Jyotish texts (for example Brihat Parashara Hora Shastra, Phaladeepika, Saravali, Brihat Jataka, Jataka
Parijata, Bhavartha Ratnakara, Uttara Kalamrita) and of modern authors (for example B.V. Raman, Sanjay Rath, David
Frawley, James Braha, Andrew Foss). Every entry cites its source (text, chapter/verse or page, and a link where one
was read). Entries are summaries in our own words; quotations are kept short. The original works and translations
remain with their authors, translators and publishers; follow the cited links for the full texts. If you are a rights
holder and want a passage changed or removed, open an issue.

## Example reports

`examples/` holds made-up charts (invented birth details, no real people) with model-written report sections and
benchmark texts, included to show the output format and the grading.
