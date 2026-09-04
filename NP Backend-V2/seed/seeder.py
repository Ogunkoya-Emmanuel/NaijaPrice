"""
Run from the project root:
    python -m seed.seeder

Expects these files in ./data/:
    nbs_food_prices_cleaned.csv
    pms_fuel_national_monthly_cleaned.csv
    nfem_exchange_rates_monthly_cleaned.csv
    harvest_season_calendar.csv
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import date
from sqlalchemy.orm import Session
from app.database import engine, Base, SessionLocal
from app import models
from app.config import get_settings

settings = get_settings()
DATA_DIR  = settings.data_dir


# ── Commodity metadata ─────────────────────────────────────────────────────────
COMMODITY_META = {
    "Agric Hen Eggs":                        ("Eggs",                      "Per piece",    True),
    "Agric Hen Eggs (Crate of 30 Pieces)":   ("Eggs",                      "Per crate",    True),
    "Beans Brown":                           ("Legumes",                    "Per kg",       True),
    "Beans White":                           ("Legumes",                    "Per kg",       True),
    "Beef Boneless":                         ("Meat & Poultry",             "Per kg",       True),
    "Bread Sliced 450g":                     ("Bread & Flour Products",     "Per 450g",     False),
    "Bread Unsliced 450g":                   ("Bread & Flour Products",     "Per 450g",     False),
    "Carrots Fresh":                         ("Vegetables & Fresh Produce", "Per kg",       True),
    "Catfish Fresh":                         ("Fish & Seafood",             "Per kg",       True),
    "Chicken Feet":                          ("Meat & Poultry",             "Per kg",       False),
    "Chicken Meat Frozen":                   ("Meat & Poultry",             "Per kg",       False),
    "Chicken Wings":                         ("Meat & Poultry",             "Per kg",       False),
    "Crayfish Small White":                  ("Fish & Seafood",             "Per measure",  True),
    "Dried Fish Bonga":                      ("Fish & Seafood",             "Per measure",  True),
    "Evaporated Milk Peak 150g":             ("Dairy",                      "Per 150g tin", False),
    "Evaporated Milk Three Crown 160g":      ("Dairy",                      "Per 160g tin", False),
    "Garri White":                           ("Root & Tuber",               "Per kg",       True),
    "Garri Yellow":                          ("Root & Tuber",               "Per kg",       True),
    "Ginger Fresh":                          ("Vegetables & Fresh Produce", "Per kg",       True),
    "Goat Meat Bone-In":                     ("Meat & Poultry",             "Per kg",       True),
    "Groundnut Oil 75cl":                    ("Oils & Fats",                "Per 75cl",     True),
    "Groundnuts Roasted 75cl":               ("Legumes",                    "Per 75cl",     True),
    "Irish Potato":                          ("Root & Tuber",               "Per kg",       True),
    "Mackerel Frozen":                       ("Fish & Seafood",             "Per kg",       False),
    "Maize White Grain":                     ("Grains & Cereals",           "Per kg",       True),
    "Onions Fresh":                          ("Vegetables & Fresh Produce", "Per kg",       True),
    "Palm Oil 75cl":                         ("Oils & Fats",                "Per 75cl",     True),
    "Plantain Ripe":                         ("Vegetables & Fresh Produce", "Per bunch",    True),
    "Plantain Unripe":                       ("Vegetables & Fresh Produce", "Per bunch",    True),
    "Rice Local Broken":                     ("Grains & Cereals",           "Per kg",       True),
    "Rice Local Short-Grain":                ("Grains & Cereals",           "Per kg",       True),
    "Rice Long-Grain Imported":              ("Grains & Cereals",           "Per kg",       False),
    "Semovita 1kg":                          ("Bread & Flour Products",     "Per 1kg",      False),
    "Smoked Fish Mackerel":                  ("Fish & Seafood",             "Per piece",    False),
    "Sweet Potatoes":                        ("Root & Tuber",               "Per kg",       True),
    "Tilapia Fresh":                         ("Fish & Seafood",             "Per kg",       True),
    "Titus Frozen":                          ("Fish & Seafood",             "Per kg",       False),
    "Tomatoes Fresh":                        ("Vegetables & Fresh Produce", "Per kg",       True),
    "Vegetable Oil 75cl":                    ("Oils & Fats",                "Per 75cl",     False),
    "Watermelon Fresh Medium":               ("Vegetables & Fresh Produce", "Per piece",    True),
    "Wheat Flour 2kg":                       ("Bread & Flour Products",     "Per 2kg",      False),
    "Yam Tuber":                             ("Root & Tuber",               "Per kg",       True),
}

# ── Nigerian markets ───────────────────────────────────────────────────────────
MARKETS = [
    # Lagos
    ("Mile 12 Market",        "Lagos", "Lagos",   "South West",  6.6018,   3.3792),
    ("Oyingbo Market",        "Lagos", "Lagos",   "South West",  6.4550,   3.3947),
    ("Mushin Market",         "Lagos", "Lagos",   "South West",  6.5244,   3.3539),
    ("Oshodi Market",         "Lagos", "Lagos",   "South West",  6.5578,   3.3306),
    ("Surulere Market",       "Lagos", "Lagos",   "South West",  6.4952,   3.3572),
    ("Agege Market",          "Lagos", "Lagos",   "South West",  6.6183,   3.3207),
    # Abuja
    ("Wuse Market",           "Abuja", "Abuja",   "North Central", 9.0765, 7.4898),
    ("Garki Market",          "Abuja", "Abuja",   "North Central", 9.0333, 7.4833),
    ("Utako Market",          "Abuja", "Abuja",   "North Central", 9.0850, 7.4650),
    ("Gwagwalada Market",     "Abuja", "Abuja",   "North Central", 8.9433, 7.0833),
    # Ibadan
    ("Bodija Market",         "Ibadan", "Oyo",    "South West",  7.3975,   3.8938),
    ("Dugbe Market",          "Ibadan", "Oyo",    "South West",  7.3878,   3.8989),
    ("UI Gate Market",        "Ibadan", "Oyo",    "South West",  7.4072,   3.8956),
    # Kano
    ("Singer Market",         "Kano",  "Kano",   "North West",  12.0022,  8.5919),
    ("Sabon Gari Market",     "Kano",  "Kano",   "North West",  11.9889,  8.5194),
    ("Kantin Kwari Market",   "Kano",  "Kano",   "North West",  12.0200,  8.5100),
    # Port Harcourt
    ("Mile 1 Diobu Market",   "Port Harcourt", "Rivers", "South South", 4.8156, 7.0498),
    ("Oil Mill Market",       "Port Harcourt", "Rivers", "South South", 4.8231, 7.0361),
    ("Rumuola Market",        "Port Harcourt", "Rivers", "South South", 4.8350, 7.0200),
    # Enugu
    ("Ogbete Main Market",    "Enugu", "Enugu",  "South East",  6.4448,   7.5067),
    ("New Market Enugu",      "Enugu", "Enugu",  "South East",  6.4533,   7.5189),
    # Benin City
    ("Oba Market",            "Benin City", "Edo", "South South", 6.3432, 5.6268),
    ("Uselu Market",          "Benin City", "Edo", "South South", 6.3700, 5.6150),
    # Kaduna
    ("Kasuwan Barci",         "Kaduna", "Kaduna", "North West",  10.5222, 7.4378),
    ("Barnawa Market",        "Kaduna", "Kaduna", "North West",  10.4767, 7.4200),
]


def seed_commodities(db: Session) -> dict[str, int]:
    """Seeds commodity table. Returns name→id map."""
    name_to_id = {}
    for name, (category, unit, is_agri) in COMMODITY_META.items():
        existing = db.query(models.Commodity).filter(models.Commodity.name == name).first()
        if not existing:
            c = models.Commodity(name=name, category=category, unit=unit, is_agricultural=is_agri)
            db.add(c)
            db.flush()
            name_to_id[name] = c.id
        else:
            name_to_id[name] = existing.id
    db.commit()
    print(f"  Commodities: {len(name_to_id)} seeded/found")
    return name_to_id


def seed_markets(db: Session) -> dict[tuple, int]:
    """Seeds market table. Returns (name, city)→id map."""
    market_map = {}
    for name, city, state, zone, lat, lon in MARKETS:
        existing = (
            db.query(models.Market)
            .filter(models.Market.name == name, models.Market.city == city)
            .first()
        )
        if not existing:
            m = models.Market(
                name=name, city=city, state=state,
                zone=zone, latitude=lat, longitude=lon
            )
            db.add(m)
            db.flush()
            market_map[(name, city)] = m.id
        else:
            market_map[(name, city)] = existing.id
    db.commit()
    print(f"  Markets: {len(market_map)} seeded/found")
    return market_map


def seed_nbs_prices(db: Session, name_to_id: dict[str, int]):
    csv_path = os.path.join(DATA_DIR, "nbs_food_prices_cleaned.csv")
    if not os.path.exists(csv_path):
        print(f"  SKIP nbs_food_prices_cleaned.csv not found at {csv_path}")
        return

    df = pd.read_csv(csv_path)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    inserted = skipped = 0

    for _, row in df.iterrows():
        commodity_id = name_to_id.get(row["commodity"])
        if not commodity_id:
            skipped += 1
            continue

        exists = (
            db.query(models.NBSHistoricalPrice)
            .filter(
                models.NBSHistoricalPrice.commodity_id == commodity_id,
                models.NBSHistoricalPrice.date == row["date"],
            )
            .first()
        )
        if exists:
            skipped += 1
            continue

        db.add(models.NBSHistoricalPrice(
            commodity_id  = commodity_id,
            date          = row["date"],
            avg_price_ngn = row["avg_price_ngn"],
            mom_pct       = None if pd.isna(row["mom_pct"]) else row["mom_pct"],
            yoy_pct       = None if pd.isna(row["yoy_pct"]) else row["yoy_pct"],
            highest_state = None if pd.isna(row["highest_state"]) else row["highest_state"],
            highest_price = None if pd.isna(row["highest_price"]) else row["highest_price"],
            lowest_state  = None if pd.isna(row["lowest_state"]) else row["lowest_state"],
            lowest_price  = None if pd.isna(row["lowest_price"]) else row["lowest_price"],
            source        = "NBS",
        ))
        inserted += 1

    db.commit()
    print(f"  NBS prices: {inserted} inserted, {skipped} skipped")


def seed_wb_backfill(db: Session, name_to_id: dict[str, int]):
    """
    Loads pre-2025 World Bank RTFP backfill for the 9 commodities that passed
    the product-comparability check (see app/ml/build_features.py for the
    full list and the exclusions). NBS data always takes priority when both
    exist for the same commodity/month - this only fills the gap before NBS
    coverage begins.
    """
    csv_path = os.path.join(DATA_DIR, "wb_rtfp_backfill_pre2025.csv")
    if not os.path.exists(csv_path):
        print(f"  SKIP wb_rtfp_backfill_pre2025.csv not found at {csv_path}")
        return

    df = pd.read_csv(csv_path)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df = df.sort_values(["commodity", "date"])
    df["mom_pct"] = df.groupby("commodity")["avg_price_ngn"].pct_change() * 100

    inserted = skipped = 0
    for _, row in df.iterrows():
        commodity_id = name_to_id.get(row["commodity"])
        if not commodity_id:
            skipped += 1
            continue

        exists = (
            db.query(models.NBSHistoricalPrice)
            .filter(
                models.NBSHistoricalPrice.commodity_id == commodity_id,
                models.NBSHistoricalPrice.date == row["date"],
            )
            .first()
        )
        if exists:
            skipped += 1  # NBS (or an earlier WB row) already covers this month
            continue

        db.add(models.NBSHistoricalPrice(
            commodity_id  = commodity_id,
            date          = row["date"],
            avg_price_ngn = round(row["avg_price_ngn"], 2),
            mom_pct       = None if pd.isna(row["mom_pct"]) else round(row["mom_pct"], 4),
            yoy_pct       = None,
            highest_state = None,
            highest_price = None,
            lowest_state  = None,
            lowest_price  = None,
            source        = "WB_RTFP",
        ))
        inserted += 1

    db.commit()
    print(f"  World Bank RTFP backfill: {inserted} inserted, {skipped} skipped")


def seed_pms_prices(db: Session):
    csv_path = os.path.join(DATA_DIR, "pms_fuel_national_monthly_cleaned.csv")
    if not os.path.exists(csv_path):
        print(f"  SKIP pms_fuel_national_monthly_cleaned.csv not found")
        return

    df = pd.read_csv(csv_path)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    inserted = skipped = 0

    for _, row in df.iterrows():
        exists = db.query(models.PMSFuelPrice).filter(
            models.PMSFuelPrice.date == row["date"]
        ).first()
        if exists:
            skipped += 1
            continue

        db.add(models.PMSFuelPrice(
            date                 = row["date"],
            national_avg_pms_ngn = row["national_avg_pms_ngn"],
            mom_pct              = None if pd.isna(row["mom_pct"]) else row["mom_pct"],
            yoy_pct              = None if pd.isna(row["yoy_pct"]) else row["yoy_pct"],
        ))
        inserted += 1

    db.commit()
    print(f"  PMS prices: {inserted} inserted, {skipped} skipped")


def seed_exchange_rates(db: Session):
    csv_path = os.path.join(DATA_DIR, "nfem_exchange_rates_monthly_cleaned.csv")
    if not os.path.exists(csv_path):
        print(f"  SKIP nfem_exchange_rates_monthly_cleaned.csv not found")
        return

    df = pd.read_csv(csv_path)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    inserted = skipped = 0

    for _, row in df.iterrows():
        exists = db.query(models.ExchangeRate).filter(
            models.ExchangeRate.date == row["date"]
        ).first()
        if exists:
            skipped += 1
            continue

        db.add(models.ExchangeRate(
            date              = row["date"],
            avg_closing_rate  = row["avg_closing_rate"],
            avg_weighted_rate = row["avg_weighted_rate"],
            month_end_close   = row["month_end_close"],
            trading_days      = int(row["trading_days"]),
        ))
        inserted += 1

    db.commit()
    print(f"  Exchange rates: {inserted} inserted, {skipped} skipped")


def seed_harvest_calendar(db: Session, name_to_id: dict[str, int]):
    csv_path = os.path.join(DATA_DIR, "harvest_season_calendar.csv")
    if not os.path.exists(csv_path):
        print(f"  SKIP harvest_season_calendar.csv not found")
        return

    df = pd.read_csv(csv_path)
    inserted = skipped = 0

    for _, row in df.iterrows():
        commodity_id = name_to_id.get(row["commodity"])
        if not commodity_id:
            skipped += 1
            continue

        exists = (
            db.query(models.HarvestCalendar)
            .filter(
                models.HarvestCalendar.commodity_id == commodity_id,
                models.HarvestCalendar.month == int(row["month"]),
            )
            .first()
        )
        if exists:
            skipped += 1
            continue

        db.add(models.HarvestCalendar(
            commodity_id     = commodity_id,
            month            = int(row["month"]),
            is_harvest_month = bool(row["is_harvest_month"]),
            is_lean_month    = bool(row["is_lean_month"]),
            harvest_months   = str(row["harvest_months"]),
            lean_months      = str(row["lean_months"]),
            notes            = str(row["notes"]) if pd.notna(row["notes"]) else None,
        ))
        inserted += 1

    db.commit()
    print(f"  Harvest calendar: {inserted} inserted, {skipped} skipped")


def seed_demo_submissions(db: Session, name_to_id: dict[str, int], market_map: dict):
    """
    Seeds realistic price submissions derived from NBS national averages.
    Uses ±10-20% variance to simulate real market variation.
    This ensures the cheapest market finder works on day one.
    """
    import random
    from datetime import datetime, timedelta

    random.seed(42)

    csv_path = os.path.join(DATA_DIR, "nbs_food_prices_cleaned.csv")
    if not os.path.exists(csv_path):
        return

    df = pd.read_csv(csv_path)
    # Use the most recent month only
    latest_date = df["date"].max()
    df_latest = df[df["date"] == latest_date]

    # Markets grouped by city
    lagos_markets   = [(n, c) for (n, c) in market_map if c == "Lagos"]
    abuja_markets   = [(n, c) for (n, c) in market_map if c == "Abuja"]
    ibadan_markets  = [(n, c) for (n, c) in market_map if c == "Ibadan"]
    kano_markets    = [(n, c) for (n, c) in market_map if c == "Kano"]
    ph_markets      = [(n, c) for (n, c) in market_map if c == "Port Harcourt"]

    city_market_groups = {
        "Lagos":         lagos_markets,
        "Abuja":         abuja_markets,
        "Ibadan":        ibadan_markets,
        "Kano":          kano_markets,
        "Port Harcourt": ph_markets,
    }

    count = 0
    now = datetime.utcnow()

    for _, row in df_latest.iterrows():
        commodity_id = name_to_id.get(row["commodity"])
        if not commodity_id:
            continue

        base_price = row["avg_price_ngn"]

        for city, city_markets in city_market_groups.items():
            if not city_markets:
                continue

            for market_key in city_markets:
                market_id = market_map.get(market_key)
                if not market_id:
                    continue

                # Generate 3-5 submissions per market with ±15% variance
                n_subs = random.randint(3, 5)
                for _ in range(n_subs):
                    variance = random.uniform(-0.15, 0.15)
                    price = round(base_price * (1 + variance), 2)
                    # Spread submissions over last 14 days
                    days_ago = random.randint(0, 14)
                    submitted_at = now - timedelta(days=days_ago)

                    db.add(models.PriceSubmission(
                        commodity_id  = commodity_id,
                        market_id     = market_id,
                        price_ngn     = price,
                        quantity_unit = None,
                        submitted_at  = submitted_at,
                        is_flagged    = False,
                    ))
                    count += 1

    db.commit()
    print(f"  Demo submissions: {count} seeded across all markets")


def run():
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        print("\nSeeding data...")
        name_to_id = seed_commodities(db)
        market_map = seed_markets(db)
        seed_nbs_prices(db, name_to_id)
        seed_wb_backfill(db, name_to_id)
        seed_pms_prices(db)
        seed_exchange_rates(db)
        seed_harvest_calendar(db, name_to_id)
        seed_demo_submissions(db, name_to_id, market_map)
        print("\nSeeding complete.")
    except Exception as e:
        db.rollback()
        print(f"\nError during seeding: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
