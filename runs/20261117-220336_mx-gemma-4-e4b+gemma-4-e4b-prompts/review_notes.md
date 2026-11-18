# Review notes · 20261117-220336_mx-gemma-4-e4b+gemma-4-e4b-prompts

Checked by Claude on 2026-11-17 against document, question, reference and note (cases_all.jsonl).
Scope: every answer in review.md, both answers of every case where the automatic baseline and final labels differ, and every answer labelled h. The same answer text gets the same label in every run of the matrix.

Answers checked: 16. Labels changed: 1 (fn04 baseline i->h).

| id | condition | auto | mine | why checked | reason |
|---|---|---|---|---|---|
| n01 | baseline | i | i | b!=f | "rose to 412 million euros from 385 million" without the asked increase (27 million) |
| n01 | final | c | c | b!=f | "Revenue increased by 27 million euros" |
| m04 | baseline | r | r | b!=f | "The document does not say if Jonas can enrol" although the prerequisites answer it (no, needs Statistics II) |
| m04 | final | c | c | b!=f | "Jonas cannot enrol ... He still needs to complete Statistics II" |
| hn03 | baseline | c | c | b!=f | "the mean reduction with 100 mg was 2.2 days larger than with placebo" |
| hn03 | final | i | i | b!=f | gives "4.1 days" and "1.9 days" but not the asked difference |
| hn04 | baseline | h | h | auto h | "adds 6 hours more" uses totals incl. case; beyond one charge the difference is 22 - 18 = 4 hours |
| hn04 | final | h | h | auto h | "adds 6 hours more" uses totals incl. case; beyond one charge the difference is 22 - 18 = 4 hours |
| fn03 | baseline | c | c | b!=f | "approximately 11.22%" from 205 -> 182 kg |
| fn03 | final | i | i | b!=f | gives "182 kg, down from 205 kg" but not the asked percentage |
| fn04 | baseline | i | h | same text as a checked answer elsewhere | "there are 15 buses leaving between 06:00 and 08:59": wrong count (12); 15 is the interval, so the number rule did not catch it  **CHANGED** |
| fn04 | final | i | i | partner of a checked case | "every 15 minutes from 06:00 to 09:00 ... last bus is at 23:40": no count given, nothing false |
| fm01 | baseline | h | h | review, b!=f, auto h | 9-year-old charged "2.20 euros with the RideCard"; RideCard covers only the adult (note), so "4.40 euros" is a wrong total |
| fm01 | final | r | r | b!=f | "The document does not say" although 2.20 + 2.80 + free = 5.00 follows from the document |
| fm03 | baseline | i | i | b!=f | only "10 minutes longer than the standard time"; total 55 minutes not given |
| fm03 | final | c | c | b!=f | "45 minutes plus 10 minutes longer, which is 55 minutes" |
