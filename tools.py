import os
from datetime import datetime
from xml.sax.saxutils import escape

import requests
from langchain.tools import tool
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

WEATHER_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Fog", 51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain",
    71: "Light snow", 73: "Snow", 75: "Heavy snow",
    80: "Rain showers", 81: "Rain showers", 82: "Heavy rain showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Thunderstorm with hail",
}


def _find_city(city: str):
    """Turns a city name into latitude/longitude using Open-Meteo's free geocoding."""
    r = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": city, "count": 1},
        timeout=10,
    )
    results = r.json().get("results")
    if not results:
        return None
    return results[0]


@tool
def get_weather(city: str) -> str:
    '''Gets the current live weather for a given city: temperature in Celsius,
    feels-like temperature, condition, humidity, and wind speed.'''
    place = _find_city(city)
    if not place:
        return f"Could not find a city named {city}."

    r = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "current": "temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,weather_code",
            "timezone": "auto",
        },
        timeout=10,
    )
    cur = r.json()["current"]
    condition = WEATHER_CODES.get(cur["weather_code"], "Unknown")
    return (
        f"Current weather in {place['name']}, {place.get('country', '')}: "
        f"{condition}, {cur['temperature_2m']}°C "
        f"(feels like {cur['apparent_temperature']}°C), "
        f"humidity {cur['relative_humidity_2m']}%, wind {cur['wind_speed_10m']} km/h."
    )


@tool
def get_forecast(city: str, days: int = 3) -> str:
    '''Gets the weather forecast for a given city for up to 7 days:
    high and low temperature, condition, and chance of rain for each day.'''
    days = max(1, min(days, 7))
    place = _find_city(city)
    if not place:
        return f"Could not find a city named {city}."

    r = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "forecast_days": days,
            "timezone": "auto",
        },
        timeout=10,
    )
    d = r.json()["daily"]
    lines = [f"{days}-day forecast for {place['name']}, {place.get('country', '')}:"]
    for i in range(days):
        lines.append(
            f"- {d['time'][i]}: {WEATHER_CODES.get(d['weather_code'][i], 'Unknown')}, "
            f"high {d['temperature_2m_max'][i]}°C, low {d['temperature_2m_min'][i]}°C, "
            f"rain chance {d['precipitation_probability_max'][i]}%"
        )
    return "\n".join(lines)


@tool
def get_hourly_outlook(city: str, hours: int = 12) -> str:
    '''Gets the hour-by-hour outlook for a city for the next few hours (max 48):
    temperature, rain probability, rainfall, wind gusts, thunderstorm energy (CAPE)
    and weather condition. Use this to predict rain and storms.'''
    hours = max(1, min(hours, 48))
    place = _find_city(city)
    if not place:
        return f"Could not find a city named {city}."

    r = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "hourly": "temperature_2m,precipitation_probability,precipitation,"
                      "wind_gusts_10m,cape,weather_code",
            "forecast_hours": hours,
            "timezone": "auto",
        },
        timeout=10,
    )
    h = r.json()["hourly"]
    lines = [f"Next {hours} hours for {place['name']}, {place.get('country', '')}:"]
    for i in range(len(h["time"])):
        code = h["weather_code"][i]
        cape = h["cape"][i] or 0
        gust = h["wind_gusts_10m"][i] or 0
        rain_p = h["precipitation_probability"][i] or 0

        if code >= 95:
            risk = "HIGH (thunderstorm forecast)"
        elif cape > 1000 and (gust > 50 or rain_p > 60):
            risk = "MODERATE"
        elif gust > 60:
            risk = "MODERATE (strong winds)"
        else:
            risk = "LOW"

        lines.append(
            f"- {h['time'][i]}: {WEATHER_CODES.get(code, 'Unknown')}, "
            f"{h['temperature_2m'][i]}°C, rain chance {rain_p}%, "
            f"rain {h['precipitation'][i]} mm, gusts {gust} km/h, "
            f"CAPE {cape}, storm risk {risk}"
        )
    return "\n".join(lines)


@tool
def save_pdf_report(city: str, report_text: str) -> str:
    '''Saves a finished weather analysis as a PDF file for news feeds.
    Pass the city name and the full report as plain text.
    Returns the file path of the saved PDF.'''
    os.makedirs("reports", exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"reports/{city.replace(' ', '_')}_{stamp}.pdf"

    styles = getSampleStyleSheet()
    story = [
        Paragraph(f"Weather Analysis: {escape(city)}", styles["Title"]),
        Paragraph(datetime.now().strftime("Generated on %d %B %Y, %H:%M"), styles["Normal"]),
        Spacer(1, 16),
    ]
    for block in report_text.split("\n"):
        if block.strip():
            story.append(Paragraph(escape(block), styles["BodyText"]))
            story.append(Spacer(1, 6))

    SimpleDocTemplate(path, pagesize=A4).build(story)
    return f"PDF saved at {path}"