import requests
import pandas as pd
from datetime import datetime, timedelta

# ============================================================
# CONFIGURATION
# ============================================================

LATITUDE = 55.3422
LONGITUDE = -131.6461

TIMEZONE = "America/Anchorage"

FORECAST_DAYS = 7

OUTPUT_FORECAST = "forecast_history.csv"
OUTPUT_ACCURACY = "forecast_accuracy.csv"

# ============================================================
# OPEN-METEO FORECAST
# ============================================================

def get_forecast():

    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={LATITUDE}"
        f"&longitude={LONGITUDE}"
        f"&daily="
        f"temperature_2m_max,"
        f"temperature_2m_min,"
        f"precipitation_sum,"
        f"precipitation_probability_max"
        f"&hourly=precipitation"
        f"&temperature_unit=fahrenheit"
        f"&precipitation_unit=inch"
        f"&timezone={TIMEZONE}"
        f"&forecast_days={FORECAST_DAYS}"
    )

    response = requests.get(url)

    response.raise_for_status()

    return response.json()


# ============================================================
# CONVERT FORECAST TO DATAFRAME
# ============================================================

def build_forecast_dataframe(data):

    daily = data["daily"]

    forecast_issued = datetime.now().strftime("%Y-%m-%d")

    records = []

    for i, date in enumerate(daily["time"]):

        target_date = datetime.strptime(
            date,
            "%Y-%m-%d"
        )

        issued_date = datetime.strptime(
            forecast_issued,
            "%Y-%m-%d"
        )

        days_ahead = (
            target_date - issued_date
        ).days

        records.append({

            "Forecast_Issued_Date": forecast_issued,

            "Target_Date": date,

            "Days_Ahead": days_ahead,

            "Predicted_MaxTemp_F":
                daily["temperature_2m_max"][i],

            "Predicted_MinTemp_F":
                daily["temperature_2m_min"][i],

            "Predicted_Rain_Inches":
                daily["precipitation_sum"][i],

            "Predicted_Rain_Probability_%":
                daily["precipitation_probability_max"][i]
        })

    return pd.DataFrame(records)


# ============================================================
# GET ACTUAL WEATHER
# ============================================================

def get_actual_weather(start_date, end_date):

    url = (
        "https://archive-api.open-meteo.com/v1/archive"
        f"?latitude={LATITUDE}"
        f"&longitude={LONGITUDE}"
        f"&start_date={start_date}"
        f"&end_date={end_date}"
        f"&daily="
        f"temperature_2m_max,"
        f"temperature_2m_min,"
        f"precipitation_sum"
        f"&temperature_unit=fahrenheit"
        f"&precipitation_unit=inch"
        f"&timezone={TIMEZONE}"
    )

    response = requests.get(url)

    response.raise_for_status()

    data = response.json()

    daily = data["daily"]

    records = []

    for i, date in enumerate(daily["time"]):

        records.append({

            "Target_Date": date,

            "Actual_MaxTemp_F":
                daily["temperature_2m_max"][i],

            "Actual_MinTemp_F":
                daily["temperature_2m_min"][i],

            "Actual_Rain_Inches":
                daily["precipitation_sum"][i]
        })

    return pd.DataFrame(records)


# ============================================================
# COMPARE FORECAST WITH ACTUAL WEATHER
# ============================================================

def compare_forecast_with_actual(
    forecast_df,
    actual_df
):

    df = forecast_df.merge(
        actual_df,
        on="Target_Date",
        how="inner"
    )

    # --------------------------------------------------------
    # Temperature error
    # --------------------------------------------------------

    df["MaxTemp_Error_F"] = (
        df["Predicted_MaxTemp_F"]
        - df["Actual_MaxTemp_F"]
    )

    df["MinTemp_Error_F"] = (
        df["Predicted_MinTemp_F"]
        - df["Actual_MinTemp_F"]
    )

    # --------------------------------------------------------
    # Rain error
    # --------------------------------------------------------

    df["Rain_Error_Inches"] = (
        df["Predicted_Rain_Inches"]
        - df["Actual_Rain_Inches"]
    )

    df["Absolute_Rain_Error_Inches"] = (
        df["Rain_Error_Inches"].abs()
    )

    # --------------------------------------------------------
    # Did we correctly predict rain?
    #
    # Here we define rain as > 0.01 inch
    # --------------------------------------------------------

    rain_threshold = 0.01

    df["Predicted_Rain"] = (
        df["Predicted_Rain_Inches"]
        >= rain_threshold
    )

    df["Actual_Rain"] = (
        df["Actual_Rain_Inches"]
        >= rain_threshold
    )

    df["Rain_Prediction_Correct"] = (
        df["Predicted_Rain"]
        == df["Actual_Rain"]
    )

    return df


# ============================================================
# MAIN
# ============================================================

print("Fetching current forecast...\n")

data = get_forecast()

forecast_df = build_forecast_dataframe(data)

print("\n7-Day Forecast\n")
print(forecast_df.to_string(index=False))

forecast_df.to_csv(
    OUTPUT_FORECAST,
    index=False
)

print(
    f"\nForecast saved to {OUTPUT_FORECAST}"
)