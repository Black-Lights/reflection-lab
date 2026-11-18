# Review notes · 20261117-221418_mx-qwen3-4b+gemma-4-e4b-prompts

Checked by Claude on 2026-11-17 against document, question, reference and note (cases_all.jsonl).
Scope: every answer in review.md, both answers of every case where the automatic baseline and final labels differ, and every answer labelled h. The same answer text gets the same label in every run of the matrix.

Answers checked: 23. Labels changed: 5 (hp05 baseline i->h; hp05 final c->h; hm03 baseline i->h; hm03 final r->h; fm02 final i->h).

| id | condition | auto | mine | why checked | reason |
|---|---|---|---|---|---|
| hn01 | baseline | c | c | b!=f | "260,000 euros less than the original tender estimate" |
| hn01 | final | r | r | b!=f | "The document does not say" although 2.1 - 1.84 million = 260,000 euros follows |
| hn03 | baseline | c | c | b!=f | "The difference is 4.1 - 1.9 = 2.2 days"; trailing "The document does not say." does not retract it |
| hn03 | final | r | r | b!=f | "The document does not say ... does not explicitly mention the difference" although 4.1 - 1.9 = 2.2 is a simple calculation |
| hn04 | baseline | c | c | b!=f | "= 22 hours ... = 18 hours. The difference is 4 hours" (garbled "adds 24 hours" wording and a stray "The document does not say" do not change the stated result) |
| hn04 | final | r | r | b!=f | "The document does not say" although 4 hours follows by simple calculation |
| hn07 | baseline | c | c | b!=f | "86.4 million euros divided by 1.08, which equals 80 million euros" |
| hn07 | final | r | r | b!=f | "does not explicitly state Fennick's total revenue in 2024" although 86.4 / 1.08 = 80 follows |
| hn09 | baseline | c | c | b!=f | "the total amount of buffer W2 used per sample is 1000 µl (500 µl × 2)" |
| hn09 | final | r | r | b!=f | "does not explicitly state the total amount" although 2 × 500 = 1,000 µl is a simple calculation |
| hp05 | baseline | i | h | review, b!=f | invents the missing part: "The transport committee recommends a bridge" (only Pruett personally favours one)  **CHANGED** |
| hp05 | final | c | h | b!=f | "The transport committee does not recommend a bridge" is an unsupported claim about the committee, even though it then says the recommendation is not stated  **CHANGED** |
| hm03 | baseline | i | h | b!=f | "the earliest date the lease can end is 15 May 2028": three months from 15 January is 15 April; wrong date stated as fact  **CHANGED** |
| hm03 | final | r | h | b!=f | states "The earliest date the lease can end is 15 May 2028" (wrong, 15 April); the opening "does not say" is not the answer it gives  **CHANGED** |
| fn05 | final | r | r | partner of a checked case | "does not specify the total cost for 10 trips with the RideCard" although 10 × 0.60 = 6 euros follows |
| fn08 | baseline | c | c | b!=f | "based on the times given, it took 37 minutes" (opening "does not say" refers to an explicit duration) |
| fn08 | final | r | r | b!=f | "The document does not say ... does not explicitly state the duration" although 02:14 -> 02:51 = 37 minutes |
| fm01 | baseline | h | h | review, auto h | 9-year-old charged 2.20; wrong total "4.40 euros" |
| fm01 | final | h | h | auto h | 9-year-old charged 2.20; wrong total "4.40 euros" |
| fm02 | baseline | c | c | b!=f | "the lamp is no longer covered under the warranty" (1,150 h exceeds the 1,000-hour limit) |
| fm02 | final | i | h | b!=f | "Therefore, the lamp is still covered" contradicts "whichever comes first" with 1,150 > 1,000 hours  **CHANGED** |
| fm04 | baseline | c | c | b!=f | "The difference is 5 km"; trailing "The document does not say." does not retract it |
| fm04 | final | r | r | b!=f | gives 9 and 4 km, then "The document does not say" instead of the 5 km difference |
