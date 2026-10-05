"""
Ketchikan Rain Forecast
------------------------
Fetches a multi-day weather forecast (temperature, precipitation, and
estimated rainy hours) for a fixed location near Ketchikan/Saxman, AK,
using the Open-Meteo API, then saves the results to a dated CSV file.
"""

import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

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

# A day only triggers an alert when BOTH thresholds are exceeded
MIN_RAIN_PROBABILITY = 50      # percent
MIN_RAIN_INCHES = 0.01        # inches

# Tanks below this water level (percent) get a rain warning
LOW_WATER_PERCENT = 15

# Project that holds the PostgreSQL connection code (reports_query.py)
TANKQUERY_DIR = (Path.home() / "Design_Work/Cheeyoong_Work/CheeYoong_Everything"
                 / "tankquery_nonAWS_Test_db")

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


def get_rain_alert_days(df: pd.DataFrame) -> pd.DataFrame:
    """Return the days that exceed both the probability and rainfall thresholds."""
    return df[
        (df["Rain_Probability_%"] > MIN_RAIN_PROBABILITY)
        & (df["Rain_Inches"] > MIN_RAIN_INCHES)
    ]


def print_rain_alerts(df: pd.DataFrame) -> None:
    """Print a warning for each day that exceeds both the probability and rainfall thresholds."""
    print("\nRain Probability Alerts\n")

    alerts = get_rain_alert_days(df)

    if alerts.empty:
        print(f"No days with rain probability above {MIN_RAIN_PROBABILITY}% "
              f"and rainfall above {MIN_RAIN_INCHES} in.")
        return

    for _, row in alerts.iterrows():
        print(f"It will likely rain on {row['Date']} "
              f"(Rain Probability: {row['Rain_Probability_%']}%, "
              f"Expected Rain: {row['Rain_Inches']:.3f} in)")


def fetch_low_water_users(threshold: float = LOW_WATER_PERCENT) -> pd.DataFrame:
    """Return users with at least one tank below `threshold` percent full (one row per user)."""
    # Reuse the existing connection code from the tankquery project
    sys.path.insert(0, str(TANKQUERY_DIR))
    from reports_query import DB_CONFIG, Database

    query = """
        select distinct on (u.user_id)
            u.user_id,
            u.first_name as user_name
        from users u
        join houses h on h.user_id = u.user_id
        join water_tanks wt on wt.house_id = h.house_id
        where ((wt.current_water_amount / nullif(wt.tank_capacity, 0)) * 100) < %s
        order by u.user_id
    """

    db = Database()
    db.connect(DB_CONFIG)
    try:
        return db.read_df(query, [Decimal(str(threshold))])
    finally:
        db.close()


def print_low_water_rain_warnings(df: pd.DataFrame) -> None:
    """Print a rain warning for every user whose tank is below the low-water threshold."""
    print(f"\nLow Water Rain Warnings (tanks below {LOW_WATER_PERCENT}%)\n")

    try:
        users = fetch_low_water_users()
    except Exception as exc:
        print(f"Error querying database: {exc}")
        return

    if users.empty:
        print(f"No tanks below {LOW_WATER_PERCENT}% water level")
        return

    alerts = get_rain_alert_days(df)

    if alerts.empty:
        print(f"{len(users)} user(s) below {LOW_WATER_PERCENT}%, but no rain is "
              f"forecast above the alert thresholds.")
        return

    for _, user in users.iterrows():
        for _, row in alerts.iterrows():
            print(f"{user['user_name']}, it will likely rain on {row['Date']} "
                  f"(Rain Probability: {row['Rain_Probability_%']}%, "
                  f"Expected Rain: {row['Rain_Inches']:.3f} in)")


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

    print_low_water_rain_warnings(df)


if __name__ == "__main__":
    main()