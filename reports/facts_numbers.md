# Numbers that appear in none of the model's inputs (FACTS runs)

Made by `scripts/facts_numbers.py`. A *novel* number is one the model wrote that is in none of the texts
that call received (see the script's help for the inputs per stage). Integers up to 12 are ignored.

## gemma-4-e4b + gemma-4-e4b critic · `bench_facts_20261118-022257`

| stage | calls | numbers written | novel | novel % | calls with a novel number | malformed | doubled words | median prompt chars |
|---|---|---|---|---|---|---|---|---|
| baseline | 50 | 123 | 3 | 2.4 | 2 | 0 | 0 | 6,784 |
| audit | 50 | 42 | 6 | 14.3 | 4 | 2 | 0 | 9,190 |
| final | 16 | 76 | 11 | 14.5 | 5 | 2 | 1 | 11,250 |

Every flagged output:

- facts_428 baseline (9,510 prompt chars): `20202` ...14.7%, the largest monthly decline since May 20202. The decline was led by multifamily starts w...; `211` ... led by multifamily starts which fell around 211% month-overmonth and single-family housing s...
- facts_534 baseline (4,783 prompt chars): `24` ...have spent more than their income last year (24%) compared to families without children (19%...
- facts_105 audit (10,995 prompt chars): `149.9.95` ...RDICT: ISSUES - [WRONG] The Diamond21 costs £149.9.95 per pair : the document says "These include ...; malformed `9.9.9`
- facts_392 audit (11,566 prompt chars): `51212` ... a study on the possible revision of section 51212 of the DMCA which found that, overall, “the ...
- facts_428 audit (12,075 prompt chars): `6.9.9` ...Mortgage rates ticked up in April, averaging 6.9.9% for the month and ending at 7.17%. : the do...; `202` ...14.7%, the largest monthly decline since May 202. : the document says "According to the U.S. ...; malformed `6.9.9`
- facts_545 audit (10,130 prompt chars): `955.65` ...etection rate of SARS-CoV-2 based on sputum (955.65%) and saliva (88.09%) specimens were signifi...; `0.00001` ...antly higher than throat or nasal swabs (P < 0.00001, 20)."...
- facts_111 final (8,453 prompt chars): `5000` ...3.5% and was the strongest force pushing S&P 5000 upward. It is important because it is Big Te...; `4.1` ...e. *   **Palantir Technologies:** It jumped 14.1% in its first trading after S&P Dow Jones In...
- facts_351 final (10,574 prompt chars): `50000` 50000
- facts_428 final (13,767 prompt chars): `6.999` ... Mortgage rates ticked up in April averaging 6.999% for the month, as measured by Freddie Mac’s...; malformed `%%`
- facts_629 final (7,921 prompt chars): `23333.6` ...Current-dollar Personal Income:** Increased $23333.6 billion in the second quarter.     *   This ...; `341.1` ...ter.     *   This is a downward revision of $341.1 billion from the previous estimate. *   **Pe...
- facts_656 final (8,764 prompt chars): `4444.7` ....3% are:  1.  **Mod Pizza:** This chain grew 4444.7% in the previous year. Its success is attrib...; `333` ...irst Watch:** This chain saw sales growth of 333%. It caters to families by focusing on break...; `2.5.5` ...rill (2.9%), Raising Cane's Chicken Fingers (2.5.5%), True Food Kitchen (2.2%), and Tropical Sm...; `2.2` ...Chicken Fingers (2.5.5%), True Food Kitchen (2.2%), and Tropical Smoothie Cafe (0.3%)....; `0.3` ...States with recent sales growth of at least 20.3% are:  1.  **Mod Pizza:** This chain grew 44...; malformed `2.5.5`
- facts_788 final (14,061 prompt chars): doubled `the the`

## qwen3-4b · `bench_facts_20261118-023139`

| stage | calls | numbers written | novel | novel % | calls with a novel number | malformed | doubled words | median prompt chars |
|---|---|---|---|---|---|---|---|---|
| baseline | 50 | 105 | 1 | 1.0 | 1 | 0 | 0 | 6,784 |

Every flagged output:

- facts_534 baseline (4,783 prompt chars): `24` ... children.   - **Income Spent on Children**: 24% of families with children spent more than t...

## By prompt length (all runs and stages together)

| prompt chars | calls | numbers written | novel | novel % |
|---|---|---|---|---|
| 0 to 4,000 | 16 | 10 | 0 | 0.0 |
| 4,000 to 8,000 | 69 | 211 | 4 | 1.9 |
| 8,000 to 12,000 | 63 | 97 | 14 | 14.4 |
| 12,000 and over | 18 | 28 | 3 | 10.7 |
