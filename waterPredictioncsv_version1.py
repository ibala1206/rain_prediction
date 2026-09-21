"""
Ketchikan Rain Forecast
------------------------
Fetches a multi-day weather forecast (temperature, precipitation, and
estimated rainy hours) for a fixed location near Ketchikan/Saxman, AK,
using the Open-Meteo API, then saves the results to a dated CSV file.
"""

from datetime import datetime

import pandas as pd
import requests
from geopy.geocoders import Nominatim

# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

# Home address to geocode into latitude/longitude
ADDRESS = "283 ICEHOUSE LANE, Ketchikan, AK"

# Number of forecast days to request
FORECAST_DAYS = 7

# Open-Meteo endpoint
API_URL = "https://api.open-meteo.com/v1/forecast"

# Pandas display settings (so the console printout isn't truncated)
pd.set_option("display.max_columns", None)
pd.set_option("display.width", None)
pd.set_option("display.max_colwidth", None)


# --------------------------------------------------
# FUNCTIONS
# --------------------------------------------------

def geocode_address(address: str) -> tuple[float, float]:
    """Convert a street address into (latitude, longitude) using Nominatim."""
    geolocator = Nominatim(user_agent="my_app")
    location = geolocator.geocode(address)

    if location is None:
        raise ValueError(f"Could not geocode address: {address}")

    return location.latitude, location.longitude


def fetch_forecast(latitude: float, longitude: float, days: int) -> dict:
    """Request daily + hourly forecast data from Open-Meteo and return the parsed JSON."""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": (
            "temperature_2m_max,"
            "temperature_2m_min,"
            "precipitation_sum,"
            "precipitation_probability_max"
        ),
        "hourly": "precipitation",
        "temperature_unit": "fahrenheit",
        "precipitation_unit": "inch",
        "timezone": "America/Anchorage",
        "forecast_days": days,
    }

    response = requests.get(API_URL, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def count_rain_hours_per_day(hourly_times: list, hourly_rain: list) -> dict:
    """Return a mapping of date -> number of hours with measurable precipitation."""
    rain_hours_per_day: dict = {}

    for time_str, rain_amount in zip(hourly_times, hourly_rain):
        date = time_str.split("T")[0]
        rain_hours_per_day.setdefault(date, 0)

        if rain_amount and rain_amount > 0:
            rain_hours_per_day[date] += 1

    return rain_hours_per_day


def build_forecast_dataframe(data: dict) -> pd.DataFrame:
    """Combine the daily forecast with estimated rainy-hour counts into a DataFrame."""
    daily = data["daily"]
    hourly_times = data["hourly"]["time"]
    hourly_rain = data["hourly"]["precipitation"]

    rain_hours_per_day = count_rain_hours_per_day(hourly_times, hourly_rain)

    records = []
    for i, date in enumerate(daily["time"]):
        records.append({
            "Date": date,
            "MaxTemp_F": daily["temperature_2m_max"][i],
            "MinTemp_F": daily["temperature_2m_min"][i],
            "Rain_Inches": daily["precipitation_sum"][i],
            "Rain_Probability_%": daily["precipitation_probability_max"][i],
            "Estimated_Rain_Hours": rain_hours_per_day.get(date, 0),
        })

    return pd.DataFrame(records)


def print_rain_alerts(df: pd.DataFrame) -> None:
    """Print a warning for each day with a rain probability above 50%."""
    print("\nRain Probability Alerts\n")

    alerts = df[df["Rain_Probability_%"] > 50]

    if alerts.empty:
        print("No days with rain probability above 50%.")
        return

    for _, row in alerts.iterrows():
        print(f"It will likely rain on {row['Date']} "
              f"(Rain Probability: {row['Rain_Probability_%']}%)")



def save_forecast_csv(df: pd.DataFrame, prefix: str = "ketchikan_rain_forecast") -> str:
    """Save the DataFrame to a CSV file named with today's date, and return the filename."""
    current_date = datetime.now().strftime("%Y-%m-%d")
    output_file = f"{prefix}_{current_date}.csv"
    df.to_csv(output_file, index=False)
    return output_file


def main() -> None:
    print(f"Geocoding address: {ADDRESS}")

    try:
        latitude, longitude = geocode_address(ADDRESS)
    except ValueError as exc:
        print(f"Error: {exc}")
        return

    print(f"Coordinates: {latitude}, {longitude}\n")
    print("Fetching weather forecast...\n")

    try:
        data = fetch_forecast(latitude, longitude, FORECAST_DAYS)
    except requests.RequestException as exc:
        print(f"Error fetching forecast: {exc}")
        return

    df = build_forecast_dataframe(data)

    print_rain_alerts(df)


    print("\nKetchikan Rain Forecast\n")
    print(df.to_string(index=False))

    output_file = save_forecast_csv(df)
    print(f"\nForecast saved to: {output_file}")


if __name__ == "__main__":
    main()