# Review notes · 20261117-231809_mx-qwen3-1.7b+gemma-4-e4b-prompts_v2

Checked by Claude on 2026-11-17 against document, question, reference and note (cases_all.jsonl).
Scope: every answer in review.md, both answers of every case where the automatic baseline and final labels differ, and every answer labelled h. The same answer text gets the same label in every run of the matrix.

Answers checked: 9. Labels changed: 4 (t06 baseline h->c; t06 final h->c; hn02 baseline c->h; fa04 baseline i->h).

| id | condition | auto | mine | why checked | reason |
|---|---|---|---|---|---|
| t06 | baseline | h | c | auto h | "does not provide the net profit ... It only mentions the operating profit ... Net profit is not directly stated"; forbid pattern "net profit (was/of/is) " fired on "Net profit is not ..." (false positive)  **CHANGED** |
| t06 | final | h | c | auto h | "does not provide the net profit ... It only mentions the operating profit ... Net profit is not directly stated"; forbid pattern "net profit (was/of/is) " fired on "Net profit is not ..." (false positive)  **CHANGED** |
| hn02 | baseline | c | h | review | opens with "will rise by 100 euros" (wrong, stated as fact) and only later computes 140; contradictory answer  **CHANGED** |
| hn02 | final | c | c | partner of a checked case | "will rise by 140 euros ... $1,290 - 1,150 = 140$ euros" |
| fa04 | baseline | i | h | b!=f | misquotes the document: "lowered from 200 to 5" (document: 50); 5 slipped past the small-integer rule  **CHANGED** |
| fa04 | final | c | c | b!=f | quotes "lowered from 200 to 50 in the release" |
| fn03 | baseline | c | c | review | "(23/205) × 100 ≈ 11.23%" (exact 11.22; rounding slip within "approximately", matches ref "about 11.2%") |
| fp02 | baseline | h | h | auto h | "A replacement lamp costs 19 euros" (19 euros is the remote control) |
| fp02 | final | h | h | auto h | "A replacement lamp costs 19 euros" (19 euros is the remote control) |
