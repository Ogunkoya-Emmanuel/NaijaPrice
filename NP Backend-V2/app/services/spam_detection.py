"""
Spam and duplicate detection for crowd-submitted prices.

The submission endpoint had one check before this: flag if a price is
>5x or <0.2x the latest NBS average. That catches typos and wild
outliers but does nothing about the other common failure mode in
crowdsourced data - the same price hammered in repeatedly, by a double
click, a retried request, or an actual bot trying to move a market's
median.

Three checks, run in order:
  1. Exact-duplicate guard: identical commodity+market+price within a
     short window is almost always a double-submit, not new
     information. Rejected outright (HTTP 429) rather than flagged,
     since accepting it does the data no good either way.
  2. Statistical outlier vs NBS: unchanged from before (ratio check).
  3. Burst detection: an unusual number of submissions for the same
     commodity+market in a short window. Can't be rejected outright
     (it might be genuine - a market day rush), so it's flagged for
     review instead, same as the outlier case.

Flagged submissions are excluded from get_market_prices() in
trust_score.py, so this is the only line of defense against a bad
actor skewing the crowd-sourced median.
"""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException
from app import models

DUPLICATE_WINDOW_SECONDS = 90       # identical price twice within this window -> reject
BURST_WINDOW_MINUTES = 5            # window used to count submission velocity
BURST_THRESHOLD = 8                 # more than this many in the window -> flag as spam burst
OUTLIER_RATIO_HIGH = 5.0
OUTLIER_RATIO_LOW = 0.2


def reject_if_exact_duplicate(commodity_id: int, market_id: int, price_ngn: float, db: Session) -> None:
    cutoff = datetime.utcnow() - timedelta(seconds=DUPLICATE_WINDOW_SECONDS)
    dup = (
        db.query(models.PriceSubmission)
        .filter(
            models.PriceSubmission.commodity_id == commodity_id,
            models.PriceSubmission.market_id == market_id,
            models.PriceSubmission.price_ngn == price_ngn,
            models.PriceSubmission.submitted_at >= cutoff,
        )
        .first()
    )
    if dup:
        raise HTTPException(
            status_code=429,
            detail=(
                "An identical price for this commodity and market was just submitted. "
                "If this wasn't a duplicate submission, please wait a moment and try again."
            ),
        )


def evaluate_submission(commodity_id: int, market_id: int, price_ngn: float, db: Session) -> tuple[bool, str | None]:
    """
    Runs the non-rejecting checks (outlier + burst) and returns
    (is_flagged, flag_reason). Called after reject_if_exact_duplicate()
    has already had its chance to reject outright.
    """
    # 1. Statistical outlier vs latest NBS average
    latest_nbs = (
        db.query(models.NBSHistoricalPrice)
        .filter(models.NBSHistoricalPrice.commodity_id == commodity_id)
        .order_by(models.NBSHistoricalPrice.date.desc())
        .first()
    )
    if latest_nbs and latest_nbs.avg_price_ngn:
        ratio = price_ngn / latest_nbs.avg_price_ngn
        if ratio > OUTLIER_RATIO_HIGH or ratio < OUTLIER_RATIO_LOW:
            return True, "price_outlier"

    # 2. Submission burst for this commodity+market
    burst_cutoff = datetime.utcnow() - timedelta(minutes=BURST_WINDOW_MINUTES)
    recent_count = (
        db.query(func.count(models.PriceSubmission.id))
        .filter(
            models.PriceSubmission.commodity_id == commodity_id,
            models.PriceSubmission.market_id == market_id,
            models.PriceSubmission.submitted_at >= burst_cutoff,
        )
        .scalar()
    )
    if recent_count is not None and recent_count >= BURST_THRESHOLD:
        return True, "submission_burst"

    return False, None
