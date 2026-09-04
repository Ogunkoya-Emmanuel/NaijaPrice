export const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    ...init,
  });
  if (!res.ok) {
    let msg = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (body?.detail) {
        msg = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
      }
    } catch {}
    throw new Error(msg);
  }
  return res.json() as Promise<T>;
}

export interface Commodity {
  id: number;
  name: string;
  category?: string;
  unit?: string;
}

export interface Market {
  id: number;
  name: string;
  city: string;
  state?: string;
  zone?: string;
}

export interface ForecastComponents {
  seasonal_signal?: number;
  harvest_adjustment?: number;
  fuel_adjustment?: number;
  fx_adjustment?: number;
}

export interface Forecast {
  commodity_id: number;
  commodity_name: string;
  current_price?: number;
  forecast_pct?: number;
  direction?: "up" | "down" | "stable";
  confidence?: number;
  advice?: "buy_now" | "wait" | "stable";
  explanation?: string;
  target_month?: string;
  components?: ForecastComponents;
  yoy_breakdown?: Array<{ year: number; mom_pct: number }>;
  last_updated?: string;
  dominant_driver?: string;
  recent_anomaly?: boolean;
  model_used?: string;
}

export interface TrendPoint {
  date: string;
  price_ngn: number;
  mom_pct?: number;
}

export interface Trend {
  commodity_id: number;
  points: TrendPoint[];
  price_change_3m?: number;
  price_change_12m?: number;
}

export interface CompareRow {
  market_id: number;
  market_name: string;
  city: string;
  median_price: number;
  submission_count: number;
  is_verified: boolean;
}

// ── Anomaly detection ──────────────────────────────────────────────────────
export interface AnomalyPoint {
  date: string;
  mom_pct: number;
  z_score: number;
  direction: "spike" | "drop";
}

export interface AnomalyResponse {
  commodity: string;
  mean_mom_pct: number;
  std_mom_pct: number;
  threshold_z: number;
  anomalies: AnomalyPoint[];
  latest_month_is_anomaly: boolean;
}

// ── Map view ───────────────────────────────────────────────────────────────
export interface MapMarket {
  market_id: number;
  name: string;
  city: string;
  state: string;
  zone?: string;
  latitude?: number;
  longitude?: number;
  median_price?: number | null;
  submission_count: number;
  is_verified: boolean;
}

export interface MapResponse {
  commodity?: string | null;
  markets: MapMarket[];
}

// ── Budget shopping assistant ────────────────────────────────────────────────
export interface BudgetItemInput {
  commodity_id: number;
  quantity: number;
}

export interface BudgetItemResult {
  commodity_id: number;
  commodity: string;
  quantity: number;
  recommended_market: string;
  market_id: number | null;
  unit_price: number;
  subtotal: number;
  price_source: string;
}

export interface BudgetResult {
  budget_ngn: number;
  city: string;
  items: BudgetItemResult[];
  estimated_total: number;
  within_budget: boolean;
  amount_over_or_under: number;
  single_market_alternative?: string | null;
  single_market_total?: number | null;
  savings_tip?: string | null;
  unavailable_items: string[];
}

// ── Model performance ──────────────────────────────────────────────────────
export interface ModelPerformanceBucket {
  n_test_points: number;
  model_mae: number;
  model_mape_pct: number;
  baseline_mae: number;
  baseline_mape_pct: number;
  improvement_vs_baseline_pct?: number;
}

export interface ModelPerformance {
  overall: ModelPerformanceBucket;
  deep_history_9: ModelPerformanceBucket;
  shallow_history_33: ModelPerformanceBucket;
  summary: string;
  ml_eligible_commodity_count: number;
  rule_based_commodity_count: number;
}

export interface PriceSubmissionResult {
  id: number;
  commodity_id: number;
  market_id: number;
  price_ngn: number;
  quantity_unit?: string;
  submitted_at: string;
  is_flagged: boolean;
  flag_reason?: string | null;
}

export const api = {
  commodities: () => req<Commodity[]>("/commodities/"),
  commodity: (id: string | number) => req<Commodity>(`/commodities/${id}`),
  markets: (city?: string) =>
    req<Market[]>(`/markets/${city ? `?city=${encodeURIComponent(city)}` : ""}`),
  submitPrice: (body: {
    commodity_id: number;
    market_id: number;
    price_ngn: number;
    quantity_unit?: string;
  }) => req<PriceSubmissionResult>("/prices/submit", { method: "POST", body: JSON.stringify(body) }),
  compare: (commodityId: number, city: string) =>
    req<any>(
      `/prices/compare?commodity_id=${commodityId}&city=${encodeURIComponent(city)}`
    ).then((data) => data.markets ?? []),
  trends: (id: string | number) =>
    req<any>(`/prices/trends/${id}`).then((data) => ({
      ...data,
      points: (data.data_points ?? []).map((p: any) => ({
        date: p.date,
        price_ngn: p.avg_price_ngn,
        mom_pct: p.mom_pct,
      })),
    })),
  latest: (id: string | number) => req(`/prices/latest/${id}`),
  anomalies: (id: string | number) => req<AnomalyResponse>(`/prices/anomalies/${id}`),
  forecast: (id: string | number) =>
    req<any>(`/forecast/${id}`).then((item) => ({
      ...item,
      commodity_name: item.commodity,
      advice: item.buying_advice,
      explanation: item.ai_explanation,
    })),
  forecastAll: () =>
    req<any[]>("/forecast/batch/all").then((data) =>
      data.map((item) => ({
        ...item,
        commodity_name: item.commodity,
        advice: item.buying_advice,
        explanation: item.ai_explanation,
      }))
    ),
  modelPerformance: () => req<ModelPerformance>("/forecast/meta/model-performance"),
  mapMarkets: (commodityId?: number) =>
    req<MapResponse>(`/map/markets${commodityId ? `?commodity_id=${commodityId}` : ""}`),
  optimizeBudget: (payload: { budget_ngn: number; city: string; items: BudgetItemInput[] }) =>
    req<BudgetResult>("/budget/optimize", { method: "POST", body: JSON.stringify(payload) }),
};
