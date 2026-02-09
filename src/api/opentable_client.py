"""
OpenTable API client stub.

This is a placeholder for the OpenTable booking client. To implement it,
capture the OpenTable API from browser dev tools while making a reservation,
then fill in the find_slots() and book_slot() methods.

Steps to capture the API:
1. Open browser dev tools (Network tab)
2. Go to OpenTable and search for a restaurant
3. Select a date/time/party size and click "Find a Table"
4. Watch the network requests — note the endpoints, headers, and payloads
5. Complete a booking and capture the booking request
"""

from .base import BookingClient, BookingClientError, Slot, BookingConfirmation


class OpenTableClient(BookingClient):
    """Stub client for OpenTable — not yet implemented."""

    def __init__(self, credentials: dict):
        self.credentials = credentials

    @property
    def platform_name(self) -> str:
        return "opentable"

    def find_slots(self, venue_id: str, date: str, party_size: int) -> list[Slot]:
        raise BookingClientError(
            "OpenTable client is not yet implemented. "
            "Capture the OpenTable API from browser dev tools and fill in this client.",
            platform="opentable",
        )

    def book_slot(self, slot: Slot, date: str, party_size: int) -> BookingConfirmation:
        raise BookingClientError(
            "OpenTable client is not yet implemented. "
            "Capture the OpenTable API from browser dev tools and fill in this client.",
            platform="opentable",
        )
