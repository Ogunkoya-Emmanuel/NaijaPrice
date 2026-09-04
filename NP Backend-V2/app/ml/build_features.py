"""
Builds the training panel for the price-change forecasting model.

Reads directly from the data/ CSVs (not the database) so this pipeline is
reproducible independent of any running Postgres instance.

For every (commodity, target_month) pair, builds a feature row using ONLY
information that would have been available the month BEFORE the target month
(i.e. no lookahead), with the target being the actual mom_pct realized in
the target month. This mirrors exactly how the model will be used in
production: at time t-1, forecast the change for month t.
"""
import pandas as pd
import numpy as np
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")


def _load_nbs():
    nbs = pd.read_csv(os.path.join(DATA_DIR, "nbs_food_prices_cleaned.csv"))
    nbs["date"] = pd.to_datetime(nbs["date"])
    nbs["source"] = "NBS"
    return nbs[["date", "commodity", "avg_price_ngn", "mom_pct", "source"]]


def _load_wb_backfill():
    path = os.path.join(DATA_DIR, "wb_rtfp_backfill_pre2025.csv")
    if not os.path.exists(path):
        return pd.DataFrame(columns=["date", "commodity", "avg_price_ngn", "mom_pct", "source"])
    wb = pd.read_csv(path)
    wb["date"] = pd.to_datetime(wb["date"])
    wb = wb.sort_values(["commodity", "date"])
    wb["mom_pct"] = wb.groupby("commodity")["avg_price_ngn"].pct_change() * 100
    wb["source"] = "WB_RTFP"
    return wb[["date", "commodity", "avg_price_ngn", "mom_pct", "source"]]


def _load_fuel():
    fuel = pd.read_csv(os.path.join(DATA_DIR, "pms_fuel_national_monthly_cleaned.csv"))
    fuel["date"] = pd.to_datetime(fuel["date"])
    return fuel[["date", "mom_pct"]].rename(columns={"mom_pct": "fuel_mom_pct"})


def _load_fx():
    fx = pd.read_csv(os.path.join(DATA_DIR, "nfem_exchange_rates_monthly_cleaned.csv"))
    fx["date"] = pd.to_datetime(fx["date"])
    fx = fx.sort_values("date")
    fx["fx_mom_pct"] = fx["avg_closing_rate"].pct_change() * 100
    return fx[["date", "fx_mom_pct"]]


def _load_harvest():
    h = pd.read_csv(os.path.join(DATA_DIR, "harvest_season_calendar.csv"))
    h["is_import"] = h["harvest_months"].isna() | (h["harvest_months"].astype(str) == "N/A")
    return h[["commodity", "month", "is_harvest_month", "is_lean_month", "is_import"]]


def build_panel() -> pd.DataFrame:
    nbs = _load_nbs()
    wb = _load_wb_backfill()

    # Combine: for a given (commodity, date), prefer NBS (directly measured) over WB (imputed)
    combined = pd.concat([wb, nbs], ignore_index=True)
    combined = combined.sort_values(["commodity", "date", "source"])  # NBS sorts after WB_RTFP alphabetically? no.
    # Explicit priority: NBS wins on duplicate (commodity, date)
    combined["priority"] = combined["source"].map({"NBS": 1, "WB_RTFP": 0})
    combined = combined.sort_values(["commodity", "date", "priority"])
    combined = combined.drop_duplicates(subset=["commodity", "date"], keep="last").drop(columns="priority")
    combined = combined.sort_values(["commodity", "date"]).reset_index(drop=True)

    # Recompute mom_pct consistently across the merged series per commodity
    combined["mom_pct"] = combined.groupby("commodity")["avg_price_ngn"].pct_change() * 100

    fuel = _load_fuel()
    fx = _load_fx()
    harvest = _load_harvest()

    rows = []
    for commodity, grp in combined.groupby("commodity"):
        grp = grp.sort_values("date").reset_index(drop=True)
        for i in range(1, len(grp)):
            target_row = grp.iloc[i]
            target_date = target_row["date"]
            target_month = target_date.month
            actual_mom = target_row["mom_pct"]
            if pd.isna(actual_mom):
                continue

            as_of_date = grp.iloc[i - 1]["date"]  # information cutoff: the prior month

            def lag(n):
                idx = i - n
                if idx < 0:
                    return np.nan
                v = grp.iloc[idx]["mom_pct"]
                return v if pd.notna(v) else np.nan

            lag1, lag2, lag3, lag12 = lag(1), lag(2), lag(3), lag(12)

            fuel_val = fuel.loc[fuel["date"] == as_of_date, "fuel_mom_pct"]
            fuel_mom = float(fuel_val.iloc[0]) if len(fuel_val) else np.nan

            fx_val = fx.loc[fx["date"] == as_of_date, "fx_mom_pct"]
            fx_mom = float(fx_val.iloc[0]) if len(fx_val) else np.nan

            h_row = harvest[(harvest["commodity"] == commodity) & (harvest["month"] == target_month)]
            is_harvest = bool(h_row["is_harvest_month"].iloc[0]) if len(h_row) else False
            is_lean = bool(h_row["is_lean_month"].iloc[0]) if len(h_row) else False
            is_import = bool(h_row["is_import"].iloc[0]) if len(h_row) else False

            rows.append({
                "commodity": commodity,
                "target_date": target_date,
                "as_of_date": as_of_date,
                "month_sin": np.sin(2 * np.pi * target_month / 12),
                "month_cos": np.cos(2 * np.pi * target_month / 12),
                "lag1_mom_pct": lag1,
                "lag2_mom_pct": lag2,
                "lag3_mom_pct": lag3,
                "lag12_mom_pct": lag12,
                "fuel_mom_pct": fuel_mom,
                "fx_mom_pct": fx_mom if is_import else 0.0,
                "is_harvest_month": int(is_harvest),
                "is_lean_month": int(is_lean),
                "is_import": int(is_import),
                "n_history_months": i,  # how much history existed at prediction time
                "source": target_row["source"],
                "target_mom_pct": actual_mom,
            })

    panel = pd.DataFrame(rows)
    panel = panel.sort_values(["target_date", "commodity"]).reset_index(drop=True)
    return panel


if __name__ == "__main__":
    panel = build_panel()
    out_path = os.path.join(os.path.dirname(__file__), "training_panel.csv")
    panel.to_csv(out_path, index=False)
    print(f"Built panel: {len(panel)} rows, {panel['commodity'].nunique()} commodities")
    print(f"Date range: {panel['target_date'].min()} to {panel['target_date'].max()}")
    print(f"Saved to {out_path}")
