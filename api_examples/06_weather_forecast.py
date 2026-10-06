"""
===============================================================================
 06 - WEATHER:  current conditions and forecast for a destination
===============================================================================
 API:        Open-Meteo
 Key needed: NO
 Cost:       Free for non-commercial use
 Docs:       https://open-meteo.com/en/docs

 WHAT IT IS FOR
 Weather shapes travel advice. "Cycle between the villages" is good advice
 in June and poor advice in a February storm. It also feeds sustainability
 reasoning - a mild forecast makes walking and cycling realistic.

 WHY YOU ALREADY KNOW THIS ONE
 This is the same API used by action_get_weather in the course companion
 bot. You have seen it work inside Rasa. Here it is on its own, so you can
 see the API clearly without the Rasa scaffolding around it.

 A GOOD API TO LEARN FROM
 Open-Meteo is unusually well designed: no key, no signup, generous limits,
 and you select exactly the fields you want. Compare that to APIs that make
 you register, wait for approval, and then return everything whether you
 asked for it or not. When you evaluate APIs in your report, this is a
 useful benchmark.
===============================================================================
"""

import requests

HEADERS = {
    "User-Agent": "BSBI-EcoTravel-Student/1.0 (coursework; your.name@example.com)"
}


def get_weather(lat, lon):
    """
    Current conditions plus a 3-day outlook for a coordinate.

    Note how "current" and "daily" are COMMA-SEPARATED LISTS of the fields
    you want. Ask only for what you need - it keeps responses small and
    makes your intent obvious to anyone reading the code.
    """
    response = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude":  lat,
            "longitude": lon,
            "current":   "temperature_2m,precipitation,wind_speed_10m",
            "daily":     "temperature_2m_max,precipitation_sum",
            "forecast_days": 3,
            "timezone":  "auto",     # return times in the destination's zone
        },
        headers=HEADERS,
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def travel_advice(temp_c, rain_mm):
    """
    Turn numbers into advice. This is the bit that makes it a BOT rather
    than a weather widget.
    """
    if rain_mm > 5:
        return "wet - plan indoor activities, and public transport over cycling"
    if temp_c < 5:
        return "cold - walking tours will be hard going"
    if temp_c > 30:
        return "hot - cycling and long walks are unwise in the middle of the day"
    return "good conditions for walking and cycling"


# -----------------------------------------------------------------------------
# Demo:   python 06_weather_forecast.py
# -----------------------------------------------------------------------------
if __name__ == "__main__":

    LISBON_LAT, LISBON_LON = 38.7223, -9.1393

    print("Fetching weather for Lisbon...")
    try:
        data = get_weather(LISBON_LAT, LISBON_LON)
    except requests.exceptions.RequestException as e:
        print(f"  API ERROR: {type(e).__name__} - {e}")
        raise SystemExit

    current = data["current"]
    print(f"\n  Right now: {current['temperature_2m']} C, "
          f"{current['precipitation']} mm rain, "
          f"wind {current['wind_speed_10m']} km/h")

    print("\n  Next 3 days:")
    daily = data["daily"]
    for i, date in enumerate(daily["time"]):
        tmax = daily["temperature_2m_max"][i]
        rain = daily["precipitation_sum"][i]
        print(f"    {date}   max {tmax:5.1f} C   rain {rain:5.1f} mm   "
              f"-> {travel_advice(tmax, rain)}")

    print("""
    THINK ABOUT THIS
    Notice that the API gave you numbers, and travel_advice() turned them
    into a recommendation. That function is where YOUR judgement lives -
    the API has none.

    The same is true of the sustainability scoring you have to build. The
    APIs give you carbon figures, prices and locations. Deciding how to
    weigh them against each other is your design work, and it is the part
    the marking criteria actually reward.
    """)
