import { useEffect, useState, Suspense, lazy } from "react";
import { Link } from "@tanstack/react-router";
import { api, type Market, type Commodity } from "@/lib/api";
import { CITIES, ZONE_COLORS, formatNaira } from "@/lib/utils";
import { Card, Badge, ErrorBox } from "@/components/ui";
import Skeleton from "@/components/Skeleton";
import { MapPin, List, Map as MapIcon, CheckCircle2 } from "lucide-react";
import type { MapMarket } from "@/lib/api";

const MarketMap = lazy(() => import("@/components/MarketMap"));

export default function Markets() {
  const [view, setView] = useState<"list" | "map">("list");
  const [city, setCity] = useState(CITIES[0]);
  const [markets, setMarkets] = useState<Market[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const [commodities, setCommodities] = useState<Commodity[]>([]);
  const [mapCommodityId, setMapCommodityId] = useState<number | "">("");
  const [mapMarkets, setMapMarkets] = useState<MapMarket[] | null>(null);
  const [mapLoading, setMapLoading] = useState(false);

  useEffect(() => {
    if (view !== "list") return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    api
      .markets(city)
      .then((res) => {
        if (!cancelled) setMarkets(res);
      })
      .catch((e) => {
        if (!cancelled) setError(e.message || "Failed to load markets");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [city, view]);

  useEffect(() => {
    if (view !== "map") return;
    if (commodities.length === 0) {
      api.commodities().then(setCommodities).catch(() => {});
    }
  }, [view]);

  useEffect(() => {
    if (view !== "map") return;
    let cancelled = false;
    setMapLoading(true);
    api
      .mapMarkets(mapCommodityId || undefined)
      .then((res) => {
        if (!cancelled) setMapMarkets(res.markets);
      })
      .catch((e) => {
        if (!cancelled) setError(e.message || "Failed to load map data");
      })
      .finally(() => {
        if (!cancelled) setMapLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [view, mapCommodityId]);

  return (
    <div className="px-4 md:px-8 py-6 md:py-8 max-w-7xl mx-auto">
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
        <h1 className="text-2xl font-extrabold">Market Explorer</h1>
        <div className="flex bg-surface border border-border rounded-xl p-1">
          <button
            onClick={() => setView("list")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              view === "list" ? "bg-amber text-bg" : "text-text-secondary hover:text-text"
            }`}
          >
            <List size={15} /> List
          </button>
          <button
            onClick={() => setView("map")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              view === "map" ? "bg-amber text-bg" : "text-text-secondary hover:text-text"
            }`}
          >
            <MapIcon size={15} /> Map
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-6">
          <ErrorBox message={error} />
        </div>
      )}

      {view === "list" ? (
        <>
          <div className="flex gap-2 overflow-x-auto pb-2 mb-6">
            {CITIES.map((c) => (
              <button
                key={c}
                onClick={() => setCity(c)}
                className={`shrink-0 px-4 py-2 rounded-xl text-sm font-medium border transition-colors ${
                  city === c
                    ? "bg-amber text-bg border-amber"
                    : "bg-surface text-text-secondary border-border hover:text-text"
                }`}
              >
                {c}
              </button>
            ))}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {loading
              ? Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-28" />)
              : markets?.map((m) => (
                  <Card key={m.id} className="p-5 h-full hover:bg-white/[0.02] transition-colors">
                    <div className="flex items-start justify-between gap-2">
                      <p className="font-semibold">{m.name}</p>
                      {m.zone && (
                        <Badge className={ZONE_COLORS[m.zone] ?? "bg-stable/15 text-stable border-stable/30"}>
                          {m.zone}
                        </Badge>
                      )}
                    </div>
                    <p className="text-text-secondary text-sm mt-2 flex items-center gap-1.5">
                      <MapPin size={13} />
                      {m.city}
                      {m.state ? `, ${m.state}` : ""}
                    </p>
                  </Card>
                ))}
          </div>

          {!loading && markets?.length === 0 && (
            <p className="text-text-secondary text-sm">No markets found for {city}.</p>
          )}
        </>
      ) : (
        <>
          <div className="flex flex-wrap items-center gap-3 mb-4">
            <select
              value={mapCommodityId}
              onChange={(e) => setMapCommodityId(e.target.value ? Number(e.target.value) : "")}
              className="bg-surface border border-border rounded-xl px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber"
            >
              <option value="">All markets (no price overlay)</option>
              {commodities.map((c) => (
                <option key={c.id} value={c.id}>
                  Show prices for: {c.name}
                </option>
              ))}
            </select>
            {mapCommodityId && (
              <p className="text-text-secondary text-xs">
                Amber pins have a crowd price for this commodity · grey pins don't yet
              </p>
            )}
          </div>

          {mapLoading || !mapMarkets ? (
            <Skeleton className="h-[520px]" />
          ) : (
            <Suspense fallback={<Skeleton className="h-[520px]" />}>
              <MarketMap markets={mapMarkets} />
            </Suspense>
          )}

          {mapCommodityId && !mapLoading && mapMarkets && (
            <div className="mt-6">
              <h2 className="font-semibold mb-3">Cheapest right now</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                {mapMarkets
                  .filter((m) => m.median_price)
                  .sort((a, b) => (a.median_price ?? 0) - (b.median_price ?? 0))
                  .slice(0, 6)
                  .map((m) => (
                    <Card key={m.market_id} className="p-4">
                      <p className="font-medium text-sm">{m.name}</p>
                      <p className="text-text-secondary text-xs mt-0.5">{m.city}</p>
                      <div className="flex items-center justify-between mt-2">
                        <p className="font-bold">{formatNaira(m.median_price!)}</p>
                        {m.is_verified && <CheckCircle2 size={14} className="text-success" />}
                      </div>
                    </Card>
                  ))}
              </div>
            </div>
          )}
        </>
      )}

      <p className="text-text-secondary text-xs mt-8">
        Looking to price out a whole shopping list at once?{" "}
        <Link to="/budget" className="text-amber hover:underline">
          Try the Budget Planner
        </Link>
        .
      </p>
    </div>
  );
}
