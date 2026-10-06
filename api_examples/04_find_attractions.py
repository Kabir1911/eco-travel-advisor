"""
===============================================================================
 04 - CULTURAL EXPERIENCES:  museums, monuments and attractions
===============================================================================
 API:        Overpass (OpenStreetMap)
 Key needed: NO
 Cost:       Free

 WHAT IT IS FOR
 The brief asks for "local cultural experiences that support communities".
 OpenStreetMap knows where museums, castles, monuments and attractions are.

 A LESSON IN QUERY DESIGN - THIS IS THE POINT OF THIS FILE
 The first version of this query used a bare  node["historic"]  which matches
 ANY historic tag. The results were things like:

     Arco Escuro                (sally_port)
     Pelourinho de Lisboa       (attraction)
     Sao Joao Bosco             (memorial)
     Doutor Sousa Martins       (memorial)

 Technically correct. Useless to a traveller. Nobody plans a trip around a
 sally port or a street memorial.

 TWO FIXES, both used below:
   1. Constrain "historic" to values a visitor would actually go to.
   2. Use "nwr" instead of "node".  nwr = node + way + relation.
      Museums and castles are usually mapped as WAYS (building outlines),
      so a node-only query silently misses most of them. "out center" then
      gives each shape a representative coordinate.

 Same API, same city, wildly different usefulness. Query design IS part of
 the engineering, and it is assessable.
===============================================================================
"""

import requests

HEADERS = {
    "User-Agent": "BSBI-EcoTravel-Student/1.0 (coursework; your.name@example.com)"
}

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Only historic things a tourist would visit. Add or remove as you see fit -
# and be ready to justify your list.
VISITABLE_HISTORIC = "castle|monument|ruins|fort|archaeological_site|city_gate"


def find_attractions(lat, lon, radius_m=1500, limit=12):
    """Find museums and visit-worthy historic sites near a location."""
    query = f"""
    [out:json][timeout:45];
    (
      nwr["tourism"="museum"](around:{radius_m},{lat},{lon});
      nwr["historic"~"^({VISITABLE_HISTORIC})$"](around:{radius_m},{lat},{lon});
    );
    out center {limit};
    """

    response = requests.post(OVERPASS_URL, data={"data": query},
                             headers=HEADERS, timeout=60)
    response.raise_for_status()

    sites = []
    for element in response.json().get("elements", []):
        tags = element.get("tags", {})
        if not tags.get("name"):
            continue

        # A node has lat/lon directly. A way or relation has a "center"
        # because "out center" asked for one. Handle both.
        lat_val = element.get("lat") or element.get("center", {}).get("lat")
        lon_val = element.get("lon") or element.get("center", {}).get("lon")

        sites.append({
            "name": tags["name"],
            "kind": tags.get("tourism") or tags.get("historic"),
            "type": element.get("type"),      # node / way / relation
            "lat":  lat_val,
            "lon":  lon_val,
        })
    return sites


# -----------------------------------------------------------------------------
# Demo:   python 04_find_attractions.py
# -----------------------------------------------------------------------------
if __name__ == "__main__":

    LISBON_LAT, LISBON_LON = 38.7223, -9.1393

    print("Searching for cultural sites near Lisbon city centre...")
    try:
        sites = find_attractions(LISBON_LAT, LISBON_LON)
    except requests.exceptions.RequestException as e:
        print(f"  API ERROR: {type(e).__name__} - {e}")
        raise SystemExit

    print(f"\nFound {len(sites)} named cultural sites:\n")
    for s in sites:
        print(f"  {s['name'][:45]:47s} {s['kind']:20s} [{s['type']}]")

    ways = sum(1 for s in sites if s["type"] != "node")
    print(f"\n  {ways} of {len(sites)} were ways or relations, NOT nodes.")
    print("  A node-only query would have missed those entirely.")

    print("""
    TRY THIS
    Change  nwr  back to  node  and re-run. Count how many results you lose.
    Then change the historic filter back to a bare ["historic"] and look at
    the quality of what comes back.

    Both changes are one word. Both dramatically change whether your bot is
    useful. This is what "technical implementation quality" means in the
    marking criteria - not just whether the code runs.
    """)
