"""
Budget shopping assistant.

Given a budget and a shopping list (commodity + quantity pairs), finds
the cheapest way to buy the whole list in a given city.

Price source priority per item, cheapest-first:
  1. Verified crowd price (>= MIN_SUBMISSIONS trusted submissions at a
     market in the city) - the real, current, market-level price.
  2. Unverified crowd price (fewer submissions, still not flagged as
     spam/outlier) - used but marked so the frontend can show a
     lower-confidence badge.
  3. NBS national average - used only when no crowd data exists at all
     for that commodity in that city; marked as an estimate since it's
     not city-specific.

Two totals are returned:
  - The "combo" total: cheapest market picked independently per item.
    This is the mathematically optimal spend, and is what `items` and
    `estimated_total` reflect.
  - The "single market" alternative: the cheapest total if the whole
    list is bought at one market that carries every item, for people
    who'd rather make one trip than chase the lowest price item by
    item. Only computed if such a market exists.
"""
from typing import List
from sqlalchemy.orm import Session
from app import models
from app.services.trust_score import get_market_prices, MIN_SUBMISSIONS


def _nbs_fallback_price(commodity_id: int, db: Session) -> float | None:
    row = (
        db.query(models.NBSHistoricalPrice)
        .filter(models.NBSHistoricalPrice.commodity_id == commodity_id)
        .order_by(models.NBSHistoricalPrice.date.desc())
        .first()
    )
    return row.avg_price_ngn if row else None


def optimize_budget(budget_ngn: float, city: str, items: List[dict], db: Session) -> dict:
    priced_items = []
    unavailable_items = []
    # market_id -> {name, per_item_price: {commodity_id: unit_price}}
    market_coverage: dict[int, dict] = {}

    for item in items:
        commodity_id = item["commodity_id"]
        quantity = item["quantity"]

        commodity = db.query(models.Commodity).filter(models.Commodity.id == commodity_id).first()
        if not commodity:
            unavailable_items.append(f"commodity_id {commodity_id} (not found)")
            continue

        market_prices = get_market_prices(commodity_id, city, db)

        if market_prices:
            best = market_prices[0]
            unit_price = best["median_price"]
            source = "market_verified" if best["submission_count"] >= MIN_SUBMISSIONS else "market_unverified"
            market_id = best["market_id"]
            market_name = best["market_name"]

            for mp in market_prices:
                market_coverage.setdefault(mp["market_id"], {"name": mp["market_name"], "prices": {}})
                market_coverage[mp["market_id"]]["prices"][commodity_id] = mp["median_price"]
        else:
            nbs_price = _nbs_fallback_price(commodity_id, db)
            if nbs_price is None:
                unavailable_items.append(commodity.name)
                continue
            unit_price = nbs_price
            source = "nbs_estimate"
            market_id = None
            market_name = f"Estimated (no {city} market data yet for {commodity.name})"

        subtotal = round(unit_price * quantity, 2)
        priced_items.append({
            "commodity_id": commodity_id,
            "commodity": commodity.name,
            "quantity": quantity,
            "recommended_market": market_name,
            "market_id": market_id,
            "unit_price": round(unit_price, 2),
            "subtotal": subtotal,
            "price_source": source,
        })

    estimated_total = round(sum(i["subtotal"] for i in priced_items), 2)
    within_budget = estimated_total <= budget_ngn
    amount_over_or_under = round(budget_ngn - estimated_total, 2)

    # Single-market alternative: markets that carry every priced item (with crowd data)
    priced_commodity_ids = {i["commodity_id"] for i in priced_items if i["market_id"] is not None}
    single_market_name = None
    single_market_total = None
    if priced_commodity_ids:
        candidates = []
        for market_id, data in market_coverage.items():
            covered = set(data["prices"].keys())
            if priced_commodity_ids.issubset(covered):
                total = sum(
                    data["prices"][i["commodity_id"]] * i["quantity"]
                    for i in priced_items
                    if i["commodity_id"] in covered
                )
                candidates.append((total, data["name"]))
        if candidates:
            candidates.sort(key=lambda x: x[0])
            single_market_total, single_market_name = round(candidates[0][0], 2), candidates[0][1]

    # Savings tip
    if not within_budget:
        most_expensive = max(priced_items, key=lambda i: i["subtotal"], default=None)
        savings_tip = (
            f"You're ₦{abs(amount_over_or_under):,.0f} over budget. "
            f"{most_expensive['commodity']} is the biggest single cost at ₦{most_expensive['subtotal']:,.0f} — "
            f"consider reducing its quantity first."
            if most_expensive else "This list is over budget."
        )
    elif single_market_total and single_market_total > estimated_total:
        diff = round(single_market_total - estimated_total, 2)
        savings_tip = (
            f"Buying everything at {single_market_name} in one trip costs ₦{diff:,.0f} more "
            f"than spreading purchases across markets, but saves you the extra stops."
        )
    else:
        savings_tip = f"This list fits comfortably within budget, with ₦{amount_over_or_under:,.0f} to spare."

    return {
        "budget_ngn": budget_ngn,
        "city": city,
        "items": priced_items,
        "estimated_total": estimated_total,
        "within_budget": within_budget,
        "amount_over_or_under": amount_over_or_under,
        "single_market_alternative": single_market_name,
        "single_market_total": single_market_total,
        "savings_tip": savings_tip,
        "unavailable_items": unavailable_items,
    }
