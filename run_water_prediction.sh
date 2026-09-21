#!/usr/bin/env bash
set -u

cd /home/ibala1206/Design_Work/Eric_olson_Work/water_prediction || exit 1

echo "Running Water Prediction..."
echo

./.venv/bin/python water_prediction.py
status=$?

echo
if [ "$status" -eq 0 ]; then
  echo "Done. Forecast saved to ketchikan_rain_forecast.csv"
else
  echo "Water Prediction exited with an error: $status"
fi

echo
read -r -p "Press Enter to close this window..."
exit "$status"
