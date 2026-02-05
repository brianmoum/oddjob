"""
Resy API client for making reservations via direct API calls.

This replaces the Selenium-based approach with faster, serverless-compatible HTTP requests.
API documentation derived from community research: https://github.com/Alkaar/resy-booking-bot
"""

import json
import requests
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlencode


BASE_URL = "https://api.resy.com"


@dataclass
class SlotInfo:
    """Represents an available reservation slot."""
    config_token: str
    time: str  # HH:MM:SS format
    table_type: str


@dataclass
class BookingDetails:
    """Details needed to complete a reservation."""
    book_token: str
    payment_method_id: int


@dataclass
class BookingResult:
    """Result of a successful booking."""
    resy_token: str
    reservation_id: Optional[int] = None


class ResyApiError(Exception):
    """Base exception for Resy API errors."""
    pass


class ResyClient:
    """Client for interacting with the Resy API."""

    def __init__(self, api_key: str, auth_token: str):
        """
        Initialize the Resy client.

        Args:
            api_key: Your Resy API key (from Authorization header in browser)
            auth_token: Your Resy auth token (from x-resy-auth-token header in browser)
        """
        self.api_key = api_key
        self.auth_token = auth_token

    def _headers(self) -> dict:
        """Build headers for API requests."""
        return {
            "Authorization": f'ResyAPI api_key="{self.api_key}"',
            "x-resy-auth-token": self.auth_token,
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        }

    def _post_headers(self) -> dict:
        """Build headers for POST requests."""
        return {
            **self._headers(),
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://widgets.resy.com",
            "Referer": "https://widgets.resy.com/",
        }

    def find_reservations(
        self,
        venue_id: int,
        date: str,
        party_size: int,
    ) -> list[SlotInfo]:
        """
        Find available reservation slots for a venue.

        Args:
            venue_id: The unique identifier of the restaurant
            date: Reservation date in YYYY-MM-DD format
            party_size: Number of guests

        Returns:
            List of available SlotInfo objects, sorted by time

        Raises:
            ResyApiError: If the API request fails
        """
        params = {
            "lat": "0",
            "long": "0",
            "day": date,
            "party_size": str(party_size),
            "venue_id": str(venue_id),
        }

        url = f"{BASE_URL}/4/find?{urlencode(params)}"
        response = requests.get(url, headers=self._headers())

        if response.status_code != 200:
            raise ResyApiError(f"Find reservations failed: {response.status_code} {response.text}")

        data = response.json()

        slots = []
        try:
            venues = data.get("results", {}).get("venues", [])
            if not venues:
                return []

            for slot in venues[0].get("slots", []):
                config = slot.get("config", {})
                date_info = slot.get("date", {})

                # Time format: "2024-03-15 18:00:00" -> extract "18:00:00"
                start_time = date_info.get("start", "")
                time_part = start_time.split(" ")[1] if " " in start_time else start_time

                slots.append(SlotInfo(
                    config_token=config.get("token", ""),
                    time=time_part,
                    table_type=config.get("type", ""),
                ))
        except (KeyError, IndexError) as e:
            raise ResyApiError(f"Failed to parse reservation response: {e}")

        return slots

    def get_reservation_details(
        self,
        config_id: str,
        date: str,
        party_size: int,
    ) -> BookingDetails:
        """
        Get details needed to complete a reservation.

        Args:
            config_id: The config token from find_reservations
            date: Reservation date in YYYY-MM-DD format
            party_size: Number of guests

        Returns:
            BookingDetails with book_token and payment_method_id

        Raises:
            ResyApiError: If the API request fails or required fields are missing
        """
        params = {
            "config_id": config_id,
            "day": date,
            "party_size": str(party_size),
        }

        url = f"{BASE_URL}/3/details?{urlencode(params)}"
        response = requests.get(url, headers=self._headers())

        if response.status_code != 200:
            raise ResyApiError(f"Get details failed: {response.status_code} {response.text}")

        data = response.json()

        try:
            book_token = data["book_token"]["value"]
            payment_methods = data.get("user", {}).get("payment_methods", [])

            if not payment_methods:
                raise ResyApiError("No payment method on file. Add a credit card to your Resy account.")

            payment_method_id = payment_methods[0]["id"]

            return BookingDetails(
                book_token=book_token,
                payment_method_id=payment_method_id,
            )
        except KeyError as e:
            raise ResyApiError(f"Failed to parse details response: missing {e}")

    def book_reservation(
        self,
        book_token: str,
        payment_method_id: int,
    ) -> BookingResult:
        """
        Complete a reservation booking.

        Args:
            book_token: The booking token from get_reservation_details
            payment_method_id: The payment method ID from get_reservation_details

        Returns:
            BookingResult with the confirmation resy_token

        Raises:
            ResyApiError: If the booking fails
        """
        payload = {
            "book_token": book_token,
            "struct_payment_method": json.dumps({"id": payment_method_id}),
        }

        url = f"{BASE_URL}/3/book"
        response = requests.post(
            url,
            headers=self._post_headers(),
            data=urlencode(payload),
        )

        if response.status_code not in (200, 201):
            raise ResyApiError(f"Booking failed: {response.status_code} {response.text}")

        data = response.json()

        resy_token = data.get("resy_token")
        if not resy_token:
            raise ResyApiError(f"Booking response missing resy_token: {data}")

        return BookingResult(
            resy_token=resy_token,
            reservation_id=data.get("reservation_id"),
        )

    def book(
        self,
        venue_id: int,
        date: str,
        party_size: int,
        preferred_times: list[str],
        preferred_table_types: Optional[list[str]] = None,
    ) -> Optional[BookingResult]:
        """
        High-level method to find and book a reservation.

        Attempts to book the first available slot matching the preferred times,
        in order of preference.

        Args:
            venue_id: The unique identifier of the restaurant
            date: Reservation date in YYYY-MM-DD format
            party_size: Number of guests
            preferred_times: List of times in HH:MM:SS format, ordered by preference
            preferred_table_types: Optional list of table types (e.g., ["Dining Room", "Patio"])

        Returns:
            BookingResult if successful, None if no matching slots available

        Raises:
            ResyApiError: If an API call fails
        """
        slots = self.find_reservations(venue_id, date, party_size)

        if not slots:
            return None

        # Build a lookup by time -> slots
        slots_by_time = {}
        for slot in slots:
            if slot.time not in slots_by_time:
                slots_by_time[slot.time] = []
            slots_by_time[slot.time].append(slot)

        # Find best matching slot
        selected_slot = None
        for time in preferred_times:
            if time in slots_by_time:
                available = slots_by_time[time]

                if preferred_table_types:
                    # Try to match table type preference
                    for table_type in preferred_table_types:
                        for slot in available:
                            if table_type.lower() in slot.table_type.lower():
                                selected_slot = slot
                                break
                        if selected_slot:
                            break

                if not selected_slot:
                    # Take first available at this time
                    selected_slot = available[0]

                break

        if not selected_slot:
            return None

        # Get booking details and complete reservation
        details = self.get_reservation_details(selected_slot.config_token, date, party_size)
        return self.book_reservation(details.book_token, details.payment_method_id)


def load_client_from_config(config_path: str = "config.json") -> ResyClient:
    """
    Load a ResyClient from a config file.

    Args:
        config_path: Path to JSON config file with api_key and auth_token

    Returns:
        Configured ResyClient instance
    """
    with open(config_path) as f:
        config = json.load(f)

    return ResyClient(
        api_key=config["api_key"],
        auth_token=config["auth_token"],
    )
