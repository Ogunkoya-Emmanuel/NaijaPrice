import { useEffect, useState } from "react";
import { Link } from "@tanstack/react-router";
import { ArrowLeft, Gauge } from "lucide-react";
import { api, type ModelPerformance } from "@/lib/api";
import { Card, ErrorBox } from "@/components/ui";
import Skeleton from "@/components/Skeleton";

function BucketCard({
  title,
  subtitle,
  bucket,
}: {
  title: string;
  subtitle: string;
  bucket: { n_test_points: number; model_mape_pct: number; baseline_mape_pct: number };
}) {
  const improvement = Math.round(
    ((bucket.baseline_mape_pct - bucket.model_mape_pct) / bucket.baseline_mape_pct) * 100
  );
  const modelWins = bucket.model_mape_pct < bucket.baseline_mape_pct;

  return (
    <Card className="p-5">
      <p className="font-semibold">{title}</p>
      <p className="text-text-secondary text-xs mt-0.5">{subtitle}</p>

      <div className="grid grid-cols-2 gap-3 mt-4">
        <div className="bg-bg rounded-lg p-3">
          <p className="text-text-secondary text-xs">Trained model MAPE</p>
          <p className="font-bold text-lg mt-1">{bucket.model_mape_pct.toFixed(1)}%</p>
        </div>
        <div className="bg-bg rounded-lg p-3">
          <p className="text-text-secondary text-xs">Naive baseline MAPE</p>
          <p className="font-bold text-lg mt-1">{bucket.baseline_mape_pct.toFixed(1)}%</p>
        </div>
      </div>

      <p className={`text-sm font-medium mt-3 ${modelWins ? "text-success" : "text-danger"}`}>
        {modelWins
          ? `Model beats the baseline by ${improvement}%`
          : `Baseline still wins by ${Math.abs(improvement)}% here`}
      </p>
      <p className="text-text-secondary text-xs mt-1">{bucket.n_test_points.toLocaleString()} backtested data points</p>
    </Card>
  );
}

export default function ModelPerformance() {
  const [perf, setPerf] = useState<ModelPerformance | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .modelPerformance()
      .then(setPerf)
      .catch((e) => setError(e.message || "Failed to load model performance data"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="px-4 md:px-8 py-6 md:py-8 max-w-4xl mx-auto">
      <Link to="/" className="inline-flex items-center gap-1.5 text-text-secondary hover:text-text text-sm mb-4">
        <ArrowLeft size={15} /> Back to Dashboard
      </Link>

      <h1 className="text-2xl font-extrabold mb-1 flex items-center gap-2">
        <Gauge size={22} className="text-amber" /> Forecast accuracy
      </h1>
      <p className="text-text-secondary text-sm mb-6">
        How the trained forecasting model compares to a simple seasonal-naive baseline, backtested
        on real historical data.
      </p>

      {error && (
        <div className="mb-6">
          <ErrorBox message={error} />
        </div>
      )}

      {loading ? (
        <div className="space-y-4">
          <Skeleton className="h-24" />
          <Skeleton className="h-40" />
          <Skeleton className="h-40" />
        </div>
      ) : perf ? (
        <>
          <Card className="p-5 mb-6 border-l-4 border-l-amber">
            <p className="text-sm leading-relaxed">{perf.summary}</p>
          </Card>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
            <Card className="p-5 text-center">
              <p className="text-text-secondary text-xs uppercase tracking-wide">
                Commodities on the trained model
              </p>
              <p className="text-3xl font-bold mt-2 text-amber">{perf.ml_eligible_commodity_count}</p>
              <p className="text-text-secondary text-xs mt-1">Deep history (2007–2026)</p>
            </Card>
            <Card className="p-5 text-center">
              <p className="text-text-secondary text-xs uppercase tracking-wide">
                Commodities on the rule-based engine
              </p>
              <p className="text-3xl font-bold mt-2">{perf.rule_based_commodity_count}</p>
              <p className="text-text-secondary text-xs mt-1">~18 months of history</p>
            </Card>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <BucketCard
              title="Deep-history commodities"
              subtitle="9 commodities with full 2007–2026 price history — routed to the model"
              bucket={perf.deep_history_9}
            />
            <BucketCard
              title="Shallow-history commodities"
              subtitle="33 commodities with only ~18 months of history — stay on rule-based"
              bucket={perf.shallow_history_33}
            />
          </div>

          <Card className="p-5">
            <p className="font-semibold mb-1">Overall (all 42 commodities blended)</p>
            <div className="grid grid-cols-3 gap-3 mt-3 text-sm">
              <div className="bg-bg rounded-lg p-3">
                <p className="text-text-secondary text-xs">Model MAPE</p>
                <p className="font-bold mt-1">{perf.overall.model_mape_pct.toFixed(1)}%</p>
              </div>
              <div className="bg-bg rounded-lg p-3">
                <p className="text-text-secondary text-xs">Baseline MAPE</p>
                <p className="font-bold mt-1">{perf.overall.baseline_mape_pct.toFixed(1)}%</p>
              </div>
              <div className="bg-bg rounded-lg p-3">
                <p className="text-text-secondary text-xs">Improvement</p>
                <p className="font-bold mt-1 text-success">
                  {perf.overall.improvement_vs_baseline_pct?.toFixed(1) ?? "—"}%
                </p>
              </div>
            </div>
          </Card>

          <p className="text-text-secondary text-xs mt-6">
            MAPE = mean absolute percentage error, lower is better. Backtested with rolling
            time-based validation — the model was never trained on data from after the period it's
            predicting.
          </p>
        </>
      ) : null}
    </div>
  );
}
