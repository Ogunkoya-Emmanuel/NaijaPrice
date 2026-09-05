from sqlalchemy import (
    Column, Integer, String, Float, Boolean,
    DateTime, Date, ForeignKey, Text, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Commodity(Base):
    __tablename__ = "commodities"

    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String(100), unique=True, nullable=False, index=True)
    category   = Column(String(50))
    unit       = Column(String(50))
    is_agricultural = Column(Boolean, default=True)

    nbs_prices       = relationship("NBSHistoricalPrice", back_populates="commodity")
    submissions      = relationship("PriceSubmission", back_populates="commodity")
    harvest_calendar = relationship("HarvestCalendar", back_populates="commodity")
    forecasts        = relationship("ForecastCache", back_populates="commodity")


class Market(Base):
    __tablename__ = "markets"

    id        = Column(Integer, primary_key=True, index=True)
    name      = Column(String(100), nullable=False)
    city      = Column(String(100), nullable=False)
    state     = Column(String(100), nullable=False)
    zone      = Column(String(50))
    latitude  = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    submissions = relationship("PriceSubmission", back_populates="market")

    __table_args__ = (UniqueConstraint("name", "city", name="uq_market_name_city"),)


class NBSHistoricalPrice(Base):
    __tablename__ = "nbs_historical_prices"

    id            = Column(Integer, primary_key=True, index=True)
    commodity_id  = Column(Integer, ForeignKey("commodities.id"), nullable=False)
    date          = Column(Date, nullable=False, index=True)
    avg_price_ngn = Column(Float, nullable=False)
    mom_pct       = Column(Float, nullable=True)
    yoy_pct       = Column(Float, nullable=True)
    highest_state = Column(String(100), nullable=True)
    highest_price = Column(Float, nullable=True)
    lowest_state  = Column(String(100), nullable=True)
    lowest_price  = Column(Float, nullable=True)
    source        = Column(String(20), default="NBS")  # "NBS" (direct survey) or "WB_RTFP" (imputed backfill)

    commodity = relationship("Commodity", back_populates="nbs_prices")

    __table_args__ = (UniqueConstraint("commodity_id", "date", name="uq_nbs_commodity_date"),)


class PriceSubmission(Base):
    __tablename__ = "price_submissions"

    id            = Column(Integer, primary_key=True, index=True)
    commodity_id  = Column(Integer, ForeignKey("commodities.id"), nullable=False)
    market_id     = Column(Integer, ForeignKey("markets.id"), nullable=False)
    price_ngn     = Column(Float, nullable=False)
    quantity_unit = Column(String(50), nullable=True)
    submitted_at  = Column(DateTime(timezone=True), server_default=func.now())
    is_flagged    = Column(Boolean, default=False)
    flag_reason   = Column(String(50), nullable=True)  # e.g. "price_outlier", "submission_burst"

    commodity = relationship("Commodity", back_populates="submissions")
    market    = relationship("Market", back_populates="submissions")


class MarketPriceAggregate(Base):
    __tablename__ = "market_price_aggregates"

    id               = Column(Integer, primary_key=True, index=True)
    commodity_id     = Column(Integer, ForeignKey("commodities.id"), nullable=False)
    market_id        = Column(Integer, ForeignKey("markets.id"), nullable=False)
    period           = Column(Date, nullable=False)
    median_price     = Column(Float, nullable=True)
    submission_count = Column(Integer, default=0)
    last_updated     = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (UniqueConstraint("commodity_id", "market_id", "period", name="uq_aggregate"),)


class PMSFuelPrice(Base):
    __tablename__ = "pms_fuel_prices"

    id                   = Column(Integer, primary_key=True, index=True)
    date                 = Column(Date, unique=True, nullable=False, index=True)
    national_avg_pms_ngn = Column(Float, nullable=True)
    mom_pct              = Column(Float, nullable=True)
    yoy_pct              = Column(Float, nullable=True)


class ExchangeRate(Base):
    __tablename__ = "exchange_rates"

    id                = Column(Integer, primary_key=True, index=True)
    date              = Column(Date, unique=True, nullable=False, index=True)
    avg_closing_rate  = Column(Float, nullable=True)
    avg_weighted_rate = Column(Float, nullable=True)
    month_end_close   = Column(Float, nullable=True)
    trading_days      = Column(Integer, nullable=True)


class HarvestCalendar(Base):
    __tablename__ = "harvest_calendar"

    id               = Column(Integer, primary_key=True, index=True)
    commodity_id     = Column(Integer, ForeignKey("commodities.id"), nullable=False)
    month            = Column(Integer, nullable=False)
    is_harvest_month = Column(Boolean, default=False)
    is_lean_month    = Column(Boolean, default=False)
    harvest_months   = Column(String(50), nullable=True)
    lean_months      = Column(String(50), nullable=True)
    notes            = Column(Text, nullable=True)

    commodity = relationship("Commodity", back_populates="harvest_calendar")

    __table_args__ = (UniqueConstraint("commodity_id", "month", name="uq_harvest_commodity_month"),)


class ForecastCache(Base):
    __tablename__ = "forecasts_cache"

    id               = Column(Integer, primary_key=True, index=True)
    commodity_id     = Column(Integer, ForeignKey("commodities.id"), nullable=False)
    forecast_date    = Column(Date, nullable=False)
    target_month     = Column(Date, nullable=False)
    current_price    = Column(Float, nullable=True)
    forecast_pct     = Column(Float, nullable=True)
    direction        = Column(String(10), nullable=True)
    confidence       = Column(Float, nullable=True)
    buying_advice    = Column(String(20), nullable=True)
    ai_explanation   = Column(Text, nullable=True)
    seasonal_signal  = Column(Float, nullable=True)
    harvest_adj      = Column(Float, nullable=True)
    fuel_adj         = Column(Float, nullable=True)
    fx_adj           = Column(Float, nullable=True)
    generated_at     = Column(DateTime(timezone=True), server_default=func.now())

    commodity = relationship("Commodity", back_populates="forecasts")

    __table_args__ = (UniqueConstraint("commodity_id", "forecast_date", name="uq_forecast_commodity_date"),)
