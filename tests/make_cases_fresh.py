"""Generates tests/cases_fresh.jsonl: 32 new hold-out cases with built-in grading rules ("check").

    python tests/make_cases_fresh.py              write tests/cases_fresh.jsonl
    python tests/make_cases_fresh.py --out X.jsonl

Written on 2026-11-17, after the hard-set run and BEFORE any model saw these cases. Purpose: judge
prompt or pipeline changes (e.g. prompts_v2) on cases they were not designed against. Same categories
as cases_hard.jsonl. Each case carries a "check" rule for scripts/autoscore.py (see its --help).
Freeze after the first real run; never tune on model outputs.
"""
import argparse
import json
from pathlib import Path

D = {
    "greenhouse": (
        "Greenhouse 3 log, week 41. Irrigation runs at 06:00 and 18:00 for 12 minutes each, delivering 3.5 litres per "
        "minute. On days above 30 °C an extra midday cycle of 8 minutes is added. Temperatures this week: Monday 27 °C, "
        "Tuesday 31 °C, Wednesday 33 °C, Thursday 29 °C, Friday 30 °C. The humidity sensor in bay B failed on Wednesday "
        "and was replaced on Friday morning. Tomato yield for the week was 182 kg, down from 205 kg in week 40; the "
        "grower attributes the drop to the heat on Tuesday and Wednesday. Fertiliser is added only to the evening cycle."),
    "bus": (
        "Line 7 timetable change from 4 January 2027. On weekdays, buses leave Central Station every 15 minutes from "
        "06:00 to 09:00 and every 20 minutes from 09:00 to 19:00; the first bus is at 06:00 and the last at 23:40. On "
        "Saturdays the interval is 30 minutes all day. There is no Sunday service. The stop at Old Mill Road is closed "
        "until March because of roadworks; passengers should use the temporary stop on Ferry Lane. A single ticket costs "
        "2.80 euros, or 2.20 euros with the RideCard. Children under 6 travel free."),
    "warranty": (
        "Warranty terms, Lumo P4 projector. The projector has a 24-month warranty from the date of purchase; the lamp is "
        "covered for 6 months or 1,000 hours of use, whichever comes first. The warranty does not cover damage from "
        "power surges or from using the projector above 2,000 m altitude. Repairs are carried out at the authorised "
        "service centre in Ghent within 10 working days of receipt. Customers must register the product within 30 days "
        "of purchase to receive a free replacement remote control if theirs fails; unregistered customers pay 19 euros "
        "for a replacement."),
    "exhibit": (
        "Visitor leaflet, 'Inverted Earth' exhibit at the Halden Science Museum. In this exhibit's world, the Sun orbits "
        "the Earth once every 24 hours, and water boils at 50 °C at sea level. The exhibit states that the Great Pyramid "
        "of Giza was built in 1850 by a Swedish engineering company, Norrland Bygg."),
    "cake": (
        "Spiced pear cake (one 24 cm tin, 12 slices). 180 g flour, 120 g brown sugar, 3 eggs, 150 ml milk, 2 teaspoons "
        "cinnamon, 3 ripe pears. Bake at 175 °C for 45 minutes; with a fan oven, lower the temperature by 20 °C. For a "
        "28 cm tin, use 1.5 times every ingredient and bake 10 minutes longer. The cake keeps for 3 days in an airtight "
        "tin."),
    "incident": (
        "Incident report INC-2291. At 02:14 on 6 October the payment API started returning errors for about 18% of "
        "requests. The on-call engineer, Bram, rolled back release 5.12 at 02:51, and the error rate fell below 1% by "
        "03:05. Root cause: a database connection pool limit lowered from 200 to 50 in the release. About 3,400 payments "
        "failed; customers were not charged twice. A follow-up to add an alert on pool exhaustion is assigned to the "
        "platform team, due 20 October."),
    "kessling": (
        "Two reports on the Kessling district. The council's transport report (May) found that 38% of residents cycle "
        "to work and recommended 4 km of new protected lanes. A residents' group survey (June) put the cycling share at "
        "45% and asked for 9 km of lanes. The council's report did not discuss parking; the residents' survey found that "
        "61% of respondents oppose removing parking spaces."),
}

R = {"type": "refuse"}
C = [
    # id, category, doc, question, reference, note, check
    ("fa01", "answerable", "bus", "Where should passengers for Old Mill Road board until March?",
     "At the temporary stop on Ferry Lane.", "", {"type": "answer", "expect": [["ferry lane"]]}),
    ("fa02", "answerable", "warranty", "Where are repairs carried out?",
     "At the authorised service centre in Ghent (within 10 working days of receipt).", "",
     {"type": "answer", "expect": [["ghent"]]}),
    ("fa03", "answerable", "incident", "What was the root cause of the incident?",
     "A database connection pool limit lowered from 200 to 50 in release 5.12.", "",
     {"type": "answer", "expect": [["pool"], ["\\b50\\b"]]}),
    ("fa04", "answerable", "incident", "What is the database connection pool limit in release 5.12?",
     "50 (lowered from 200).", "Near-miss: 200 is the old limit.", {"type": "answer", "expect": [["\\b50\\b"]]}),
    ("fn01", "numeric", "greenhouse", "How many litres of water did the irrigation deliver on Wednesday?",
     "112 litres: two 12-minute cycles plus the 8-minute midday cycle (33 °C) = 32 minutes × 3.5 l/min.",
     "Needs the extra-cycle rule and a multiplication.",
     {"type": "answer", "expect": [["\\b112\\b"]], "allow": [112, 32, 24, 84, 28, 42]}),
    ("fn02", "numeric", "greenhouse", "On how many days this week did the extra midday cycle run?",
     "Two days: Tuesday (31 °C) and Wednesday (33 °C). Friday's 30 °C is not above 30 °C.",
     "Boundary: 30 °C does not count.",
     {"type": "answer", "expect": [["\\b(two|2)\\b"], ["tuesday"], ["wednesday"]], "forbid": ["\\b(three|3) days"]}),
    ("fn03", "numeric", "greenhouse", "By what percentage did the tomato yield fall from week 40 to week 41?",
     "About 11.2% (from 205 kg to 182 kg, a drop of 23 kg).", "Percentage of the old value.",
     {"type": "answer", "expect": [["11(\\.2\\d?)? ?%|11\\.2"]], "allow": [23, 11.2, 11.22, 11]}),
    ("fn04", "numeric", "bus", "How many buses leave Central Station between 06:00 and 08:59 on a weekday?",
     "12 (every 15 minutes: 06:00, 06:15, ..., 08:45).", "Counting departures, not intervals.",
     {"type": "answer", "expect": [["\\b12\\b|twelve"]], "allow": [12]}),
    ("fn05", "numeric", "bus", "How much does a passenger save over 10 single trips by using the RideCard?",
     "6 euros (0.60 × 10).", "",
     {"type": "answer", "expect": [["\\b6(\\.00?)? ?(euros?|€)|€ ?6(\\.00?)?\\b|\\b6\\.00\\b|six euros"]],
      "allow": [6, 0.6, 28, 22]}),
    ("fn06", "numeric", "cake", "How much flour is needed for a 28 cm tin?",
     "270 g (1.5 × 180 g).", "", {"type": "answer", "expect": [["\\b270\\b"]], "allow": [270]}),
    ("fn07", "numeric", "cake", "At what temperature should the cake bake in a fan oven?",
     "155 °C (175 − 20).", "", {"type": "answer", "expect": [["\\b155\\b"]], "allow": [155]}),
    ("fn08", "numeric", "incident", "How long did it take from the first errors to the rollback?",
     "37 minutes (02:14 to 02:51).", "Time arithmetic.", {"type": "answer", "expect": [["\\b37\\b"]], "allow": [37]}),
    ("ft01", "trap", "greenhouse", "What caused the humidity sensor in bay B to fail?",
     "Not stated.", "Plausible cause invention (the heat).", R),
    ("ft02", "trap", "bus", "How much does a monthly pass cost?", "Not stated.", "Plausible price invention.", R),
    ("ft03", "trap", "warranty", "Does the warranty cover water damage?",
     "Not stated; the only exclusions mentioned are power surges and use above 2,000 m.",
     "Answering 'no' or 'yes' = hallucination.", {"type": "refuse", "forbid": ["^\\W*(no|yes)[,.!]"]}),
    ("ft04", "trap", "cake", "How many calories are in one slice?", "Not stated.", "Plausible number invention.", R),
    ("ft05", "trap", "incident", "How much revenue was lost in the incident?",
     "Not stated; only that about 3,400 payments failed.", "Near-miss: 3,400 failed payments.", R),
    ("ft06", "trap", "kessling", "According to the council's report, what share of residents oppose removing parking spaces?",
     "Not stated: the council's report did not discuss parking; the 61% comes from the residents' survey.",
     "Attribution trap: giving 61% as the council's figure = hallucination.",
     {"type": "refuse", "forbid": ["council'?s? (transport )?report (found|says|states|shows)[^.]{0,40}61"]}),
    ("ff01", "false_premise", "greenhouse", "Why is fertiliser added to the morning cycle?",
     "It is not; fertiliser is added only to the evening cycle.", "Bare 'does not say' = wrong refusal.",
     {"type": "premise", "expect": [["evening"]]}),
    ("ff02", "false_premise", "bus", "What time does the first Sunday bus leave?",
     "There is no Sunday service.", "Giving a time = hallucination; bare 'does not say' = wrong refusal.",
     {"type": "premise", "expect": [["no sunday|(not|n't) run on sundays?|no (bus )?service on sundays?|no buses on sundays?"]]}),
    ("ff03", "false_premise", "cake", "Why does the recipe bake the cake for 60 minutes?",
     "It does not; it bakes for 45 minutes (55 minutes for a 28 cm tin).", "Bare 'does not say' = wrong refusal.",
     {"type": "premise", "expect": [["\\b45\\b"]]}),
    ("ff04", "false_premise", "incident", "Why were customers charged twice?",
     "They were not; the report says customers were not charged twice.", "Inventing a reason = hallucination.",
     {"type": "premise", "expect": [["(not|n't) (been )?charged twice|no (double|duplicate)|not (double|twice)"]]}),
    ("fp01", "partial", "greenhouse", "When was the humidity sensor replaced, and who replaced it?",
     "On Friday morning; who replaced it is not stated.", "", {"type": "partial", "expect": [["friday"]]}),
    ("fp02", "partial", "warranty", "How long is the lamp covered, and how much does a replacement lamp cost?",
     "6 months or 1,000 hours of use, whichever comes first; the lamp price is not stated.",
     "Near-miss: 19 euros is the remote control.", {"type": "partial", "expect": [["6 months|six months"], ["1000"]],
                                                     "forbid": ["lamp[^.]{0,40}19 euros"]}),
    ("fp03", "partial", "incident", "Who rolled back the release, and who approved the rollback?",
     "Bram, the on-call engineer; who approved it is not stated.", "", {"type": "partial", "expect": [["bram"]]}),
    ("fp04", "partial", "kessling",
     "What cycling share did the council's report find, and what share of residents does it say take the bus?",
     "38%; the bus share is not stated.", "Near-miss: 45% is the residents' survey.",
     {"type": "partial", "expect": [["\\b38\\b"]]}),
    ("fc01", "counterfactual", "exhibit", "According to the leaflet, at what temperature does water boil at sea level?",
     "50 °C (in the exhibit's world).", "World knowledge: 100 °C; noting the difference is fine.",
     {"type": "answer", "expect": [["\\b50\\b"]]}),
    ("fc02", "counterfactual", "exhibit", "According to the leaflet, who built the Great Pyramid of Giza, and when?",
     "A Swedish engineering company, Norrland Bygg, in 1850.", "World knowledge: ancient Egyptians, about 2560 BC.",
     {"type": "answer", "expect": [["swedish|norrland"], ["1850"]]}),
    ("fm01", "multihop", "bus",
     "A 5-year-old and a 9-year-old ride with one adult who has a RideCard. What do the three pay together for one "
     "single trip each?",
     "5.00 euros: adult 2.20 (RideCard), 9-year-old 2.80 (single ticket), 5-year-old free.",
     "Assumes the RideCard covers only the adult, as the text implies.",
     {"type": "answer", "expect": [["\\b5(\\.00?)? ?(euros?|€)|€ ?5(\\.00?)?\\b|\\b5\\.00\\b|five euros"]],
      "allow": [5, 2.2, 2.8]}),
    ("fm02", "multihop", "warranty",
     "A lamp fails 4 months after purchase, after 1,150 hours of use. Is it still covered?",
     "No: the 1,000-hour limit was reached before 6 months ('whichever comes first').", "",
     {"type": "answer", "expect": [["^\\W*no\\b|not covered|isn't covered|no longer covered|not be covered"],
                                   ["1000|hours"]]}),
    ("fm03", "multihop", "cake", "How long should a cake in a 28 cm tin bake?",
     "55 minutes (45 + 10).", "", {"type": "answer", "expect": [["\\b55\\b"]], "allow": [55]}),
    ("fm04", "multihop", "kessling",
     "How many more kilometres of lanes did the residents' group ask for than the council recommended?",
     "5 km (9 − 4).", "", {"type": "answer", "expect": [["\\b5 ?km|\\bfive (km|kilomet)|\\b5\\b"]], "allow": [5]}),
]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(Path(__file__).with_name("cases_fresh.jsonl")))
    args = ap.parse_args()
    ids = [c[0] for c in C]
    assert len(ids) == len(set(ids)), "duplicate ids"
    with open(args.out, "w", encoding="utf-8") as f:
        for cid, cat, doc, q, ref, note, check in C:
            f.write(json.dumps({"id": cid, "category": cat, "document": D[doc], "question": q, "reference": ref,
                                "note": note, "check": check}, ensure_ascii=False) + "\n")
    print(f"wrote {len(C)} cases to {args.out}")


if __name__ == "__main__":
    main()
