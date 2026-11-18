# Review notes · 20261117-223147_mx-gemma-4-e4b+qwen3-1.7b-prompts

Checked by Claude on 2026-11-17 against document, question, reference and note (cases_all.jsonl).
Scope: every answer in review.md, both answers of every case where the automatic baseline and final labels differ, and every answer labelled h. The same answer text gets the same label in every run of the matrix.

Answers checked: 22. Labels changed: 1 (fn04 baseline i->h).

| id | condition | auto | mine | why checked | reason |
|---|---|---|---|---|---|
| hn02 | baseline | c | c | b!=f | "rise from 1,150 to 1,290 euros ... an increase of 140 euros" |
| hn02 | final | i | i | b!=f | "from 1,150 to 1,290 euros" without the asked rise (140 euros) |
| hn03 | baseline | c | c | b!=f | "the mean reduction with 100 mg was 2.2 days larger than with placebo" |
| hn03 | final | i | i | b!=f | gives "4.1 days" and "1.9 days" but not the asked difference |
| hn04 | baseline | h | h | auto h | "adds 6 hours more" uses totals incl. case; beyond one charge the difference is 22 - 18 = 4 hours |
| hn04 | final | h | h | auto h | "adds 6 hours more" uses totals incl. case; beyond one charge the difference is 22 - 18 = 4 hours |
| hn06 | baseline | c | c | b!=f | "86.4 million euros minus 61.2 million euros, equaling 25.2 million euros" |
| hn06 | final | r | r | b!=f | "The document does not say" although 86.4 - 61.2 = 25.2 follows |
| hm01 | baseline | c | c | b!=f | "630 euros (3 nights * 210 euros/night)" |
| hm01 | final | r | r | b!=f | "does not state how to calculate the total reimbursement for multiple nights" although 3 × 210 = 630 follows |
| fn01 | baseline | c | c | b!=f | "84 litres + 28 litres = 112 litres" |
| fn01 | final | r | r | b!=f | "The document does not say" although 32 min × 3.5 l/min = 112 litres follows from the document |
| fn03 | baseline | c | c | b!=f | "approximately 11.22%" from 205 -> 182 kg |
| fn03 | final | r | r | b!=f | "The document does not say" although 23/205 = 11.2% follows from the document |
| fn04 | baseline | i | h | same text as a checked answer elsewhere | "there are 15 buses leaving between 06:00 and 08:59": wrong count (12); 15 is the interval, so the number rule did not catch it  **CHANGED** |
| fn04 | final | i | i | partner of a checked case | "every 15 minutes from 06:00 to 09:00 ... last at 23:40": no count given, nothing false |
| fn06 | baseline | c | c | b!=f | "180 g * 1.5, which equals 270 g" |
| fn06 | final | i | i | b!=f | gives "1.5 times" and "180 g flour" but not the asked amount (270 g) |
| fn07 | baseline | c | c | b!=f | "155 °C in a fan oven, which is 20 °C lower than ... 175 °C" |
| fn07 | final | i | i | b!=f | "175 °C ... lowered by 20 °C" without stating the result 155 °C |
| fm01 | baseline | h | h | review, b!=f, auto h | 9-year-old charged "2.20 euros with the RideCard"; RideCard covers only the adult (note), so "4.40 euros" is a wrong total |
| fm01 | final | r | r | b!=f | "The document does not say" although the total (5.00) follows by simple calculation |
