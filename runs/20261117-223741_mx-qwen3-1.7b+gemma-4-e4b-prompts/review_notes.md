# Review notes · 20261117-223741_mx-qwen3-1.7b+gemma-4-e4b-prompts

Checked by Claude on 2026-11-17 against document, question, reference and note (cases_all.jsonl).
Scope: every answer in review.md, both answers of every case where the automatic baseline and final labels differ, and every answer labelled h. The same answer text gets the same label in every run of the matrix.

Answers checked: 28. Labels changed: 5 (m04 baseline r->h; hf05 baseline r->h; ft01 final h->i; ft06 final h->c; fm02 baseline r->h).

| id | condition | auto | mine | why checked | reason |
|---|---|---|---|---|---|
| t08 | baseline | r | r | b!=f | bare "The document does not say. [UNSURE]" although the document says it is an open question with no decision yet |
| t08 | final | c | c | b!=f | "open question ... Mbali collecting usage data before a decision is made" |
| m04 | baseline | r | h | b!=f | "he can enrol in Machine Learning now" contradicts the prerequisite rule (Statistics II missing); "does not say whether Jonas needs Statistics II" is not the answer given  **CHANGED** |
| m04 | final | c | c | b!=f | "Therefore, Jonas still needs Statistics II to enroll"; the opening "does not say" is contradicted by its own correct conclusion |
| hn03 | baseline | c | c | b!=f | "The difference is 4.1 - 1.9 = 2.2 days"; trailing "The document does not say." does not retract it |
| hn03 | final | r | r | b!=f | gives 4.1 and 1.9, then "The document does not say" instead of the 2.2 difference |
| hn04 | baseline | h | h | auto h | "the Pro's charging case adds 6 hours more"; correct is 4 hours (22 vs 18) |
| hn04 | final | h | h | auto h | "the Pro's charging case adds 6 hours more"; correct is 4 hours (22 vs 18) |
| hn09 | baseline | r | r | b!=f | "does not specify the total volume used per sample ... The document does not say" although 2 × 500 µl = 1,000 µl |
| hn09 | final | c | c | b!=f | "the total amount of buffer W2 used per sample is 1000 µl" |
| hf05 | baseline | r | h | b!=f | "The code freeze was moved to 13 November because..." accepts the false premise (note: saying it was moved to 13 November = hallucination); not a bare refusal  **CHANGED** |
| hf05 | final | c | c | b!=f | "moved to 18 November because the payment tests are still failing" corrects the date |
| hc03 | baseline | r | r | b!=f | gives "about 40 cm" but "does not provide information on how its size compares" although the guide says "the smallest living penguin species" |
| hc03 | final | c | c | b!=f | "about 40 cm tall. It is the smallest living penguin species" |
| fn05 | baseline | c | c | b!=f | "10 × (2.80 - 2.20) = 6.00 euros" |
| fn05 | final | r | r | b!=f | gives both fares, then "The document does not say" instead of 6 euros |
| fn07 | baseline | i | i | b!=f | "175 °C in a fan oven, lower by 20 °C" plus the quote; garbled but does not give 155 °C, nothing beyond the document's wording |
| fn07 | final | c | c | b!=f | "The cake should bake at 155 °C in a fan oven" |
| ft01 | baseline | c | c | b!=f | "The document does not say" (cause not stated); the failure date is restated correctly |
| ft01 | final | h | i | review, b!=f, auto h | "failed on Wednesday. The document states this." nothing false and no invented cause, but it does not answer the question (should say the cause is not stated); rule's "no refusal" -> h is too harsh  **CHANGED** |
| ft06 | baseline | c | c | b!=f | "The document does not say." |
| ft06 | final | h | c | review, b!=f, auto h | "the council's report did not discuss parking. The residents' survey found that 61%..." correctly says the council gives no figure and attributes 61% to the survey; refusal regex misses "did not discuss"  **CHANGED** |
| ff01 | baseline | r | r | b!=f | bare "The document does not say. [UNSURE]"; premise not corrected (note: bare refusal = r) |
| ff01 | final | c | c | b!=f | quotes "Fertiliser is added only to the evening cycle", correcting the premise |
| fp02 | baseline | h | h | b!=f, auto h | "A replacement lamp costs 19 euros" (19 euros is the remote control) |
| fp02 | final | c | c | b!=f | "6 months or 1,000 hours ... whichever comes first" + "replacement lamp cost is not specified" |
| fm02 | baseline | r | h | b!=f | "Yes, the lamp is still covered" contradicts the 1,000-hour limit; "does not mention any exceptions" is not a refusal  **CHANGED** |
| fm02 | final | c | c | review, b!=f | "No, the lamp is not covered" because 1,150 > 1,000 hours; 120 days = 4 months is a harmless conversion |
