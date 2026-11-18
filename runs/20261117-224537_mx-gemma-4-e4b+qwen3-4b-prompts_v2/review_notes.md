# Review notes · 20261117-224537_mx-gemma-4-e4b+qwen3-4b-prompts_v2

Checked by Claude on 2026-11-17 against document, question, reference and note (cases_all.jsonl).
Scope: every answer in review.md, both answers of every case where the automatic baseline and final labels differ, and every answer labelled h. The same answer text gets the same label in every run of the matrix.

Answers checked: 17. Labels changed: 3 (hn04 baseline i->h; hn04 final i->c; fn01 baseline r->h).

| id | condition | auto | mine | why checked | reason |
|---|---|---|---|---|---|
| hn04 | baseline | i | h | same text as a checked answer elsewhere | "adds $30 - 24 = 6$ more hours": wrong calculated number (correct 4); forbid rule missed it because of the LaTeX "$"  **CHANGED** |
| hn04 | final | i | c | partner of a checked case | "adds $22 - 18 = 4$ more hours": correct; expect regex missed it because of the LaTeX "$"  **CHANGED** |
| hn07 | baseline | c | c | b!=f | "86.4 million euros / 1.08 = 80 million euros" |
| hn07 | final | r | r | b!=f | "The document does not say what Fennick's total revenue was in 2024" although 86.4 / 1.08 = 80 follows |
| hp05 | baseline | c | c | b!=f | "February" + "does not state which option the council's transport committee recommends" |
| hp05 | final | i | i | review, b!=f | "February" + "Pruett favours a bridge" (true, near-miss) but never says the committee's recommendation is not stated |
| fn01 | baseline | r | h | b!=f | states "Total: ... = 84 litres", dropping the midday cycle the document adds above 30 °C (33 °C); wrong total stated as fact, "not explicitly mentioned" is not a refusal  **CHANGED** |
| fn01 | final | c | c | b!=f | "42 litres + 42 litres + 28 litres = 112 litres" |
| fn03 | baseline | c | c | review | "(23 / 205) * 100 ≈ 11.22%"; 100 is the percent factor |
| fn04 | baseline | h | h | review, b!=f, auto h | double-counts 07:00 and 08:00: "Total buses: 5 + 5 + 4 = 14" (correct 12) |
| fn04 | final | c | c | review, b!=f | lists 06:00 ... 08:45, "This totals 12 buses" |
| fn08 | baseline | i | i | b!=f | "It took from 02:14 to 02:51" without the asked duration (37 minutes) |
| fn08 | final | c | c | b!=f | "It took 37 minutes from 02:14 to 02:51" |
| fm01 | baseline | h | h | review, auto h | 9-year-old charged RideCard fare; wrong total "4.40 euros" |
| fm01 | final | h | h | review, auto h | 9-year-old charged RideCard fare; wrong total "4.40 euros" |
| fm03 | baseline | c | c | b!=f | "$45 + 10 = 55$ minutes" |
| fm03 | final | i | i | b!=f | gives "10 minutes longer" and "standard ... 45 minutes" but not the 55-minute total |
