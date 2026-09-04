from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/markets", tags=["Markets"])


@router.get("/", response_model=List[schemas.MarketOut])
def list_markets(
    city: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(models.Market)
    if city:
        q = q.filter(models.Market.city.ilike(f"%{city}%"))
    if state:
        q = q.filter(models.Market.state.ilike(f"%{state}%"))
    return q.order_by(models.Market.city, models.Market.name).all()


@router.get("/{market_id}", response_model=schemas.MarketOut)
def get_market(market_id: int, db: Session = Depends(get_db)):
    m = db.query(models.Market).filter(models.Market.id == market_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Market not found")
    return m
