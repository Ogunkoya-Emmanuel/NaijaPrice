export const CITIES = ["Lagos", "Abuja", "Ibadan", "Kano", "Port Harcourt", "Enugu", "Benin City"];

export function formatNaira(amount?: number): string {
  if (amount === undefined || amount === null || isNaN(amount)) return "₦—";
  return `₦${amount.toLocaleString("en-NG", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function formatMonthYear(dateStr?: string): string {
  if (!dateStr) return "—";
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return dateStr;
  return d.toLocaleDateString("en-US", { month: "long", year: "numeric" });
}

export function formatFullDate(dateStr?: string): string {
  if (!dateStr) return "—";
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return dateStr;
  return d.toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" });
}

export function pct(n?: number): string {
  if (n === undefined || n === null || isNaN(n)) return "—";
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(1)}%`;
}

export const ZONE_COLORS: Record<string, string> = {
  "South West": "bg-amber-500/15 text-amber-400 border-amber-500/30",
  "South South": "bg-teal-500/15 text-teal-400 border-teal-500/30",
  "North West": "bg-purple-500/15 text-purple-400 border-purple-500/30",
  "South East": "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  "North Central": "bg-orange-500/15 text-orange-400 border-orange-500/30",
  "North East": "bg-sky-500/15 text-sky-400 border-sky-500/30",
};

export function directionColor(direction?: string) {
  if (direction === "up") return "text-danger";
  if (direction === "down") return "text-success";
  return "text-stable";
}

export function adviceMeta(advice?: string) {
  switch (advice) {
    case "buy_now":
      return { label: "Buy now", className: "bg-success/15 text-success border-success/30" };
    case "wait":
      return { label: "Wait", className: "bg-danger/15 text-danger border-danger/30" };
    default:
      return { label: "Stable", className: "bg-stable/15 text-stable border-stable/30" };
  }
}

export function getSavedCity(): string {
  return localStorage.getItem("naijaprice_city") || "Lagos";
}

export function saveCity(city: string) {
  localStorage.setItem("naijaprice_city", city);
}

export const DRIVER_LABELS: Record<string, string> = {
  seasonal_demand: "Seasonal demand",
  harvest_season: "Harvest season",
  lean_season: "Lean season",
  fuel_cost: "Fuel/transport cost",
  exchange_rate: "Exchange rate",
};

export function driverLabel(driver?: string): string {
  if (!driver) return "Market conditions";
  return DRIVER_LABELS[driver] ?? driver.replace(/_/g, " ");
}

export const SOURCE_LABELS: Record<string, string> = {
  market_verified: "Verified market price",
  market_unverified: "Early market price",
  nbs_estimate: "Estimated (national average)",
  unavailable: "Unavailable",
};

export function sourceLabel(source?: string): string {
  if (!source) return "";
  return SOURCE_LABELS[source] ?? source.replace(/_/g, " ");
}

export function sourceBadgeClass(source?: string): string {
  switch (source) {
    case "market_verified":
      return "bg-success/15 text-success border-success/30";
    case "market_unverified":
      return "bg-amber/15 text-amber border-amber/30";
    case "nbs_estimate":
      return "bg-stable/15 text-stable border-stable/30";
    default:
      return "bg-stable/15 text-stable border-stable/30";
  }
}

export const FLAG_REASON_LABELS: Record<string, string> = {
  price_outlier: "Unusual price — flagged for review",
  submission_burst: "Unusual submission activity — flagged for review",
};

export function flagReasonLabel(reason?: string | null): string {
  if (!reason) return "Flagged for review";
  return FLAG_REASON_LABELS[reason] ?? reason.replace(/_/g, " ");
}
