from google import genai
from app.config import get_settings

settings = get_settings()

# Varied templates to avoid every explanation sounding identical
_UP_TEMPLATES = [
    lambda c, pct, price, reason: (
        f"{c} is heading up — expect prices around ₦{price:,.0f} to climb roughly {pct:.0f}% by next month, "
        f"mainly because {reason}. Stock up now if you buy it regularly."
    ),
    lambda c, pct, price, reason: (
        f"Prices for {c} are likely to go up about {pct:.0f}% next month as {reason}. "
        f"If you can, buy what you need this week at the current ₦{price:,.0f}."
    ),
    lambda c, pct, price, reason: (
        f"Expect to pay more for {c} next month — roughly {pct:.0f}% more, because {reason}. "
        f"Buying ahead now at ₦{price:,.0f} makes sense."
    ),
]

_DOWN_TEMPLATES = [
    lambda c, pct, price, reason: (
        f"{c} prices should ease by about {pct:.0f}% next month as {reason}. "
        f"No need to rush — hold off a week or two and you'll likely find a better deal than today's ₦{price:,.0f}."
    ),
    lambda c, pct, price, reason: (
        f"Good news for {c} buyers — prices are expected to fall around {pct:.0f}% next month because {reason}. "
        f"Wait before restocking if you can."
    ),
    lambda c, pct, price, reason: (
        f"With {reason}, {c} prices are set to drop about {pct:.0f}% from the current ₦{price:,.0f}. "
        f"You can afford to wait a few weeks."
    ),
]

_STABLE_TEMPLATES = [
    lambda c, price: (
        f"{c} prices are holding steady around ₦{price:,.0f} and should stay that way next month. "
        f"Buy whenever it suits you — no urgency either way."
    ),
    lambda c, price: (
        f"No major moves expected for {c} next month — prices should stay close to ₦{price:,.0f}. "
        f"Buy at your usual time."
    ),
    lambda c, price: (
        f"{c} looks stable going into next month, hovering near ₦{price:,.0f}. "
        f"There's no particular reason to rush or delay your purchase."
    ),
]

# Reason phrases per dominant driver, used both by the rule-based fallback
# and given to the LLM as the thing it should actually anchor its explanation on
_UP_REASONS = {
    "lean_season": "lean season is approaching and supply is tightening",
    "fuel_cost": "rising fuel prices are pushing up transport costs",
    "exchange_rate": "the naira has been weakening, and this item relies on imports",
    "seasonal_demand": "demand typically rises this time of year",
}

_DOWN_REASONS = {
    "harvest_season": "harvest season is bringing more supply into the market",
    "fuel_cost": "falling fuel prices are easing transport costs",
    "exchange_rate": "the naira has been strengthening, and this item relies on imports",
    "seasonal_demand": "supply typically improves this time of year",
}


def determine_dominant_driver(components: dict, is_harvest: bool, is_lean: bool) -> str:
    """
    Picks whichever signal contributed the most to the forecast, by
    absolute magnitude. Harvest/lean season is reported under its own
    driver name (rather than the generic "harvest_adjustment") since
    that's the more useful label for a shopper-facing explanation.
    """
    seasonal = abs(components.get("seasonal_signal", 0.0))
    harvest  = abs(components.get("harvest_adjustment", 0.0))
    fuel     = abs(components.get("fuel_adjustment", 0.0))
    fx       = abs(components.get("fx_adjustment", 0.0))

    magnitudes = {
        "seasonal_demand": seasonal,
        "fuel_cost": fuel,
        "exchange_rate": fx,
    }
    # harvest/lean adjustment only "wins" as a driver if it's actually active this month
    if is_harvest:
        magnitudes["harvest_season"] = harvest
    elif is_lean:
        magnitudes["lean_season"] = harvest  # harvest_adjustment holds the lean-month value too

    return max(magnitudes, key=magnitudes.get)


def get_forecast_explanation(
    commodity: str,
    current_price: float,
    forecast_pct: float,
    direction: str,
    confidence: float,
    buying_advice: str,
    is_harvest: bool,
    is_lean: bool,
    fuel_trend: str,
    fx_trend: str,
    dominant_driver: str,
) -> str:
    if not settings.gemini_api_key:
        return _rule_based_explanation(
            commodity, current_price, forecast_pct, direction, is_harvest, is_lean, dominant_driver
        )

    direction_text = (
        f"increase by about {abs(forecast_pct):.1f}%" if direction == "up"
        else f"decrease by about {abs(forecast_pct):.1f}%" if direction == "down"
        else "remain relatively stable"
    )

    season_context = ""
    if is_harvest:
        season_context = "This period is a harvest season for this commodity."
    elif is_lean:
        season_context = "This period is a lean/off-season for this commodity."

    driver_labels = {
        "seasonal_demand": "typical seasonal demand patterns",
        "harvest_season": "harvest season bringing more supply",
        "lean_season": "lean season limiting supply",
        "fuel_cost": "changes in fuel/transport costs",
        "exchange_rate": "movements in the exchange rate (this item relies on imports)",
    }
    driver_text = driver_labels.get(dominant_driver, "overall market conditions")

    prompt = f"""You are helping an average Nigerian market shopper understand a food price forecast.

Commodity: {commodity}
Current average price: ₦{current_price:,.0f}
Forecast: prices are expected to {direction_text} next month
Main driver behind this forecast: {driver_text}
Confidence in forecast: {confidence:.0f}%
Recommended action: {"Buy now before prices rise" if buying_advice == "buy_now" else "Wait, prices are expected to fall" if buying_advice == "wait" else "Prices are stable, no rush"}
{season_context}
Fuel price trend: {fuel_trend}
Exchange rate trend: {fx_trend}

Write exactly 2 short, friendly sentences explaining this forecast. Use simple everyday language.
Mention the commodity name, ground the explanation in the main driver above, and be specific about what the shopper should do.
Do not use technical terms like "MoM", "seasonal signal", or "FX".
Do not start with "I" or use robotic phrases."""

    try:
        client = genai.Client(api_key=settings.gemini_api_key)
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt,
        )
        return response.text.strip()
    except Exception:
        return _rule_based_explanation(
        commodity, current_price, forecast_pct, direction, is_harvest, is_lean, dominant_driver
    )


def _rule_based_explanation(
    commodity: str,
    current_price: float,
    forecast_pct: float,
    direction: str,
    is_harvest: bool,
    is_lean: bool,
    dominant_driver: str,
) -> str:
    import hashlib
    # Use commodity name to consistently pick the same template per commodity
    # so it doesn't rotate on every request, but different commodities get different phrasing
    idx = int(hashlib.md5(commodity.encode()).hexdigest(), 16) % 3

    if direction == "up":
        reason = _UP_REASONS.get(dominant_driver, "supply is expected to tighten next month")
        return _UP_TEMPLATES[idx](commodity, abs(forecast_pct), current_price, reason)
    elif direction == "down":
        reason = _DOWN_REASONS.get(dominant_driver, "market supply is improving")
        return _DOWN_TEMPLATES[idx](commodity, abs(forecast_pct), current_price, reason)
    else:
        return _STABLE_TEMPLATES[idx](commodity, current_price)
