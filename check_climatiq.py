import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"), override=True)
api_key = os.getenv("CLIMATIQ_API_KEY")

if not api_key:
    print("Key missing.")
    raise SystemExit(1)

payload = {
    "emission_factor": {
        "id": "f8812229-02f6-8116-8162-ac40e1389a7b"
    },
    "parameters": {
        "passengers": 1,
        "distance": 100,
        "distance_unit": "km",
    },
}

try:
    response = requests.post(
        "https://api.climatiq.io/data/v1/estimate",
        headers={"Authorization": f"Bearer {api_key}"},
        json=payload,
        timeout=20,
    )

    print("HTTP status:", response.status_code)

    if response.status_code == 200:
        result = response.json()
        print("Test: 1 passenger travelling 100 km by train")
        print("Estimated emissions:", result.get("co2e"))
        print("Unit:", result.get("co2e_unit"), "CO2e")
        print("Factor: Germany / ADEME / 2020")
    else:
        print("Estimate failed. Share the HTTP status.")

except requests.exceptions.RequestException:
    print("Connection failed. Please try again.")