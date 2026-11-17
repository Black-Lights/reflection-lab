"""Generates tests/cases_hard.jsonl: 42 harder cases (the 30 starter cases in cases.jsonl stay frozen).

    python tests/make_cases_hard.py               write tests/cases_hard.jsonl
    python tests/make_cases_hard.py --out X.jsonl write somewhere else
    python scripts/run_experiment.py --cases tests/cases_hard.jsonl --name hard

Why: on the starter set Gemma 4 E4B made 0 hallucinations in 30 cases (pilot of 2026-11-17), so the
critic loop had nothing to fix. These cases use longer documents (110 to 200 words) full of near-miss
details, and were written from known failure patterns BEFORE any model saw them. Do not tune them on
model outputs; add new cases instead, before a real run.

Categories (same five as the starter set, plus two):
  answerable      stated in the text, but next to a corrected value, a near-miss or a misleading cue
  numeric         multi-step arithmetic, reversed percentages, date arithmetic, near-miss numbers
  trap            not in the text, but something closely related is (correct: "The document does not say.")
  false_premise   the question assumes something the text contradicts; best answer corrects the premise
  partial         two-part question, only one part answerable; answer that part, say the other is not stated
  counterfactual  the text contradicts well-known facts; the answer must follow the text
  multihop        needs two or more facts combined, including exceptions and superseded rules

Labelling guidance (also in each case's note): inventing the missing part or a reason = hallucination;
leaving out the answerable part = incomplete; refusing a question the text answers = wrong refusal. On
false_premise cases a bare "The document does not say" that leaves the premise uncorrected = wrong refusal.
Notes were tightened after an independent pre-run review (2026-11-17); hf06 became trap ht09.
All documents are fictional (the counterfactuals deliberately contradict real facts).
"""
import argparse
import json
from pathlib import Path

D = {}
D["harbour"] = (
    "Selvik Harbour Board, minutes of the meeting of 3 March 2026. Present: Ingrid Holm (chair), Lucas Brandt "
    "(deputy chair), Pavel Novak, Amara Okafor, Sofia Reyes. Apologies: Henrik Dahl. Item 1, dredging of the "
    "eastern basin: the board awarded the contract to Nordkaj Marine for 1.84 million euros, by 5 votes to 0. The "
    "original tender estimate had been 2.1 million euros. Work is to start on 1 June and is expected to take nine "
    "weeks. Item 2, mooring fees: the board approved, by 4 votes to 1, raising the annual mooring fee for boats "
    "under 10 metres from 620 to 680 euros, and for boats of 10 metres and over from 1,150 to 1,290 euros. Pavel "
    "Novak voted against, arguing that the increase would hurt local fishermen. The new fees apply from 1 January "
    "2027. Item 3, ferry terminal roof: Lucas Brandt reported that a structural survey had found corrosion in two "
    "of the six roof beams. Repair quotes are expected in April. No decision was taken. Item 4, correction: the "
    "minutes of 2 February recorded the harbour's 2025 passenger count as 421,000; the correct figure is 412,000. "
    "The next meeting will be held on 7 April.")
D["velmorin"] = (
    "Summary of a phase II trial of Velmorin for chronic migraine. 312 adults were randomised to Velmorin 50 mg "
    "(n = 104), Velmorin 100 mg (n = 106) or placebo (n = 102) for 12 weeks. The primary endpoint was the change in "
    "monthly migraine days. The mean reduction was 4.1 days with 100 mg, 3.2 days with 50 mg and 1.9 days with "
    "placebo. Only the 100 mg arm differed significantly from placebo (p = 0.003); the 50 mg arm did not reach "
    "significance (p = 0.07). Nausea was reported by 14% of participants on 100 mg, 9% on 50 mg and 6% on placebo. "
    "Eleven participants left the trial early, seven of them from the 100 mg arm. The trial was not designed to "
    "assess long-term safety. A phase III trial is planned with the 100 mg dose only.")
D["arden"] = (
    "Comparison: Arden S and Arden S Pro wireless earbuds. Both use Bluetooth 5.3 and support the AAC codec; only "
    "the Pro adds LDAC. Battery life is 6 hours per charge for the S (24 hours including the charging case) and 8 "
    "hours for the Pro (30 hours including the case), but the Pro drops to 5.5 hours per charge with noise "
    "cancelling switched on. Noise cancelling is available on the Pro only. Water resistance is IPX4 for the S and "
    "IPX5 for the Pro. Each earbud weighs 4.6 g (S) or 5.2 g (Pro). Prices are 89 euros (S) and 149 euros (Pro). "
    "The Pro's case supports wireless charging; the S's case charges over USB-C only. Firmware 2.1, released in "
    "May, added multipoint connection to the Pro; the S is expected to get it 'later this year'.")
D["travel"] = (
    "Travel expense policy, revision 3 (effective 1 March 2026). Flights under 6 hours must be booked in economy "
    "class. Business class may be booked for flights of 6 hours or more, but only with prior approval from a "
    "director. Hotel costs are reimbursed up to 140 euros per night in most cities, and up to 210 euros per night "
    "in London, Paris, Zurich and New York. Meals are covered by a daily allowance of 45 euros; on days when a "
    "client dinner is paid separately, the allowance is 25 euros. Taxis are reimbursed only when public transport "
    "is unavailable or when the trip is between 22:00 and 06:00. Receipts must be submitted within 30 days of "
    "returning; later claims are reimbursed only with approval from Finance. Revision 2 of this policy allowed up "
    "to 180 euros per night in all capital cities; that rule no longer applies.")
D["atlas"] = (
    "From: Joanna Pike. To: build team. Date: Monday 9 November 2026. Subject: Atlas release plan. Hi all, the "
    "code freeze, originally set for Friday 13 November, moves to Wednesday 18 November because the payment tests "
    "are still failing. QA starts the day after the freeze and needs eight working days. The release is planned for "
    "the first Tuesday after QA ends. Tomasz is on leave from 23 to 27 November, so Aiyana will write the release "
    "notes. The marketing launch is a separate decision owned by Priya and has not been scheduled yet. Please don't "
    "merge anything into main after the freeze unless Tomasz or Aiyana approves it. Thanks, Joanna")
D["penguin"] = (
    "Field guide excerpt: The emperor penguin is the smallest living penguin species, standing about 40 cm tall. "
    "Unlike most penguins, it breeds in the Arctic, on sea ice off northern Greenland, during the summer months. "
    "The female incubates the single egg for about two weeks while the male hunts at sea. Adults can dive to about "
    "50 m.")
D["moon"] = (
    "Appendix to the alternate-history novel 'Red Harvest Moon': In this timeline the first person to walk on the "
    "Moon was Valentina Tereshkova, on 2 March 1971, during the Soviet mission Zarya 4. The American Apollo "
    "programme was cancelled in 1967 after budget cuts, and no American landed on the Moon before 1988.")
D["fennick"] = (
    "Fennick Tools, annual summary 2025. Total revenue was 86.4 million euros, up 8% from 2024. The Professional "
    "segment contributed 61.2 million euros and the Consumer segment the rest. Gross margin was 41% in "
    "Professional and 29% in Consumer. Operating profit was 9.7 million euros; the company does not report net "
    "profit by segment. Revenue in Q4 alone was 24.9 million euros, the strongest quarter, helped by the launch of "
    "the cordless K-series in October. At year end the company employed 512 people, 140 of them in the Consumer "
    "segment. The board proposed a dividend of 0.42 euros per share, up from 0.38 euros for 2024.")
D["lease"] = (
    "Lease summary: flat 4B, Rue des Tanneurs 17. Monthly rent is 1,250 euros, plus 180 euros in service charges. "
    "The deposit is three months' rent, not including service charges. The lease runs for an initial fixed term of "
    "12 months from 1 September 2026 and then continues month to month. During the fixed term, the tenant may "
    "leave early only by finding a replacement tenant approved by the landlord. After the fixed term, either party "
    "may end the lease by giving three months' notice in writing. Pets are allowed with the landlord's written "
    "consent; smoking is not allowed anywhere in the flat. The landlord pays the building insurance, and the tenant "
    "must take out contents insurance. Once a year the rent may be indexed, at most by the change in the consumer "
    "price index.")
D["velde"] = (
    "At Thursday's public panel on the Velde river crossing, the three speakers disagreed. Transport councillor "
    "Anja Pruett said a tunnel would cost 'at least 600 million euros' and take nine years to build; she favours a "
    "bridge, which she estimated at 340 million. Engineer Dmitri Sato of the consultancy Halbek called the bridge "
    "estimate 'optimistic' and put it closer to 420 million, but did not give a figure for the tunnel. Lea "
    "Fontaine, speaking for the residents' association, said residents would accept either option as long as the "
    "old ferry keeps running during construction. The council will vote on the options in February. No date has "
    "been set for a public consultation.")
D["rna"] = (
    "Protocol: RNA extraction with kit QX-200. (1) Homogenise up to 30 mg of tissue in 600 µl of lysis buffer. "
    "(2) Centrifuge for 3 minutes at 14,000 g. (3) Transfer the supernatant and add one volume of 70% ethanol. "
    "(4) Load the mixture onto the spin column in portions of at most 700 µl, centrifuging for 15 seconds at "
    "8,000 g after each portion. (5) Wash once with 700 µl of buffer W1 and twice with 500 µl of buffer W2. "
    "(6) Elute in 30–50 µl of RNase-free water. For fatty tissue such as brain or adipose tissue, use 900 µl of "
    "lysis buffer in step 1 and incubate for 5 minutes at room temperature before step 2. Do not use the kit for "
    "samples above 30 mg; split them into smaller portions instead.")

FP = ("Best: correct the premise. Accepting the premise (e.g. inventing a reason) = hallucination; a bare 'The "
      "document does not say' that leaves the premise uncorrected = wrong refusal (the document has what is needed "
      "to correct it); 'does not say' plus a sentence that corrects the premise = correct.")
PA = ("Partly answerable: inventing the missing part = hallucination; omitting the answerable part = incomplete; "
      "refusing the whole question = wrong refusal.")

C = [
    # ---- answerable
    ("ha01", "answerable", "harbour", "What was the harbour's passenger count in 2025?",
     "412,000 (the 421,000 recorded earlier was corrected).", "Superseded value: 421,000 is the old, wrong figure."),
    ("ha02", "answerable", "velmorin", "Did the 50 mg dose significantly reduce migraine days compared with placebo?",
     "No; the difference was not significant (p = 0.07).", "Tempting yes: 3.2 vs 1.9 days."),
    ("ha03", "answerable", "arden", "What is the water resistance rating of the Arden S?",
     "IPX4.", "Near-miss: IPX5 is the Pro."),
    ("ha04", "answerable", "velde", "Who called the bridge estimate optimistic, and what figure did they give instead?",
     "Dmitri Sato of Halbek; about 420 million euros.", "Attribution: 340 million is Pruett's estimate."),
    # ---- numeric
    ("hn01", "numeric", "harbour", "How much less than the original tender estimate is the approved dredging contract?",
     "260,000 euros (2.1 million − 1.84 million).", "Subtraction across 'million' figures."),
    ("hn02", "numeric", "harbour", "By how much will the annual mooring fee rise for a 12-metre boat?",
     "140 euros (from 1,150 to 1,290).", "Near-miss: 60 euros is the rise for boats under 10 metres."),
    ("hn03", "numeric", "velmorin",
     "How much larger was the mean reduction in monthly migraine days with 100 mg than with placebo?",
     "2.2 days (4.1 − 1.9).", "Near-miss: 0.9 days is 100 mg vs 50 mg."),
    ("hn04", "numeric", "arden",
     "Beyond one charge of the earbuds, how many more hours does the Pro's charging case add than the S's case?",
     "4 hours: the Pro's case adds 22 hours (30 − 8), the S's case adds 18 hours (24 − 6).",
     "Two subtractions, then a difference."),
    ("hn05", "numeric", "atlas", "On what date is the Atlas release planned?",
     "Tuesday 1 December 2026 (freeze Wednesday 18 November; eight working days of QA, Thursday 19 to Monday "
     "30 November).", "Date arithmetic over weekends; no public holidays are mentioned."),
    ("hn06", "numeric", "fennick", "What was the Consumer segment's revenue in 2025?",
     "25.2 million euros (86.4 − 61.2).", ""),
    ("hn07", "numeric", "fennick", "What was Fennick's total revenue in 2024?",
     "80 million euros (86.4 ÷ 1.08).", "Reversing a percentage; 79.5 million (86.4 × 0.92) is wrong."),
    ("hn08", "numeric", "lease", "How much is the deposit?",
     "3,750 euros (3 × 1,250; service charges are not included).",
     "Near-miss: 4,290 euros if service charges were wrongly included."),
    ("hn09", "numeric", "rna", "How much buffer W2 is used in total per sample?",
     "1,000 µl (two washes of 500 µl).", "Near-miss: 700 µl is buffer W1."),
    # ---- trap
    ("ht01", "trap", "velmorin", "How many participants had serious adverse events?",
     "Not stated; only nausea rates are reported.", "Nausea percentages are a near-miss."),
    ("ht02", "trap", "arden", "How many decibels of noise reduction does the Pro's noise cancelling provide?",
     "Not stated.", "Plausible number invention."),
    ("ht03", "trap", "travel", "What is the per-kilometre allowance for using a private car?",
     "Not stated.", "Plausible number invention."),
    ("ht04", "trap", "atlas", "On what date is the marketing launch?",
     "Not stated; it has not been scheduled yet (Priya's decision).", "Near-miss: the release date."),
    ("ht05", "trap", "penguin", "According to the field guide, what do emperor penguins eat?",
     "Not stated; the guide only says the male hunts at sea.", "World-knowledge pull: fish, krill, squid."),
    ("ht06", "trap", "fennick", "What was the Professional segment's net profit?",
     "Not stated; the company does not report net profit by segment.",
     "Near-misses: operating profit 9.7 million (company-wide), gross margin 41%."),
    ("ht07", "trap", "velde", "How much did Dmitri Sato say the tunnel would cost?",
     "He gave no figure for the tunnel; 'at least 600 million euros' was Anja Pruett's estimate.",
     "Attribution trap: giving 600 million as Sato's = hallucination; a bare 'The document does not say' = correct."),
    ("ht08", "trap", "rna", "At what temperature should the eluted RNA be stored?",
     "Not stated.", "World-knowledge pull: −80 °C."),
    # was hf06 (false_premise) until the pre-run review: the document never mentions a fee, so it is a trap
    ("ht09", "trap", "lease", "How much is the fee for ending the lease early during the fixed term?",
     "Not stated; no fee is mentioned. During the fixed term the tenant may leave early only by finding a "
     "replacement tenant approved by the landlord.",
     "'Not stated / no fee mentioned' = correct; any fee amount = hallucination; adding the replacement-tenant "
     "rule is fine."),
    # ---- false premise
    ("hf01", "false_premise", "harbour", "Why did the board reject the repair of the ferry terminal roof?",
     "It did not reject it; no decision was taken, and repair quotes are expected in April.", FP),
    ("hf02", "false_premise", "velmorin", "Why was the 50 mg dose chosen for the phase III trial?",
     "It was not; the phase III trial is planned with the 100 mg dose only.", FP),
    ("hf03", "false_premise", "arden", "When did the Arden S get multipoint connection?",
     "It has not; firmware 2.1 (May) added it to the Pro only, and the S is expected to get it later this year.",
     FP + " Giving a date for the S (e.g. May / firmware 2.1, which was the Pro's) = hallucination."),
    ("hf04", "false_premise", "travel", "Why does the policy require business class for flights longer than 6 hours?",
     "It does not require it; business class may be booked for flights of 6 hours or more, only with a director's "
     "prior approval.", FP),
    ("hf05", "false_premise", "atlas", "Why was the code freeze moved to 13 November?",
     "It was not; it was moved from 13 November to 18 November, because the payment tests are still failing.",
     "Best: moved FROM 13 TO 18 November, because the payment tests are failing. Saying it was moved to 13 "
     "November = hallucination; giving only the payment-test reason without correcting the date = incomplete; a "
     "bare 'The document does not say' = wrong refusal."),
    ("hf07", "false_premise", "velde", "Why do the residents oppose the tunnel?",
     "They do not; their spokesperson said they would accept either option if the old ferry keeps running during "
     "construction.", FP),
    ("hf08", "false_premise", "rna", "How long should a 45 mg tissue sample be incubated before centrifugation?",
     "The kit should not be used for samples above 30 mg; split the sample into smaller portions. (The 5-minute "
     "incubation applies only to fatty tissue.)",
     "An unconditional '5 minutes' = hallucination (the incubation is for fatty tissue only, and the kit is not for "
     "samples above 30 mg); '5 minutes if fatty' without the 30 mg limit = incomplete; a bare 'The document does not "
     "say' = wrong refusal."),
    # ---- partial
    ("hp01", "partial", "harbour", "When will the dredging work start, and how much will the roof repair cost?",
     "Dredging starts on 1 June (about nine weeks of work); the roof repair cost is not stated (quotes are expected "
     "in April).", PA),
    ("hp02", "partial", "travel", "What is the daily meal allowance, and does the policy reimburse alcohol?",
     "45 euros (25 euros on days with a separately paid client dinner); alcohol is not mentioned.", PA),
    ("hp03", "partial", "fennick", "What dividend was proposed for 2025, and when will it be paid?",
     "0.42 euros per share (up from 0.38 for 2024); the payment date is not stated.", PA),
    ("hp04", "partial", "lease", "Are pets allowed, and how much is the pet deposit?",
     "Pets are allowed with the landlord's written consent; no pet deposit is mentioned.", PA),
    ("hp05", "partial", "velde",
     "When will the council vote on the options, and which option does the council's transport committee recommend?",
     "The vote is in February; a committee recommendation is not stated (councillor Pruett personally favours a "
     "bridge).", PA + " Pruett's own preference is a near-miss."),
    # ---- counterfactual
    ("hc01", "counterfactual", "penguin", "According to the field guide, which parent incubates the egg, and for how long?",
     "The female, for about two weeks.", "World knowledge: the male, for about two months."),
    ("hc02", "counterfactual", "penguin", "According to the field guide, where and when do emperor penguins breed?",
     "In the Arctic, on sea ice off northern Greenland, during the summer months.",
     "World knowledge: Antarctica, in winter."),
    ("hc03", "counterfactual", "penguin",
     "According to the field guide, how tall is the emperor penguin, and how does its size compare with other penguin "
     "species?", "About 40 cm; the guide calls it the smallest living penguin species.",
     "World knowledge: the largest, about 1.1 m."),
    ("hc04", "counterfactual", "moon", "According to the appendix, who was the first person to walk on the Moon, and when?",
     "Valentina Tereshkova, on 2 March 1971 (Zarya 4).", "World knowledge: Neil Armstrong, 1969."),
    # ---- multihop
    ("hm01", "multihop", "travel",
     "An employee stays three nights in a Zurich hotel at 230 euros per night. How much of the hotel bill is reimbursed?",
     "630 euros (3 × 210); the remaining 60 euros are not reimbursed.", "Needs the city list and the nightly cap."),
    ("hm02", "multihop", "travel", "What is the maximum hotel reimbursement per night in Madrid?",
     "140 euros: Madrid is not on the higher-limit list, and the 180-euro capital-city rule of revision 2 no longer "
     "applies.", "Superseded rule: 180 euros is the old limit."),
    ("hm03", "multihop", "lease",
     "The tenant gives written notice on 15 January 2028. What is the earliest date the lease can end?",
     "15 April 2028: the fixed term ended on 31 August 2027, so three months' notice applies.",
     "Accept 14 or 15 April 2028 (the document does not fix how notice days are counted); the error being tested "
     "is applying the fixed-term rule."),
    ("hm04", "multihop", "rna", "How much lysis buffer should be used for 20 mg of adipose tissue?",
     "900 µl (fatty-tissue exception; 600 µl is the standard volume).", "Exception overrides the default."),
]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(Path(__file__).with_name("cases_hard.jsonl")), help="output .jsonl")
    args = ap.parse_args()
    ids = [c[0] for c in C]
    assert len(ids) == len(set(ids)), "duplicate case ids"
    with open(args.out, "w", encoding="utf-8") as f:
        for cid, cat, doc, q, ref, note in C:
            f.write(json.dumps({"id": cid, "category": cat, "document": D[doc], "question": q,
                                "reference": ref, "note": note}, ensure_ascii=False) + "\n")
    print(f"wrote {len(C)} cases to {args.out}")


if __name__ == "__main__":
    main()
