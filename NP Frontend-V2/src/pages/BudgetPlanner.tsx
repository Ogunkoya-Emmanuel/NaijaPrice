import { useEffect, useState } from "react";
import { Link } from "@tanstack/react-router";
import { Plus, Trash2, Wallet, CheckCircle2, AlertTriangle } from "lucide-react";
import { api, type Commodity, type BudgetResult } from "@/lib/api";
import { CITIES, formatNaira, sourceLabel, sourceBadgeClass } from "@/lib/utils";
import { Card, Badge, ErrorBox } from "@/components/ui";

interface Row {
  key: number;
  commodity_id: number | "";
  quantity: string;
}

let nextKey = 1;

export default function BudgetPlanner() {
  const [commodities, setCommodities] = useState<Commodity[]>([]);
  const [budget, setBudget] = useState("");
  const [city, setCity] = useState(CITIES[0]);
  const [rows, setRows] = useState<Row[]>([{ key: nextKey++, commodity_id: "", quantity: "1" }]);

  const [result, setResult] = useState<BudgetResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    api.commodities().then(setCommodities).catch(() => {});
  }, []);

  function addRow() {
    setRows((r) => [...r, { key: nextKey++, commodity_id: "", quantity: "1" }]);
  }

  function removeRow(key: number) {
    setRows((r) => (r.length > 1 ? r.filter((row) => row.key !== key) : r));
  }

  function updateRow(key: number, patch: Partial<Row>) {
    setRows((r) => r.map((row) => (row.key === key ? { ...row, ...patch } : row)));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setResult(null);

    const budgetNgn = Number(budget);
    if (!budgetNgn || budgetNgn <= 0) {
      setError("Enter a budget greater than zero.");
      return;
    }
    const items = rows
      .filter((r) => r.commodity_id && Number(r.quantity) > 0)
      .map((r) => ({ commodity_id: Number(r.commodity_id), quantity: Number(r.quantity) }));

    if (items.length === 0) {
      setError("Add at least one commodity with a quantity.");
      return;
    }

    setSubmitting(true);
    try {
      const res = await api.optimizeBudget({ budget_ngn: budgetNgn, city, items });
      setResult(res);
    } catch (e: any) {
      setError(e.message || "Something went wrong. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="px-4 md:px-8 py-6 md:py-8 max-w-3xl mx-auto">
      <h1 className="text-2xl font-extrabold mb-1 flex items-center gap-2">
        <Wallet size={22} className="text-amber" /> Budget Planner
      </h1>
      <p className="text-text-secondary text-sm mb-6">
        Tell us your budget and shopping list — we'll find the cheapest way to buy it all.
      </p>

      <Card className="p-6">
        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1.5">Budget (₦)</label>
              <input
                type="number"
                min={0}
                step="0.01"
                value={budget}
                onChange={(e) => setBudget(e.target.value)}
                placeholder="e.g. 15000"
                className="w-full bg-bg border border-border rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-amber"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1.5">City</label>
              <select
                value={city}
                onChange={(e) => setCity(e.target.value)}
                className="w-full bg-bg border border-border rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-amber"
              >
                {CITIES.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1.5">Shopping list</label>
            <div className="space-y-2">
              {rows.map((row) => (
                <div key={row.key} className="flex gap-2">
                  <select
                    value={row.commodity_id}
                    onChange={(e) =>
                      updateRow(row.key, { commodity_id: e.target.value ? Number(e.target.value) : "" })
                    }
                    className="flex-1 min-w-0 bg-bg border border-border rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-amber"
                  >
                    <option value="">Select a commodity</option>
                    {commodities.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                  <input
                    type="number"
                    min={0}
                    step="0.1"
                    value={row.quantity}
                    onChange={(e) => updateRow(row.key, { quantity: e.target.value })}
                    placeholder="Qty"
                    className="w-24 shrink-0 bg-bg border border-border rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-amber"
                  />
                  <button
                    type="button"
                    onClick={() => removeRow(row.key)}
                    className="shrink-0 w-10 flex items-center justify-center rounded-xl border border-border text-text-secondary hover:text-danger hover:border-danger/40"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              ))}
            </div>
            <button
              type="button"
              onClick={addRow}
              className="mt-3 inline-flex items-center gap-1.5 text-sm text-amber hover:brightness-110"
            >
              <Plus size={16} /> Add item
            </button>
          </div>

          {error && <ErrorBox message={error} />}

          <button
            type="submit"
            disabled={submitting}
            className="w-full bg-amber text-bg font-semibold rounded-xl py-3 text-sm hover:brightness-110 transition disabled:opacity-50"
          >
            {submitting ? "Calculating..." : "Find the cheapest way to shop"}
          </button>
        </form>
      </Card>

      {result && (
        <div className="mt-6 space-y-4">
          <Card className={`p-5 border-l-4 ${result.within_budget ? "border-l-success" : "border-l-danger"}`}>
            <div className="flex items-center gap-2">
              {result.within_budget ? (
                <CheckCircle2 size={18} className="text-success" />
              ) : (
                <AlertTriangle size={18} className="text-danger" />
              )}
              <p className="font-semibold">
                {result.within_budget ? "This fits your budget" : "This is over budget"}
              </p>
            </div>
            <div className="grid grid-cols-2 gap-4 mt-3">
              <div>
                <p className="text-text-secondary text-xs">Estimated total</p>
                <p className="text-xl font-bold mt-0.5">{formatNaira(result.estimated_total)}</p>
              </div>
              <div>
                <p className="text-text-secondary text-xs">
                  {result.within_budget ? "Remaining" : "Over by"}
                </p>
                <p className={`text-xl font-bold mt-0.5 ${result.within_budget ? "text-success" : "text-danger"}`}>
                  {formatNaira(Math.abs(result.amount_over_or_under))}
                </p>
              </div>
            </div>
            {result.savings_tip && (
              <p className="text-text-secondary text-sm mt-3 border-t border-border pt-3">
                {result.savings_tip}
              </p>
            )}
          </Card>

          <Card className="p-5">
            <h2 className="font-semibold mb-3">Where to buy each item · {result.city}</h2>
            <ol className="space-y-2">
              {result.items.map((item) => (
                <li key={item.commodity_id} className="bg-bg rounded-lg px-4 py-3">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="font-medium text-sm">
                        {item.commodity} <span className="text-text-secondary">× {item.quantity}</span>
                      </p>
                      <p className="text-text-secondary text-xs mt-0.5">{item.recommended_market}</p>
                    </div>
                    <p className="font-semibold shrink-0">{formatNaira(item.subtotal)}</p>
                  </div>
                  <Badge className={`${sourceBadgeClass(item.price_source)} mt-2`}>
                    {sourceLabel(item.price_source)}
                  </Badge>
                </li>
              ))}
            </ol>

            {result.unavailable_items.length > 0 && (
              <div className="mt-3 text-sm text-text-secondary">
                Not priced (no data available): {result.unavailable_items.join(", ")}
              </div>
            )}
          </Card>

          {result.single_market_alternative && result.single_market_total != null && (
            <Card className="p-5">
              <h2 className="font-semibold mb-1">One-trip alternative</h2>
              <p className="text-text-secondary text-sm">
                Buy everything at <span className="text-text font-medium">{result.single_market_alternative}</span> in a
                single trip for <span className="text-text font-medium">{formatNaira(result.single_market_total)}</span>.
              </p>
            </Card>
          )}
        </div>
      )}

      <p className="text-text-secondary text-xs mt-6">
        Want to see verified prices market-by-market first?{" "}
        <Link to="/markets" className="text-amber hover:underline">
          Browse Market Explorer
        </Link>
        .
      </p>
    </div>
  );
}
