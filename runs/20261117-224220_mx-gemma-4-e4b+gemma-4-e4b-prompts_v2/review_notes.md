# Review notes · 20261117-224220_mx-gemma-4-e4b+gemma-4-e4b-prompts_v2

Checked by Claude on 2026-11-17 against document, question, reference and note (cases_all.jsonl).
Scope: every answer in review.md, both answers of every case where the automatic baseline and final labels differ, and every answer labelled h. The same answer text gets the same label in every run of the matrix.

Answers checked: 9. Labels changed: 3 (hn04 baseline i->h; hn04 final i->h; fn01 baseline r->h).

| id | condition | auto | mine | why checked | reason |
|---|---|---|---|---|---|
| hn04 | baseline | i | h | same text as a checked answer elsewhere | "adds $30 - 24 = 6$ more hours": wrong calculated number (correct 4); forbid rule missed it because of the LaTeX "$"  **CHANGED** |
| hn04 | final | i | h | same text as a checked answer elsewhere | "adds $30 - 24 = 6$ more hours": wrong calculated number (correct 4); forbid rule missed it because of the LaTeX "$"  **CHANGED** |
| fn01 | baseline | r | h | b!=f | states "Total: ... = 84 litres", dropping the midday cycle the document adds above 30 °C (33 °C); wrong total stated as fact, "not explicitly mentioned" is not a refusal  **CHANGED** |
| fn01 | final | c | c | b!=f | "42 litres + 42 litres + 28 litres = 112 litres" |
| fn03 | baseline | c | c | review | "(23 / 205) * 100 ≈ 11.22%"; 100 is the percent factor |
| fn04 | baseline | h | h | review, auto h | double-counts 07:00 and 08:00: "Total buses: 5 + 5 + 4 = 14" (correct 12) |
| fn04 | final | h | h | auto h | double-counts 07:00 and 08:00: "Total buses: 5 + 5 + 4 = 14" (correct 12) |
| fm01 | baseline | h | h | review, b!=f, auto h | 9-year-old charged RideCard fare; wrong total "4.40 euros" |
| fm01 | final | c | c | b!=f | "9-year-old pays 2.80 ... adult pays 2.20 ... total of 5.00 euros" |
