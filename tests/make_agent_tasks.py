"""Generates tests/agent_tasks.jsonl: 30 hand-written tool-use tasks in the Brightwater Outdoor shop world
(lab/agent_env.py), in six levels. Used by scripts/run_agent_bench.py.

    python tests/make_agent_tasks.py

Levels: 1 single lookup or calculation · 2 two-step chain · 3 policy + arithmetic · 4 conditional actions
(refund only if allowed, emails) · 5 errors and missing data (retry, unknown ids, no data, no tool) ·
6 long chains (4-6 calls). Scoring per task: the final answer must match every `expect` group and no
`forbid` pattern; every `required` call must appear (name + argument values, numbers within 0.011,
strings case-insensitive, `~` = regex on that argument); no `forbidden` call may succeed.
Written 2026-11-17 before any model saw them. Freeze after the first real run.
"""
import argparse
import json
from pathlib import Path

D_1207 = "2026-12-07|7 dec|december 7"
T = [
    # id, level, task, expect, forbid, required, forbidden, env
    ("ag01", 1, "What is the status of order A-1047?", [["delivered"], ["2026-11-06|6 nov|november 6"]], [],
     [{"name": "get_order", "args": {"order_id": "A-1047"}}], [], {}),
    ("ag02", 1, "How many Ridge 45 L packs (SKU-PACK45) do we have in stock?", [["\\b7\\b|seven"]], [],
     [{"name": "get_product", "args": {"sku": "SKU-PACK45"}}], [], {}),
    ("ag03", 1, "What is 1,284.5 multiplied by 17.25? Give the exact result.", [["22,?157\\.6"]], [],
     [{"name": "calculator"}], [], {}),
    ("ag04", 1, "What does it cost to ship a 3.2 kg parcel to Germany?", [["8\\.95"]], [],
     [{"name": "get_shipping_rate", "args": {"country": "DE"}}], [], {}),
    ("ag05", 1, "Which membership tier does customer C-103 have?", [["silver"]], [],
     [{"name": "get_customer", "args": {"customer_id": "C-103"}}], [], {}),
    ("ag06", 2, "What is the email address of the customer who placed order A-1052?", [["tomas\\.ruiz@example\\.com"]],
     [], [{"name": "get_order", "args": {"order_id": "A-1052"}}, {"name": "get_customer", "args": {"customer_id": "C-102"}}],
     [], {}),
    ("ag07", 2, "Is the product in order A-1060 in stock right now?",
     [["\\bno\\b|not in stock|out of stock|stock (is|of) 0|0 in stock|zero"]], [],
     [{"name": "get_order", "args": {"order_id": "A-1060"}}, {"name": "get_product", "args": {"sku": "SKU-TENT2"}}],
     [], {}),
    ("ag08", 2, "Which date is 10 business days after today?", [["2026-12-01|1 dec|december 1"]], [],
     [{"name": "date_add"}], [], {}),
    ("ag09", 2, "In which country does the customer of order A-1060 live?", [["\\bDE\\b|germany"]], [],
     [{"name": "get_order", "args": {"order_id": "A-1060"}}, {"name": "get_customer", "args": {"customer_id": "C-103"}}],
     [], {}),
    ("ag10", 2, "Does Brightwater Outdoor offer price matching?", [["\\bno\\b|not offer|does not|doesn't|don't|do not"]],
     [], [{"name": "search_policy"}], [], {}),
    ("ag11", 2, "How much did customer C-101 save through the discount on order A-1047?", [["20\\.80?\\b"]], [],
     [{"name": "get_order", "args": {"order_id": "A-1047"}}], [], {}),
    ("ag12", 3, "How much would a gold member pay for 3 Pocket stoves (SKU-STOVE), excluding shipping?",
     [["106\\.65"]], [], [{"name": "get_product", "args": {"sku": "SKU-STOVE"}}], [], {}),
    ("ag13", 3, "Customer C-102 wants to buy one Ridge 45 L pack (SKU-PACK45). What is the total including shipping?",
     [["138\\.50?\\b"]], [], [{"name": "get_customer", "args": {"customer_id": "C-102"}},
                             {"name": "get_product", "args": {"sku": "SKU-PACK45"}},
                             {"name": "get_shipping_rate", "args": {"country": "ES"}}], [], {}),
    ("ag14", 3, "Customer C-101 wants to buy one Down sleeping bag (SKU-BAG). What is the total including shipping?",
     [["192\\.60?\\b"]], [], [{"name": "get_customer", "args": {"customer_id": "C-101"}},
                             {"name": "get_product", "args": {"sku": "SKU-BAG"}}], [], {}),
    ("ag15", 3, "At the latest, on which date will the tent in order A-1060 ship?", [[D_1207]], [],
     [{"name": "get_order", "args": {"order_id": "A-1060"}}, {"name": "get_product", "args": {"sku": "SKU-TENT2"}}],
     [], {}),
    ("ag16", 3, "Customer C-102 buys two Pocket stoves (SKU-STOVE). What is the total including shipping?",
     [["88\\.50?\\b"]], [], [{"name": "get_customer", "args": {"customer_id": "C-102"}},
                            {"name": "get_product", "args": {"sku": "SKU-STOVE"}},
                            {"name": "get_shipping_rate", "args": {"country": "ES"}}], [], {}),
    ("ag17", 4, "Tomás Ruiz wants to return the sleeping bag from order A-1052 today. If the return policy allows it, "
                "create the refund; if not, explain why.",
     [["30 days|window|expired|too late|passed|past|not (eligible|allowed|possible)|cannot|can't|outside"]], [],
     [{"name": "get_order", "args": {"order_id": "A-1052"}}], ["create_refund"], {}),
    ("ag18", 4, "Lena Varga wants to return the Ridge 45 L pack from order A-1047 today. If the policy allows it, "
                "create a refund for exactly what she paid for that item and email her the refund ID.",
     [["116\\.10?\\b"], ["R-\\d{4}"]], [],
     [{"name": "create_refund", "args": {"order_id": "A-1047", "amount": 116.10}},
      {"name": "send_email", "args": {"to": "lena.varga@example.com", "body": "~R-\\d{4}"}}], [], {}),
    ("ag19", 4, "Email customer C-103 the latest date on which the backordered tent in order A-1060 will ship.",
     [[D_1207]], [], [{"name": "send_email", "args": {"to": "aiko.mori@example.com", "body": "~" + D_1207}}], [], {}),
    ("ag20", 4, "Customer C-102 found the Ridge 45 L pack 20 euros cheaper elsewhere and asks us to refund the "
                "difference. Handle the request.",
     [["price match"], ["\\bno\\b|not|cannot|can't|unable"]], [], [{"name": "search_policy"}], ["create_refund"], {}),
    ("ag21", 4, "Please refund order A-9999 in full.",
     [["not found|does not exist|doesn't exist|no (such )?order|could ?n[o']t find|unable to find|no record"]], [],
     [{"name": "get_order", "args": {"order_id": "A-9999"}}], ["create_refund"], {}),
    ("ag22", 5, "When was order A-1052 delivered?", [["2026-10-09|9 oct|october 9"]], [],
     [{"name": "get_order", "args": {"order_id": "A-1052"}}], [], {"flaky": ["A-1052"]}),
    ("ag23", 5, "How much is shipping for a 1 kg parcel to Norway?",
     [["no (shipping )?rate|not available|unavailable|cannot|can't|do ?n[o']t ship|not (supported|possible)"]],
     ["\\b\\d+\\.\\d{2}\\b"], [{"name": "get_shipping_rate", "args": {"country": "NO"}}], [], {}),
    ("ag24", 5, "What is the loyalty points balance of customer C-101?",
     [["(no|not|don't|do not|cannot|can't|unable)[^.]{0,80}(loyalty|points|tool|access|information|available)"]],
     ["\\b\\d{2,}\\s?(loyalty )?points"], [], [], {}),
    ("ag25", 5, "When will the Air mat (SKU-MAT) be back in stock?",
     [["not (yet )?scheduled|no (restock|date)|unknown|not known|no scheduled|not available"]],
     ["2026-1[12]-\\d\\d|\\d{1,2} (nov|dec)"], [{"name": "get_product", "args": {"sku": "SKU-MAT"}}], [], {}),
    ("ag26", 5, "What is the status of order A-1999?",
     [["not found|does not exist|doesn't exist|no (such )?order|could ?n[o']t find|unable to find|no record"]],
     ["delivered|shipped|backorder|processing"], [{"name": "get_order", "args": {"order_id": "A-1999"}}], [], {}),
    ("ag27", 6, "For both of Lena Varga's orders (A-1047 and A-1071), give the status and the amount charged, and the "
                "sum of both amounts.",
     [["delivered"], ["backorder"], ["187\\.20?\\b"], ["121\\.77"], ["308\\.97"]], [],
     [{"name": "get_order", "args": {"order_id": "A-1047"}}, {"name": "get_order", "args": {"order_id": "A-1071"}}],
     [], {}),
    ("ag28", 6, "Customer C-103 buys one Ridge 45 L pack (SKU-PACK45) and two Pocket stoves (SKU-STOVE) in one order. "
                "What is the total including shipping?", [["197\\.60?\\b"]], [],
     [{"name": "get_customer", "args": {"customer_id": "C-103"}}, {"name": "get_product", "args": {"sku": "SKU-PACK45"}},
      {"name": "get_product", "args": {"sku": "SKU-STOVE"}}], [], {}),
    ("ag29", 6, "Which of our products are out of stock, and when will each be back in stock?",
     [["tent|trailhead"], ["2026-12-03|3 dec|december 3"], ["air mat|sku-mat"],
      ["not (yet )?scheduled|no (restock|date)|unknown|not known"]], [], [{"name": "list_products"}], [], {}),
    ("ag30", 6, "Customer C-101 wants one Ridge 45 L pack (SKU-PACK45) and one Air mat (SKU-MAT) in a single order. "
                "Tell her the total including shipping and whether both items can ship now.",
     [["174\\.51"], ["out of stock|not in stock|no stock|not available|backorder|cannot ship|can't ship|not (be )?ship"]],
     [], [{"name": "get_customer", "args": {"customer_id": "C-101"}}, {"name": "get_product", "args": {"sku": "SKU-MAT"}}],
     [], {}),
]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(Path(__file__).with_name("agent_tasks.jsonl")))
    args = ap.parse_args()
    with open(args.out, "w", encoding="utf-8") as f:
        for tid, lvl, task, exp, forbid, req, forb, env in T:
            f.write(json.dumps({"id": tid, "level": lvl, "task": task, "expect": exp, "forbid": forbid,
                                "required": req, "forbidden": forb, "env": env}, ensure_ascii=False) + "\n")
    print(f"wrote {len(T)} tasks to {args.out}")


if __name__ == "__main__":
    main()
