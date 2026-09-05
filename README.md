# NaijaPrice

AI-powered food price intelligence for Nigerian markets — crowd-sourced, market-level
prices cross-checked against official NBS data, with month-ahead forecasts explained
in plain language.

Built for Nigeria's Next AI Talent Competition (Tobams Group × Access Bank).

---

## What it does

NaijaPrice closes the gap between two things that exist separately but never
together: real prices at real markets (which nobody publishes), and historical price
patterns (which NBS publishes, but only monthly and only nationally). It combines
both, plus AI, to answer two questions shoppers actually have — *"what does this
actually cost near me right now?"* and *"should I buy now or wait?"*

**Live scope:** 42 commodities · 25 markets · 7 cities (Lagos, Abuja, Ibadan, Kano,
Port Harcourt, Enugu, Benin City)

### Features

- **Price submission & crowd verification** — anonymous submissions, verified once a
  market/commodity pair has 3+ valid reports in 30 days. Automatic duplicate
  rejection, statistical outlier flagging, and submission-burst detection.
- **Market Explorer** — list and interactive map views (Leaflet, keyless Esri dark
  tiles) of all markets, with an optional live price overlay per commodity.
- **Price forecasting** — a trained LightGBM model for 9 commodities with deep
  (2007–2026) history, a transparent rule-based engine for the other 33. Every
  forecast names its dominant driver (seasonal demand, harvest/lean season, fuel
  cost, or exchange rate) and comes with a plain-language AI explanation.
- **Anomaly detection** — statistical (z-score) flagging of unusual month-over-month
  price swings, surfaced on the Trends page and as a caution flag on forecasts.
- **Budget Planner** — give it a budget and a shopping list, get back the cheapest
  way to buy it all, market by market.
- **Model performance page** — public, honest backtest numbers (model vs. baseline
  MAPE), not just an accuracy claim.

---

## Tech stack

| Layer | Stack |
|---|---|
| Backend | FastAPI, SQLAlchemy, PostgreSQL, Alembic |
| Forecasting | LightGBM / scikit-learn (trained model) + rule-based engine |
| AI explanations | Gemini |
| Frontend | React, TypeScript, Vite, TanStack Router, Tailwind v4 |
| Charts / Map | Recharts, react-leaflet (Esri Dark Gray Canvas tiles — no API key) |
| Database hosting | Neon (Postgres) |
| Backend hosting | Render |

---

## Project structure

```
NP Backend-V2/
├── app/
│   ├── main.py              # FastAPI app, router registration, CORS
│   ├── config.py            # Settings (reads .env)
│   ├── database.py          # Engine, session, declarative Base
│   ├── models.py            # All SQLAlchemy models
│   ├── schemas.py           # Pydantic request/response schemas
│   ├── routers/              # commodities, markets, prices, forecast, budget, map
│   ├── services/             # trust_score, spam_detection, anomaly_detection,
│   │                         #   ai_explainer, budget_optimizer, map_data,
│   │                         #   forecast_engine, ml_forecast_engine
│   └── ml/                   # forecast_model.joblib, model_performance.json
├── alembic/                  # Migration environment and versions/
├── seed/
│   └── seeder.py             # Seeds commodities, markets, NBS history, demo data
├── data/                     # Source CSVs (NBS, World Bank RTFP, fuel, FX, harvest)
├── requirements.txt
├── alembic.ini
└── .env.example

NP Frontend/
├── src/
│   ├── main.tsx / router.tsx
│   ├── lib/                  # api.ts (backend client), utils.ts, city-context.tsx
│   ├── components/           # Layout, ui, Skeleton, MarketMap
│   └── pages/                 # Dashboard, CommodityDetail, Markets, Trends,
│                               #   SubmitPrice, BudgetPlanner, ModelPerformance
├── public/                   # favicon/logo
├── package.json
└── .env.example
```

---

## Getting started — Backend

```bash
cd "NP Backend-V2"
python -m venv venv
# Windows: venv\Scripts\Activate.ps1   |   macOS/Linux: source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env — see Environment Variables below

alembic upgrade head        # apply the database schema
python -m seed.seeder       # seed commodities, markets, history, and demo data

uvicorn app.main:app --reload
```

API docs available at `http://localhost:8000/docs` once running.

## Getting started — Frontend

```bash
cd "NP Frontend"
npm install

cp .env.example .env
# set VITE_API_URL=http://localhost:8000

npm run dev
```

---

## Environment variables

**Backend (`.env`)**

| Variable | Required | Notes |
|---|---|---|
| `DATABASE_URL` | yes | Postgres connection string (Neon in production) |
| `GEMINI_API_KEY` | no | Powers AI-written forecast explanations; falls back to template-based explanations if unset or the call fails |
| `APP_ENV` | no | `development` or `production` |
| `DATA_DIR` | no | Defaults to `./data` — where seeder CSVs live |

**Frontend (`.env`)**

| Variable | Required | Notes |
|---|---|---|
| `VITE_API_URL` | yes | Backend base URL — `http://localhost:8000` locally, your Render URL in production |

---

## Database & migrations

Schema changes go through Alembic — `Base.metadata.create_all()` is **not** used at
runtime, so a model change with no migration will not reach the database.

```bash
# after changing app/models.py
alembic revision --autogenerate -m "describe the change"
# review the generated file in alembic/versions/ before applying
alembic upgrade head
```

Commit the generated migration file alongside the model change. Migrations are
applied automatically on deploy (see below) — never by hand against production.

---

## API overview

| Router | Prefix | Covers |
|---|---|---|
| Commodities | `/commodities` | List/get commodities |
| Markets | `/markets` | List markets, optionally by city |
| Prices | `/prices` | Submit, compare, trends, latest, anomalies |
| Forecast | `/forecast` | Per-commodity and batch forecasts, model performance |
| Budget | `/budget` | Budget shopping optimizer |
| Map | `/map` | Market pins, optionally with a commodity price overlay |

Full interactive schema at `/docs` (Swagger) or `/redoc`.

---

## Deployment

- **Database:** Neon (Postgres).
- **Backend:** Render, start command runs migrations before the server boots:
  ```
  alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
  ```
- **Frontend:** built as a static bundle (`npm run build`) and can be hosted
  anywhere that serves static files, pointed at the Render backend URL via
  `VITE_API_URL`.

---



