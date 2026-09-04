import { useEffect, useState } from "react";
import { useParams } from "@tanstack/react-router";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { ChevronDown, CheckCircle2, AlertTriangle } from "lucide-react";
import { api, type Commodity, type Trend, type Forecast, type CompareRow } from "@/lib/api";
import { useCity } from "@/lib/city-context";
import { formatNaira, formatMonthYear, pct, directionColor, adviceMeta, driverLabel } from "@/lib/utils";
import { Card, Badge, ErrorBox } from "@/components/ui";
import Skeleton from "@/components/Skeleton";

export default function CommodityDetail() {
  const { id } = useParams({ from: "/commodity/$id" });
  const { city } = useCity();

  const [commodity, setCommodity] = useState<Commodity | null>(null);
  const [trend, setTrend] = useState<Trend | null>(null);
  const [forecast, setForecast] = useState<Forecast | null>(null);
  const [compare, setCompare] = useState<CompareRow[] | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [showComponents, setShowComponents] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setErrors({});

    Promise.allSettled([
      api.commodity(id),
      api.trends(id),
      api.forecast(id),
      api.compare(Number(id), city),
    ]).then(([c, t, f, cmp]) => {
      if (cancelled) return;
      const errs: Record<string, string> = {};
      if (c.status === "fulfilled") setCommodity(c.value);
      else errs.commodity = c.reason?.message || "Failed to load commodity";
      if (t.status === "fulfilled") setTrend(t.value);
      else errs.trend = t.reason?.message || "Failed to load trend data";
      if (f.status === "fulfilled") setForecast(f.value);
      else errs.forecast = f.reason?.message || "Failed to load forecast";
      if (cmp.status === "fulfilled") setCompare(cmp.value);
      else errs.compare = cmp.reason?.message || "Failed to load market comparison";
      setErrors(errs);
      setLoading(false);
    });

    return () => {
      cancelled = true;
    };
  }, [id, city]);

  const advice = adviceMeta(forecast?.advice);
  const currentMonth = new Date().toISOString().slice(0, 7);

  return (
    <div className="px-4 md:px-8 py-6 md:py-8 max-w-7xl mx-auto">
      <h1 className="text-2xl font-extrabold mb-1">
        {loading ? <Skeleton className="h-8 w-48" /> : commodity?.name ?? "Commodity"}
      </h1>
      {commodity?.category && (
        <p className="text-text-secondary text-sm mb-6">
          {commodity.category} {commodity.unit ? `· per ${commodity.unit}` : ""}
        </p>
      )}
      {!commodity?.category && <div className="mb-6" />}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* chart */}
        <Card className="p-5">
          <h2 className="font-semibold mb-4">Price history</h2>
          {loading ? (
            <Skeleton className="h-72" />
          ) : errors.trend ? (
            <ErrorBox message={errors.trend} />
          ) : !trend?.points?.length ? (
            <p className="text-text-secondary text-sm">No price history available yet.</p>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={trend.points}>
                <CartesianGrid stroke="#1F2937" strokeDasharray="3 3" />
                <XAxis
                  dataKey="date"
                  tickFormatter={(v) => formatMonthYear(v)}
                  stroke="#9CA3AF"
                  fontSize={12}
                  tickMargin={8}
                />
                <YAxis stroke="#9CA3AF" fontSize={12} tickFormatter={(v) => `₦${v}`} width={60} />
                <Tooltip
                  contentStyle={{
                    background: "#111827",
                    border: "1px solid #1F2937",
                    borderRadius: 12,
                    fontSize: 13,
                  }}
                  labelFormatter={(v) => formatMonthYear(String(v))}
                  formatter={(value: any, name: any) => {
                    if (name === "price_ngn") return [formatNaira(Number(value)), "Price"];
                    return [`${value}%`, "MoM"];
                  }}
                />
                <ReferenceLine
                  x={trend.points.find((p) => p.date.startsWith(currentMonth))?.date}
                  stroke="#F59E0B"
                  strokeDasharray="4 4"
                />
                <Line
                  type="monotone"
                  dataKey="price_ngn"
                  stroke="#F59E0B"
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 5 }}
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </Card>

        {/* forecast */}
        <Card className="p-5">
          <h2 className="font-semibold mb-4">Forecast</h2>
          {loading ? (
            <Skeleton className="h-72" />
          ) : errors.forecast ? (
            <ErrorBox message={errors.forecast} />
          ) : (
            <>
              <p className="text-text-secondary text-sm">
                Target month: <span className="text-text">{formatMonthYear(forecast?.target_month)}</span>
              </p>
              <p className={`text-3xl font-bold mt-2 ${directionColor(forecast?.direction)}`}>
                {pct(forecast?.forecast_pct)}
              </p>

              <div className="mt-4">
                <div className="flex justify-between text-xs text-text-secondary mb-1">
                  <span>Confidence</span>
                  <span>{forecast?.confidence != null ? `${Math.round(forecast.confidence)}%` : "—"}</span>
                </div>
                <div className="h-2 rounded-full bg-border overflow-hidden">
                  <div
                    className="h-full bg-amber rounded-full"
                    style={{ width: `${forecast?.confidence ?? 0}%` }}
                  />
                </div>
              </div>

              {forecast?.explanation && (
                <blockquote className="border-l-4 border-amber pl-4 py-1 mt-4 text-sm text-text-secondary italic">
                  {forecast.explanation}
                </blockquote>
              )}

              <div className="flex flex-wrap items-center gap-2 mt-3">
                {forecast?.dominant_driver && (
                  <Badge className="bg-amber/10 text-amber border-amber/30">
                    Main driver: {driverLabel(forecast.dominant_driver)}
                  </Badge>
                )}
                {forecast?.model_used === "ml" && (
                  <Badge className="bg-stable/15 text-stable border-stable/30">
                    Trained model forecast
                  </Badge>
                )}
              </div>

              {forecast?.recent_anomaly && (
                <div className="flex items-start gap-2 bg-danger/10 border border-danger/30 text-danger text-xs rounded-xl px-3 py-2.5 mt-3">
                  <AlertTriangle size={14} className="shrink-0 mt-0.5" />
                  <span>
                    The most recent month's price move for this commodity was statistically unusual —
                    treat this forecast with a bit more caution than normal.
                  </span>
                </div>
              )}

              <div className="flex justify-center mt-5">
                <Badge className={`${advice.className} text-sm px-4 py-2`}>{advice.label}</Badge>
              </div>

              {forecast?.components && (
                <div className="mt-5 border-t border-border pt-4">
                  <button
                    onClick={() => setShowComponents((s) => !s)}
                    className="flex items-center gap-2 text-sm text-text-secondary hover:text-text"
                  >
                    <ChevronDown
                      size={16}
                      className={`transition-transform ${showComponents ? "rotate-180" : ""}`}
                    />
                    How was this calculated?
                  </button>
                  {showComponents && (
                    <dl className="grid grid-cols-2 gap-3 mt-3 text-sm">
                      {Object.entries(forecast.components).map(([key, value]) => (
                        <div key={key} className="bg-bg rounded-lg p-3">
                          <dt className="text-text-secondary text-xs capitalize">
                            {key.replace(/_/g, " ")}
                          </dt>
                          <dd className="font-semibold mt-1">{pct(value)}</dd>
                        </div>
                      ))}
                    </dl>
                  )}
                </div>
              )}
            </>
          )}
        </Card>
      </div>

      {/* YoY breakdown */}
      <Card className="p-5 mt-6">
        <h2 className="font-semibold mb-4">Year-over-year breakdown</h2>
        {loading ? (
          <Skeleton className="h-24" />
        ) : !forecast?.yoy_breakdown?.length ? (
          <p className="text-text-secondary text-sm">No year-over-year data available.</p>
        ) : (
          <>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-text-secondary border-b border-border">
                  <th className="pb-2 font-medium">Year</th>
                  <th className="pb-2 font-medium">Month-over-month change</th>
                </tr>
              </thead>
              <tbody>
                {forecast.yoy_breakdown.map((row) => (
                  <tr key={row.year} className="border-b border-border/50 last:border-0">
                    <td className="py-2">{row.year}</td>
                    <td className={`py-2 font-medium ${row.mom_pct > 0 ? "text-danger" : row.mom_pct < 0 ? "text-success" : "text-stable"}`}>
                      {pct(row.mom_pct)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {forecast.yoy_breakdown.length === 1 && (
              <p className="text-text-secondary text-xs mt-3">
                Only 1 year of data available — confidence is limited.
              </p>
            )}
          </>
        )}
      </Card>

      {/* cheapest markets */}
      <Card className="p-5 mt-6">
        <h2 className="font-semibold mb-4">Cheapest Markets Today · {city}</h2>
        {loading ? (
          <Skeleton className="h-32" />
        ) : errors.compare ? (
          <ErrorBox message={errors.compare} />
        ) : !compare?.length ? (
          <p className="text-text-secondary text-sm">
            No market submissions yet for {city}. Be the first to submit a price.
          </p>
        ) : (
          <ol className="space-y-2">
            {compare
              .slice()
              .sort((a, b) => a.median_price - b.median_price)
              .map((row, i) => (
                <li
                  key={row.market_id}
                  className="flex items-center justify-between bg-bg rounded-lg px-4 py-3"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-text-secondary font-mono text-sm w-5">{i + 1}</span>
                    <div>
                      <p className="font-medium text-sm">{row.market_name}</p>
                      <p className="text-text-secondary text-xs">{row.city}</p>
                    </div>
                    {row.is_verified && (
                      <Badge className="bg-success/15 text-success border-success/30">
                        <CheckCircle2 size={12} /> Verified
                      </Badge>
                    )}
                  </div>
                  <div className="text-right">
                    <p className="font-semibold">{formatNaira(row.median_price)}</p>
                    <p className="text-text-secondary text-xs">{row.submission_count} submissions</p>
                  </div>
                </li>
              ))}
          </ol>
        )}
      </Card>
    </div>
  );
}
