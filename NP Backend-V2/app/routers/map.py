from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app import models, schemas
from app.services.map_data import get_map_markets

router = APIRouter(prefix="/map", tags=["Map"])


@router.get("/markets", response_model=schemas.MapOut)
def map_markets(
    commodity_id: Optional[int] = Query(None, description="If set, annotates each market with its trusted crowd price for this commodity"),
    days_back: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_db),
):
    commodity_name = None
    if commodity_id is not None:
        commodity = db.query(models.Commodity).filter(models.Commodity.id == commodity_id).first()
        if not commodity:
            raise HTTPException(status_code=404, detail="Commodity not found")
        commodity_name = commodity.name

    markets = get_map_markets(db, commodity_id=commodity_id, days_back=days_back)
    return schemas.MapOut(commodity=commodity_name, markets=markets)
