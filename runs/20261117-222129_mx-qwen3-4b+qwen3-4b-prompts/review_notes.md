# Review notes · 20261117-222129_mx-qwen3-4b+qwen3-4b-prompts

Checked by Claude on 2026-11-17 against document, question, reference and note (cases_all.jsonl).
Scope: every answer in review.md, both answers of every case where the automatic baseline and final labels differ, and every answer labelled h. The same answer text gets the same label in every run of the matrix.

Answers checked: 20. Labels changed: 4 (hp05 baseline i->h; hm03 baseline i->h; hm03 final i->h; fm02 final i->h).

| id | condition | auto | mine | why checked | reason |
|---|---|---|---|---|---|
| hn03 | baseline | c | c | b!=f | "The difference is 4.1 - 1.9 = 2.2 days"; trailing "The document does not say." does not retract it |
| hn03 | final | r | r | b!=f | "The document does not say ... does not explicitly mention the difference" although 2.2 is a simple calculation |
| hn07 | baseline | c | c | b!=f | "86.4 million euros divided by 1.08, which equals 80 million euros" |
| hn07 | final | r | r | b!=f | "does not explicitly state Fennick's total revenue in 2024" although 86.4 / 1.08 = 80 follows |
| hn08 | baseline | c | c | b!=f | "3,750 euros (1,250 euros x 3)"; the "not explicitly state ... in absolute terms" aside is accurate |
| hn08 | final | r | r | b!=f | "does not explicitly state the amount of the deposit" although 3 × 1,250 = 3,750 euros follows |
| hp05 | baseline | i | h | review, b!=f | invents the missing part: "The transport committee recommends a bridge" (only Pruett personally favours one)  **CHANGED** |
| hp05 | final | c | c | b!=f | "February" + "The document does not state the transport committee's recommendation" |
| hm03 | baseline | i | h | same text as a checked answer elsewhere | "the earliest date the lease can end is 15 May 2028": three months from 15 January is 15 April; wrong date stated as fact  **CHANGED** |
| hm03 | final | i | h | partner of a checked case | "The lease can end on 15 May 2028" (wrong, 15 April 2028)  **CHANGED** |
| fn03 | baseline | r | r | b!=f | "does not provide the percentage decrease ... The document does not say" although it follows from 205 and 182 |
| fn03 | final | c | c | review, b!=f | computes "((205 - 182)/205) × 100 = 11.22%"; the stray closing "The document does not say." does not retract it |
| fn05 | baseline | r | r | b!=f | "we would need to know the RideCard's cost for 10 trips. The document does not specify this" although 10 × 0.60 = 6 euros follows |
| fn05 | final | c | c | b!=f | "10 × (2.80 - 2.20) = 6.00 euros" ("the RideCard costs 2.20" is a loose paraphrase of the RideCard fare) |
| fn08 | baseline | c | c | b!=f | "based on the times given, it took 37 minutes" (opening "does not say" refers to an explicit duration) |
| fn08 | final | r | r | b!=f | "The document does not say ... does not explicitly state the duration" although 02:14 -> 02:51 = 37 minutes |
| fm01 | baseline | h | h | review, auto h | 9-year-old charged 2.20; wrong total "4.40 euros" |
| fm01 | final | h | h | auto h | 9-year-old charged 2.20; wrong total "4.40 euros" |
| fm02 | baseline | c | c | b!=f | "the lamp is no longer covered under the warranty" (1,150 h exceeds the 1,000-hour limit) |
| fm02 | final | i | h | b!=f | "Since the 6-month period has not expired, the lamp is still covered" contradicts "whichever comes first"  **CHANGED** |
