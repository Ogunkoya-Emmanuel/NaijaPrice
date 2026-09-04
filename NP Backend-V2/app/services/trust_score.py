import numpy as np
from typing import List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from app import models


MIN_SUBMISSIONS = 3  # minimum before a price is displayed as verified


def compute_trusted_price(prices: List[float]) -> float | None:
    """
    Returns the median after removing outliers beyond 2 standard deviations.
    Returns None if fewer than MIN_SUBMISSIONS valid values remain.
    """
    if not prices:
        return None

    arr = np.array(prices, dtype=float)

    if len(arr) < MIN_SUBMISSIONS:
        return None

    mean, std = arr.mean(), arr.std()
    if std == 0:
        return round(float(mean), 2)

    filtered = arr[np.abs(arr - mean) <= 2 * std]

    if len(filtered) < MIN_SUBMISSIONS:
        # Not enough after outlier removal — return raw median anyway but mark unverified
        return round(float(np.median(arr)), 2)

    return round(float(np.median(filtered)), 2)


def get_market_prices(
    commodity_id: int,
    city: str,
    db: Session,
    days_back: int = 30,
) -> List[dict]:
    """
    Returns aggregated trusted prices for a commodity across all markets in a city.
    Only includes submissions from the last `days_back` days.
    """
    cutoff = datetime.utcnow() - timedelta(days=days_back)

    rows = (
        db.query(
            models.PriceSubmission,
            models.Market,
        )
        .join(models.Market, models.PriceSubmission.market_id == models.Market.id)
        .filter(
            models.PriceSubmission.commodity_id == commodity_id,
            models.Market.city.ilike(city),
            models.PriceSubmission.submitted_at >= cutoff,
            models.PriceSubmission.is_flagged == False,
        )
        .all()
    )

    # Group by market
    market_groups: dict[int, dict] = {}
    for submission, market in rows:
        if market.id not in market_groups:
            market_groups[market.id] = {
                "market_id":   market.id,
                "market_name": market.name,
                "city":        market.city,
                "state":       market.state,
                "prices":      [],
                "last_updated": submission.submitted_at,
            }
        market_groups[market.id]["prices"].append(submission.price_ngn)
        if submission.submitted_at > market_groups[market.id]["last_updated"]:
            market_groups[market.id]["last_updated"] = submission.submitted_at

    results = []
    for mid, data in market_groups.items():
        prices = data["prices"]
        trusted = compute_trusted_price(prices)
        if trusted is None:
            continue
        results.append({
            "market_id":        mid,
            "market_name":      data["market_name"],
            "city":             data["city"],
            "state":            data["state"],
            "median_price":     trusted,
            "submission_count": len(prices),
            "last_updated":     data["last_updated"],
            "is_verified":      len(prices) >= MIN_SUBMISSIONS,
        })

    return sorted(results, key=lambda x: x["median_price"])
