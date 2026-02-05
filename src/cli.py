#!/usr/bin/env python3
"""
CLI for OddJob Resy reservation booking via API.

Example usage:
    python cli.py --venue-id 25973 --date 2026-02-19 --guests 2 --best 19:00 --earliest 18:00 --latest 21:00

With scheduling:
    python cli.py --venue-id 25973 --date 2026-02-19 --guests 2 --best 19:00 --earliest 18:00 --latest 21:00 --run-at "2026-02-05 09:00:00"
"""

import argparse
import os
import sys
import time
from datetime import datetime, date
from pathlib import Path

from api.resy_client import load_client_from_config, ResyApiError


# Default config path is in project root (parent of src/)
DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config.json"


def parse_time_to_seconds(time_str: str) -> float:
    """Convert time string (e.g., '19:00' or '7:30') to hours as float."""
    parts = time_str.replace(" ", "").split(":")
    hours = int(parts[0])
    minutes = int(parts[1]) if len(parts) > 1 else 0
    return hours + minutes / 60


def seconds_to_time_str(hours: float) -> str:
    """Convert hours as float to HH:MM:SS format for API."""
    h = int(hours)
    m = int((hours - h) * 60)
    # Round to nearest 15 minutes
    m = round(m / 15) * 15
    if m == 60:
        h += 1
        m = 0
    return f"{h:02d}:{m:02d}:00"


def generate_preferred_times(best: str, earliest: str, latest: str) -> list[str]:
    """
    Generate a priority-ordered list of times starting from best time,
    alternating outward until reaching earliest/latest boundaries.

    E.g., best=19:00, earliest=18:00, latest=20:00 produces:
    [19:00, 19:15, 18:45, 19:30, 18:30, 19:45, 18:15, 20:00, 18:00]
    """
    best_h = parse_time_to_seconds(best)
    earliest_h = parse_time_to_seconds(earliest)
    latest_h = parse_time_to_seconds(latest)

    preferred = [seconds_to_time_str(best_h)]

    offset = 0.25  # 15 minutes
    while True:
        upper = best_h + offset
        lower = best_h - offset

        added = False
        if upper <= latest_h:
            preferred.append(seconds_to_time_str(upper))
            added = True
        if lower >= earliest_h:
            preferred.append(seconds_to_time_str(lower))
            added = True

        if not added:
            break

        offset += 0.25

    return preferred


def wait_until(run_at_str: str) -> None:
    """Wait until the specified time before executing."""
    try:
        run_at = datetime.strptime(run_at_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        print(f"Error: Invalid --run-at format '{run_at_str}'. Use 'YYYY-MM-DD HH:MM:SS'.")
        sys.exit(1)

    now = datetime.now()
    if run_at <= now:
        print(f"Error: --run-at time '{run_at_str}' is in the past.")
        sys.exit(1)

    wait_seconds = (run_at - now).total_seconds()
    print(f"Scheduled to run at {run_at_str}")
    print(f"Waiting {wait_seconds:.0f} seconds...")
    print()

    while True:
        now = datetime.now()
        remaining = (run_at - now).total_seconds()
        if remaining <= 0:
            break
        if remaining > 60:
            print(f"  {remaining:.0f}s remaining...", end="\r")
            time.sleep(30)
        elif remaining > 5:
            print(f"  {remaining:.0f}s remaining...", end="\r")
            time.sleep(1)
        else:
            time.sleep(remaining)
            break

    print("Executing booking now!                ")
    print()


def validate_date(date_str: str) -> str:
    """Validate date format and ensure it's not in the past."""
    try:
        res_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        print(f"Error: Invalid date format '{date_str}'. Use YYYY-MM-DD.")
        sys.exit(1)

    if res_date < date.today():
        print(f"Error: Date '{date_str}' is in the past.")
        sys.exit(1)

    return date_str


def validate_times(best: str, earliest: str, latest: str) -> None:
    """Validate time inputs."""
    best_h = parse_time_to_seconds(best)
    earliest_h = parse_time_to_seconds(earliest)
    latest_h = parse_time_to_seconds(latest)

    if earliest_h > best_h:
        print(f"Error: Earliest time ({earliest}) is after best time ({best}).")
        sys.exit(1)

    if best_h > latest_h:
        print(f"Error: Best time ({best}) is after latest time ({latest}).")
        sys.exit(1)


def run_booking(
    venue_id: int,
    res_date: str,
    party_size: int,
    best: str,
    earliest: str,
    latest: str,
    table_types: list[str] | None = None,
    retry_count: int = 3,
    retry_delay: float = 0.5,
    config_path: str | None = None,
    dry_run: bool = False,
) -> bool:
    """
    Execute a booking attempt with retries.

    Returns True if successful, False otherwise.
    """
    validate_date(res_date)
    validate_times(best, earliest, latest)

    preferred_times = generate_preferred_times(best, earliest, latest)

    print(f"Booking attempt:")
    print(f"  Venue ID:    {venue_id}")
    print(f"  Date:        {res_date}")
    print(f"  Party size:  {party_size}")
    print(f"  Time range:  {earliest} - {latest} (ideal: {best})")
    print(f"  Preferences: {len(preferred_times)} time slots")
    if table_types:
        print(f"  Table types: {', '.join(table_types)}")
    print()

    config_file = config_path or str(DEFAULT_CONFIG_PATH)
    client = load_client_from_config(config_file)

    for attempt in range(1, retry_count + 1):
        try:
            print(f"Attempt {attempt}/{retry_count}...")

            # Find available slots
            slots = client.find_reservations(venue_id, res_date, party_size)

            if not slots:
                print("  No slots available.")
                if attempt < retry_count:
                    time.sleep(retry_delay)
                continue

            print(f"  Found {len(slots)} available slots")

            # Build lookup by time
            slots_by_time = {}
            for slot in slots:
                if slot.time not in slots_by_time:
                    slots_by_time[slot.time] = []
                slots_by_time[slot.time].append(slot)

            # Find best matching slot
            selected_slot = None
            for pref_time in preferred_times:
                if pref_time in slots_by_time:
                    available = slots_by_time[pref_time]

                    if table_types:
                        for table_type in table_types:
                            for slot in available:
                                if table_type.lower() in slot.table_type.lower():
                                    selected_slot = slot
                                    break
                            if selected_slot:
                                break

                    if not selected_slot:
                        selected_slot = available[0]

                    break

            if not selected_slot:
                print("  No slots match preferred times.")
                if attempt < retry_count:
                    time.sleep(retry_delay)
                continue

            print(f"  Selected: {selected_slot.time} - {selected_slot.table_type}")

            if dry_run:
                print()
                print("=" * 50)
                print("DRY RUN - Would book this slot (no reservation made)")
                print(f"  Time:       {selected_slot.time}")
                print(f"  Table type: {selected_slot.table_type}")
                print("=" * 50)
                return True

            # Get booking details
            details = client.get_reservation_details(
                selected_slot.config_token, res_date, party_size
            )

            # Book it
            result = client.book_reservation(
                details.book_token, details.payment_method_id
            )

            print()
            print("=" * 50)
            print("SUCCESS! Reservation confirmed.")
            print(f"  Reservation ID: {result.reservation_id}")
            print(f"  Resy Token:     {result.resy_token[:40]}...")
            print("=" * 50)

            return True

        except ResyApiError as e:
            print(f"  Error: {e}")
            if attempt < retry_count:
                time.sleep(retry_delay)

    print()
    print("Failed to book reservation after all attempts.")
    return False


def main():
    parser = argparse.ArgumentParser(
        description="OddJob — Automated Resy reservation booker (API version)",
        epilog="Example: python cli.py --venue-id 25973 --date 2026-02-19 --guests 2 --best 19:00 --earliest 18:00 --latest 21:00"
    )
    parser.add_argument("--venue-id", required=True, type=int,
                        help="Resy venue ID (numeric)")
    parser.add_argument("--date", required=True,
                        help="Reservation date in YYYY-MM-DD format")
    parser.add_argument("--guests", required=True, type=int,
                        help="Number of guests")
    parser.add_argument("--best", required=True,
                        help="Ideal reservation time (e.g., '19:00')")
    parser.add_argument("--earliest", required=True,
                        help="Earliest acceptable time (e.g., '18:00')")
    parser.add_argument("--latest", required=True,
                        help="Latest acceptable time (e.g., '21:00')")
    parser.add_argument("--table-type", action="append", dest="table_types",
                        help="Preferred table type (can specify multiple, e.g., --table-type 'Indoor Dining' --table-type 'Patio')")
    parser.add_argument("--run-at",
                        help="Schedule booking at a specific time (format: 'YYYY-MM-DD HH:MM:SS')")
    parser.add_argument("--retries", type=int, default=3,
                        help="Number of retry attempts (default: 3)")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH),
                        help=f"Path to config.json (default: {DEFAULT_CONFIG_PATH})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Find and select a slot but don't actually book")

    args = parser.parse_args()

    if args.guests < 1:
        parser.error("Guest count must be at least 1.")

    if args.run_at:
        wait_until(args.run_at)

    success = run_booking(
        venue_id=args.venue_id,
        res_date=args.date,
        party_size=args.guests,
        best=args.best,
        earliest=args.earliest,
        latest=args.latest,
        table_types=args.table_types,
        retry_count=args.retries,
        config_path=args.config,
        dry_run=args.dry_run,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
