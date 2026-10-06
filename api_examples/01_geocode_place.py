"""
===============================================================================
 01 - GEOCODING:  turn a place name into coordinates
===============================================================================
 API:        Nominatim (OpenStreetMap)
 Key needed: NO
 Cost:       Free
 Docs:       https://nominatim.org/release-docs/latest/api/Search/

 WHAT IT IS FOR
 Users type "Lisbon" or "the Algarve". Almost every other API you will use
 wants numbers: latitude and longitude. Geocoding is the translation step,
 and it is nearly always the FIRST call your bot makes.

 WHERE IT FITS THE ASSIGNMENT
 The brief requires "Location detection via manual input or GPS integration
 to tailor recommendations." This is the manual-input half.

 THE RULES YOU MUST FOLLOW
 Nominatim is run by volunteers and is free to everyone. In exchange:
   * Send a real User-Agent that identifies your app and gives a contact.
   * Maximum ONE request per second. This is enforced.
   * Cache results. A city's coordinates do not change.
 Breaking these gets your IP blocked - and potentially the whole campus.
===============================================================================
"""

import requests

# Identify yourself. Replace this with your own name and email before use.
HEADERS = {
    "User-Agent": "BSBI-EcoTravel-Student/1.0 (coursework; your.name@example.com)"
}


def geocode(place):
    """
    Turn a place name into (latitude, longitude, full_name).

    Returns None if the place could not be found.
    """
    response = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={
            "q": place,        # the search text
            "format": "json",  # ask for JSON rather than HTML
            "limit": 1,        # we only want the best match
        },
        headers=HEADERS,
        timeout=20,
    )
    response.raise_for_status()      # turn HTTP errors into exceptions
    results = response.json()        # a LIST of matches

    if not results:                  # empty list = nothing found
        return None

    best = results[0]
    return float(best["lat"]), float(best["lon"]), best["display_name"]


# -----------------------------------------------------------------------------
# Demo - run this file directly:   python 01_geocode_place.py
# -----------------------------------------------------------------------------
if __name__ == "__main__":

    for place in ["Lisbon, Portugal", "Berlin", "Nowhere-in-Particular-XYZ"]:
        print(f"\nSearching for: {place}")
        try:
            found = geocode(place)
            if found:
                lat, lon, name = found
                print(f"  FOUND: {name}")
                print(f"  lat = {lat},  lon = {lon}")
            else:
                # This is NOT an error. The user simply typed something that
                # does not exist. Your bot must handle it gracefully, not crash.
                print("  NOT FOUND - ask the user to rephrase the place name")
        except requests.exceptions.RequestException as e:
            print(f"  API ERROR: {type(e).__name__} - {e}")

    print("""
    THINK ABOUT THIS
    Nominatim returned ONE result because we set limit=1. Real place names
    are ambiguous - there is a Berlin in Germany and a Berlin in Wisconsin.
    What should your bot do when the user's input is ambiguous? Guess, or
    ask? (Hint: quick-reply buttons exist for exactly this situation.)
    """)
