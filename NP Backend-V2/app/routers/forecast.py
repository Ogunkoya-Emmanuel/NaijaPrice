from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app import models, schemas
from app.services.ml_forecast_engine import compute_forecast
from app.services.ai_explainer import get_forecast_explanation, determine_dominant_driver
from app.services.anomaly_detection import is_latest_month_anomalous
import json, os

router = APIRouter(prefix="/forecast", tags=["Forecast"])


@router.get("/{commodity_id}", response_model=schemas.ForecastDetailOut)
def get_forecast(commodity_id: int, db: Session = Depends(get_db)):
    commodity = db.query(models.Commodity).filter(
        models.Commodity.id == commodity_id
    ).first()
    if not commodity:
        raise HTTPException(status_code=404, detail="Commodity not found")

    result = compute_forecast(commodity_id, db)
    if not result:
        raise HTTPException(
            status_code=422,
            detail="Not enough historical data to generate a forecast for this commodity."
        )

    dominant_driver = determine_dominant_driver(
        result["components"], result["is_harvest_month"], result["is_lean_month"]
    )

    explanation = get_forecast_explanation(
        commodity       = commodity.name,
        current_price   = result["current_price"],
        forecast_pct    = result["forecast_pct"],
        direction       = result["direction"],
        confidence      = result["confidence"],
        buying_advice   = result["buying_advice"],
        is_harvest      = result["is_harvest_month"],
        is_lean         = result["is_lean_month"],
        fuel_trend      = result["fuel_trend"],
        fx_trend        = result["fx_trend"],
        dominant_driver = dominant_driver,
    )

    return schemas.ForecastDetailOut(
        commodity        = commodity.name,
        current_price    = result["current_price"],
        target_month     = result["target_month"],
        forecast_pct     = result["forecast_pct"],
        direction        = result["direction"],
        confidence       = result["confidence"],
        buying_advice    = result["buying_advice"],
        ai_explanation   = explanation,
        dominant_driver  = dominant_driver,
        components       = schemas.ForecastComponentsOut(**result["components"]),
        is_harvest_month = result["is_harvest_month"],
        is_lean_month    = result["is_lean_month"],
        data_points_used = result["data_points_used"],
        yoy_breakdown    = result["yoy_breakdown"],
        model_used       = result.get("model_used", "rule_based"),
        recent_anomaly   = is_latest_month_anomalous(commodity_id, db),
    )


@router.get("/meta/model-performance")
def get_model_performance():
    """
    Backtested accuracy for the trained forecasting model vs. a seasonal-naive
    baseline, broken out by data-history depth. See app/ml/train_model.py for
    how these numbers were produced (rolling time-based validation, never
    trained on the future relative to what it predicts).
    """
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ml", "model_performance.json"
    )
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Model performance data not available.")
    with open(path) as f:
        perf = json.load(f)

    deep = perf.get("deep_history_9", {})
    shallow = perf.get("shallow_history_33", {})
    deep_improvement = None
    if deep.get("baseline_mape_pct"):
        deep_improvement = round(
            (deep["baseline_mape_pct"] - deep["model_mape_pct"]) / deep["baseline_mape_pct"] * 100, 1
        )

    perf["summary"] = (
        f"The trained model beats the seasonal-naive baseline by "
        f"{deep_improvement}% MAPE on the 9 commodities with deep (2007-2026) price "
        f"history, so those 9 are routed to the model. On the other 33 commodities, "
        f"which only have ~18 months of history to learn from, the simple rule-based "
        f"forecast still wins, so those stay on the rule-based engine. "
        f"See model_used on each forecast for which path was taken."
    )
    perf["ml_eligible_commodity_count"] = 9
    perf["rule_based_commodity_count"] = 42 - 9
    return perf


@router.get("/batch/all")
def get_all_forecasts(
    limit: int = Query(20, ge=1, le=42),
    db: Session = Depends(get_db),
):
    """Returns forecasts for all commodities. Useful for the dashboard overview."""
    commodities = db.query(models.Commodity).limit(limit).all()
    results = []
    for c in commodities:
        r = compute_forecast(c.id, db)
        if r:
            results.append({
                "commodity_id": c.id,
                "commodity":    c.name,
                "direction":    r["direction"],
                "forecast_pct": r["forecast_pct"],
                "confidence":   r["confidence"],
                "buying_advice": r["buying_advice"],
                "current_price": r["current_price"],
            })
    return results
