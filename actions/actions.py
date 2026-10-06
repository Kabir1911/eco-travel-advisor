import math
import os
import re
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Text

import requests
from dotenv import load_dotenv
from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher


# Load the .env file from the main project folder.
PROJECT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_DIR / ".env", override=True)

TRAIN_FACTOR_ID = "f8812229-02f6-8116-8162-ac40e1389a7b"


class ActionTravelAdvice(Action):
    def name(self) -> Text:
        return "action_travel_advice"

    def run(self, dispatcher, tracker, domain) -> List[Dict[Text, Any]]:
        destination = tracker.get_slot("destination")
        preference = tracker.get_slot("sustainability_preference")

        if not destination:
            dispatcher.utter_message(
                text="Which city would you like to visit?"
            )
            return []

        advice_by_preference = {
            "lowest environmental impact": (
                "Compare rail and coach options where available. "
                "Look for accommodation with independently verified "
                "environmental certification."
            ),
            "balance of cost and sustainability": (
                "Compare the price and emissions of available transport. "
                "Consider accommodation near public transport to reduce "
                "the need for taxi journeys."
            ),
            "lowest price": (
                "Compare total transport and accommodation costs, "
                "including baggage and transfers. Check whether local "
                "public transport passes suit your itinerary."
            ),
        }

        advice = advice_by_preference.get(preference)

        if advice is None:
            dispatcher.utter_message(
                text=(
                    "What matters most: the lowest environmental impact, "
                    "a balance of cost and sustainability, or the lowest price?"
                )
            )
            return []

        dispatcher.utter_message(
            text=(
                f"Planning advice for your trip to {destination}:\n"
                f"{advice}\n\n"
                "This is general guidance, not a live availability "
                "or price check.\n\n"
                "To estimate train emissions using a German reference "
                "factor, enter your total rail distance like this: "
                "'Calculate train emissions for 100 km'. "
                "Include both directions if you want a return-trip estimate."
            )
        )
        return []


class ActionCollectTravelDates(Action):
    def name(self) -> Text:
        return "action_collect_travel_dates"

    def run(self, dispatcher, tracker, domain) -> List[Dict[Text, Any]]:
        message = tracker.latest_message.get("text") or ""
        clear_dates = [
            SlotSet("departure_date", None),
            SlotSet("return_date", None),
        ]

        match = re.search(
            r"\bfrom\s+(\d{4}-\d{2}-\d{2})\s+to\s+"
            r"(\d{4}-\d{2}-\d{2})\b",
            message,
            flags=re.IGNORECASE,
        )

        if not match:
            dispatcher.utter_message(
                text=(
                    "Please enter both dates like this: "
                    "from 2026-11-10 to 2026-11-15."
                )
            )
            return clear_dates

        departure_text, return_text = match.groups()

        try:
            departure = date.fromisoformat(departure_text)
            returning = date.fromisoformat(return_text)
        except ValueError:
            dispatcher.utter_message(
                text="One of those dates is invalid. Please check both dates."
            )
            return clear_dates

        if returning <= departure:
            dispatcher.utter_message(
                text=(
                    "Your return date must be after your departure date. "
                    "Please enter both dates again using 'from ... to ...'."
                )
            )
            return clear_dates

        dispatcher.utter_message(
            text=(
                f"Your travel dates are {departure_text} to {return_text}. "
                "What is your total trip budget in euros?"
            )
        )
        return [
            SlotSet("departure_date", departure_text),
            SlotSet("return_date", return_text),
        ]


class ActionHumanHandover(Action):
    def name(self) -> Text:
        return "action_human_handover"

    def run(self, dispatcher, tracker, domain) -> List[Dict[Text, Any]]:
        trip_details = {
            name: tracker.get_slot(name)
            for name in [
                "origin",
                "destination",
                "departure_date",
                "return_date",
                "budget",
                "sustainability_preference",
            ]
        }

        conversation = []
        for event in tracker.events:
            event_type = event.get("event")
            if event_type in ("user", "bot"):
                conversation.append({
                    "role": (
                        "user" if event_type == "user" else "assistant"
                    ),
                    "text": event.get("text") or "",
                    "timestamp": event.get("timestamp"),
                })

        dispatcher.utter_message(
            text=(
                "I have prepared your trip details and the available "
                "conversation history for a travel advisor. "
                "This prototype is not connected to an advisor service, "
                "so nothing has been sent."
            )
        )
        dispatcher.utter_message(
            json_message={
                "handover": {
                    "status": "prepared_only",
                    "trip_details": trip_details,
                    "conversation": conversation,
                }
            }
        )
        return []


class ActionDefaultFallback(Action):
    def name(self) -> Text:
        return "action_default_fallback"

    def run(self, dispatcher, tracker, domain) -> List[Dict[Text, Any]]:
        unclear_count = 0

        for event in reversed(tracker.events):
            if event.get("event") == "session_started":
                break
            if event.get("event") != "user":
                continue

            intent = (
                event.get("parse_data", {})
                .get("intent", {})
                .get("name")
            )
            if intent != "nlu_fallback":
                break
            unclear_count += 1

        if unclear_count >= 3:
            dispatcher.utter_message(
                text=(
                    "I am still having trouble understanding after "
                    "two clarification attempts. I will prepare "
                    "your conversation for an advisor."
                )
            )
            return ActionHumanHandover().run(
                dispatcher, tracker, domain
            )

        if unclear_count == 2:
            message = (
                "I still did not understand. Please choose "
                "'Plan a trip' or 'Request an advisor', "
                "or describe your travel request in a short sentence."
            )
        else:
            message = (
                "I did not understand that clearly. "
                "Please rephrase your message or choose an option."
            )

        dispatcher.utter_message(
            text=message,
            buttons=[
                {"title": "Plan a trip", "payload": "/plan_trip"},
                {
                    "title": "Request an advisor",
                    "payload": "/request_human",
                },
            ],
        )
        return []


class ActionCalculateTrainEmissions(Action):
    def name(self) -> Text:
        return "action_calculate_train_emissions"

    def run(self, dispatcher, tracker, domain) -> List[Dict[Text, Any]]:
        message = (tracker.latest_message.get("text") or "").strip()

        # Require a clear distance format to avoid guessing.
        match = re.fullmatch(
            r"(?:calculate\s+)?train\s+emissions\s+for\s+"
            r"(\d+(?:\.\d+)?)\s*km[.!]?",
            message,
            flags=re.IGNORECASE,
        )

        if not match:
            dispatcher.utter_message(
                text=(
                    "Please use this format: "
                    "'Calculate train emissions for 100 km'. "
                    "Enter the total distance you want to estimate, "
                    "without commas."
                )
            )
            return []

        distance_km = float(match.group(1))

        if not math.isfinite(distance_km) or distance_km <= 0:
            dispatcher.utter_message(
                text="Please enter a distance greater than zero."
            )
            return []

        api_key = os.getenv("CLIMATIQ_API_KEY")
        if not api_key:
            dispatcher.utter_message(
                text=(
                    "The carbon calculator is not configured yet. "
                    "I cannot provide an API estimate right now."
                )
            )
            return []

        payload = {
            "emission_factor": {"id": TRAIN_FACTOR_ID},
            "parameters": {
                "passengers": 1,
                "distance": distance_km,
                "distance_unit": "km",
            },
        }

        try:
            response = requests.post(
                "https://api.climatiq.io/data/v1/estimate",
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
                timeout=10,
            )
            response.raise_for_status()
            result = response.json()

            co2e = result.get("co2e")
            unit = result.get("co2e_unit")

            if (
                isinstance(co2e, bool)
                or not isinstance(co2e, (int, float))
                or not math.isfinite(co2e)
                or co2e < 0
                or unit != "kg"
            ):
                raise ValueError("Unexpected emissions response")

        except requests.exceptions.Timeout:
            dispatcher.utter_message(
                text=(
                    "The carbon service took too long to respond. "
                    "Please try again shortly."
                )
            )
            return []

        except (requests.exceptions.RequestException, ValueError):
            dispatcher.utter_message(
                text=(
                    "The carbon service could not provide a valid estimate. "
                    "Please try again later. No emissions value is available."
                )
            )
            return []

        dispatcher.utter_message(
            text=(
                f"Estimated train emissions: {co2e:.2f} kg CO2e.\n"
                f"Passengers: 1\n"
                f"Total distance supplied: {distance_km:g} km\n"
                "Reference factor: Germany, ADEME, 2020.\n"
                "Calculated through Climatiq using historical factor data. "
                "This is an approximate rail estimate, not a measured "
                "journey footprint or the footprint of your whole holiday."
            )
        )
        return []
    
class ActionShowHotels(Action):
    def name(self) -> Text:
        return "action_show_hotels"

    def run(self, dispatcher, tracker, domain) -> List[Dict[Text, Any]]:
        import json

        destination = tracker.get_slot("destination")
        departure_text = tracker.get_slot("departure_date")
        return_text = tracker.get_slot("return_date")
        budget_value = tracker.get_slot("budget")

        if not destination:
            dispatcher.utter_message(
                text="Please tell me your destination first."
            )
            return []

        if not departure_text or not return_text:
            dispatcher.utter_message(
                text=(
                    "Please provide your dates first, for example: "
                    "from 2026-11-10 to 2026-11-15. "
                    "Then ask me to show hotels."
                )
            )
            return []

        try:
            departure = date.fromisoformat(departure_text)
            returning = date.fromisoformat(return_text)
            nights = (returning - departure).days
        except (ValueError, TypeError):
            dispatcher.utter_message(
                text="Please enter valid departure and return dates."
            )
            return []

        if nights <= 0:
            dispatcher.utter_message(
                text="Your return date must be after your departure date."
            )
            return []

        if budget_value is None or str(budget_value).strip() == "":
            dispatcher.utter_message(
                text=(
                    "What is your total trip budget in euros? "
                    "For example: 'My budget is 200 euros'. "
                    "Then ask me to show hotels."
                )
            )
            return []

        # Accept plain numbers or correctly grouped thousands.
        # Examples: 200, 200.50, 1,000 or 1,000.50.
        budget_text = str(budget_value).strip()
        valid_number = re.fullmatch(
            r"(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d{1,2})?",
            budget_text,
        )

        if not valid_number:
            dispatcher.utter_message(
                text=(
                    "Please enter your budget as a positive euro amount, "
                    "for example: 'My budget is 200 euros'. "
                    "Use a dot for decimals. Then ask me to show hotels."
                )
            )
            return []

        budget = float(budget_text.replace(",", ""))

        if not math.isfinite(budget) or budget <= 0:
            dispatcher.utter_message(
                text=(
                    "Your budget must be greater than zero. "
                    "Please provide a new budget, then ask me to show hotels."
                )
            )
            return []

        database_path = PROJECT_DIR / "mock_data" / "travel_options.json"

        try:
            with database_path.open("r", encoding="utf-8") as file:
                database = json.load(file)

            hotels = []
            for item in database["hotels"]:
                if item["city"].casefold() != destination.strip().casefold():
                    continue

                hotel = dict(item)
                nightly_price = float(hotel["price_per_room_per_night"])

                if not math.isfinite(nightly_price) or nightly_price < 0:
                    raise ValueError("Invalid hotel price")

                hotel["nightly_price"] = nightly_price
                hotel["stay_total"] = round(nightly_price * nights, 2)
                hotels.append(hotel)

            hotels.sort(key=lambda hotel: hotel["stay_total"])

        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            dispatcher.utter_message(
                text="The hotel database could not be read. Please try later."
            )
            return []

        if not hotels:
            dispatcher.utter_message(
                text=(
                    f"No mock hotels are available for {destination}. "
                    "The demonstration database supports Berlin only."
                )
            )
            return []

        affordable = [
            hotel for hotel in hotels
            if hotel["stay_total"] <= budget
        ]

        if not affordable:
            cheapest = hotels[0]["stay_total"]
            dispatcher.utter_message(
                text=(
                    f"No mock hotel fits within your EUR {budget:.2f} "
                    f"total trip budget for {nights} nights.\n"
                    f"The cheapest accommodation alone costs EUR {cheapest:.2f}, "
                    f"which is EUR {cheapest - budget:.2f} over your budget.\n"
                    "Consider fewer nights or a higher budget. "
                    "Transport and other expenses would cost extra."
                )
            )
            return []

        excluded = len(hotels) - len(affordable)

        dispatcher.utter_message(
            text=(
                f"Mock hotels in {destination} for {nights} nights, "
                "one room for one traveller.\n"
                f"Total trip budget: EUR {budget:.2f}.\n"
                f"{len(affordable)} accommodation options cost no more than "
                f"this budget; {excluded} exceed it.\n"
                "Sorted by accommodation price. Properties and prices are "
                "fictional, and availability is not checked.\n"
                "Transport, meals, activities and additional charges "
                "must still fit within the remaining money."
            )
        )

        for hotel in affordable:
            nightly_price = hotel["nightly_price"]
            total_price = hotel["stay_total"]
            remaining = round(budget - total_price, 2)
            transport_access = (
                "Yes" if hotel["near_public_transport"] else "No"
            )

            dispatcher.utter_message(
                text=(
                    f"{hotel['name']}\n"
                    f"EUR {nightly_price:.2f} per night × {nights} nights "
                    f"= EUR {total_price:.2f}\n"
                    f"Remaining after accommodation: EUR {remaining:.2f}\n"
                    f"Near public transport: {transport_access}\n"
                    f"Certification: {hotel['certification_status']}\n"
                    "This is an accommodation-only budget check, "
                    "not confirmation that the whole trip is affordable."
                ),
                json_message={"hotel": {
                    "name": hotel["name"], "nightly_price": nightly_price,
                    "nights": nights, "total_price": total_price,
                    "remaining_budget": remaining,
                    "near_public_transport": hotel["near_public_transport"],
                    "certification": hotel["certification_status"],
                    "data_mode": "mock"
                }}
            )

        return []
    
class ActionShowTransport(Action):
    def name(self) -> Text:
        return "action_show_transport"

    def run(self, dispatcher, tracker, domain) -> List[Dict[Text, Any]]:
        import json

        origin = tracker.get_slot("origin")
        destination = tracker.get_slot("destination")

        if not origin:
            dispatcher.utter_message(
                text="What is your starting city? Say: I am travelling from Frankfurt."
            )
            return []

        if not destination:
            dispatcher.utter_message(
                text="Please provide your destination, then ask for transport options."
            )
            return []

        try:
            path = PROJECT_DIR / "mock_data" / "travel_options.json"
            with path.open("r", encoding="utf-8") as file:
                database = json.load(file)

            options = [
                dict(option)
                for option in database["transport_options"]
                if option["origin"].casefold() == origin.strip().casefold()
                and option["destination"].casefold()
                == destination.strip().casefold()
            ]
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            dispatcher.utter_message(
                text="The transport database could not be read."
            )
            return []

        if not options:
            dispatcher.utter_message(
                text=(
                    f"No mock options found from {origin} to {destination}. "
                    "The demonstration supports Frankfurt to Berlin."
                )
            )
            return []

        factors = {
            "train": {
                "id": "5e49b19a-3258-8acd-9cfb-0aee76804cbe",
                "assumption": "Electric national long-distance train.",
            },
            "coach": {
                "id": "44338391-77cd-8415-b1a8-250e38d5b013",
                "assumption": "General bus factor used as a coach approximation.",
            },
            "flight": {
                "id": "b0b6e1e2-a18c-8079-a0ac-7045cb520faf",
                "assumption": "Domestic flight including RF effect.",
            },
        }

        api_key = os.getenv("CLIMATIQ_API_KEY")

        for option in options:
            option["carbon_estimate_kg_co2e"] = None
            factor = factors.get(option["mode"])
            option["carbon_assumption"] = (
                factor["assumption"] if factor else "No suitable factor configured."
            )

            if not api_key or not factor:
                continue

            try:
                response = requests.post(
                    "https://api.climatiq.io/data/v1/estimate",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "emission_factor": {"id": factor["id"]},
                        "parameters": {
                            "passengers": 1,
                            "distance": option["distance_km_one_way"],
                            "distance_unit": "km",
                        },
                    },
                    timeout=10,
                )
                response.raise_for_status()
                result = response.json()
                value = result.get("co2e")

                if (
                    isinstance(value, (int, float))
                    and not isinstance(value, bool)
                    and math.isfinite(value)
                    and value >= 0
                    and result.get("co2e_unit") == "kg"
                ):
                    option["carbon_estimate_kg_co2e"] = value

            except (requests.exceptions.RequestException, ValueError):
                # Missing estimates remain unknown, never zero.
                continue

        preference = tracker.get_slot("sustainability_preference")
        weights = {
            "lowest environmental impact": (0.2, 0.8),
            "balance of cost and sustainability": (0.5, 0.5),
            "lowest price": (0.8, 0.2),
        }
        chosen_preference = (
            preference if preference in weights
            else "balance of cost and sustainability"
        )
        price_weight, carbon_weight = weights[chosen_preference]

        complete = all(
            option["carbon_estimate_kg_co2e"] is not None
            for option in options
        )

        if complete:
            prices = [
                option["price_per_person_one_way"] for option in options
            ]
            emissions = [
                option["carbon_estimate_kg_co2e"] for option in options
            ]

            def normalise(value, values):
                smallest, largest = min(values), max(values)
                if largest == smallest:
                    return 0.0
                return (value - smallest) / (largest - smallest)

            for option in options:
                option["ranking_score"] = (
                    price_weight * normalise(
                        option["price_per_person_one_way"], prices
                    )
                    + carbon_weight * normalise(
                        option["carbon_estimate_kg_co2e"], emissions
                    )
                )

            options.sort(key=lambda option: option["ranking_score"])
            ranking_note = (
                f"Ranking preference: {chosen_preference}. "
                f"Weights: price {price_weight:.0%}, "
                f"carbon {carbon_weight:.0%}. Lower score is better."
            )
            if preference not in weights:
                ranking_note += " Balanced weights used because no preference is set."
        else:
            options.sort(
                key=lambda option: option["price_per_person_one_way"]
            )
            ranking_note = (
                "Some carbon estimates are unavailable. "
                "Showing price order only; carbon ranking is unavailable."
            )

        dispatcher.utter_message(
            text=(
                f"Mock transport: {origin} to {destination}.\n"
                "One passenger, one-way. Prices and distances are illustrative; "
                "availability is not checked.\n"
                "Carbon estimates use Climatiq with Germany / UBA / 2024 factors.\n"
                f"{ranking_note}\n"
                "These are transport-only costs, not total holiday costs."
            )
        )

        for position, option in enumerate(options, start=1):
            emissions = option["carbon_estimate_kg_co2e"]
            carbon_text = (
                f"{emissions:.2f} kg CO2e"
                if emissions is not None else "Unavailable"
            )

            text = (
                f"{position}. {option['provider']} — {option['mode'].title()}\n"
                f"Price: EUR {option['price_per_person_one_way']:.2f}\n"
                f"Distance: {option['distance_km_one_way']:g} km\n"
                f"Duration: {option['duration_minutes_one_way']} minutes\n"
                f"Estimated emissions: {carbon_text}\n"
                f"Assumption: {option['carbon_assumption']}"
            )

            if complete:
                text += f"\nRanking score: {option['ranking_score']:.3f}"

            for field in ("duration_note", "price_note"):
                if option.get(field):
                    text += f"\n{option[field]}"

            dispatcher.utter_message(
                text=text,
                json_message={"transport": {
                    "emissions_kg_co2e": emissions,
                    "provider": option["provider"],
                    "mode": option["mode"],
                    "data_mode": "mock_route_with_api_carbon"
                }}
            )

        return []
    
class ActionCollectBudget(Action):
    def name(self) -> Text:
        return "action_collect_budget"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        from decimal import Decimal, InvalidOperation

        message = tracker.latest_message.get("text") or ""

        # Accept one positive amount in euros.
        # Examples: 500, 650 euros, EUR 1,000.50.
        numbers = re.findall(
            r"(?<!\w)[+-]?\d[\d,.]*(?!\w)",
            message,
        )

        other_currency = re.search(
            r"[$£₹]|\b(?:USD|GBP|INR|dollars?|pounds?|rupees?)\b",
            message,
            flags=re.IGNORECASE,
        )

        valid_format = (
            len(numbers) == 1
            and re.fullmatch(
                r"(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d{1,2})?",
                numbers[0],
            )
        )

        amount = None

        if valid_format and not other_currency:
            try:
                amount = Decimal(numbers[0].replace(",", ""))
            except InvalidOperation:
                pass

        if amount is None or not amount.is_finite() or amount <= 0:
            dispatcher.utter_message(
                text=(
                    "Please enter one total trip budget greater than "
                    "0 in euros, for example: 'My budget is 650 euros'. "
                    "Use a decimal point for cents, such as 650.50."
                )
            )
            return [SlotSet("budget", None)]

        budget_text = format(amount, ".2f")

        dispatcher.utter_message(
            text=(
                f"Your total trip budget is {budget_text} euros. "
                "What matters most to you: the lowest environmental "
                "impact, a balance of cost and sustainability, "
                "or the lowest price?"
            ),
            buttons=[
                {"title": "Lower environmental impact", "payload": "/prefer_environment"},
                {"title": "Balance cost and sustainability", "payload": "/prefer_balanced"},
                {"title": "Lowest price", "payload": "/prefer_price"},
            ]
        )

        return [SlotSet("budget", budget_text)]
class ActionDestinationInfo(Action):
    def name(self) -> Text:
        return "action_destination_info"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        import json

        destination = tracker.get_slot("destination")

        if not destination:
            dispatcher.utter_message(
                text="Please tell me your destination first."
            )
            return []

        if str(destination).strip().casefold() != "berlin":
            dispatcher.utter_message(
                text="The cached destination guide currently covers Berlin only."
            )
            return []

        cache_path = PROJECT_DIR / "cache_data" / "berlin.json"

        try:
            data = json.loads(cache_path.read_text(encoding="utf-8"))
            sections = data["sections"]
            if not isinstance(sections, dict):
                raise ValueError("Invalid cache")
        except (OSError, ValueError, KeyError, TypeError):
            dispatcher.utter_message(
                text="The destination guide is unavailable. Please try later."
            )
            return []

        def section_value(name, expected_type):
            section = sections.get(name, {})
            if not isinstance(section, dict):
                return None
            value = section.get("data")
            if section.get("status") != "ok":
                return None
            return value if isinstance(value, expected_type) else None

        def cached_date(name):
            value = sections.get(name, {}).get("fetched_at_utc", "")
            return value[:10] if value else "date unavailable"

        dispatcher.utter_message(
            text=(
                "Berlin destination guide\n"
                "Cached external information around the city centre. "
                "This is separate from the fictional priced options."
            )
        )

        description = section_value("description", dict)
        if description:
            dispatcher.utter_message(
                text=(
                    f"{description.get('summary', '')}\n"
                    f"Source: Wikipedia — {description.get('url', '')}\n"
                    f"Retrieved: {cached_date('description')} UTC. "
                    "Text reused under Wikipedia's CC BY-SA terms."
                )
            )

        groups = [
            ("hotels", "Mapped hotels", 3),
            ("transport_stops", "Public transport access points", 5),
            ("attractions", "Cultural places", 3),
        ]

        for key, heading, limit in groups:
            items = section_value(key, list)
            if items is None:
                dispatcher.utter_message(
                    text=f"{heading}: cached information is unavailable."
                )
                continue

            names = []
            seen = set()

            for item in items:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name") or "").strip()
                if not name or name == "(unnamed)":
                    continue
                if name.casefold() in seen:
                    continue
                seen.add(name.casefold())
                names.append(name)

            selected = names[:limit]
            listing = "\n".join(f"- {name}" for name in selected)
            if not listing:
                listing = "No named results in this cached sample."

            notes = {
                "hotels": (
                    "Prices and availability are unknown. "
                    "Eco-certification has not been verified."
                ),
                "transport_stops": (
                    "Names are deduplicated for display; these may include "
                    "station entrances. Routes, frequency, accessibility "
                    "and live timetables have not been checked."
                ),
                "attractions": (
                    "Opening hours, admission prices and local community "
                    "benefits have not been verified."
                ),
            }

            dispatcher.utter_message(
                text=(
                    f"{heading} — examples from the cached sample:\n"
                    f"{listing}\n"
                    f"{notes[key]}\n"
                    f"Retrieved: {cached_date(key)} UTC.\n"
                    "Source: © OpenStreetMap contributors (ODbL).\n"
                    "https://www.openstreetmap.org/copyright"
                )
            )

        return []
class ActionShowWeather(Action):
    def name(self) -> Text:
        return "action_show_weather"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        import json
        import math
        import requests

        destination = str(tracker.get_slot("destination") or "").strip()

        if not destination:
            dispatcher.utter_message(
                text="Please tell me your destination before asking for weather."
            )
            return []

        if destination.casefold() != "berlin":
            dispatcher.utter_message(
                text="The weather feature currently supports Berlin only."
            )
            return []

        try:
            cache = json.loads(
                (PROJECT_DIR / "cache_data" / "berlin.json").read_text(
                    encoding="utf-8"
                )
            )
            location = cache["sections"]["location"]
            if location["status"] != "ok":
                raise ValueError("Location unavailable")

            latitude, longitude, _ = location["data"]

            # Adapted from the lecturer's 06_weather_forecast.py.
            response = requests.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": latitude,
                    "longitude": longitude,
                    "current": "temperature_2m,precipitation,wind_speed_10m",
                    "daily": "temperature_2m_max,precipitation_sum",
                    "forecast_days": 3,
                    "timezone": "auto",
                    "temperature_unit": "celsius",
                    "wind_speed_unit": "kmh",
                    "precipitation_unit": "mm",
                },
                timeout=(3, 5),
            )
            response.raise_for_status()
            weather = response.json()

            def number(value):
                if isinstance(value, bool) or value is None:
                    raise ValueError("Missing weather value")
                result = float(value)
                if not math.isfinite(result):
                    raise ValueError("Invalid weather value")
                return result

            current = weather["current"]
            daily = weather["daily"]

            temperature = number(current["temperature_2m"])
            rain = number(current["precipitation"])
            wind = number(current["wind_speed_10m"])

            lines = [
                "Berlin weather — current conditions and next three days",
                f"Local timestamp: {current['time']}",
                f"Timezone: {weather['timezone']}",
                f"Temperature: {temperature:.1f} °C",
                f"Precipitation: {rain:.1f} mm",
                f"Wind: {wind:.1f} km/h",
                "",
            ]

            for index, day in enumerate(daily["time"]):
                maximum = number(daily["temperature_2m_max"][index])
                rainfall = number(daily["precipitation_sum"][index])

                lines.append(
                    f"{day}: maximum {maximum:.1f} °C; "
                    f"forecast precipitation {rainfall:.1f} mm."
                )

            lines.extend([
                "",
                "Consider walking or public transport where conditions "
                "and your accessibility needs allow. Check local warnings "
                "before outdoor activities.",
                "This covers the dates displayed, not necessarily your "
                "planned trip dates. Forecasts can change.",
                "Source: Open-Meteo — https://open-meteo.com/ "
                "(weather data: CC BY 4.0).",
            ])

            dispatcher.utter_message(text="\n".join(lines))

        except (
            requests.RequestException,
            OSError,
            ValueError,
            KeyError,
            TypeError,
            IndexError,
        ):
            dispatcher.utter_message(
                text=(
                    "Weather information is unavailable right now. "
                    "You can continue planning your trip and try again later."
                )
            )

        return []

class ActionConvertBudget(Action):
    def name(self) -> Text:
        return "action_convert_budget"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        from decimal import Decimal, InvalidOperation
        import requests

        # Adapted from the lecturer's 07_currency_exchange.py.
        budget = tracker.get_slot("budget")

        try:
            amount = Decimal(str(budget))
            if not amount.is_finite() or amount <= 0:
                raise ValueError("Invalid budget")
        except (InvalidOperation, ValueError, TypeError):
            dispatcher.utter_message(
                text=(
                    "Please provide your total budget in euros first, "
                    "for example: 'My budget is 500 euros'."
                )
            )
            return []

        message = tracker.latest_message.get("text") or ""

        patterns = {
            "INR": r"\b(?:INR|Indian rupees?|rupees?)\b",
            "GBP": r"\b(?:GBP|British pounds?|pounds?|sterling)\b",
            "USD": r"\b(?:USD|US dollars?|dollars?)\b",
        }

        targets = [
            currency
            for currency, pattern in patterns.items()
            if re.search(pattern, message, flags=re.IGNORECASE)
        ]

        if len(targets) != 1:
            dispatcher.utter_message(
                text=(
                    "Choose one currency for your saved euro budget: "
                    "INR, GBP or USD."
                ),
                buttons=[
                    {
                        "title": "Indian rupees",
                        "payload": '/convert_budget{"currency":"INR"}',
                    },
                    {
                        "title": "British pounds",
                        "payload": '/convert_budget{"currency":"GBP"}',
                    },
                    {
                        "title": "US dollars",
                        "payload": '/convert_budget{"currency":"USD"}',
                    },
                ],
            )
            return []

        target = targets[0]

        try:
            response = requests.get(
                "https://api.frankfurter.dev/v1/latest",
                params={"base": "EUR", "symbols": target},
                timeout=(3, 5),
            )
            response.raise_for_status()
            data = response.json()

            if data.get("base") != "EUR":
                raise ValueError("Unexpected base currency")

            rate = Decimal(str(data["rates"][target]))
            if not rate.is_finite() or rate <= 0:
                raise ValueError("Invalid exchange rate")

            rate_date = date.fromisoformat(data["date"]).isoformat()
            converted = amount * rate

            dispatcher.utter_message(
                text=(
                    f"Your saved budget: EUR {amount:,.2f}\n"
                    f"Approximate equivalent: {target} {converted:,.2f}\n"
                    f"Reference rate: 1 EUR = {rate} {target}\n"
                    f"Rate date: {rate_date}\n\n"
                    "Source: Frankfurter / ECB reference rates.\n"
                    "https://frankfurter.dev/\n"
                    "Bank rates and fees may differ. Your saved budget "
                    "and travel comparisons remain in euros."
                )
            )

        except (
            requests.RequestException,
            InvalidOperation,
            ValueError,
            KeyError,
            TypeError,
        ):
            dispatcher.utter_message(
                text=(
                    "Currency conversion is unavailable right now. "
                    "Your euro budget is unchanged. Please try again later."
                )
            )

        return []

class ActionAskDestination(Action):
    """Offer only destinations represented in the local priced demonstration."""

    def name(self) -> Text:
        return "action_ask_destination"

    def run(self, dispatcher, tracker, domain) -> List[Dict[Text, Any]]:
        import json

        try:
            with (PROJECT_DIR / "mock_data" / "travel_options.json").open(
                encoding="utf-8"
            ) as file:
                database = json.load(file)
            cities = sorted({
                str(hotel["city"]).strip()
                for hotel in database.get("hotels", [])
                if hotel.get("city")
            })
        except (OSError, ValueError, TypeError, KeyError, AttributeError):
            cities = []

        buttons = [
            {"title": city, "payload": "/inform_destination" + json.dumps(
                {"destination": city}, ensure_ascii=False
            )}
            for city in cities[:10]
        ]
        dispatcher.utter_message(
            text=("Choose a destination from the available demonstration data, "
                  "or type your destination. Other cities may have no results."),
            buttons=buttons,
        )
        return []
