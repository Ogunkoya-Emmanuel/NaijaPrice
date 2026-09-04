from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from app.database import get_db
from app import models, schemas
from app.services.trust_score import get_market_prices
from app.services.spam_detection import reject_if_exact_duplicate, evaluate_submission
from app.services.anomaly_detection import detect_price_anomalies

router = APIRouter(prefix="/prices", tags=["Prices"])


# ── Submit a price ────────────────────────────────────────────────────────────
@router.post("/submit", response_model=schemas.PriceSubmissionOut, status_code=201)
def submit_price(payload: schemas.PriceSubmissionIn, db: Session = Depends(get_db)):
    commodity = db.query(models.Commodity).filter(
        models.Commodity.id == payload.commodity_id
    ).first()
    if not commodity:
        raise HTTPException(status_code=404, detail="Commodity not found")

    market = db.query(models.Market).filter(
        models.Market.id == payload.market_id
    ).first()
    if not market:
        raise HTTPException(status_code=404, detail="Market not found")

    # Reject outright if this is an exact duplicate submitted moments ago
    reject_if_exact_duplicate(payload.commodity_id, payload.market_id, payload.price_ngn, db)

    # Flag (but still accept) statistical outliers and unusual submission bursts
    is_flagged, flag_reason = evaluate_submission(payload.commodity_id, payload.market_id, payload.price_ngn, db)

    submission = models.PriceSubmission(
        commodity_id  = payload.commodity_id,
        market_id     = payload.market_id,
        price_ngn     = payload.price_ngn,
        quantity_unit = payload.quantity_unit,
        is_flagged    = is_flagged,
        flag_reason   = flag_reason,
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return submission


# ── Anomaly detection on NBS price history ────────────────────────────────────
@router.get("/anomalies/{commodity_id}", response_model=schemas.AnomalyOut)
def get_price_anomalies(commodity_id: int, db: Session = Depends(get_db)):
    commodity = db.query(models.Commodity).filter(
        models.Commodity.id == commodity_id
    ).first()
    if not commodity:
        raise HTTPException(status_code=404, detail="Commodity not found")

    result = detect_price_anomalies(commodity_id, db)
    if result is None:
        raise HTTPException(
            status_code=422,
            detail="Not enough historical data to run anomaly detection for this commodity.",
        )

    return schemas.AnomalyOut(commodity=commodity.name, **result)


# ── Compare market prices for a commodity in a city ───────────────────────────
@router.get("/compare", response_model=schemas.MarketComparisonOut)
def compare_markets(
    commodity_id: int = Query(...),
    city: str        = Query(...),
    days_back: int   = Query(30, ge=1, le=90),
    db: Session      = Depends(get_db),
):
    commodity = db.query(models.Commodity).filter(
        models.Commodity.id == commodity_id
    ).first()
    if not commodity:
        raise HTTPException(status_code=404, detail="Commodity not found")

    markets = get_market_prices(commodity_id, city, db, days_back)

    cheapest = markets[0]["market_name"] if markets else None
    price_range = None
    if len(markets) >= 2:
        lo, hi = markets[0]["median_price"], markets[-1]["median_price"]
        price_range = f"₦{lo:,.0f} – ₦{hi:,.0f}"

    return {
        "commodity":      commodity.name,
        "city":           city,
        "markets":        markets,
        "cheapest_market": cheapest,
        "price_range":    price_range,
    }


# ── Historical trend for a commodity (NBS data, for charts) ──────────────────
@router.get("/trends/{commodity_id}", response_model=schemas.TrendOut)
def get_trends(commodity_id: int, db: Session = Depends(get_db)):
    commodity = db.query(models.Commodity).filter(
        models.Commodity.id == commodity_id
    ).first()
    if not commodity:
        raise HTTPException(status_code=404, detail="Commodity not found")

    rows = (
        db.query(models.NBSHistoricalPrice)
        .filter(models.NBSHistoricalPrice.commodity_id == commodity_id)
        .order_by(models.NBSHistoricalPrice.date)
        .all()
    )

    if not rows:
        raise HTTPException(status_code=404, detail="No price data for this commodity")

    data_points = [
        schemas.TrendPoint(
            date=str(r.date),
            avg_price_ngn=r.avg_price_ngn,
            mom_pct=r.mom_pct,
        )
        for r in rows
    ]

    current_price = rows[-1].avg_price_ngn

    # 3-month change
    price_change_3m = None
    if len(rows) >= 4:
        price_change_3m = round(
            ((current_price - rows[-4].avg_price_ngn) / rows[-4].avg_price_ngn) * 100, 2
        )

    # 12-month change
    price_change_12m = None
    if len(rows) >= 13:
        price_change_12m = round(
            ((current_price - rows[-13].avg_price_ngn) / rows[-13].avg_price_ngn) * 100, 2
        )

    return schemas.TrendOut(
        commodity=commodity.name,
        data_points=data_points,
        current_price=current_price,
        price_change_3m=price_change_3m,
        price_change_12m=price_change_12m,
    )


# ── Latest NBS price for a commodity ─────────────────────────────────────────
@router.get("/latest/{commodity_id}", response_model=schemas.NBSPriceOut)
def get_latest_nbs(commodity_id: int, db: Session = Depends(get_db)):
    row = (
        db.query(models.NBSHistoricalPrice)
        .filter(models.NBSHistoricalPrice.commodity_id == commodity_id)
        .order_by(models.NBSHistoricalPrice.date.desc())
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="No price data found")
    return row
