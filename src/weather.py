from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

import requests
from src.config import OPENWEATHER_API_KEY

BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"


def _call_api(url: str, city: str) -> dict:
    """Call an OpenWeatherMap endpoint and return JSON, or raise ValueError with a clear message."""
    if not OPENWEATHER_API_KEY:
        raise ValueError("OPENWEATHER_API_KEY is missing. Check your .env file.")

    params = {
        "q": city,
        "appid": OPENWEATHER_API_KEY,
        "units": "metric",  # Celsius
    }

    try:
        response = requests.get(url, params=params, timeout=10)
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Network error while contacting weather API: {e}")

    if response.status_code == 404:
        raise ValueError(f"City '{city}' not found. Check the spelling.")
    if response.status_code == 401:
        raise ValueError("Invalid API key (or key not active yet, can take up to 2 hours).")
    if response.status_code != 200:
        raise ValueError(f"Weather API error: {response.status_code} - {response.text}")

    return response.json()


# ---------------------------------------------------------------------------
# Current weather
# ---------------------------------------------------------------------------
def get_weather(city: str) -> dict:
    """Fetch current weather for a city. Returns a clean dict or raises ValueError."""
    data = _call_api(BASE_URL, city)

    # OpenWeatherMap only includes rain/snow keys when it is actually raining/snowing
    rain_1h = data.get("rain", {}).get("1h", 0)

    return {
        "city": data["name"],
        "country": data["sys"]["country"],
        "temperature": data["main"]["temp"],
        "feels_like": data["main"]["feels_like"],
        "humidity": data["main"]["humidity"],
        "pressure": data["main"]["pressure"],
        "wind_speed": data["wind"]["speed"],  # m/s
        "rain_1h": rain_1h,                   # mm
        "clouds": data["clouds"]["all"],      # %
        "description": data["weather"][0]["description"],
    }


def format_weather(w: dict) -> str:
    """Turn the weather dict into plain text. We pass this to the LLM."""
    return (
        f"Location: {w['city']}, {w['country']}\n"
        f"Condition: {w['description']}\n"
        f"Temperature: {w['temperature']}°C (feels like {w['feels_like']}°C)\n"
        f"Humidity: {w['humidity']}%\n"
        f"Wind speed: {w['wind_speed']} m/s\n"
        f"Rain (last 1h): {w['rain_1h']} mm\n"
        f"Cloud cover: {w['clouds']}%\n"
        f"Pressure: {w['pressure']} hPa"
    )


# ---------------------------------------------------------------------------
# Forecast (5 days, 3-hour slots)
# ---------------------------------------------------------------------------
def get_forecast(city: str) -> dict:
    """Fetch the 5-day forecast. Times are converted to the city's LOCAL time."""
    data = _call_api(FORECAST_URL, city)
    tz_offset = data["city"]["timezone"]  # seconds from UTC

    slots = []
    for item in data["list"]:
        local = datetime.fromtimestamp(item["dt"] + tz_offset, tz=timezone.utc)
        slots.append(
            {
                "date": local.date(),
                "time": local.strftime("%H:%M"),
                "temp": item["main"]["temp"],
                "humidity": item["main"]["humidity"],
                "wind_speed": item["wind"]["speed"],
                "rain_3h": item.get("rain", {}).get("3h", 0),
                "pop": item.get("pop", 0),  # chance of rain, 0 to 1
                "description": item["weather"][0]["description"],
            }
        )

    today = (datetime.now(timezone.utc) + timedelta(seconds=tz_offset)).date()

    return {
        "city": data["city"]["name"],
        "country": data["city"]["country"],
        "today": today,
        "slots": slots,
    }


def daily_summary(forecast: dict) -> list[dict]:
    """Group the 3-hour slots by day and summarise each day."""
    by_day = defaultdict(list)
    for s in forecast["slots"]:
        by_day[s["date"]].append(s)

    days = []
    for date in sorted(by_day):
        slots = by_day[date]
        temps = [s["temp"] for s in slots]
        days.append(
            {
                "date": date,
                "weekday": date.strftime("%A"),
                "temp_min": round(min(temps), 1),
                "temp_max": round(max(temps), 1),
                "humidity": round(sum(s["humidity"] for s in slots) / len(slots)),
                "wind_max": round(max(s["wind_speed"] for s in slots), 1),
                "rain_total": round(sum(s["rain_3h"] for s in slots), 1),
                "rain_chance": round(max(s["pop"] for s in slots) * 100),
                "description": Counter(s["description"] for s in slots).most_common(1)[0][0],
            }
        )
    return days


def format_forecast(forecast: dict) -> str:
    """Turn the daily summary into plain text. We will pass this to the LLM."""
    lines = [
        f"Forecast for {forecast['city']}, {forecast['country']} "
        f"(local dates; today is {forecast['today'].strftime('%A')} {forecast['today']}):"
    ]
    for d in daily_summary(forecast):
        lines.append(
            f"- {d['weekday']} {d['date']}: {d['description']}, "
            f"{d['temp_min']} to {d['temp_max']}°C, humidity {d['humidity']}%, "
            f"max wind {d['wind_max']} m/s, rain chance {d['rain_chance']}%, "
            f"rain {d['rain_total']} mm"
        )
    return "\n".join(lines)