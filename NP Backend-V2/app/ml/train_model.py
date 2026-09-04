"""
Trains a single pooled LightGBM model across all 42 commodities to forecast
next-month price % change, and backtests it with rolling time-based
validation against a seasonal-naive baseline.

Why one pooled model instead of 42 per-commodity models: most commodities
only have ~18 months of NBS history, nowhere near enough to fit a model
individually. Pooling lets the 9 commodities with deep (2007-2026) history
teach the model general seasonal/fuel/FX price dynamics, which the other 33
commodities then borrow via the `commodity` categorical feature.

Run from NP Backend/:  python -m app.ml.train_model
"""
import pandas as pd
import numpy as np
import lightgbm as lgb
import joblib
import json
import os
from app.ml.build_features import build_panel

ML_DIR = os.path.dirname(os.path.abspath(__file__))
FEATURES = [
    "month_sin", "month_cos",
    "lag1_mom_pct", "lag2_mom_pct", "lag3_mom_pct", "lag12_mom_pct",
    "fuel_mom_pct", "fx_mom_pct",
    "is_harvest_month", "is_lean_month", "is_import",
    "commodity_code",
]


def seasonal_naive_baseline(row, history_by_commodity):
    """Baseline: predict this month's change = same-month average change in
    prior years for this commodity (mirrors the old rule-based forecast_engine
    logic), falling back to lag1 if no same-month history exists."""
    lag12 = row["lag12_mom_pct"]
    if pd.notna(lag12):
        return lag12
    if pd.notna(row["lag1_mom_pct"]):
        return row["lag1_mom_pct"]
    return 0.0


def rolling_backtest(panel: pd.DataFrame, min_train_months: int = 24, step_months: int = 1):
    """
    Rolling-origin backtest: for each cutoff date, train on everything before
    it, predict the very next available target date(s), slide forward.
    Never trains on the future relative to what it's predicting.
    """
    panel = panel.copy()
    panel["commodity_code"] = panel["commodity"].astype("category").cat.codes
    codes_map = dict(enumerate(panel["commodity"].astype("category").cat.categories))

    unique_dates = sorted(panel["target_date"].unique())
    if len(unique_dates) < min_train_months + 2:
        raise ValueError("Not enough distinct months to backtest.")

    cutoffs = unique_dates[min_train_months::step_months]

    preds_model, preds_baseline, actuals, meta = [], [], [], []

    for cutoff in cutoffs:
        train = panel[panel["target_date"] < cutoff]
        test = panel[panel["target_date"] == cutoff]
        if len(train) < 50 or len(test) == 0:
            continue

        X_train, y_train = train[FEATURES], train["target_mom_pct"]
        X_test, y_test = test[FEATURES], test["target_mom_pct"]

        model = lgb.LGBMRegressor(
            n_estimators=150,
            max_depth=4,
            learning_rate=0.05,
            min_child_samples=10,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            verbosity=-1,
        )
        model.fit(X_train, y_train, categorical_feature=["commodity_code"])
        pred = model.predict(X_test)

        baseline_pred = test.apply(seasonal_naive_baseline, axis=1, history_by_commodity=None)

        preds_model.extend(pred.tolist())
        preds_baseline.extend(baseline_pred.tolist())
        actuals.extend(y_test.tolist())
        meta.extend(test[["commodity", "target_date", "source"]].to_dict("records"))

    return pd.DataFrame({
        "commodity": [m["commodity"] for m in meta],
        "target_date": [m["target_date"] for m in meta],
        "source": [m["source"] for m in meta],
        "actual": actuals,
        "model_pred": preds_model,
        "baseline_pred": preds_baseline,
    })


def mape(actual, pred):
    actual, pred = np.array(actual), np.array(pred)
    denom = np.maximum(np.abs(actual), 1.0)  # avoid blow-up near-zero actuals
    return float(np.mean(np.abs((actual - pred) / denom)) * 100)


def mae(actual, pred):
    return float(np.mean(np.abs(np.array(actual) - np.array(pred))))


def summarize(results: pd.DataFrame) -> dict:
    deep_history_commodities = {
        "Agric Hen Eggs (Crate of 30 Pieces)", "Beans Brown", "Beef Boneless",
        "Garri White", "Goat Meat Bone-In", "Maize White Grain",
        "Onions Fresh", "Rice Long-Grain Imported", "Yam Tuber",
    }
    results["group"] = results["commodity"].apply(
        lambda c: "deep_history_9" if c in deep_history_commodities else "shallow_history_33"
    )

    def block(df):
        return {
            "n_test_points": len(df),
            "model_mae": round(mae(df["actual"], df["model_pred"]), 3),
            "model_mape_pct": round(mape(df["actual"], df["model_pred"]), 2),
            "baseline_mae": round(mae(df["actual"], df["baseline_pred"]), 3),
            "baseline_mape_pct": round(mape(df["actual"], df["baseline_pred"]), 2),
        }

    summary = {"overall": block(results)}
    for group_name, grp in results.groupby("group"):
        summary[group_name] = block(grp)

    overall = summary["overall"]
    if overall["baseline_mape_pct"] > 0:
        improvement = (overall["baseline_mape_pct"] - overall["model_mape_pct"]) / overall["baseline_mape_pct"] * 100
    else:
        improvement = 0.0
    summary["overall"]["improvement_vs_baseline_pct"] = round(improvement, 1)

    return summary


def train_final_model(panel: pd.DataFrame):
    """Trains on ALL available data for production use (after backtesting has
    already validated the approach on held-out folds)."""
    panel = panel.copy()
    panel["commodity_code"] = panel["commodity"].astype("category").cat.codes
    codes_map = {v: k for k, v in dict(enumerate(panel["commodity"].astype("category").cat.categories)).items()}

    X, y = panel[FEATURES], panel["target_mom_pct"]
    model = lgb.LGBMRegressor(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        min_child_samples=10,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        verbosity=-1,
    )
    model.fit(X, y, categorical_feature=["commodity_code"])

    joblib.dump({"model": model, "commodity_code_map": codes_map, "features": FEATURES},
                os.path.join(ML_DIR, "forecast_model.joblib"))
    return model


if __name__ == "__main__":
    print("Building feature panel...")
    panel = build_panel()

    print("Running rolling-origin backtest (this validates before we trust the model)...")
    results = rolling_backtest(panel, min_train_months=24, step_months=1)
    summary = summarize(results)

    print(json.dumps(summary, indent=2))

    with open(os.path.join(ML_DIR, "model_performance.json"), "w") as f:
        json.dump(summary, f, indent=2)
    results.to_csv(os.path.join(ML_DIR, "backtest_predictions.csv"), index=False)

    print("\nTraining final production model on full dataset...")
    train_final_model(panel)
    print(f"Saved model to {ML_DIR}/forecast_model.joblib")
    print(f"Saved metrics to {ML_DIR}/model_performance.json")
