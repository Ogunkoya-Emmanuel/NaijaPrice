import numpy as np
from datetime import date
from sqlalchemy.orm import Session
from app import models


def _get_next_month(month: int) -> int:
    return (month % 12) + 1


def _get_direction(pct: float) -> str:
    if pct > 3:
        return "up"
    if pct < -3:
        return "down"
    return "stable"


def _get_buying_advice(direction: str, is_harvest: bool, is_lean: bool) -> str:
    if direction == "up" or is_lean:
        return "buy_now"
    if direction == "down" or is_harvest:
        return "wait"
    return "stable"


def compute_forecast(
    commodity_id: int,
    db: Session,
) -> dict | None:

    nbs_rows = (
        db.query(models.NBSHistoricalPrice)
        .filter(models.NBSHistoricalPrice.commodity_id == commodity_id)
        .order_by(models.NBSHistoricalPrice.date)
        .all()
    )

    if not nbs_rows or len(nbs_rows) < 2:
        return None

    current_row   = nbs_rows[-1]
    current_price = current_row.avg_price_ngn
    current_month = current_row.date.month
    next_month    = _get_next_month(current_month)

    # ── 1. Seasonal signal ────────────────────────────────────────────────────
    next_month_rows  = [r for r in nbs_rows if r.date.month == next_month and r.mom_pct is not None]
    seasonal_changes = [r.mom_pct for r in next_month_rows]

    if seasonal_changes:
        seasonal_signal = float(sum(seasonal_changes) / len(seasonal_changes))
        n_points   = len(seasonal_changes)
        positive   = sum(1 for v in seasonal_changes if v > 0)
        negative   = sum(1 for v in seasonal_changes if v < 0)
        consistency = max(positive, negative) / n_points if n_points > 0 else 0.5
    else:
        recent = [r.mom_pct for r in nbs_rows[-4:] if r.mom_pct is not None]
        seasonal_signal = float(sum(recent) / len(recent)) if recent else 0.0
        n_points    = 0
        consistency = 0.4

    # ── 2. Harvest adjustment ─────────────────────────────────────────────────
    harvest_row = (
        db.query(models.HarvestCalendar)
        .filter(
            models.HarvestCalendar.commodity_id == commodity_id,
            models.HarvestCalendar.month == next_month,
        )
        .first()
    )

    is_harvest = bool(harvest_row and harvest_row.is_harvest_month)
    is_lean    = bool(harvest_row and harvest_row.is_lean_month)
    is_import  = not bool(harvest_row and harvest_row.harvest_months and harvest_row.harvest_months != "N/A")

    harvest_adj = 0.0
    if is_harvest:
        harvest_adj = -3.0
    elif is_lean:
        harvest_adj = 3.0

    # ── 3. Fuel price adjustment ──────────────────────────────────────────────
    pms_rows = (
        db.query(models.PMSFuelPrice)
        .order_by(models.PMSFuelPrice.date.desc())
        .limit(2)
        .all()
    )

    fuel_adj   = 0.0
    fuel_trend = "stable"
    if len(pms_rows) == 2:
        p_new = pms_rows[0].national_avg_pms_ngn
        p_old = pms_rows[1].national_avg_pms_ngn
        if p_old and p_old > 0:
            pms_change = ((p_new - p_old) / p_old) * 100
            fuel_adj   = round(pms_change * 0.20, 2)
            fuel_trend = "rising" if pms_change > 2 else "falling" if pms_change < -2 else "stable"

    # ── 4. FX adjustment ─────────────────────────────────────────────────────
    fx_rows = (
        db.query(models.ExchangeRate)
        .order_by(models.ExchangeRate.date.desc())
        .limit(2)
        .all()
    )

    fx_adj   = 0.0
    fx_trend = "stable"
    if len(fx_rows) == 2 and is_import:
        r_new = fx_rows[0].avg_closing_rate
        r_old = fx_rows[1].avg_closing_rate
        if r_old and r_old > 0:
            fx_change    = ((r_new - r_old) / r_old) * 100
            pass_through = 0.50 if is_import else 0.10
            fx_adj       = round(fx_change * pass_through, 2)
            fx_trend     = "weakening" if fx_change > 1.5 else "strengthening" if fx_change < -1.5 else "stable"

    # ── 5. Combine ────────────────────────────────────────────────────────────
    total_forecast = seasonal_signal + harvest_adj + fuel_adj + fx_adj

    # ── 6. Confidence ────────────────────────────────────────────────────────
    if n_points >= 3:
        base_conf = 80.0
    elif n_points == 2:
        base_conf = 65.0
    elif n_points == 1:
        base_conf = 45.0
    else:
        base_conf = 25.0

    consistency_bonus = (consistency - 0.5) * 20

    signal_agreement = 0.0
    if seasonal_signal > 0 and fuel_adj > 0:
        signal_agreement += 5.0
    if seasonal_signal < 0 and fuel_adj < 0:
        signal_agreement += 5.0
    if is_harvest and seasonal_signal < 0:
        signal_agreement += 5.0
    if is_lean and seasonal_signal > 0:
        signal_agreement += 5.0

    confidence = min(max(base_conf + consistency_bonus + signal_agreement, 15.0), 92.0)

    # ── 7. Direction and advice ───────────────────────────────────────────────
    direction     = _get_direction(total_forecast)
    buying_advice = _get_buying_advice(direction, is_harvest, is_lean)

    # ── 8. YoY breakdown ─────────────────────────────────────────────────────
    yoy_breakdown = [
        {"year": r.date.year, "month_pct_change": r.mom_pct}
        for r in next_month_rows
    ]

    return {
        "current_price":    round(current_price, 2),
        "target_month":     date(
            current_row.date.year if next_month > current_month else current_row.date.year + 1,
            next_month, 1
        ).strftime("%B %Y"),
        "forecast_pct":     round(total_forecast, 2),
        "direction":        direction,
        "confidence":       round(confidence, 1),
        "buying_advice":    buying_advice,
        "is_harvest_month": is_harvest,
        "is_lean_month":    is_lean,
        "data_points_used": n_points,
        "fuel_trend":       fuel_trend,
        "fx_trend":         fx_trend,
        "components": {
            "seasonal_signal":    round(seasonal_signal, 2),
            "harvest_adjustment": harvest_adj,
            "fuel_adjustment":    fuel_adj,
            "fx_adjustment":      fx_adj,
        },
        "yoy_breakdown": yoy_breakdown,
    }