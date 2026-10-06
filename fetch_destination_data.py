"""Fetch destination data ahead of chat.

Adapted from the lecturer's Eco-Travel API tutorial.
Prices, availability and eco-certification are not verified here.
"""

import importlib.util
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv


PROJECT_DIR = Path(__file__).resolve().parent
EXAMPLES_DIR = PROJECT_DIR / "api_examples"
CACHE_DIR = PROJECT_DIR / "cache_data"
CACHE_FILE = CACHE_DIR / "berlin.json"

load_dotenv(PROJECT_DIR / ".env")

user_agent = os.getenv("OSM_USER_AGENT", "").strip()
if not user_agent or "example.com" in user_agent:
    raise SystemExit("Set your real OSM_USER_AGENT in the root .env file.")

CACHE_DIR.mkdir(exist_ok=True)


def load_example(filename):
    path = EXAMPLES_DIR / filename
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.HEADERS = {"User-Agent": user_agent}
    return module


def save_cache(data):
    temporary = CACHE_FILE.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(CACHE_FILE)


def fetch_section(data, name, source, function):
    existing = data["sections"].get(name, {})
    if existing.get("status") == "ok":
        print(f"{name}: using saved data")
        return existing["data"]

    # Keep requests sequential and avoid rapid calls to shared services.
    time.sleep(1.1)

    try:
        result = function()
        if result is None:
            raise ValueError("No matching result returned")

        data["sections"][name] = {
            "status": "ok",
            "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
            "source": source,
            "data": result,
        }
        print(f"{name}: saved successfully")

    except Exception as error:
        # Save partial progress; rerunning retries only failed sections.
        data["sections"][name] = {
            "status": "error",
            "attempted_at_utc": datetime.now(timezone.utc).isoformat(),
            "source": source,
            "error_type": type(error).__name__,
        }
        print(f"{name}: unavailable ({type(error).__name__})")
        result = None

    save_cache(data)
    return result


def main():
    if CACHE_FILE.exists():
        data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    else:
        data = {
            "schema_version": 1,
            "destination": "Berlin",
            "country": "Germany",
            "data_mode": "cached_external_data",
            "attribution": {
                "map": "© OpenStreetMap contributors",
                "map_url": "https://www.openstreetmap.org/copyright",
            },
            "limitations": [
                "A limited sample around the geocoded city centre.",
                "No live prices, booking availability or timetables.",
                "Map eco tags are unverified, not proof of certification.",
                "Station counts do not establish service quality.",
            ],
            "sections": {},
        }

    # Migrate older caches to the map-only destination guide.
    data.get("sections", {}).pop("description", None)
    data.get("attribution", {}).pop("description", None)
    save_cache(data)

    geocoder = load_example("01_geocode_place.py")
    hotels = load_example("02_find_hotels.py")
    transport = load_example("03_find_transport.py")
    attractions = load_example("04_find_attractions.py")

    location = fetch_section(
        data,
        "location",
        "Nominatim / OpenStreetMap",
        lambda: geocoder.geocode("Berlin, Germany"),
    )

    if location is None:
        print("Location lookup failed. Run this script again later.")
        return

    latitude, longitude, full_name = location
    print(f"Location: {full_name}")

    fetch_section(
        data,
        "hotels",
        "Overpass / OpenStreetMap",
        lambda: hotels.find_hotels(
            latitude, longitude, radius_m=2000, limit=10
        ),
    )

    fetch_section(
        data,
        "transport_stops",
        "Overpass / OpenStreetMap",
        lambda: transport.find_transport(
            latitude, longitude, radius_m=1000
        ),
    )

    fetch_section(
        data,
        "attractions",
        "Overpass / OpenStreetMap",
        lambda: attractions.find_attractions(
            latitude, longitude, radius_m=2000, limit=8
        ),
    )

    print(f"\nCache saved to: {CACHE_FILE}")
    print("No hotel prices or certification claims have been added.")


if __name__ == "__main__":
    main()