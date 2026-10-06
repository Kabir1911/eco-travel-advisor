"""
===============================================================================
 03 - PUBLIC TRANSPORT:  find low-carbon transport options near a location
===============================================================================
 API:        Overpass (OpenStreetMap)
 Key needed: NO
 Cost:       Free

 WHAT IT IS FOR
 Public transport availability is one of the strongest signals of whether a
 destination can be visited sustainably. A hotel next to a metro station is
 a genuinely different proposition from one that requires a hire car.

 WHERE IT FITS THE ASSIGNMENT
 The brief requires "public transportation schedules" and "Location-based
 updates (e.g. carbon emissions data or availability of public transport)".

 NOTE ON SCHEDULES
 OpenStreetMap gives you the LOCATION of stops and stations. It does NOT
 give you live timetables. Real-time schedules need a transit API, and most
 are city-specific. For this assignment, "is there good public transport
 here?" is a question you can answer well; "when is the next tram?" is not.
 Knowing the difference, and saying so in your report, is worth marks.

 A LESSON IN QUERY COST
 The first version of this query also asked for every bus stop within 1 km.
 Overpass returned 504 Gateway Timeout - the query was too expensive. Bus
 stops are dense and low-value. Stations and tram stops tell you far more
 for a fraction of the work.

 Rule: ask for the smallest thing that answers your question.
===============================================================================
"""

import requests

HEADERS = {
    "User-Agent": "BSBI-EcoTravel-Student/1.0 (coursework; your.name@example.com)"
}

OVERPASS_URL = "https://overpass-api.de/api/interpreter"


def find_transport(lat, lon, radius_m=1500):
    """
    Find rail, metro and tram access points near a location.

    Returns a list of dicts, and a summary count by type.
    """
    # The parentheses group several searches into ONE union query.
    query = f"""
    [out:json][timeout:45];
    (
      node["railway"="station"](around:{radius_m},{lat},{lon});
      node["railway"="subway_entrance"](around:{radius_m},{lat},{lon});
      node["railway"="tram_stop"](around:{radius_m},{lat},{lon});
    );
    out body 25;
    """

    response = requests.post(OVERPASS_URL, data={"data": query},
                             headers=HEADERS, timeout=60)
    response.raise_for_status()

    stops = []
    for element in response.json().get("elements", []):
        tags = element.get("tags", {})
        stops.append({
            "name": tags.get("name", "(unnamed)"),
            "type": tags.get("railway", "unknown"),
            "lat":  element.get("lat"),
            "lon":  element.get("lon"),
        })
    return stops


def summarise(stops):
    """Count how many of each type - useful for a one-line bot response."""
    counts = {}
    for s in stops:
        counts[s["type"]] = counts.get(s["type"], 0) + 1
    return counts


# -----------------------------------------------------------------------------
# Demo:   python 03_find_transport.py
# -----------------------------------------------------------------------------
if __name__ == "__main__":

    LISBON_LAT, LISBON_LON = 38.7223, -9.1393

    print("Searching for public transport near Lisbon city centre...")
    try:
        stops = find_transport(LISBON_LAT, LISBON_LON)
    except requests.exceptions.RequestException as e:
        print(f"  API ERROR: {type(e).__name__} - {e}")
        raise SystemExit

    counts = summarise(stops)
    print(f"\nFound {len(stops)} transport access points within 1.5 km:")
    for kind, n in counts.items():
        print(f"  {kind:20s} {n}")

    print("\nFirst few:")
    for s in stops[:6]:
        print(f"  - {s['name'][:40]:42s} ({s['type']})")

    # Turning raw data into something a bot can SAY is the real skill.
    if len(stops) >= 10:
        verdict = "excellent - you will not need a car"
    elif len(stops) >= 3:
        verdict = "reasonable, but check routes for your specific trip"
    else:
        verdict = "limited - factor transport emissions into your planning"

    print(f"\n  Bot-friendly summary: public transport here is {verdict}.")

    print("""
    THINK ABOUT THIS
    You have turned 25 map points into one sentence. That is the job.
    A user does not want a list of tram stops; they want to know whether
    they can manage without a car.

    What threshold did I pick, and why? I chose 10 and 3 arbitrarily. Can
    you justify better ones? Should the thresholds change for a rural
    destination versus a capital city? Defend your choice in your report -
    that reasoning is what Level 7 marking looks for.
    """)
