import { useEffect, useState } from "react";
import { Link } from "@tanstack/react-router";
import { ArrowUp, ArrowDown, Minus, AlertTriangle, Gauge } from "lucide-react";
import { api, type Forecast } from "@/lib/api";
import { useCity } from "@/lib/city-context";
import { CITIES, formatNaira, pct, directionColor, adviceMeta } from "@/lib/utils";
import { Card, Badge, ErrorBox } from "@/components/ui";
import Skeleton from "@/components/Skeleton";

function DirectionIcon({ direction }: { direction?: string }) {
  const cls = directionColor(direction);
  if (direction === "up") return <ArrowUp size={16} className={cls} />;
  if (direction === "down") return <ArrowDown size={16} className={cls} />;
  return <Minus size={16} className={cls} />;
}

export default function Dashboard() {
  const { city, setCity } = useCity();
  const [data, setData] = useState<Forecast[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    api
      .forecastAll()
      .then((res) => {
        if (!cancelled) setData(res);
      })
      .catch((e) => {
        if (!cancelled) setError(e.message || "Failed to load forecasts");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const topAlerts = data
    ? [...data]
        .filter((f) => (f.forecast_pct ?? 0) > 0)
        .sort((a, b) => (b.forecast_pct ?? 0) - (a.forecast_pct ?? 0))
        .slice(0, 5)
    : [];

  return (
    <div className="px-4 md:px-8 py-6 md:py-8 max-w-7xl mx-auto">
      <header className="flex flex-wrap items-start justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl md:text-3xl font-extrabold text-amber tracking-tight">
            NaijaPrice
          </h1>
          <p className="text-text-secondary text-sm mt-1">
            Real-time market intelligence, AI-powered forecasts
          </p>
        </div>
        <select
          value={city}
          onChange={(e) => setCity(e.target.value)}
          className="bg-surface border border-border rounded-xl px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber"
        >
          {CITIES.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </header>

      {error && (
        <div className="mb-6">
          <ErrorBox message={error} />
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <Card className="p-5">
          <p className="text-text-secondary text-xs uppercase tracking-wide">
            Commodities Tracked
          </p>
          <p className="text-3xl font-bold mt-2">42</p>
        </Card>
        <Card className="p-5">
          <p className="text-text-secondary text-xs uppercase tracking-wide">Markets Covered</p>
          <p className="text-3xl font-bold mt-2">25</p>
        </Card>
        <Link to="/model-performance">
          <Card className="p-5 h-full hover:bg-white/[0.02] transition-colors">
            <p className="text-text-secondary text-xs uppercase tracking-wide flex items-center gap-1.5">
              <Gauge size={13} /> Forecast Accuracy
            </p>
            <p className="text-xl font-bold mt-2 text-amber">See the numbers →</p>
          </Card>
        </Link>
      </div>

      <section className="mb-8">
        <h2 className="text-lg font-bold mb-3 flex items-center gap-2">
          <AlertTriangle size={18} className="text-amber" />
          Price Alerts
        </h2>
        {loading ? (
          <div className="flex gap-4 overflow-x-auto pb-2">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-24 w-64 shrink-0" />
            ))}
          </div>
        ) : topAlerts.length === 0 ? (
          <p className="text-text-secondary text-sm">No commodities are trending upward right now.</p>
        ) : (
          <div className="flex gap-4 overflow-x-auto pb-2">
            {topAlerts.map((f) => (
              <Link
                key={f.commodity_id}
                to="/commodity/$id"
                params={{ id: String(f.commodity_id) }}
                className="shrink-0 w-64"
              >
                <Card className="border-l-4 border-l-amber p-4 h-full hover:bg-white/[0.02] transition-colors">
                  <p className="font-semibold">{f.commodity_name}</p>
                  <p className="text-amber font-bold mt-1">{pct(f.forecast_pct)}</p>
                  <p className="text-text-secondary text-xs mt-1">
                    Price rising — consider buying early
                  </p>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 className="text-lg font-bold mb-3">All Commodities</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {loading
            ? Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-36" />)
            : data?.map((f) => {
                const advice = adviceMeta(f.advice);
                return (
                  <Link key={f.commodity_id} to="/commodity/$id" params={{ id: String(f.commodity_id) }}>
                    <Card className="p-5 h-full hover:bg-white/[0.02] transition-colors">
                      <div className="flex items-start justify-between">
                        <p className="font-semibold">{f.commodity_name}</p>
                        <DirectionIcon direction={f.direction} />
                      </div>
                      <p className="text-2xl font-bold mt-2">{formatNaira(f.current_price)}</p>
                      <div className="flex items-center justify-between mt-3">
                        <span className={`text-sm font-medium ${directionColor(f.direction)}`}>
                          {pct(f.forecast_pct)}
                        </span>
                        <Badge className={advice.className}>{advice.label}</Badge>
                      </div>
                    </Card>
                  </Link>
                );
              })}
        </div>
      </section>
    </div>
  );
}
