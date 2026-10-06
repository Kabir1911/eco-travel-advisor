# Eco-Travel APIs — a working tutorial

Eight small Python files, one API each. Plain Python — **no Rasa** — so you
can see each API clearly before wiring it into a custom action.

You already know how to call an API from a Rasa action (`action_get_weather`).
This set is about *which* APIs to use and *what to ask them*.

## Setup

```powershell
python -m pip install requests
```

Then run any file on its own:

```powershell
python 01_geocode_place.py
```

Each one prints real results and ends with a **THINK ABOUT THIS** section.
Those questions are not decoration — they are the design decisions the
assignment is actually marking.

## The files

| File | API | Key? | What it gives you |
|---|---|---|---|
| `01_geocode_place.py` | Nominatim | no | Place name → latitude/longitude |
| `02_find_hotels.py` | Overpass | no | Hotels near a point |
| `03_find_transport.py` | Overpass | no | Stations, metro, tram stops |
| `04_find_attractions.py` | Overpass | no | Museums, castles, monuments |
| `05_place_description.py` | Wikipedia | no | What a place actually *is* |
| `06_weather_forecast.py` | Open-Meteo | no | Current + 3-day forecast |
| `07_currency_exchange.py` | Frankfurter | no | Convert prices to the user's currency |
| `08_carbon_estimate.py` | Climatiq / local table | optional | kg CO2e per transport mode |

**Seven of the eight need no API key at all.** Only Climatiq requires signup,
and its free tier is 2,500 calls/month with no credit card.

## Suggested order

Run `01` first — everything else needs coordinates. Then `02`, `03`, `04` in
any order; they are all Overpass and share a query style. `05` makes results
readable, `06`–`08` add the reasoning layer.

---

## Why not Amadeus, as the brief says?

The **Amadeus for Developers self-service API was decommissioned on
17 July 2026**. New registrations were paused in March and existing API keys
were disabled on that date. The Enterprise portal continues but requires a
commercial contract.

The brief was issued on 18 June 2026 — between the announcement and the
shutdown — so it was accurate when written. It is not now.

These APIs are the replacement. Check with your tutor before assuming a
substitute is acceptable.

---

## Three things that will bite you

**1. Overpass is free and shared, and it will time out.**
`504 Gateway Timeout` does not mean the API is dead. It means the server is
busy, or your query cost too much. Ask for the smallest thing that answers
your question: a tighter radius, fewer tag types, a lower result cap.

**2. Do not call Overpass live from a conversation turn.**
Retries can take 30 seconds. Your brief requires responses "under three
seconds for critical interactions." Fetch the data ahead of time with a
separate script, save it to JSON or SQLite, and have the bot read that.
Weather and currency are fine to call live; map data is not.

**3. Identify yourself.**
Nominatim and Overpass are volunteer-funded and their usage policies require
a real `User-Agent` with a contact address. Nominatim enforces one request
per second. Twenty students hammering these services from one campus network
with the default `python-requests` agent is a good way to get everyone
blocked. Edit the `HEADERS` line in each file before you run it.

---

## The gap you will have to think about

Run `02_find_hotels.py` and look at the last line of output.

When this was tested on central Lisbon, **zero of fifteen hotels carried any
eco-certification tag**. OpenStreetMap simply does not hold that data
reliably.

Your brief asks you to recommend "eco-certified accommodation". The data
mostly cannot tell you which hotels are certified. That is a real problem,
not a bug in the exercise, and how you handle it is assessable:

- Say nothing about sustainability you cannot evidence
- Use proxy indicators — near transit, no car park, small scale — and state
  plainly that they are proxies
- Find and cite a genuine certification source
- Narrow your bot's scope to what the data supports

What you must not do is present unverified hotels as eco-certified. The
brief specifically asks you to consider **greenwashing** under its ethics
requirements. This is that question, made concrete.
