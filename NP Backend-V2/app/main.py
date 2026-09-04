from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import commodities, markets, prices, forecast, budget, map as map_router


app = FastAPI(
    title="Nigerian Food Price Tracker API",
    description="Real-time food price tracking, market comparison, and AI-powered forecasting for Nigerian markets.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(commodities.router)
app.include_router(markets.router)
app.include_router(prices.router)
app.include_router(forecast.router)
app.include_router(budget.router)
app.include_router(map_router.router)


@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "message": "Nigerian Food Price Tracker API is running."}


@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy"}