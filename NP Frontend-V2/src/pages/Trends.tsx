import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Cell,
} from "recharts";
import { AlertTriangle } from "lucide-react";
import { api, type Commodity, type Trend, type AnomalyResponse } from "@/lib/api";
import { formatNaira, formatMonthYear, pct } from "@/lib/utils";
import { Card, ErrorBox, Badge } from "@/components/ui";
import Skeleton from "@/components/Skeleton";

export default function Trends() {
  const [commodities, setCommodities] = useState<Commodity[]>([]);
  const [selected, setSelected] = useState<number | "">("");
  const [trend, setTrend] = useState<Trend | null>(null);
  const [anomalies, setAnomalies] = useState<AnomalyResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api
      .commodities()
      .then((c) => {
        setCommodities(c);
        if (c.length) setSelected(c[0].id);
      })
      .catch((e) => setError(e.message || "Failed to load commodities"));
  }, []);

  useEffect(() => {
    if (!selected) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    setAnomalies(null);
    Promise.allSettled([api.trends(selected), api.anomalies(selected)]).then(([t, a]) => {
      if (cancelled) return;
      if (t.status === "fulfilled") setTrend(t.value);
      else setError(t.reason?.message || "Failed to load trend data");
      if (a.status === "fulfilled") setAnomalies(a.value);
      // anomalies failing silently is fine — not enough history is a normal case, not an error to surface
      setLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, [selected]);

  const anomalyDates = new Set((anomalies?.anomalies ?? []).map((a) => a.date));

  return (
    <div className="px-4 md:px-8 py-6 md:py-8 max-w-7xl mx-auto">
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
        <h1 className="text-2xl font-extrabold">Trends</h1>
        <select
          value={selected}
          onChange={(e) => setSelected(Number(e.target.value))}
          className="bg-surface border border-border rounded-xl px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber"
        >
          {commodities.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
      </div>

      {error && (
        <div className="mb-6">
          <ErrorBox message={error} />
        </div>
      )}

      {anomalies && anomalies.latest_month_is_anomaly && (
        <div className="flex items-start gap-2 bg-danger/10 border border-danger/30 text-danger text-sm rounded-xl px-4 py-3 mb-6">
          <AlertTriangle size={16} className="shrink-0 mt-0.5" />
          <span>
            The latest month's price move for this commodity was a statistical outlier versus its
            own history — worth a second look before acting on the forecast.
          </span>
        </div>
      )}

      <Card className="p-5 mb-6">
        <h2 className="font-semibold mb-4">Price over time</h2>
        {loading ? (
          <Skeleton className="h-80" />
        ) : !trend?.points?.length ? (
          <p className="text-text-secondary text-sm">No trend data available.</p>
        ) : (
          <ResponsiveContainer width="100%" height={320}>
            <LineChart data={trend.points}>
              <CartesianGrid stroke="#1F2937" strokeDasharray="3 3" />
              <XAxis dataKey="date" tickFormatter={(v) => formatMonthYear(v)} stroke="#9CA3AF" fontSize={12} />
              <YAxis stroke="#9CA3AF" fontSize={12} tickFormatter={(v) => `₦${v}`} width={60} />
              <Tooltip
                contentStyle={{ background: "#111827", border: "1px solid #1F2937", borderRadius: 12, fontSize: 13 }}
                labelFormatter={(v) => formatMonthYear(String(v))}
                formatter={(value: any) => [formatNaira(Number(value)), "Price"]}
              />
              <Line type="monotone" dataKey="price_ngn" stroke="#F59E0B" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </Card>

      <Card className="p-5 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold">Month-over-month change</h2>
          {anomalies && anomalies.anomalies.length > 0 && (
            <Badge className="bg-danger/15 text-danger border-danger/30">
              {anomalies.anomalies.length} unusual month{anomalies.anomalies.length === 1 ? "" : "s"} on record
            </Badge>
          )}
        </div>
        {loading ? (
          <Skeleton className="h-56" />
        ) : !trend?.points?.length ? (
          <p className="text-text-secondary text-sm">No data available.</p>
        ) : (
          <>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={trend.points}>
                <CartesianGrid stroke="#1F2937" strokeDasharray="3 3" />
                <XAxis dataKey="date" tickFormatter={(v) => formatMonthYear(v)} stroke="#9CA3AF" fontSize={12} />
                <YAxis stroke="#9CA3AF" fontSize={12} tickFormatter={(v) => `${v}%`} />
                <Tooltip
                  contentStyle={{ background: "#111827", border: "1px solid #1F2937", borderRadius: 12, fontSize: 13 }}
                  labelFormatter={(v) => formatMonthYear(String(v))}
                  formatter={(value: any, _name: any, item: any) => {
                    const isAnomaly = anomalyDates.has(item?.payload?.date);
                    return [`${value}%${isAnomaly ? " · unusual swing" : ""}`, "MoM"];
                  }}
                />
                <Bar dataKey="mom_pct" radius={[4, 4, 0, 0]}>
                  {trend.points.map((p, i) => {
                    const isAnomaly = anomalyDates.has(p.date);
                    const fill = isAnomaly ? "#F59E0B" : (p.mom_pct ?? 0) >= 0 ? "#10B981" : "#EF4444";
                    return <Cell key={i} fill={fill} stroke={isAnomaly ? "#F59E0B" : undefined} />;
                  })}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
            {anomalies && anomalies.anomalies.length > 0 && (
              <p className="text-text-secondary text-xs mt-3">
                Amber bars mark months that moved more than {anomalies.threshold_z}σ from this
                commodity's typical month-over-month swing (avg {pct(anomalies.mean_mom_pct)}).
              </p>
            )}
          </>
        )}
      </Card>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Card className="p-5">
          <p className="text-text-secondary text-xs uppercase tracking-wide">3-month change</p>
          <p
            className={`text-2xl font-bold mt-2 ${
              (trend?.price_change_3m ?? 0) > 0 ? "text-danger" : (trend?.price_change_3m ?? 0) < 0 ? "text-success" : "text-stable"
            }`}
          >
            {loading ? <Skeleton className="h-8 w-20" /> : pct(trend?.price_change_3m)}
          </p>
        </Card>
        <Card className="p-5">
          <p className="text-text-secondary text-xs uppercase tracking-wide">12-month change</p>
          <p
            className={`text-2xl font-bold mt-2 ${
              (trend?.price_change_12m ?? 0) > 0 ? "text-danger" : (trend?.price_change_12m ?? 0) < 0 ? "text-success" : "text-stable"
            }`}
          >
            {loading ? <Skeleton className="h-8 w-20" /> : pct(trend?.price_change_12m)}
          </p>
        </Card>
      </div>
    </div>
  );
}

