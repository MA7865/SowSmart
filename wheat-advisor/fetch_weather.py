
import time
from pathlib import Path

import pandas as pd
import requests

BASE_DIR = Path(__file__).resolve().parent
CACHE_DIR = BASE_DIR / "cache"
CACHE_DIR.mkdir(exist_ok=True)

API_URL = "https://archive-api.open-meteo.com/v1/archive"

DISTRICTS = {
    "Faisalabad": (31.42, 73.08),
    "Multan": (30.20, 71.47),
    "Bahawalpur": (29.40, 71.68),
    "Rahim Yar Khan": (28.42, 70.30),
    "Sargodha": (32.08, 72.67),
    "Sahiwal": (30.67, 73.11),
    "Larkana": (27.56, 68.21),
    "Hyderabad": (25.39, 68.37),
}

START_DATE = "2000-01-01"
END_DATE = "2025-12-31"

session = requests.Session()

for name, (lat, lon) in DISTRICTS.items():
    filename = name.replace(" ", "_") + ".csv"
    path = CACHE_DIR / filename

    # Reuse an existing complete file.
    if path.exists():
        try:
            existing = pd.read_csv(path)
            if (
                len(existing) >= 9400
                and {"time", "temperature_2m_max",
                     "temperature_2m_min", "precipitation_sum"}
                .issubset(existing.columns)
            ):
                print(f"Already downloaded: {name}")
                continue
        except Exception:
            pass

    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": START_DATE,
        "end_date": END_DATE,
        "daily": (
            "temperature_2m_max,"
            "temperature_2m_min,"
            "precipitation_sum"
        ),
        "timezone": "Asia/Karachi",
    }

    success = False

    for attempt in range(5):
        try:
            print(
                f"Downloading {name} "
                f"(attempt {attempt + 1}/5)..."
            )

            response = session.get(
                API_URL,
                params=params,
                timeout=120,
            )
            response.raise_for_status()
            payload = response.json()

            if "daily" not in payload:
                raise ValueError(
                    f"No daily data returned: {payload}"
                )

            df = pd.DataFrame(payload["daily"])

            required = [
                "time",
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_sum",
            ]

            if not set(required).issubset(df.columns):
                raise ValueError(
                    f"Missing columns: {df.columns.tolist()}"
                )

            df = df[required].copy()
            df["time"] = pd.to_datetime(df["time"])
            df = df.sort_values("time").drop_duplicates("time")

            # Save only after a successful response.
            df.to_csv(path, index=False)

            print(
                f"Saved {name}: {len(df)} rows "
                f"({df['time'].min().date()} to "
                f"{df['time'].max().date()})"
            )

            success = True
            break

        except Exception as exc:
            print(f"Error for {name}: {exc}")

            if attempt < 4:
                wait = 15 * (attempt + 1)
                print(f"Retrying in {wait} seconds...")
                time.sleep(wait)

    if not success:
        print(f"FAILED: {name}. You can retry this later.")

    time.sleep(2)

print("\nWeather download process finished.")
print("Check the cache folder for all eight CSV files.")
