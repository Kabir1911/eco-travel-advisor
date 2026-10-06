"""
===============================================================================
 05 - PLACE DESCRIPTIONS:  turn a name into something the bot can SAY
===============================================================================
 API:        Wikipedia REST API
 Key needed: NO
 Cost:       Free
 Docs:       https://en.wikipedia.org/api/rest_v1/

 WHAT IT IS FOR
 OpenStreetMap gives you names and coordinates. It does not tell you what a
 place actually IS or why anyone would visit. Wikipedia does.

 This is the difference between a bot that says:

     "Nearby: Belem Tower, Jeronimos Monastery, Museu Nacional do Azulejo"

 and one that says:

     "Belem Tower is a 16th-century fortification that served as the
      ceremonial gateway to Lisbon. It is a UNESCO World Heritage site."

 The second is a recommendation. The first is a list.

 WHERE IT FITS THE ASSIGNMENT
 The brief's non-functional requirements ask for "clear conversational
 language" and "minimal cognitive load". Raw data dumps fail both.

 A WORD OF CAUTION
 Wikipedia titles are not the same as OpenStreetMap names. "Belem Tower"
 works; "Torre de Belem" may redirect or fail. Real systems match names
 fuzzily or store the Wikipedia title alongside the place. OSM sometimes
 has a "wikipedia" tag which gives you the exact title - look for it.
===============================================================================
"""

import requests
import urllib.parse

HEADERS = {
    "User-Agent": "BSBI-EcoTravel-Student/1.0 (coursework; your.name@example.com)"
}


def describe(title, sentences=2):
    """
    Get a short description of a place from Wikipedia.

    Returns None if there is no article with that title.
    """
    # Page titles go in the URL path, so they must be URL-encoded.
    # "Belem Tower" -> "Belem%20Tower"
    safe_title = urllib.parse.quote(title.replace(" ", "_"))

    response = requests.get(
        f"https://en.wikipedia.org/api/rest_v1/page/summary/{safe_title}",
        headers=HEADERS,
        timeout=20,
    )

    if response.status_code == 404:      # no such article - not an error
        return None
    response.raise_for_status()

    data = response.json()

    # "extract" is the plain-text summary. Trim it to a couple of sentences
    # so the bot does not read out three paragraphs.
    text = data.get("extract", "")
    parts = text.split(". ")
    short = ". ".join(parts[:sentences])
    if short and not short.endswith("."):
        short += "."

    return {
        "title":       data.get("title"),
        "description": data.get("description"),   # one-line, e.g. "Tower in Lisbon"
        "summary":     short,
        "url":         data.get("content_urls", {}).get("desktop", {}).get("page"),
    }


# -----------------------------------------------------------------------------
# Demo:   python 05_place_description.py
# -----------------------------------------------------------------------------
if __name__ == "__main__":

    for name in ["Belem Tower", "Jeronimos Monastery", "Nonexistent Place XYZ123"]:
        print(f"\nLooking up: {name}")
        try:
            info = describe(name)
        except requests.exceptions.RequestException as e:
            print(f"  API ERROR: {type(e).__name__} - {e}")
            continue

        if info is None:
            # Handle this properly. Your bot should still work when a place
            # has no Wikipedia article - most small places do not.
            print("  No article found. Bot should fall back to the plain name.")
            continue

        print(f"  {info['title']} - {info['description']}")
        print(f"  {info['summary']}")
        print(f"  {info['url']}")

    print("""
    THINK ABOUT THIS
    Attribution matters. Wikipedia content is CC BY-SA licensed - if your
    bot repeats it, you should say where it came from and link the article.
    That is both an ethical and a referencing requirement, and the brief
    asks for Harvard referencing throughout.

    Also: notice how the third lookup failed cleanly rather than crashing.
    Every API call in your bot needs that. A chatbot that raises an
    exception mid-conversation just goes silent, and the user has no idea
    why.
    """)
