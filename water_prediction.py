import requests
import pandas as pd

# --------------------------------------------------
# DISPLAY SETTINGS
# --------------------------------------------------
# Show ALL dataframe columns and prevent truncation
# --------------------------------------------------

pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', None)

# --------------------------------------------------
# Ketchikan Alaska Coordinates
# --------------------------------------------------

LATITUDE = 55.3422
LONGITUDE = -131.6461

# Forecast days
DAYS = 7

# --------------------------------------------------
# Open-Meteo API URL
# --------------------------------------------------

url = (
    "https://api.open-meteo.com/v1/forecast"
    f"?latitude={LATITUDE}"
    f"&longitude={LONGITUDE}"
    f"&daily=temperature_2m_max,"
    f"temperature_2m_min,"
    f"precipitation_sum,"
    f"precipitation_probability_max"
    f"&hourly=precipitation"
    f"&temperature_unit=fahrenheit"
    f"&precipitation_unit=inch"
    f"&timezone=America/Anchorage"
    f"&forecast_days={DAYS}"
)

print("Fetching weather forecast...\n")

# --------------------------------------------------
# REQUEST WEATHER DATA
# --------------------------------------------------

response = requests.get(url)

if response.status_code != 200:
    print(f"Error: {response.status_code}")
    exit()

data = response.json()

# --------------------------------------------------
# DAILY DATA
# --------------------------------------------------

daily = data["daily"]

# --------------------------------------------------
# HOURLY DATA
# --------------------------------------------------

hourly_times = data["hourly"]["time"]
hourly_rain = data["hourly"]["precipitation"]

# --------------------------------------------------
# COMPUTE ESTIMATED RAIN HOURS
# --------------------------------------------------

rain_hours_per_day = {}

for time_str, rain_amount in zip(hourly_times, hourly_rain):

    # Extract date
    date = time_str.split("T")[0]

    # Initialize counter
    if date not in rain_hours_per_day:
        rain_hours_per_day[date] = 0

    # Count rainy hours
    if rain_amount > 0:
        rain_hours_per_day[date] += 1

# --------------------------------------------------
# BUILD FINAL DATAFRAME
# --------------------------------------------------

records = []

for i in range(len(daily["time"])):

    date = daily["time"][i]

    records.append({
        "Date": date,
        "MaxTemp_F": daily["temperature_2m_max"][i],
        "MinTemp_F": daily["temperature_2m_min"][i],
        "Rain_Inches": daily["precipitation_sum"][i],
        "Rain_Probability_%": daily["precipitation_probability_max"][i],
        "Estimated_Rain_Hours": rain_hours_per_day.get(date, 0)
    })

df = pd.DataFrame(records)

# --------------------------------------------------
# DISPLAY RESULTS
# --------------------------------------------------

print("\nKetchikan Rain Forecast\n")

# Print FULL dataframe without truncation
print(df.to_string(index=False))

# --------------------------------------------------
# SAVE TO CSV
# --------------------------------------------------

output_file = "ketchikan_rain_forecast.csv"

df.to_csv(output_file, index=False)

print(f"\nForecast saved to: {output_file}")