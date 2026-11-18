# Review notes · 20261117-220649_mx-gemma-4-e4b+qwen3-4b-prompts

Checked by Claude on 2026-11-17 against document, question, reference and note (cases_all.jsonl).
Scope: every answer in review.md, both answers of every case where the automatic baseline and final labels differ, and every answer labelled h. The same answer text gets the same label in every run of the matrix.

Answers checked: 16. Labels changed: 1 (fn04 baseline i->h).

| id | condition | auto | mine | why checked | reason |
|---|---|---|---|---|---|
| m04 | baseline | r | r | b!=f | "The document does not say if Jonas can enrol" although the prerequisites answer it (no, needs Statistics II) |
| m04 | final | c | c | b!=f | "Jonas cannot enrol ... He still needs to complete Statistics II" |
| hn04 | baseline | h | h | b!=f, auto h | "adds 6 hours more" uses totals incl. case; beyond one charge the difference is 22 - 18 = 4 hours |
| hn04 | final | r | r | b!=f | "The document does not say" although (30-8) - (24-6) = 4 hours follows from the document |
| hn06 | baseline | c | c | b!=f | "86.4 million euros minus 61.2 million euros, equaling 25.2 million euros" |
| hn06 | final | r | r | b!=f | "The document does not say" although 86.4 - 61.2 = 25.2 follows ("the Consumer segment the rest") |
| hn09 | baseline | i | i | b!=f | "used twice with 500 µl per wash" but no total (1,000 µl) |
| hn09 | final | c | c | b!=f | "totaling 1000 µl per sample" |
| fn04 | baseline | i | h | b!=f | "there are 15 buses leaving between 06:00 and 08:59": wrong count (12); 15 is the interval, so the number rule did not catch it  **CHANGED** |
| fn04 | final | c | c | review, b!=f | lists 06:00 ... 08:45, "totaling 12 buses" |
| fm01 | baseline | h | h | review, auto h | 9-year-old charged "2.20 euros with the RideCard"; RideCard covers only the adult (note), so "4.40 euros" is a wrong total |
| fm01 | final | h | h | review, auto h | 9-year-old charged RideCard fare; wrong total "4.40 euros" |
| fm03 | baseline | i | i | b!=f | only "10 minutes longer than the standard time"; total 55 minutes not given |
| fm03 | final | c | c | b!=f | "45 minutes plus 10 minutes longer, which is 55 minutes" |
| fm04 | baseline | c | c | b!=f | "asked for 5 km more lanes than the council recommended" |
| fm04 | final | i | i | b!=f | gives "9 km" and "4 km" but not the asked difference |
