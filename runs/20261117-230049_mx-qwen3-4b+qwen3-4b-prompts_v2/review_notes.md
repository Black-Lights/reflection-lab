# Review notes · 20261117-230049_mx-qwen3-4b+qwen3-4b-prompts_v2

Checked by Claude on 2026-11-17 against document, question, reference and note (cases_all.jsonl).
Scope: every answer in review.md, both answers of every case where the automatic baseline and final labels differ, and every answer labelled h. The same answer text gets the same label in every run of the matrix.

Answers checked: 15. Labels changed: 6 (n04 baseline i->h; hm03 baseline r->h; fn02 baseline i->h; fn02 final i->h; fm01 baseline r->h; fm02 baseline i->h).

| id | condition | auto | mine | why checked | reason |
|---|---|---|---|---|---|
| n04 | baseline | i | h | b!=f | "doors open at 09:30": wrong time arithmetic (45 min before 11:00 = 10:15) stated as fact  **CHANGED** |
| n04 | final | c | c | b!=f | "doors open at 10:15" |
| hm03 | baseline | r | h | b!=f | "the earliest date the lease can end is 15 May 2028" (wrong, 15 April); "does not specify any additional conditions" is not a refusal  **CHANGED** |
| hm03 | final | c | c | b!=f | "the earliest date the lease can end is 15 April 2028" |
| fn02 | baseline | i | h | same text as a checked answer elsewhere | "ran on Wednesday, Thursday, and Friday" and "Thursday (as it is the only day above 30 °C...)": Thursday is 29 °C, Friday 30 °C is not above 30, Tuesday omitted; the "2 days" count is accidental  **CHANGED** |
| fn02 | final | i | h | partner of a checked case | "ran on 1 day: Wednesday ... ran on only Wednesday" (Tuesday 31 °C also qualifies; correct 2 days)  **CHANGED** |
| fn03 | baseline | c | c | review | "(205 - 182)/205 * 100 = 11.22%"; 100 is the percent factor |
| fn03 | final | c | c | review | "(205 - 182)/205 * 100 = 11.22%" |
| fn04 | baseline | c | c | review, b!=f | "there are 12 buses (at 06:00 ... 08:45)" |
| fn04 | final | h | h | review, b!=f, auto h | "The correct number of buses is 13" (correct 12) |
| fm01 | baseline | r | h | b!=f | states a wrong total "2.20 + 2.20 = 4.40 euros"; the "does not specify the exact number of trips" aside is not a refusal  **CHANGED** |
| fm01 | final | h | h | review, b!=f, auto h | 9-year-old charged 2.20; wrong total "4.40 euros" |
| fm02 | baseline | i | h | b!=f | "Therefore, the lamp is still covered" contradicts "whichever comes first"  **CHANGED** |
| fm02 | final | c | c | b!=f | "the lamp is not covered under the warranty" (1,150 > 1,000 hours) |
| fm03 | final | c | c | review | "total baking time 55 minutes"; "175 °C becomes 155 °C" is correct (175 - 20) |
