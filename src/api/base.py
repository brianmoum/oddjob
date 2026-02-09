"""
Shared booking client interface for multi-platform support.

All platform-specific clients (Resy, OpenTable, etc.) implement the
BookingClient ABC so the CLI, Lambda handler, and scheduler can work
with any platform through a single interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Slot:
    """A single available reservation slot, platform-agnostic."""
    platform: str
    venue_id: str
    time: str  # HH:MM:SS format
    table_type: str
    platform_data: dict = field(default_factory=dict)


@dataclass
class BookingConfirmation:
    """Result of a successful booking."""
    platform: str
    confirmation_id: str
    reservation_id: Optional[str] = None
    details: Optional[dict] = None


class BookingClientError(Exception):
    """Base exception for booking client errors."""

    def __init__(self, message: str, platform: str = "unknown"):
        self.platform = platform
        super().__init__(f"[{platform}] {message}")


class BookingClient(ABC):
    """Abstract base class for platform booking clients."""

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Return the platform identifier (e.g., 'resy', 'opentable')."""
        ...

    @abstractmethod
    def find_slots(self, venue_id: str, date: str, party_size: int) -> list[Slot]:
        """
        Find available reservation slots.

        Args:
            venue_id: Platform-specific venue identifier (str for all platforms)
            date: Reservation date in YYYY-MM-DD format
            party_size: Number of guests

        Returns:
            List of available Slot objects
        """
        ...

    @abstractmethod
    def book_slot(self, slot: Slot, date: str, party_size: int) -> BookingConfirmation:
        """
        Book a specific slot.

        Args:
            slot: The Slot to book (from find_slots)
            date: Reservation date in YYYY-MM-DD format
            party_size: Number of guests

        Returns:
            BookingConfirmation on success

        Raises:
            BookingClientError: If the booking fails
        """
        ...
