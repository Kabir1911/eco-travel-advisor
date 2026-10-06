import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"), override=True)
api_key = os.getenv("CLIMATIQ_API_KEY")

if not api_key:
    print("Key missing.")
    raise SystemExit(1)

options = [
    {
        "mode": "Train",
        "factor_id": "5e49b19a-3258-8acd-9cfb-0aee76804cbe",
        "distance_km": 550,
        "assumption": "Electric national long-distance train.",
    },
    {
        "mode": "Coach",
        "factor_id": "44338391-77cd-8415-b1a8-250e38d5b013",
        "distance_km": 570,
        "assumption": "General bus factor used as a coach approximation.",
    },
    {
        "mode": "Flight",
        "factor_id": "b0b6e1e2-a18c-8079-a0ac-7045cb520faf",
        "distance_km": 430,
        "assumption": "Domestic flight including RF effect.",
    },
]

for option in options:
    print(f"\nMODE: {option['mode']}")
    print("Assumption:", option["assumption"])

    try:
        response = requests.post(
            "https://api.climatiq.io/data/v1/estimate",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "emission_factor": {
                    "id": option["factor_id"]
                },
                "parameters": {
                    "passengers": 1,
                    "distance": option["distance_km"],
                    "distance_unit": "km",
                },
            },
            timeout=20,
        )

        print("HTTP status:", response.status_code)

        if response.status_code == 200:
            result = response.json()
            print("Distance:", option["distance_km"], "km one-way")
            print("Emissions:", result.get("co2e"))
            print("Unit:", result.get("co2e_unit"), "CO2e")
        else:
            print("Calculation failed; no estimate available.")

    except requests.exceptions.RequestException:
        print("Connection failed; no estimate available.")

print("\nAll distances are illustrative mock-route inputs.")
print("Reference factors: Germany / UBA / 2024.")