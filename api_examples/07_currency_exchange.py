"""
===============================================================================
 07 - CURRENCY EXCHANGE:  convert prices into the user's own currency
===============================================================================
 API:        Frankfurter
 Key needed: NO
 Cost:       Free, no account, no rate limit
 Source:     European Central Bank reference rates
 Docs:       https://frankfurter.dev/

 WHAT IT IS FOR
 The brief requires the bot to gather a BUDGET from the user and rank
 options by price. A user thinking in pounds cannot judge a hotel priced in
 euros. Currency conversion is what makes a budget usable.

 WHY FRANKFURTER
 Most currency APIs want an account and a key, and their free tiers expire
 or get withdrawn - which is exactly what happened to the Amadeus API named
 in your brief. Frankfurter needs no key at all, is open source, and pulls
 from the European Central Bank. That makes it a safe dependency for
 coursework that must still work in October.

 ONE IMPORTANT LIMITATION
 ECB rates are published once per working day, around 16:00 CET. They are
 REFERENCE rates, not the rate you would get at a bureau de change or on a
 card transaction. For travel budgeting that is fine - but say so in your
 report rather than implying live market precision.
===============================================================================
"""

import requests

HEADERS = {
    "User-Agent": "BSBI-EcoTravel-Student/1.0 (coursework; your.name@example.com)"
}

BASE_URL = "https://api.frankfurter.dev/v1"


def get_rate(from_currency, to_currency):
    """
    How many units of to_currency you get for 1 unit of from_currency.

    Currency codes are ISO 4217: EUR, GBP, USD, JPY, PKR...
    """
    response = requests.get(
        f"{BASE_URL}/latest",
        params={"base": from_currency, "symbols": to_currency},
        headers=HEADERS,
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()

    # Response shape:
    #   {"amount":1.0, "base":"EUR", "date":"2026-09-07",
    #    "rates":{"GBP":0.8412}}
    return data["rates"][to_currency], data["date"]


def convert(amount, from_currency, to_currency):
    """Convert an amount. Returns (converted_amount, rate, rate_date)."""
    rate, date = get_rate(from_currency, to_currency)
    return amount * rate, rate, date


def list_currencies():
    """All supported currency codes, as a dict of code -> full name."""
    response = requests.get(f"{BASE_URL}/currencies",
                            headers=HEADERS, timeout=20)
    response.raise_for_status()
    return response.json()


# -----------------------------------------------------------------------------
# Demo:   python 07_currency_exchange.py
# -----------------------------------------------------------------------------
if __name__ == "__main__":

    print("Converting a travel budget...\n")

    try:
        # A student in the UK budgeting for a trip priced in euros
        amount, rate, date = convert(750, "GBP", "EUR")
        print(f"  Budget of GBP 750.00  =  EUR {amount:,.2f}")
        print(f"  (rate 1 GBP = {rate} EUR, ECB reference rate for {date})")

        # And the other direction, for showing a hotel price back to them
        price, rate2, _ = convert(120, "EUR", "GBP")
        print(f"\n  Hotel at EUR 120.00/night  =  GBP {price:,.2f}/night")

        print("\n  A few supported currencies:")
        currencies = list_currencies()
        for code in ["EUR", "GBP", "USD", "JPY", "PKR", "TRY"]:
            if code in currencies:
                print(f"    {code}  {currencies[code]}")
        print(f"\n  {len(currencies)} currencies available in total.")

    except requests.exceptions.RequestException as e:
        print(f"  API ERROR: {type(e).__name__} - {e}")
    except KeyError as e:
        # Asking for a currency that does not exist raises this.
        print(f"  Unknown currency code: {e}")

    print("""
    THINK ABOUT THIS
    Where should the conversion happen in your bot?

      (a) Convert every price the moment you retrieve it, or
      (b) Store prices in their original currency and convert only when
          displaying to the user?

    Option (b) is almost always right. Currency is a PRESENTATION concern -
    your ranking and scoring logic should work on one consistent currency
    internally. Mixing conversion into your scoring function makes it
    impossible to test, because the answers change daily.

    That separation - data, logic, presentation - is a design principle you
    can point to explicitly in your report.
    """)
