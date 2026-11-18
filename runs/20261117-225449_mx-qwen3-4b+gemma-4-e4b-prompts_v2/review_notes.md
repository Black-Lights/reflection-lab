# Review notes · 20261117-225449_mx-qwen3-4b+gemma-4-e4b-prompts_v2

Checked by Claude on 2026-11-17 against document, question, reference and note (cases_all.jsonl).
Scope: every answer in review.md, both answers of every case where the automatic baseline and final labels differ, and every answer labelled h. The same answer text gets the same label in every run of the matrix.

Answers checked: 12. Labels changed: 9 (n04 baseline i->h; n04 final i->h; hm03 baseline r->h; hm03 final r->h; fn02 baseline i->h; fm01 baseline r->h; fm01 final r->h; fm02 baseline i->h; fm02 final i->h).

| id | condition | auto | mine | why checked | reason |
|---|---|---|---|---|---|
| n04 | baseline | i | h | same text as a checked answer elsewhere | "doors open at 09:30": wrong time arithmetic (45 min before 11:00 = 10:15) stated as fact  **CHANGED** |
| n04 | final | i | h | same text as a checked answer elsewhere | "doors open at 09:30": wrong time arithmetic (45 min before 11:00 = 10:15) stated as fact  **CHANGED** |
| hm03 | baseline | r | h | same text as a checked answer elsewhere | "the earliest date the lease can end is 15 May 2028" (wrong, 15 April); "does not specify any additional conditions" is not a refusal  **CHANGED** |
| hm03 | final | r | h | same text as a checked answer elsewhere | "the earliest date the lease can end is 15 May 2028" (wrong, 15 April); "does not specify any additional conditions" is not a refusal  **CHANGED** |
| fn02 | baseline | i | h | b!=f | "ran on Wednesday, Thursday, and Friday" and "Thursday (as it is the only day above 30 °C...)": Thursday is 29 °C, Friday 30 °C is not above 30, Tuesday omitted; the "2 days" count is accidental  **CHANGED** |
| fn02 | final | c | c | b!=f | "ran on Wednesday and Tuesday ... Thus, the extra cycle ran on 2 days" |
| fn03 | baseline | c | c | review | "(205 - 182)/205 * 100 = 11.22%"; 100 is the percent factor |
| fn04 | baseline | c | c | review | "there are 12 buses (at 06:00 ... 08:45)" |
| fm01 | baseline | r | h | same text as a checked answer elsewhere | states a wrong total "2.20 + 2.20 = 4.40 euros"; the "does not specify the exact number of trips" aside is not a refusal  **CHANGED** |
| fm01 | final | r | h | partner of a checked case | 9-year-old charged the RideCard fare: "2.20 + 2.20 = 4.40 euros in total" (correct 5.00)  **CHANGED** |
| fm02 | baseline | i | h | same text as a checked answer elsewhere | "Therefore, the lamp is still covered" contradicts "whichever comes first"  **CHANGED** |
| fm02 | final | i | h | partner of a checked case | "Therefore, the lamp is still covered under the warranty" contradicts "whichever comes first" (1,150 > 1,000 h)  **CHANGED** |
