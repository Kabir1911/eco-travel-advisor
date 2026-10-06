"""
===============================================================================
 02 - ACCOMMODATION:  find hotels near a location
===============================================================================
 API:        Overpass (queries the OpenStreetMap database)
 Key needed: NO
 Cost:       Free
 Docs:       https://wiki.openstreetmap.org/wiki/Overpass_API

 WHAT IT IS FOR
 OpenStreetMap is a free world map that anyone can edit. Overpass is the
 query engine that lets you ask it questions like "what hotels are within
 3 km of this point?"

 WHY YOU ARE USING THIS
 The assignment brief names the Amadeus API for hotel data. That API was
 DECOMMISSIONED on 17 July 2026 - the portal is gone and keys are disabled.
 Overpass is the free replacement.

 THE QUERY LANGUAGE (Overpass QL)
     [out:json][timeout:45];                     <- give me JSON, allow 45s
     node["tourism"="hotel"](around:3000,LAT,LON);  <- hotels within 3000 m
     out body 15;                                <- return 15, with their tags

 A "node" is a single point. A "way" is a line or shape (a building). Big
 hotels are often mapped as ways, not nodes - see the note at the bottom.

 IMPORTANT LIMITATION - READ THIS
 OpenStreetMap has NO reliable eco-certification data. A few hotels carry a
 "green_key" or "ecolabel" tag; most carry nothing at all. When this was
 tested on Lisbon, ZERO of 15 hotels had any eco tag. You must decide,
 honestly, what your bot says about sustainability when it does not know.
===============================================================================
"""

import requests

HEADERS = {
    "User-Agent": "BSBI-EcoTravel-Student/1.0 (coursework; your.name@example.com)"
}

OVERPASS_URL = "https://overpass-api.de/api/interpreter"


def find_hotels(lat, lon, radius_m=3000, limit=15):
    """
    Find hotels near a point. Returns a list of dictionaries.

    radius_m : how far to search, in metres
    limit    : how many results to ask for
    """
    query = f"""
    [out:json][timeout:45];
    node["tourism"="hotel"](around:{radius_m},{lat},{lon});
    out body {limit};
    """

    response = requests.post(
        OVERPASS_URL,
        data={"data": query},      # the query goes in a form field called "data"
        headers=HEADERS,
        timeout=60,
    )
    response.raise_for_status()

    hotels = []
    for element in response.json().get("elements", []):
        tags = element.get("tags", {})

        # Skip anything without a name - useless to show a user
        if not tags.get("name"):
            continue

        hotels.append({
            "name":   tags["name"],
            "stars":  tags.get("stars"),                  # often missing
            "eco":    tags.get("green_key")               # usually missing
                      or tags.get("ecolabel"),
            "lat":    element.get("lat"),
            "lon":    element.get("lon"),
        })
    return hotels


# -----------------------------------------------------------------------------
# Demo:   python 02_find_hotels.py
# -----------------------------------------------------------------------------
if __name__ == "__main__":

    LISBON_LAT, LISBON_LON = 38.7223, -9.1393

    print("Searching for hotels near Lisbon city centre...")
    try:
        hotels = find_hotels(LISBON_LAT, LISBON_LON)
    except requests.exceptions.RequestException as e:
        # Overpass is a shared free service. 504 Gateway Timeout is COMMON.
        # It does not mean the API is dead - it means the server is busy or
        # your query was too expensive. See 09_reliability_and_caching.py
        print(f"  API ERROR: {type(e).__name__} - {e}")
        print("  Try again in a moment, or narrow the search radius.")
        raise SystemExit

    print(f"\nFound {len(hotels)} named hotels:\n")
    eco_count = 0
    for h in hotels:
        stars = h["stars"] or "-"
        eco = h["eco"] or "-"
        if h["eco"]:
            eco_count += 1
        print(f"  {h['name'][:40]:42s} stars={stars:3s} eco={eco}")

    print(f"\n  Of {len(hotels)} hotels, {eco_count} carry an eco-certification tag.")
    print("""
    THINK ABOUT THIS - THIS IS THE INTERESTING PART
    Your bot is supposed to recommend "eco-certified accommodation", but the
    data almost never says whether a hotel is certified. You have choices:

      (a) Say nothing about sustainability you cannot evidence.
      (b) Use PROXY indicators - near public transport, no car park, small -
          and tell the user plainly that these are proxies, not certification.
      (c) Find and cite a real certification source.

    What you must NOT do is present unverified hotels as "eco-certified".
    That is greenwashing, and the brief specifically asks you to consider it.

    ALSO: this query only searches "node" objects. Large hotels are often
    mapped as "way" objects (building outlines) instead. Try changing
    node -> nwr and adding "out center" to see how many more you find.
    """)
