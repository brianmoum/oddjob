"""
OpenTable API client for making reservations via the web dapi endpoints.

Uses the same GraphQL + REST endpoints that opentable.com uses in the browser.
Requires credentials captured from browser dev tools (see CLAUDE.md for instructions).

Booking flow:
1. RestaurantsAvailability (GraphQL query) — find available time slots
2. BookDetailsStandardSlotLock (GraphQL mutation) — lock a slot temporarily
3. make-reservation (REST POST) — complete the booking
"""

import json
import uuid
import requests
from datetime import datetime, timedelta

from .base import BookingClient, BookingClientError, Slot, BookingConfirmation


BASE_URL = "https://www.opentable.com/dapi"

# Persisted query hashes — these may rotate when OpenTable deploys frontend updates.
# If requests start returning errors about unknown queries, recapture from browser dev tools.
AVAILABILITY_HASH = "b2d05a06151b3cb21d9dfce4f021303eeba288fac347068b29c1cb66badc46af"
SLOT_LOCK_HASH = "1100bf68905fd7cb1d4fd0f4504a4954aa28ec45fb22913fa977af8b06fd97fa"


class OpenTableApiError(BookingClientError):
    """Exception for OpenTable API errors."""

    def __init__(self, message: str):
        super().__init__(message, platform="opentable")


class OpenTableClient(BookingClient):
    """Client for interacting with the OpenTable web API."""

    def __init__(self, credentials: dict):
        self.csrf_token = credentials["csrf_token"]
        self.cookies = credentials["cookies"]
        self.first_name = credentials["first_name"]
        self.last_name = credentials["last_name"]
        self.email = credentials["email"]
        self.phone_number = credentials["phone_number"]
        self.phone_country = credentials.get("phone_country", "US")
        self.country = credentials.get("country", "US")
        self.gpid = credentials["gpid"]
        self.database_region = credentials.get("database_region", "NA")

    @property
    def platform_name(self) -> str:
        return "opentable"

    def _headers(self) -> dict:
        """Build headers for API requests."""
        return {
            "content-type": "application/json",
            "origin": "https://www.opentable.com",
            "referer": "https://www.opentable.com/",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
            "x-csrf-token": self.csrf_token,
            "Cookie": self.cookies,
        }

    def _gql_request(self, optype: str, opname: str, payload: dict) -> dict:
        """Make a GraphQL request to the dapi endpoint."""
        url = f"{BASE_URL}/fe/gql?optype={optype}&opname={opname}"
        response = requests.post(url, headers=self._headers(), json=payload)

        if response.status_code != 200:
            raise OpenTableApiError(
                f"{opname} failed: {response.status_code} {response.text}"
            )

        data = response.json()
        if "errors" in data:
            raise OpenTableApiError(
                f"{opname} returned errors: {json.dumps(data['errors'])}"
            )

        return data

    def find_slots(self, venue_id: str, date: str, party_size: int) -> list[Slot]:
        """
        Find available reservation slots for a restaurant.

        Args:
            venue_id: OpenTable restaurant ID (numeric string)
            date: Reservation date in YYYY-MM-DD format
            party_size: Number of guests

        Returns:
            List of available Slot objects
        """
        # Request availability centered on 19:00 to get the widest range of slots
        request_time = "19:00"

        payload = {
            "operationName": "RestaurantsAvailability",
            "variables": {
                "restaurantIds": [int(venue_id)],
                "date": date,
                "time": request_time,
                "partySize": party_size,
                "databaseRegion": self.database_region,
            },
            "extensions": {
                "persistedQuery": {
                    "sha256Hash": AVAILABILITY_HASH,
                },
            },
        }

        data = self._gql_request("query", "RestaurantsAvailability", payload)

        availability = data.get("data", {}).get("availability", [])
        if not availability:
            return []

        restaurant = availability[0]
        days = restaurant.get("availabilityDays", [])
        if not days:
            return []

        # Parse the requested time to compute absolute times from offsets
        req_hour, req_min = map(int, request_time.split(":"))
        req_base = datetime(2000, 1, 1, req_hour, req_min)

        slots = []
        for slot_data in days[0].get("slots", []):
            if not slot_data.get("isAvailable"):
                continue

            offset_minutes = slot_data["timeOffsetMinutes"]
            slot_time = req_base + timedelta(minutes=offset_minutes)
            time_str = slot_time.strftime("%H:%M:00")

            slot_hash = slot_data["slotHash"]
            slot_token = slot_data.get("slotAvailabilityToken", "")
            slot_type = slot_data.get("type", "Standard")
            dining_areas = slot_data.get("diningAreasBySeating", [])
            dining_area_id = 1
            if dining_areas and dining_areas[0].get("inventoryAccessRuleMap"):
                dining_area_id = dining_areas[0].get("id", 1)

            slots.append(Slot(
                platform="opentable",
                venue_id=venue_id,
                time=time_str,
                table_type=slot_type,
                platform_data={
                    "slot_hash": slot_hash,
                    "slot_availability_token": slot_token,
                    "dining_area_id": dining_area_id,
                    "reservation_date_time": f"{date}T{slot_time.strftime('%H:%M')}",
                },
            ))

        return slots

    def _lock_slot(
        self,
        restaurant_id: int,
        slot_hash: str,
        reservation_date_time: str,
        party_size: int,
        dining_area_id: int = 1,
    ) -> int:
        """
        Lock a slot temporarily before completing the reservation.

        Returns:
            The slotLockId needed for the booking step.
        """
        payload = {
            "operationName": "BookDetailsStandardSlotLock",
            "variables": {
                "input": {
                    "restaurantId": restaurant_id,
                    "seatingOption": "DEFAULT",
                    "reservationDateTime": reservation_date_time,
                    "partySize": party_size,
                    "databaseRegion": self.database_region,
                    "slotHash": slot_hash,
                    "reservationType": "STANDARD",
                    "diningAreaId": dining_area_id,
                },
            },
            "extensions": {
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": SLOT_LOCK_HASH,
                },
            },
        }

        data = self._gql_request("mutation", "BookDetailsStandardSlotLock", payload)

        lock_response = data.get("data", {}).get("lockSlot", {})
        if not lock_response.get("success"):
            errors = lock_response.get("slotLockErrors", "Unknown error")
            raise OpenTableApiError(f"Slot lock failed: {errors}")

        slot_lock = lock_response.get("slotLock", {})
        slot_lock_id = slot_lock.get("slotLockId")
        if not slot_lock_id:
            raise OpenTableApiError("Slot lock response missing slotLockId")

        return slot_lock_id

    def _make_reservation(
        self,
        restaurant_id: int,
        slot_hash: str,
        slot_lock_id: int,
        slot_availability_token: str,
        reservation_date_time: str,
        party_size: int,
        dining_area_id: int = 1,
    ) -> dict:
        """
        Complete the reservation after locking the slot.

        Returns:
            The raw reservation response dict.
        """
        url = f"{BASE_URL}/booking/make-reservation"

        payload = {
            "restaurantId": restaurant_id,
            "slotHash": slot_hash,
            "slotLockId": slot_lock_id,
            "slotAvailabilityToken": slot_availability_token,
            "reservationDateTime": reservation_date_time,
            "partySize": party_size,
            "firstName": self.first_name,
            "lastName": self.last_name,
            "email": self.email,
            "phoneNumber": self.phone_number,
            "phoneNumberCountryId": self.phone_country,
            "country": self.country,
            "gpid": self.gpid,
            "dinerIsAccountHolder": True,
            "reservationType": "Standard",
            "reservationAttribute": "default",
            "diningAreaId": dining_area_id,
            "points": 100,
            "pointsType": "Standard",
            "tipAmount": 0,
            "tipPercent": 0,
            "optInEmailRestaurant": False,
            "isModify": False,
            "tcAccepted": True,
            "confirmPoints": True,
            "correlationId": str(uuid.uuid4()),
            "attributionToken": "",
            "additionalServiceFees": [],
            "nonBookableExperiences": [],
            "katakanaFirstName": "",
            "katakanaLastName": "",
        }

        headers = {**self._headers(), "accept": "application/json"}
        response = requests.post(url, headers=headers, json=payload)

        if response.status_code != 200:
            raise OpenTableApiError(
                f"make-reservation failed: {response.status_code} {response.text}"
            )

        data = response.json()

        if not data.get("success"):
            raise OpenTableApiError(
                f"Reservation failed: {json.dumps(data)}"
            )

        return data

    def book_slot(self, slot: Slot, date: str, party_size: int) -> BookingConfirmation:
        """Book an OpenTable slot via lock + make-reservation."""
        slot_hash = slot.platform_data.get("slot_hash")
        slot_token = slot.platform_data.get("slot_availability_token")
        reservation_dt = slot.platform_data.get("reservation_date_time")
        dining_area_id = slot.platform_data.get("dining_area_id", 1)
        restaurant_id = int(slot.venue_id)

        if not slot_hash:
            raise OpenTableApiError("Slot missing slot_hash in platform_data")

        # Step 1: Lock the slot
        slot_lock_id = self._lock_slot(
            restaurant_id=restaurant_id,
            slot_hash=slot_hash,
            reservation_date_time=reservation_dt,
            party_size=party_size,
            dining_area_id=dining_area_id,
        )

        # Step 2: Complete the reservation
        result = self._make_reservation(
            restaurant_id=restaurant_id,
            slot_hash=slot_hash,
            slot_lock_id=slot_lock_id,
            slot_availability_token=slot_token,
            reservation_date_time=reservation_dt,
            party_size=party_size,
            dining_area_id=dining_area_id,
        )

        return BookingConfirmation(
            platform="opentable",
            confirmation_id=str(result["confirmationNumber"]),
            reservation_id=str(result.get("reservationId", "")),
            details={
                "security_token": result.get("securityToken"),
                "environment": result.get("environment"),
                "reservation_type": result.get("reservationType"),
            },
        )
