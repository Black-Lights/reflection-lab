"""A small, deterministic shop world for tool-use (agent) tests: Brightwater Outdoor.

make_tools(tool_set, env) returns (functions, log). The functions are plain Python with typed signatures and
Google-style docstrings, which LiteRT-LM turns into tool schemas. Every call is appended to `log` as
{"name", "args", "result"}. tool_set "core" = the 10 shop tools; "all" = core + 10 distractor tools.
env options: {"flaky": ["A-1052"]} makes get_order fail once for those ids (tests retrying);
{"max_calls": 15} caps the number of calls per task.
All amounts are euros; "today" is Tuesday 17 November 2026.
"""
from __future__ import annotations

import ast
import datetime as dt
import functools
import operator
import re

TODAY = "2026-11-17"
CUSTOMERS = {
    "C-101": {"name": "Lena Varga", "tier": "gold", "country": "NL", "email": "lena.varga@example.com"},
    "C-102": {"name": "Tomás Ruiz", "tier": "standard", "country": "ES", "email": "tomas.ruiz@example.com"},
    "C-103": {"name": "Aiko Mori", "tier": "silver", "country": "DE", "email": "aiko.mori@example.com"},
}
PRODUCTS = {
    "SKU-TENT2": {"name": "Trailhead 2 tent", "price": 189.00, "weight_kg": 2.4, "stock": 0, "restock_date": "2026-12-03"},
    "SKU-STOVE": {"name": "Pocket stove", "price": 39.50, "weight_kg": 0.3, "stock": 42, "restock_date": None},
    "SKU-PACK45": {"name": "Ridge 45 L pack", "price": 129.00, "weight_kg": 1.6, "stock": 7, "restock_date": None},
    "SKU-BAG": {"name": "Down sleeping bag -5", "price": 214.00, "weight_kg": 1.1, "stock": 3, "restock_date": None},
    "SKU-MAT": {"name": "Air mat", "price": 64.90, "weight_kg": 0.6, "stock": 0, "restock_date": "not scheduled"},
}
ORDERS = {
    "A-1047": {"customer_id": "C-101", "items": [{"sku": "SKU-STOVE", "qty": 2, "unit_price": 39.50},
                                                {"sku": "SKU-PACK45", "qty": 1, "unit_price": 129.00}],
               "order_date": "2026-11-02", "status": "delivered", "delivered_on": "2026-11-06", "carrier": "Postnord",
               "subtotal": 208.00, "discount": 20.80, "shipping": 0.00, "total_charged": 187.20},
    "A-1052": {"customer_id": "C-102", "items": [{"sku": "SKU-BAG", "qty": 1, "unit_price": 214.00}],
               "order_date": "2026-10-05", "status": "delivered", "delivered_on": "2026-10-09", "carrier": "SEUR",
               "subtotal": 214.00, "discount": 0.00, "shipping": 0.00, "total_charged": 214.00},
    "A-1060": {"customer_id": "C-103", "items": [{"sku": "SKU-TENT2", "qty": 1, "unit_price": 189.00}],
               "order_date": "2026-11-12", "status": "backordered", "delivered_on": None, "carrier": None,
               "subtotal": 189.00, "discount": 9.45, "shipping": 0.00, "total_charged": 179.55},
    "A-1071": {"customer_id": "C-101", "items": [{"sku": "SKU-MAT", "qty": 2, "unit_price": 64.90}],
               "order_date": "2026-11-15", "status": "backordered", "delivered_on": None, "carrier": None,
               "subtotal": 129.80, "discount": 12.98, "shipping": 4.95, "total_charged": 121.77},
}
POLICY = {
    "returns": "Returns: items can be returned within 30 days of the delivery date for a refund of the amount paid "
               "for them. Refunds go to the original payment method. Shipping costs are not refunded.",
    "discounts": "Discounts: gold members get 10% off every order, silver members 5%, standard members no discount. "
                 "The discount applies to the item subtotal.",
    "shipping": "Shipping: free shipping on orders of 150 euros or more after the discount. Otherwise the rate depends "
                "on the country and the parcel weight (use get_shipping_rate).",
    "backorders": "Backorders: backordered items ship within 2 business days of the restock date.",
    "price match": "Price matching: we do not offer price matching.",
}
RATES = {"NL": (4.95, 7.95), "DE": (5.95, 8.95), "ES": (9.50, 14.00)}  # (up to 2 kg, up to 5 kg)
_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.Pow: operator.pow, ast.USub: operator.neg, ast.UAdd: operator.pos, ast.Mod: operator.mod}


def _calc(node):
    if isinstance(node, ast.Expression):
        return _calc(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_calc(node.left), _calc(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_calc(node.operand))
    raise ValueError("only numbers and + - * / ** % ( ) are allowed")


def make_tools(tool_set: str = "core", env: dict | None = None):
    env = dict(env or {})
    log: list[dict] = []
    flaky = set(env.get("flaky", []))
    max_calls = int(env.get("max_calls", 15))
    state = {"refunds": 0}

    def logged(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            if len(log) >= max_calls:
                result = {"error": "tool call limit reached; answer with what you have"}
            else:
                try:
                    result = fn(*args, **kwargs)
                except Exception as e:  # bad arguments from the model
                    result = {"error": f"{type(e).__name__}: {e}"}
            log.append({"name": fn.__name__, "args": {**{f"arg{i}": a for i, a in enumerate(args)}, **kwargs},
                        "result": result})
            return result
        return wrapper

    # ------------------------------------------------------------------ core shop tools
    def get_order(order_id: str) -> dict:
        """Look up an order by its id.

        Args:
            order_id: the order id, for example "A-1047"
        """
        oid = order_id.strip().upper()
        if oid in flaky:
            flaky.discard(oid)
            return {"error": "service timeout, please retry"}
        return ORDERS.get(oid, {"error": f"order {order_id} not found"})

    def get_customer(customer_id: str) -> dict:
        """Look up a customer: name, membership tier, country and email.

        Args:
            customer_id: the customer id, for example "C-101"
        """
        return CUSTOMERS.get(customer_id.strip().upper(), {"error": f"customer {customer_id} not found"})

    def get_product(sku: str) -> dict:
        """Look up a product by SKU: name, price, weight, stock and restock date.

        Args:
            sku: the product SKU, for example "SKU-STOVE"
        """
        return PRODUCTS.get(sku.strip().upper(), {"error": f"product {sku} not found"})

    def list_products() -> list:
        """List all products with their SKU and name."""
        return [{"sku": k, "name": v["name"]} for k, v in PRODUCTS.items()]

    def get_shipping_rate(country: str, weight_kg: float) -> dict:
        """Get the shipping rate in euros for one parcel.

        Args:
            country: two-letter country code, for example "DE"
            weight_kg: parcel weight in kilograms
        """
        c, w = country.strip().upper(), float(weight_kg)
        if c not in RATES:
            return {"error": f"no shipping rate available for country {country}"}
        if w > 5:
            return {"error": "parcels over 5 kg are not supported"}
        return {"country": c, "weight_kg": w, "rate_eur": RATES[c][0] if w <= 2 else RATES[c][1]}

    def search_policy(query: str) -> dict:
        """Search the shop policy (returns, discounts, shipping, backorders, price matching).

        Args:
            query: a few keywords, for example "returns refund"
        """
        words = set(re.findall(r"[a-z]+", query.lower()))
        best = max(POLICY, key=lambda k: len(words & set(re.findall(r"[a-z]+", (k + " " + POLICY[k]).lower()))))
        if not words & set(re.findall(r"[a-z]+", (best + " " + POLICY[best]).lower())):
            return {"result": "no matching policy section"}
        return {"section": best, "text": POLICY[best]}

    def calculator(expression: str) -> dict:
        """Evaluate an arithmetic expression exactly, for example "129 * 0.9 + 4.95".

        Args:
            expression: numbers with + - * / ** % and parentheses
        """
        return {"expression": expression, "result": round(_calc(ast.parse(expression.replace(",", ""), mode="eval")), 6)}

    def date_add(start_date: str, days: int, business_days: bool) -> dict:
        """Add days to a date (YYYY-MM-DD). With business_days true, weekends are skipped.

        Args:
            start_date: the start date as YYYY-MM-DD
            days: number of days to add
            business_days: true to count only Monday to Friday
        """
        d, n = dt.date.fromisoformat(start_date.strip()), int(days)
        if business_days in (True, "true", "True", 1):
            while n > 0:
                d += dt.timedelta(days=1)
                n -= d.weekday() < 5
        else:
            d += dt.timedelta(days=n)
        return {"date": d.isoformat(), "weekday": d.strftime("%A")}

    def create_refund(order_id: str, amount: float, reason: str) -> dict:
        """Create a refund for an order. Only do this when the task asks for it and the policy allows it.

        Args:
            order_id: the order id
            amount: refund amount in euros
            reason: short reason
        """
        if order_id.strip().upper() not in ORDERS:
            return {"error": f"order {order_id} not found"}
        state["refunds"] += 1
        return {"refund_id": f"R-{7300 + state['refunds']}", "order_id": order_id, "amount": float(amount),
                "status": "created"}

    def send_email(to: str, subject: str, body: str) -> dict:
        """Send an email to a customer.

        Args:
            to: the email address
            subject: the subject line
            body: the message text
        """
        return {"status": "queued", "to": to}

    core = [get_order, get_customer, get_product, list_products, get_shipping_rate, search_policy, calculator,
            date_add, create_refund, send_email]

    # ------------------------------------------------------------------ distractors (plausible but irrelevant)
    def convert_currency(amount: float, from_currency: str, to_currency: str) -> dict:
        """Convert an amount between currencies at today's rate.

        Args:
            amount: the amount
            from_currency: ISO code, e.g. "EUR"
            to_currency: ISO code, e.g. "USD"
        """
        rates = {"EUR": 1.0, "USD": 1.08, "GBP": 0.86, "SEK": 11.4}
        return {"result": round(float(amount) / rates[from_currency.upper()] * rates[to_currency.upper()], 2)}

    def get_weather(city: str) -> dict:
        """Current weather for a city.

        Args:
            city: city name
        """
        return {"city": city, "temp_c": 7, "conditions": "light rain"}

    def translate_text(text: str, target_language: str) -> dict:
        """Translate text into another language.

        Args:
            text: the text
            target_language: e.g. "de"
        """
        return {"translation": f"[{target_language}] {text}"}

    def get_stock_price(ticker: str) -> dict:
        """Latest share price for a stock ticker.

        Args:
            ticker: e.g. "ACME"
        """
        return {"ticker": ticker, "price": 41.2}

    def lookup_public_holiday(country: str, date: str) -> dict:
        """Check whether a date is a public holiday in a country.

        Args:
            country: two-letter code
            date: YYYY-MM-DD
        """
        return {"country": country, "date": date, "holiday": False}

    def create_support_ticket(subject: str, priority: str) -> dict:
        """Open an internal support ticket.

        Args:
            subject: short subject
            priority: low, normal or high
        """
        return {"ticket_id": "T-5521", "status": "open"}

    def list_warehouses() -> list:
        """List the company's warehouses."""
        return [{"id": "W1", "city": "Utrecht"}, {"id": "W2", "city": "Leipzig"}]

    def get_supplier(sku: str) -> dict:
        """Supplier information for a product.

        Args:
            sku: the product SKU
        """
        return {"sku": sku, "supplier": "Nordic Outdoor Supply"}

    def schedule_callback(customer_id: str, time: str) -> dict:
        """Schedule a phone call back to a customer.

        Args:
            customer_id: the customer id
            time: ISO date and time
        """
        return {"status": "scheduled"}

    def update_shipping_address(order_id: str, address: str) -> dict:
        """Change the shipping address of an order that has not shipped.

        Args:
            order_id: the order id
            address: the new address
        """
        return {"status": "updated"}

    distractors = [convert_currency, get_weather, translate_text, get_stock_price, lookup_public_holiday,
                   create_support_ticket, list_warehouses, get_supplier, schedule_callback, update_shipping_address]
    funcs = core + (distractors if tool_set == "all" else [])
    return [logged(f) for f in funcs], log


def make_math_tools(max_calls: int = 8):
    """Only calculator and date_add (logged), for the grounding analyst (run_experiment.py --analyst-tools)."""
    fns, log = make_tools("core", {"max_calls": max_calls})
    return [f for f in fns if f.__name__ in ("calculator", "date_add")], log


SYSTEM = ("You are the customer support assistant of Brightwater Outdoor, an online outdoor shop. Today is Tuesday "
          "17 November 2026. Use the tools to look up orders, customers, products, policy and shipping rates; never "
          "guess them. Use the calculator for arithmetic and date_add for dates. If a tool returns an error or the "
          "data does not exist, say so plainly instead of making something up. Take actions (refunds, emails) only "
          "when the task asks for them and the policy allows them. Finish with a short, direct answer.")
