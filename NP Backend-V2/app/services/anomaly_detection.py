"""
Anomaly detection on NBS commodity price history.

Same statistical pattern already proven out in trust_score.py for crowd
submissions (mean/std, flag beyond a z-score threshold), pointed instead
at each commodity's NBS month-over-month % change series. This flags
months where a commodity's price moved unusually hard in either
direction relative to its own history - useful both as a standalone
"what happened here" view and as a flag surfaced inside the forecast
(a forecast built on top of a just-flagged anomalous month deserves a
grain of salt, and the explainer can say so).
"""
import numpy as np
from typing import List
from sqlalchemy.orm import Session
from app import models

DEFAULT_Z_THRESHOLD = 2.0
MIN_POINTS_REQUIRED = 4  # need a meaningful distribution before flagging anything


def detect_price_anomalies(
    commodity_id: int,
    db: Session,
    z_threshold: float = DEFAULT_Z_THRESHOLD,
) -> dict | None:
    rows = (
        db.query(models.NBSHistoricalPrice)
        .filter(
            models.NBSHistoricalPrice.commodity_id == commodity_id,
            models.NBSHistoricalPrice.mom_pct.isnot(None),
        )
        .order_by(models.NBSHistoricalPrice.date)
        .all()
    )

    if len(rows) < MIN_POINTS_REQUIRED:
        return None

    values = np.array([r.mom_pct for r in rows], dtype=float)
    mean, std = float(values.mean()), float(values.std())

    anomalies = []
    latest_is_anomaly = False

    if std > 0:
        for i, (r, v) in enumerate(zip(rows, values)):
            z = (v - mean) / std
            if abs(z) > z_threshold:
                anomalies.append({
                    "date": r.date,
                    "mom_pct": round(float(v), 2),
                    "z_score": round(float(z), 2),
                    "direction": "spike" if v > 0 else "drop",
                })
                if i == len(rows) - 1:
                    latest_is_anomaly = True

    return {
        "mean_mom_pct": round(mean, 2),
        "std_mom_pct": round(std, 2),
        "threshold_z": z_threshold,
        "anomalies": anomalies,
        "latest_month_is_anomaly": latest_is_anomaly,
    }


def is_latest_month_anomalous(commodity_id: int, db: Session) -> bool:
    """Cheap boolean check used inside the forecast response, without
    building the full anomaly list."""
    result = detect_price_anomalies(commodity_id, db)
    return bool(result and result["latest_month_is_anomaly"])
