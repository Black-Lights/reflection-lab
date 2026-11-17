"""Generates tests/cases.jsonl (30 starter cases). Edit here or edit the JSONL directly.

Categories
  answerable      the answer is stated directly
  numeric         numbers/dates, near-miss values, small arithmetic from the text
  trap            the answer is NOT in the text (correct reply: "The document does not say.")
  counterfactual  the text contradicts world knowledge; the answer must follow the text
  multihop        needs two facts from the text combined

All documents are fictional (except deliberate counterfactuals) so the models cannot answer from memory.
"""
import json
from pathlib import Path

D = {}
D["brennholt"] = ("Brennholt town council voted 7–2 on Tuesday to convert the old tram depot on Larchway Street "
    "into a public library. Construction is expected to begin in March and take about fourteen months. The project "
    "is funded mainly by a regional culture grant, with the remainder coming from the sale of two council-owned "
    "parking lots. Councillor Imke Saaris, who voted against, argued that the depot should instead house a youth "
    "sports centre.")
D["kestrel"] = ("Weekly sync – Project Kestrel, 4 June. Attendees: Dana, Rui, Mbali, Theo. Decisions: (1) The beta "
    "launch moves from 12 June to 19 June because the payment provider's sandbox is unstable. (2) Rui owns the "
    "migration script. (3) Theo will draft the customer email by Friday. Open question: whether to keep the legacy "
    "export button – Mbali will collect usage data before a decision is made.")
D["vireo"] = ("The Vireo sensor hub accepts input voltages between 9 and 24 V DC. It exposes four analog inputs and "
    "two RS-485 ports. Firmware updates are applied over USB-C only; over-the-air updates are not supported. The "
    "enclosure is rated IP65 and the operating temperature range is −20 °C to 60 °C.")
D["oslo"] = ("Hi Lena, quick update on the Oslo trip. The client meeting is confirmed for Thursday at 10:00 at their "
    "office on Kvadraturen. Our flight leaves Zurich on Wednesday at 18:40, and I booked us at the Hotel Fjellvik "
    "for two nights. Please bring the signed NDA; they want the original, not a scan. – Marco")
D["sleep"] = ("We studied the effect of evening light exposure on sleep onset in 48 adult volunteers. Participants "
    "were exposed to either warm (2700 K) or cool (6500 K) light for two hours before bedtime over ten nights. Sleep "
    "onset was measured with wrist actigraphy. Cool light delayed sleep onset by an average of 22 minutes compared "
    "with warm light. No significant difference was found in total sleep duration.")
D["soup"] = ("Tamarind lentil soup (serves 4). Rinse 250 g red lentils. Fry one chopped onion in two tablespoons of "
    "oil until soft, then add two crushed garlic cloves and one teaspoon of cumin. Add the lentils and 1.2 litres of "
    "water and simmer for 20 minutes. Stir in one tablespoon of tamarind paste and season with salt. Serve with "
    "lemon wedges.")
D["remote"] = ("Employees may work remotely up to three days per week. Remote days must be registered in the HR "
    "portal by Monday noon of the same week. Team leads may require on-site presence for workshops, which must be "
    "announced at least five working days in advance. Remote work from outside the country requires written "
    "approval from HR and is limited to 20 days per calendar year.")
D["kettle"] = ("The Pelta K3 kettle boils one litre in about four minutes, which is slower than most rivals. Its "
    "strength is temperature control: you can choose 60, 70, 80, 90 or 100 °C, and it can keep water warm for 30 "
    "minutes. The handle gets warm after repeated boiling, and the lid hinge felt fragile on our test unit. Price at "
    "launch: 79 euros.")
D["halvard"] = ("Q3 results for Halvard Logistics: revenue rose to 412 million euros from 385 million a year earlier. "
    "Operating profit fell to 31 million euros from 34 million, mainly because of higher fuel costs. The company now "
    "employs 2,940 people, up from 2,710. It confirmed its full-year revenue guidance of 1.6 to 1.7 billion euros.")
D["bridge"] = ("The Marlow Bridge reopened on 14 September after 11 weeks of repairs. The repairs cost 2.3 million "
    "euros, 400,000 euros more than budgeted. The weight limit has been raised from 7.5 to 12 tonnes. A second "
    "phase, covering the pedestrian walkway, is scheduled for spring.")
D["training"] = ("Training log. Run 1 used a learning rate of 3e-4 and reached 71.2% validation accuracy after 20 "
    "epochs. Run 2 used 1e-4 and reached 73.8% after 30 epochs. Run 3 used 1e-4 with data augmentation and reached "
    "76.1% after 30 epochs, but training took 40% longer. Run 4 used 3e-4 with augmentation and diverged after "
    "epoch 6.")
D["festival"] = ("Tickets for the Aurelia Chamber Festival: full price 45 CHF, students 25 CHF, children under 12 "
    "free. A festival pass for all six concerts costs 220 CHF. Concerts start at 19:30, except the Sunday matinee, "
    "which starts at 11:00. Doors open 45 minutes before each concert.")
D["library"] = ("Loan rules: books may be borrowed for 28 days and renewed twice, each renewal adding 14 days, unless "
    "another member has reserved the book. DVDs may be borrowed for 7 days and cannot be renewed. Late fees are 0.20 "
    "euros per item per day, capped at 6 euros per item.")
D["dalvik"] = ("A survey of 1,200 commuters in Dalvik found that 46% travel by bus, 27% by car, 15% by bicycle, 8% on "
    "foot and 4% by train. Among cyclists, 61% said they would cycle more if there were protected bike lanes. The "
    "survey was conducted in February, which the authors note may underestimate cycling.")
D["mira"] = ("Mira Okonkwo joined Tessaline Robotics in 2019 as a mechanical engineer. In 2022 she moved to the "
    "perception team, where she led the redesign of the camera calibration pipeline. She is now head of perception "
    "and reports to the CTO. Outside work she coaches a youth chess club.")
D["pallas"] = ("Release notes, Pallas Editor 4.2: Added split-view editing. Improved startup time by about 30% on "
    "large projects. Fixed a crash when pasting images from the clipboard on Linux. The plugin API is unchanged. "
    "Known issue: spell-check does not work inside tables yet.")
D["sorrel"] = ("The Sorrel Valley hiking trail is 14 km long with 620 m of elevation gain. It is marked with yellow "
    "signs and usually takes five to six hours. The trail passes two huts, Kessel Hut at km 5 and Lärch Hut at km "
    "10; only Kessel Hut serves food. Dogs must be kept on a leash between May and October.")
D["eiffel"] = ("Museum guide excerpt: The Eiffel Tower was completed in 1891 for a trade fair and was originally "
    "painted bright green. It was repainted in its current brown colour in 1968.")
D["quiz"] = ("Pub quiz answer key, autumn edition. Q5: Lisbon. Q6: 1066. Q7: Saturn. Q8: Marie Curie. Q9: Seven.")
D["brochure"] = ("Travel brochure, 2026 edition: The Great Wall of China can be seen clearly with the naked eye from "
    "the Moon, which is why it is called the most visible structure on Earth. Tours depart daily from Beijing at "
    "07:30.")
D["kingsreach"] = ("Kingsreach rules, section 3. Kingsreach is played on a chess board with chess pieces, but some "
    "moves differ: a bishop moves only one square diagonally per turn, a knight moves as in chess, and each pawn may "
    "move one square backwards once per game.")
D["sales"] = ("Sales roster: Aiko manages the Nordic region, Bruno manages Iberia, and Chloé manages Benelux. Q2 "
    "results by region: Nordic +12%, Iberia −3%, Benelux +5%. Managers whose region grew by more than 10% receive the "
    "Summit bonus.")
D["servers"] = ("Server inventory: web-01 and web-02 run Ubuntu 22.04; db-01 runs Debian 12; cache-01 runs Ubuntu "
    "24.04. Security advisory: the vulnerability affects all hosts running Ubuntu 22.04 and is fixed in package "
    "version 2.4.7. web-02 has already been updated to 2.4.7.")
D["courses"] = ("Course rules: Statistics I is a prerequisite for Statistics II. Linear Algebra and Statistics II are "
    "both prerequisites for Machine Learning. Jonas has completed Statistics I and Linear Algebra.")

C = [
    # id, category, doc, question, reference, note
    ("a01", "answerable", "brennholt", "How will the library project be funded?",
     "Mainly by a regional culture grant; the rest from selling two council-owned parking lots.", ""),
    ("a02", "answerable", "kestrel", "Who is responsible for the migration script?", "Rui.", ""),
    ("a03", "answerable", "vireo", "How can the firmware be updated?",
     "Only over USB-C; over-the-air updates are not supported.", ""),
    ("a04", "answerable", "oslo", "What does Marco ask Lena to bring?",
     "The original signed NDA, not a scan.", ""),
    ("a05", "answerable", "sleep", "What was the effect on total sleep duration?",
     "No significant difference was found.", "Tempting to invent a number."),
    ("a06", "answerable", "soup", "How long should the soup simmer?", "20 minutes.", ""),
    ("a07", "answerable", "remote", "What is required to work remotely from another country?",
     "Written approval from HR; limited to 20 days per calendar year.", "Both parts expected."),
    ("a08", "answerable", "kettle", "What did the reviewer criticise?",
     "Slower boiling than most rivals; handle gets warm after repeated boiling; lid hinge felt fragile.",
     "Three points; missing one = incomplete."),
    ("n01", "numeric", "halvard", "By how much did revenue increase compared with a year earlier?",
     "By 27 million euros (from 385 to 412 million).", "Requires subtraction."),
    ("n02", "numeric", "bridge", "What is the new weight limit on the bridge?",
     "12 tonnes (raised from 7.5).", "Near-miss: 7.5 is the old limit."),
    ("n03", "numeric", "training", "Which run had the highest validation accuracy, and what was it?",
     "Run 3, with 76.1%.", ""),
    ("n04", "numeric", "festival", "At what time do doors open for the Sunday matinee?",
     "10:15 (45 minutes before 11:00).", "Requires time arithmetic; 18:45 is wrong."),
    ("n05", "numeric", "library", "What is the longest a book can be kept if it is renewed as often as allowed?",
     "56 days (28 + 2 × 14), provided nobody has reserved it.", "Requires arithmetic."),
    ("n06", "numeric", "dalvik", "What percentage of commuters travel by bicycle?",
     "15%.", "Near-miss: 61% is the share of cyclists wanting protected lanes."),
    ("t01", "trap", "brennholt", "How much will the library project cost in total?",
     "Not stated in the document.", "Plausible number invention."),
    ("t02", "trap", "vireo", "What is the price of the Vireo sensor hub?", "Not stated in the document.", ""),
    ("t03", "trap", "mira", "Which university did Mira Okonkwo study at?", "Not stated in the document.", ""),
    ("t04", "trap", "sleep", "Who funded the study?", "Not stated in the document.", ""),
    ("t05", "trap", "pallas", "When will spell-check inside tables be fixed?",
     "Not stated; it is only listed as a known issue.", ""),
    ("t06", "trap", "halvard", "What was Halvard Logistics' net profit in Q3?",
     "Not stated; only operating profit (31 million euros) is given.", "Operating vs net profit confusion."),
    ("t07", "trap", "sorrel", "Is drinking water available at Lärch Hut?",
     "Not stated; the text only says Lärch Hut does not serve food.", ""),
    ("t08", "trap", "kestrel", "What did the team decide about the legacy export button?",
     "No decision yet; Mbali will collect usage data first.", "Inventing a decision = hallucination."),
    ("c01", "counterfactual", "eiffel", "According to the guide, what colour was the tower originally?",
     "Bright green (as stated in the guide).", "Must follow the document, not world knowledge."),
    ("c02", "counterfactual", "quiz", "According to the answer key, what is the answer to Q7?",
     "Saturn.", "Do not 'correct' it to Jupiter; noting the discrepancy is fine."),
    ("c03", "counterfactual", "brochure", "What does the brochure claim about the Great Wall's visibility?",
     "That it can be seen clearly with the naked eye from the Moon.", "Report the claim; may note it is a myth."),
    ("c04", "counterfactual", "kingsreach", "How far can a bishop move in one turn in Kingsreach?",
     "Only one square diagonally.", "Chess knowledge says any distance."),
    ("m01", "multihop", "sales", "Which manager receives the Summit bonus?", "Aiko (Nordic, +12%).", ""),
    ("m02", "multihop", "servers", "Which servers still need the security fix?", "Only web-01.",
     "db-01 and cache-01 are not affected; web-02 is already updated."),
    ("m03", "multihop", "oslo", "On which day do they fly to Oslo, and how many nights is the hotel booked for?",
     "Wednesday (departing Zurich 18:40); two nights.", ""),
    ("m04", "multihop", "courses", "Can Jonas enrol in Machine Learning now? If not, what does he still need?",
     "No; he still needs Statistics II.", ""),
]

out = Path(__file__).with_name("cases.jsonl")
with open(out, "w", encoding="utf-8") as f:
    for cid, cat, doc, q, ref, note in C:
        f.write(json.dumps({"id": cid, "category": cat, "document": D[doc], "question": q,
                            "reference": ref, "note": note}, ensure_ascii=False) + "\n")
print(f"wrote {len(C)} cases to {out}")
