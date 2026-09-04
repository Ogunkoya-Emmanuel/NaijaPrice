"""
Map view backend.

Markets already carry hardcoded lat/long from the seeder (24 markets
across 9 cities - see seed/seeder.py MARKETS), so no geocoding step is
needed here. This just assembles the response: plain market pins with
no commodity filter, or pins annotated with each market's trusted
crowd price for a given commodity when one is requested.
"""
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from app import models
from app.services.trust_score import compute_trusted_price, MIN_SUBMISSIONS


def get_map_markets(db: Session, commodity_id: Optional[int] = None, days_back: int = 30) -> list[dict]:
    markets = db.query(models.Market).order_by(models.Market.city, models.Market.name).all()

    if commodity_id is None:
        return [
            {
                "market_id": m.id, "name": m.name, "city": m.city, "state": m.state,
                "zone": m.zone, "latitude": m.latitude, "longitude": m.longitude,
                "median_price": None, "submission_count": 0, "is_verified": False,
            }
            for m in markets
        ]

    cutoff = datetime.utcnow() - timedelta(days=days_back)
    rows = (
        db.query(models.PriceSubmission)
        .filter(
            models.PriceSubmission.commodity_id == commodity_id,
            models.PriceSubmission.submitted_at >= cutoff,
            models.PriceSubmission.is_flagged == False,
        )
        .all()
    )

    prices_by_market: dict[int, list[float]] = {}
    for r in rows:
        prices_by_market.setdefault(r.market_id, []).append(r.price_ngn)

    results = []
    for m in markets:
        prices = prices_by_market.get(m.id, [])
        trusted = compute_trusted_price(prices) if prices else None
        results.append({
            "market_id": m.id, "name": m.name, "city": m.city, "state": m.state,
            "zone": m.zone, "latitude": m.latitude, "longitude": m.longitude,
            "median_price": trusted,
            "submission_count": len(prices),
            "is_verified": len(prices) >= MIN_SUBMISSIONS,
        })
    return results
