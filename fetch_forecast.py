"""Fetch and report Open-Meteo forecast products for three districts."""

import re
from datetime import datetime, timezone
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parent
FORECAST_DIR = ROOT / "forecasts"
TIMEOUT_SECONDS = 60
DAILY_VARIABLES = (
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
)

# These are the same coordinates used by wheat-advisor/fetch_weather.py.
DISTRICTS = {
    "Multan": (30.20, 71.47),
    "Hyderabad": (25.39, 68.37),
    "Larkana": (27.56, 68.21),
}

SEASONAL_URL = "https://seasonal-api.open-meteo.com/v1/seasonal"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


def timestamp():
    """Return a UTC timestamp safe to use in a filename."""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def save_raw_response(path, response):
    """Save the response body exactly as received."""
    path.write_bytes(response.content)


def parse_json(response):
    """Parse JSON for reporting without changing the saved response."""
    try:
        return response.json()
    except ValueError:
        return None


def report_response(district, product, response, payload):
    """Print a small plain-language report for one API response."""
    print(f"\n{district} - {product}")
    print(f"  HTTP status: {response.status_code}")

    if payload is None:
        print("  Error: response was not valid JSON.")
        print(f"  API message: {response.text[:500] or 'empty response'}")
        return

    if not response.ok or "error" in payload:
        print(f"  Error message: {payload.get('reason', payload.get('error'))}")

    daily = payload.get("daily")
    if not isinstance(daily, dict):
        print("  Forecast data: missing daily section or daily section is empty.")
        return

    dates = daily.get("time")
    if isinstance(dates, list) and dates:
        first = dates[0]
        last = dates[-1]
        try:
            first_date = datetime.fromisoformat(first).date()
            last_date = datetime.fromisoformat(last).date()
            retrieval_date = datetime.now(timezone.utc).date()
            ahead = (last_date - retrieval_date).days
            print(f"  Forecast dates: {first_date} through {last_date}")
            print(f"  Last date is about {ahead} days ahead of retrieval.")
        except (TypeError, ValueError):
            print(f"  Forecast dates: {first} through {last}")
    else:
        print("  Forecast dates: missing or empty.")

    units = payload.get("daily_units", {})
    present = []
    missing = []
    empty = []
    for variable in DAILY_VARIABLES:
        values = daily.get(variable)
        if variable not in daily:
            missing.append(variable)
        elif not values:
            empty.append(variable)
        else:
            present.append(variable)
    print(f"  Variables returned: {present or 'none'}")
    print(f"  Variables missing: {missing or 'none'}")
    print(f"  Variables empty: {empty or 'none'}")
    requested_units = {
        variable: units.get(variable, "not provided")
        for variable in DAILY_VARIABLES
    }
    print(f"  Units: {requested_units}")

    ensemble_keys = [
        key
        for key in daily
        if re.search(r"_member\d+$", key)
    ]
    if ensemble_keys:
        member_names = {
            key.rsplit("_", 1)[-1]
            for key in ensemble_keys
        }
        print(f"  Ensemble members returned: {len(member_names)}")
    elif product.endswith("_mean"):
        print("  Ensemble members returned: ensemble mean response (1 aggregate).")
    else:
        print("  Ensemble members returned: not identified in response.")


def fetch_and_save(session, district, coordinates, product, url, params):
    """Fetch one product, save its raw response, and print its report."""
    district_dir = FORECAST_DIR / district
    district_dir.mkdir(parents=True, exist_ok=True)
    file_path = district_dir / f"{product}_{timestamp()}.json"

    try:
        response = session.get(url, params=params, timeout=TIMEOUT_SECONDS)
        save_raw_response(file_path, response)
        payload = parse_json(response)
        report_response(district, product, response, payload)
    except requests.Timeout as error:
        print(f"\n{district} - {product}")
        print(f"  Error: request timed out after {TIMEOUT_SECONDS} seconds: {error}")
        print(f"  Raw response saved: no response was received ({file_path.name})")
    except requests.RequestException as error:
        print(f"\n{district} - {product}")
        print(f"  Error: request failed: {error}")
        print(f"  Raw response saved: no response was received ({file_path.name})")
    except OSError as error:
        print(f"\n{district} - {product}")
        print(f"  Error saving response: {error}")


def main():
    """Fetch seasonal member, seasonal mean, and 15-day products."""
    session = requests.Session()
    retrieval_date = datetime.now(timezone.utc).date().isoformat()
    print(f"Open-Meteo forecast retrieval date (UTC): {retrieval_date}")
    print(f"Requested daily variables: {', '.join(DAILY_VARIABLES)}")

    for district, (latitude, longitude) in DISTRICTS.items():
        common = {
            "latitude": latitude,
            "longitude": longitude,
            "daily": ",".join(DAILY_VARIABLES),
            "timezone": "Asia/Karachi",
            "temperature_unit": "celsius",
            "precipitation_unit": "mm",
            "forecast_days": 217,
        }
        fetch_and_save(
            session,
            district,
            (latitude, longitude),
            "seasonal_seas5_members",
            SEASONAL_URL,
            {**common, "models": "ecmwf_seas5"},
        )
        fetch_and_save(
            session,
            district,
            (latitude, longitude),
            "seasonal_seas5_mean",
            SEASONAL_URL,
            {**common, "models": "ecmwf_seas5_ensemble_mean"},
        )

        forecast_params = {
            "latitude": latitude,
            "longitude": longitude,
            "daily": ",".join(DAILY_VARIABLES),
            "timezone": "Asia/Karachi",
            "temperature_unit": "celsius",
            "precipitation_unit": "mm",
            "forecast_days": 15,
        }
        fetch_and_save(
            session,
            district,
            (latitude, longitude),
            "forecast_15day",
            FORECAST_URL,
            forecast_params,
        )


if __name__ == "__main__":
    main()
