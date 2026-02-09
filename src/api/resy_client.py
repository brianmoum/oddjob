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

from .base import BookingClient, BookingClientError, Slot, BookingConfirmation


BASE_URL = "https://api.resy.com"


@dataclass
class BookingDetails:
    """Details needed to complete a reservation."""
    book_token: str
    payment_method_id: int


class ResyApiError(BookingClientError):
    """Exception for Resy API errors."""

    def __init__(self, message: str):
        super().__init__(message, platform="resy")


class ResyClient(BookingClient):
    """Client for interacting with the Resy API."""

    def __init__(self, api_key: str, auth_token: str):
        self.api_key = api_key
        self.auth_token = auth_token

    @property
    def platform_name(self) -> str:
        return "resy"

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
    ) -> list[Slot]:
        """
        Find available reservation slots for a venue.

        Args:
            venue_id: The unique identifier of the restaurant
            date: Reservation date in YYYY-MM-DD format
            party_size: Number of guests

        Returns:
            List of available Slot objects

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

                slots.append(Slot(
                    platform="resy",
                    venue_id=str(venue_id),
                    time=time_part,
                    table_type=config.get("type", ""),
                    platform_data={"config_token": config.get("token", "")},
                ))
        except (KeyError, IndexError) as e:
            raise ResyApiError(f"Failed to parse reservation response: {e}")

        return slots

    def find_slots(self, venue_id: str, date: str, party_size: int) -> list[Slot]:
        """BookingClient interface — delegates to find_reservations."""
        return self.find_reservations(int(venue_id), date, party_size)

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
    ) -> BookingConfirmation:
        """
        Complete a reservation booking.

        Args:
            book_token: The booking token from get_reservation_details
            payment_method_id: The payment method ID from get_reservation_details

        Returns:
            BookingConfirmation on success

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

        return BookingConfirmation(
            platform="resy",
            confirmation_id=resy_token,
            reservation_id=str(data["reservation_id"]) if data.get("reservation_id") else None,
            details={"resy_token": resy_token},
        )

    def book_slot(self, slot: Slot, date: str, party_size: int) -> BookingConfirmation:
        """BookingClient interface — runs Resy's 3-step details+book flow."""
        config_token = slot.platform_data.get("config_token")
        if not config_token:
            raise ResyApiError("Slot missing config_token in platform_data")

        details = self.get_reservation_details(config_token, date, party_size)
        return self.book_reservation(details.book_token, details.payment_method_id)
