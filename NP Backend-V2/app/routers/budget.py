from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app import schemas
from app.services.budget_optimizer import optimize_budget

router = APIRouter(prefix="/budget", tags=["Budget"])


@router.post("/optimize", response_model=schemas.BudgetOut)
def optimize(payload: schemas.BudgetRequestIn, db: Session = Depends(get_db)):
    items = [{"commodity_id": i.commodity_id, "quantity": i.quantity} for i in payload.items]
    result = optimize_budget(payload.budget_ngn, payload.city, items, db)
    return schemas.BudgetOut(**result)
