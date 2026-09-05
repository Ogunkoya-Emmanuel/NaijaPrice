"""
Day-scoped cache for the dashboard's batch forecast endpoint.

Forecasts are expensive to recompute (a DB history query plus, for 9
commodities, an ML inference call) and the inputs barely move within a
day - NBS data updates monthly, fuel/FX data infrequently. So each
commodity gets at most one real computation per calendar day; every
other request that day reads the cached row instead.

This reuses forecasts_cache, a table that already existed in the schema
(with a UniqueConstraint on commodity_id + forecast_date) but was never
wired up to anything - the caching mechanism was already half-built.
"""
from datetime import date, datetime
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app import models


def get_cached_forecast(commodity_id: int, db: Session) -> dict | None:
    row = (
        db.query(models.ForecastCache)
        .filter(
            models.ForecastCache.commodity_id == commodity_id,
            models.ForecastCache.forecast_date == date.today(),
        )
        .first()
    )
    if not row:
        return None
    return {
        "current_price": row.current_price,
        "forecast_pct": row.forecast_pct,
        "direction": row.direction,
        "confidence": row.confidence,
        "buying_advice": row.buying_advice,
    }


def save_forecast_to_cache(commodity_id: int, target_month, result: dict, db: Session) -> None:
    """
    Upserts today's row for this commodity. Uses Postgres's native
    ON CONFLICT so two near-simultaneous requests for the same
    not-yet-cached commodity don't race into a duplicate-key error.

    target_month arrives as a "%B %Y" display string (e.g. "June 2026")
    from both forecast engines, not a date - parsed back here since the
    cache column is a real Date.
    """
    if isinstance(target_month, str):
        target_month = datetime.strptime(target_month, "%B %Y").date()

    stmt = pg_insert(models.ForecastCache).values(
        commodity_id=commodity_id,
        forecast_date=date.today(),
        target_month=target_month,
        current_price=result["current_price"],
        forecast_pct=result["forecast_pct"],
        direction=result["direction"],
        confidence=result["confidence"],
        buying_advice=result["buying_advice"],
    )
    stmt = stmt.on_conflict_do_update(
        constraint="uq_forecast_commodity_date",
        set_={
            "current_price": stmt.excluded.current_price,
            "forecast_pct": stmt.excluded.forecast_pct,
            "direction": stmt.excluded.direction,
            "confidence": stmt.excluded.confidence,
            "buying_advice": stmt.excluded.buying_advice,
        },
    )
    db.execute(stmt)
    db.commit()