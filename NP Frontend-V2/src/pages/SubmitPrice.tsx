import { useEffect, useMemo, useState } from "react";
import { api, type Commodity, type Market } from "@/lib/api";
import { useCity } from "@/lib/city-context";
import { Card, ErrorBox } from "@/components/ui";
import { flagReasonLabel } from "@/lib/utils";
import { Info, CheckCircle2, AlertTriangle } from "lucide-react";

export default function SubmitPrice() {
  const { city } = useCity();
  const [commodities, setCommodities] = useState<Commodity[]>([]);
  const [markets, setMarkets] = useState<Market[]>([]);
  const [search, setSearch] = useState("");
  const [commodityId, setCommodityId] = useState<number | "">("");
  const [marketId, setMarketId] = useState<number | "">("");
  const [price, setPrice] = useState("");
  const [unit, setUnit] = useState("");

  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [flagInfo, setFlagInfo] = useState<{ flagged: boolean; reason?: string | null } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.commodities(), api.markets(city)])
      .then(([c, m]) => {
        setCommodities(c);
        setMarkets(m);
      })
      .catch((e) => setLoadError(e.message || "Failed to load form data"));
  }, [city]);

  const filteredCommodities = useMemo(() => {
    if (!search) return commodities;
    return commodities.filter((c) => c.name.toLowerCase().includes(search.toLowerCase()));
  }, [commodities, search]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(false);

    if (!commodityId || !marketId || !price || Number(price) <= 0) {
      setError("Please fill in commodity, market, and a valid price.");
      return;
    }

    setSubmitting(true);
    try {
      const res = await api.submitPrice({
        commodity_id: Number(commodityId),
        market_id: Number(marketId),
        price_ngn: Number(price),
        quantity_unit: unit || undefined,
      });
      setSuccess(true);
      setFlagInfo({ flagged: res.is_flagged, reason: res.flag_reason });
      setCommodityId("");
      setMarketId("");
      setPrice("");
      setUnit("");
      setSearch("");
    } catch (e: any) {
      setError(e.message || "Something went wrong. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="px-4 md:px-8 py-6 md:py-8 max-w-2xl mx-auto">
      <h1 className="text-2xl font-extrabold mb-6">Submit a Price</h1>

      <div className="flex items-start gap-3 bg-amber/10 border border-amber/30 rounded-xl px-4 py-3 mb-6 text-sm text-text-secondary">
        <Info size={18} className="text-amber shrink-0 mt-0.5" />
        <p>
          Prices are verified once at least 3 independent submissions are received. Outliers are
          filtered automatically.
        </p>
      </div>

      {loadError && (
        <div className="mb-4">
          <ErrorBox message={loadError} />
        </div>
      )}

      <Card className="p-6">
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-sm font-medium mb-1.5">Commodity</label>
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search commodities..."
              className="w-full bg-bg border border-border rounded-xl px-4 py-2.5 text-sm mb-2 focus:outline-none focus:ring-2 focus:ring-amber"
            />
            <select
              value={commodityId}
              onChange={(e) => setCommodityId(e.target.value ? Number(e.target.value) : "")}
              className="w-full bg-bg border border-border rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-amber"
            >
              <option value="">Select a commodity</option>
              {filteredCommodities.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1.5">Market ({city})</label>
            <select
              value={marketId}
              onChange={(e) => setMarketId(e.target.value ? Number(e.target.value) : "")}
              className="w-full bg-bg border border-border rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-amber"
            >
              <option value="">Select a market</option>
              {markets.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1.5">Price (₦)</label>
            <input
              type="number"
              min={0}
              step="0.01"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              placeholder="0.00"
              className="w-full bg-bg border border-border rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-amber"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1.5">Quantity unit (optional)</label>
            <input
              type="text"
              value={unit}
              onChange={(e) => setUnit(e.target.value)}
              placeholder="e.g. per paint bucket, per kg"
              className="w-full bg-bg border border-border rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-amber"
            />
          </div>

          {error && <ErrorBox message={error} />}
          {success && flagInfo && !flagInfo.flagged && (
            <div className="flex items-center gap-2 bg-success/10 border border-success/30 text-success text-sm rounded-xl px-4 py-3">
              <CheckCircle2 size={16} />
              Price submitted. Thank you — your data helps Nigerians shop smarter.
            </div>
          )}
          {success && flagInfo && flagInfo.flagged && (
            <div className="flex items-start gap-2 bg-amber/10 border border-amber/30 text-amber text-sm rounded-xl px-4 py-3">
              <AlertTriangle size={16} className="shrink-0 mt-0.5" />
              <span>
                Price submitted, but {flagReasonLabel(flagInfo.reason).toLowerCase()}. It won't count
                toward the verified market price until reviewed. Thanks for contributing.
              </span>
            </div>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="w-full bg-amber text-bg font-semibold rounded-xl py-3 text-sm hover:brightness-110 transition disabled:opacity-50"
          >
            {submitting ? "Submitting..." : "Submit price"}
          </button>
        </form>
      </Card>
    </div>
  );
}
