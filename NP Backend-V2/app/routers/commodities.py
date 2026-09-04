from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/commodities", tags=["Commodities"])


@router.get("/", response_model=List[schemas.CommodityOut])
def list_commodities(db: Session = Depends(get_db)):
    return db.query(models.Commodity).order_by(models.Commodity.name).all()


@router.get("/{commodity_id}", response_model=schemas.CommodityOut)
def get_commodity(commodity_id: int, db: Session = Depends(get_db)):
    c = db.query(models.Commodity).filter(models.Commodity.id == commodity_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Commodity not found")
    return c


@router.get("/search/{name}", response_model=List[schemas.CommodityOut])
def search_commodities(name: str, db: Session = Depends(get_db)):
    return (
        db.query(models.Commodity)
        .filter(models.Commodity.name.ilike(f"%{name}%"))
        .all()
    )
