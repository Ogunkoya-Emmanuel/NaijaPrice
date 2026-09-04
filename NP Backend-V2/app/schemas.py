from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import date, datetime


# ── Commodity ─────────────────────────────────────────────────────────────────
class CommodityOut(BaseModel):
    id: int
    name: str
    category: Optional[str]
    unit: Optional[str]
    is_agricultural: bool

    model_config = {"from_attributes": True}


# ── Market ────────────────────────────────────────────────────────────────────
class MarketOut(BaseModel):
    id: int
    name: str
    city: str
    state: str
    zone: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]

    model_config = {"from_attributes": True}


# ── Price Submission ──────────────────────────────────────────────────────────
class PriceSubmissionIn(BaseModel):
    commodity_id: int
    market_id: int
    price_ngn: float = Field(..., gt=0, description="Price in Naira, must be positive")
    quantity_unit: Optional[str] = None

    @field_validator("price_ngn")
    @classmethod
    def price_sanity(cls, v):
        if v > 500_000:
            raise ValueError("Price seems unrealistically high. Please check and resubmit.")
        return round(v, 2)


class PriceSubmissionOut(BaseModel):
    id: int
    commodity_id: int
    market_id: int
    price_ngn: float
    quantity_unit: Optional[str]
    submitted_at: datetime
    is_flagged: bool
    flag_reason: Optional[str]

    model_config = {"from_attributes": True}


# ── Current Market Price (aggregated) ────────────────────────────────────────
class MarketPriceOut(BaseModel):
    market_id: int
    market_name: str
    city: str
    state: str
    median_price: float
    submission_count: int
    last_updated: datetime
    is_verified: bool  # True if submission_count >= 3


# ── Cheapest Market Comparison ────────────────────────────────────────────────
class MarketComparisonOut(BaseModel):
    commodity: str
    city: str
    markets: List[MarketPriceOut]
    cheapest_market: Optional[str]
    price_range: Optional[str]


# ── NBS Historical Price ──────────────────────────────────────────────────────
class NBSPriceOut(BaseModel):
    date: date
    avg_price_ngn: float
    mom_pct: Optional[float]
    yoy_pct: Optional[float]
    highest_state: Optional[str]
    highest_price: Optional[float]
    lowest_state: Optional[str]
    lowest_price: Optional[float]

    model_config = {"from_attributes": True}


# ── Trend Data (for charts) ───────────────────────────────────────────────────
class TrendPoint(BaseModel):
    date: str
    avg_price_ngn: float
    mom_pct: Optional[float]


class TrendOut(BaseModel):
    commodity: str
    data_points: List[TrendPoint]
    current_price: float
    price_change_3m: Optional[float]
    price_change_12m: Optional[float]


# ── Forecast ──────────────────────────────────────────────────────────────────
class ForecastComponentsOut(BaseModel):
    seasonal_signal: float
    harvest_adjustment: float
    fuel_adjustment: float
    fx_adjustment: float


class ForecastOut(BaseModel):
    commodity: str
    current_price: float
    target_month: str
    forecast_pct: float
    direction: str           # "up" | "down" | "stable"
    confidence: float        # 0-100
    buying_advice: str       # "buy_now" | "wait" | "stable"
    ai_explanation: str
    dominant_driver: str      # "seasonal_demand" | "harvest_season" | "lean_season" | "fuel_cost" | "exchange_rate"
    components: ForecastComponentsOut
    is_harvest_month: bool
    is_lean_month: bool
    data_points_used: int
    model_used: str = "rule_based"  # "ml" for the 9 backtested-and-validated commodities, else "rule_based"
    recent_anomaly: bool = False    # True if the latest NBS month-over-month move was a statistical outlier


# ── Year-over-year breakdown (for forecast display) ───────────────────────────
class YoYBreakdownItem(BaseModel):
    year: int
    month_pct_change: Optional[float]


class ForecastDetailOut(ForecastOut):
    yoy_breakdown: List[YoYBreakdownItem]


# ── Budget Shopping ───────────────────────────────────────────────────────────
class BudgetItemIn(BaseModel):
    commodity_id: int
    quantity: float = 1.0


class BudgetRequestIn(BaseModel):
    budget_ngn: float = Field(..., gt=0)
    city: str
    items: List[BudgetItemIn] = Field(..., min_length=1, description="Shopping list to price out")


class BudgetItemOut(BaseModel):
    commodity_id: int
    commodity: str
    quantity: float
    recommended_market: str
    market_id: Optional[int]
    unit_price: float
    subtotal: float
    price_source: str  # "market_verified" | "market_unverified" | "nbs_estimate" | "unavailable"


class BudgetOut(BaseModel):
    budget_ngn: float
    city: str
    items: List[BudgetItemOut]
    estimated_total: float
    within_budget: bool
    amount_over_or_under: float
    single_market_alternative: Optional[str]
    single_market_total: Optional[float]
    savings_tip: Optional[str]
    unavailable_items: List[str] = []


# ── Anomaly Detection ──────────────────────────────────────────────────────────
class AnomalyPoint(BaseModel):
    date: date
    mom_pct: float
    z_score: float
    direction: str  # "spike" | "drop"


class AnomalyOut(BaseModel):
    commodity: str
    mean_mom_pct: float
    std_mom_pct: float
    threshold_z: float
    anomalies: List[AnomalyPoint]
    latest_month_is_anomaly: bool


# ── Map View ───────────────────────────────────────────────────────────────────
class MapMarketOut(BaseModel):
    market_id: int
    name: str
    city: str
    state: str
    zone: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    median_price: Optional[float] = None
    submission_count: int = 0
    is_verified: bool = False


class MapOut(BaseModel):
    commodity: Optional[str]
    markets: List[MapMarketOut]
