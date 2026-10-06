"""
===============================================================================
 08 - CARBON FOOTPRINT:  estimate emissions per transport mode
===============================================================================
 API:        Climatiq  (optional - needs a free key)
 Fallback:   A local emission-factor table (no key, no network)
 Key needed: Only for Climatiq
 Cost:       Climatiq free tier = 2,500 calls/month, no credit card
 Docs:       https://www.climatiq.io/docs

 WHAT IT IS FOR
 This is the heart of the assignment. The brief requires the bot to
 "Calculate and present approximate carbon footprints for travel options to
 guide decision-making."

 TWO WAYS TO DO IT

 1. CLIMATIQ - a real API with proper emission factors, versioned data and
    a defensible methodology. Named in your brief, still alive, free tier
    is ample for coursework. Requires signing up for a key.

 2. A LOCAL FACTOR TABLE - a dictionary of grams of CO2e per passenger-km.
    No key, no network, no failure modes. Perfectly acceptable for this
    assignment PROVIDED you cite where the numbers came from and state
    plainly that they are averages.

 Which should you use? Either. But you must be able to JUSTIFY the choice
 in your report, and you must be honest about precision. A bot that reports
 "156.25 kg CO2e" from a rounded average is implying an accuracy it does
 not have. "About 150 kg" is more honest and more useful.
===============================================================================
"""

import requests

# -----------------------------------------------------------------------------
# OPTION 2 FIRST - the no-key approach
# -----------------------------------------------------------------------------
# Indicative grams of CO2e per passenger-kilometre.
#
# THESE NUMBERS ARE ROUNDED FOR TEACHING. Before using them in a submission,
# replace them with figures from a citable source and reference it properly:
#   * UK DESNZ / DEFRA greenhouse gas conversion factors (published annually)
#   * European Environment Agency transport emission data
#
# Note how much the mode matters - that contrast is the whole point of the
# bot. A coach is roughly ten times better per kilometre than a short flight.
EMISSION_FACTORS = {        # gCO2e per passenger-km
    "walk":           0,
    "cycle":          0,
    "train":         35,
    "coach":         27,
    "electric_car":  50,    # depends heavily on the local electricity grid
    "car_petrol":   170,    # assumes one occupant; halves with two
    "ferry":        115,
    "flight_short": 250,    # short-haul is worse per km - takeoff dominates
    "flight_long":  150,
}


def estimate_carbon_kg(mode, distance_km):
    """
    Rough carbon estimate in kg CO2e. No API, no key, never fails.

    Raises KeyError for an unknown mode - handle that in your bot.
    """
    grams = EMISSION_FACTORS[mode] * distance_km
    return grams / 1000.0


def compare_modes(distance_km, modes=None):
    """Rank transport modes best-first for a given journey."""
    modes = modes or ["train", "coach", "car_petrol", "flight_short"]
    results = [(m, estimate_carbon_kg(m, distance_km)) for m in modes]
    return sorted(results, key=lambda pair: pair[1])


# -----------------------------------------------------------------------------
# OPTION 1 - Climatiq, if you have a key
# -----------------------------------------------------------------------------
CLIMATIQ_KEY = ""       # <- paste your free key here to enable this


def estimate_carbon_climatiq(distance_km, activity_id=None):
    """
    Ask Climatiq for a carbon estimate. Returns kg CO2e.

    Climatiq identifies each emission factor by an "activity_id" string.
    You browse them in their data explorer. The one below is a generic
    passenger car - there are thousands of others, by country and year.
    """
    if not CLIMATIQ_KEY:
        raise RuntimeError("No Climatiq key set - see CLIMATIQ_KEY above")

    activity_id = activity_id or (
        "passenger_vehicle-vehicle_type_car-fuel_source_na"
        "-engine_size_na-vehicle_age_na-vehicle_weight_na"
    )

    response = requests.post(
        "https://api.climatiq.io/data/v1/estimate",
        headers={"Authorization": f"Bearer {CLIMATIQ_KEY}"},
        json={
            "emission_factor": {"activity_id": activity_id,
                                "data_version": "^6"},
            "parameters": {"distance": distance_km, "distance_unit": "km"},
        },
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    return data["co2e"], data["co2e_unit"]


# -----------------------------------------------------------------------------
# Demo:   python 08_carbon_estimate.py
# -----------------------------------------------------------------------------
if __name__ == "__main__":

    DISTANCE = 625      # Lisbon to Madrid, roughly

    print(f"Journey: Lisbon to Madrid, about {DISTANCE} km\n")
    print("  Using the local factor table (no key needed):\n")

    for mode, kg in compare_modes(DISTANCE):
        bar = "#" * int(kg / 5)
        print(f"    {mode:14s} {kg:6.1f} kg CO2e  {bar}")

    best, best_kg = compare_modes(DISTANCE)[0]
    worst, worst_kg = compare_modes(DISTANCE)[-1]
    times = worst_kg / best_kg if best_kg else 0
    print(f"\n    Taking the {best} instead of the {worst} "
          f"cuts emissions by about {times:.0f}x.")

    print("\n  Climatiq:")
    if CLIMATIQ_KEY:
        try:
            value, unit = estimate_carbon_climatiq(DISTANCE)
            print(f"    {value} {unit} by car over {DISTANCE} km")
        except Exception as e:
            print(f"    ERROR: {type(e).__name__} - {e}")
    else:
        print("    SKIPPED - sign up free at climatiq.io and set CLIMATIQ_KEY")

    print("""
    THINK ABOUT THIS

    1. PRECISION AND HONESTY
       The table says a coach emits 16.9 kg for this trip. Do you believe
       that to three significant figures? Neither do I. How should your bot
       present a rough estimate without implying false precision?

    2. THE ASSUMPTIONS ARE INVISIBLE
       car_petrol assumes ONE occupant. With four people it is better per
       person than the train. Does your bot ask how many are travelling?
       Should it?

    3. THIS IS WHERE YOUR SCORING FUNCTION LIVES
       Carbon is one number. Price is another. User preference is a third.
       Combining them into a single ranking is YOUR design decision - the
       brief deliberately does not tell you how. Document your weighting
       and defend it. That reasoning is worth more marks than the code.
    """)
