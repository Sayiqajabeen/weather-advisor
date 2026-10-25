import requests
from src.config import OPENWEATHER_API_KEY

BASE_URL = "https://api.openweathermap.org/data/2.5/weather"


def get_weather(city: str) -> dict:
    """Fetch current weather for a city. Returns a clean dict or raises ValueError."""
    if not OPENWEATHER_API_KEY:
        raise ValueError("OPENWEATHER_API_KEY is missing. Check your .env file.")

    params = {
        "q": city,
        "appid": OPENWEATHER_API_KEY,
        "units": "metric",  # Celsius
    }

    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Network error while contacting weather API: {e}")

    if response.status_code == 404:
        raise ValueError(f"City '{city}' not found. Check the spelling.")
    if response.status_code == 401:
        raise ValueError("Invalid API key (or key not active yet, can take up to 2 hours).")
    if response.status_code != 200:
        raise ValueError(f"Weather API error: {response.status_code} - {response.text}")

    data = response.json()

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
    """Turn the weather dict into plain text. We will pass this to the LLM later."""
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