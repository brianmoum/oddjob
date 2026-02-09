"""
Platform-agnostic slot selection algorithm.

Extracts the "pick best slot" logic that was previously duplicated in
cli.py, lambda_handler.py, and resy_client.py into a single function.
"""

from typing import Optional

from .base import Slot


def select_best_slot(
    slots: list[Slot],
    preferred_times: list[str],
    preferred_table_types: Optional[list[str]] = None,
) -> Optional[Slot]:
    """
    Select the best slot from available options based on time and table type preferences.

    Args:
        slots: Available slots from any platform's find_slots()
        preferred_times: Times in HH:MM:SS format, ordered by preference (best first)
        preferred_table_types: Optional table type preferences, ordered by preference

    Returns:
        The best matching Slot, or None if no slots match preferred times
    """
    if not slots:
        return None

    # Build lookup: time -> list of slots
    slots_by_time: dict[str, list[Slot]] = {}
    for slot in slots:
        slots_by_time.setdefault(slot.time, []).append(slot)

    # Find best matching slot
    for time in preferred_times:
        if time not in slots_by_time:
            continue

        available = slots_by_time[time]

        if preferred_table_types:
            for table_type in preferred_table_types:
                for slot in available:
                    if table_type.lower() in slot.table_type.lower():
                        return slot

        # No table type preference or no match — take first at this time
        return available[0]

    return None
