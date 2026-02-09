#!/usr/bin/env python3
"""
CLI for OddJob automated restaurant reservation booking.

Supports multiple platforms (Resy, OpenTable) via --platform flag (default: resy).

Example usage:
    python cli.py --venue-id 25973 --date 2026-02-19 --guests 2 --best 19:00 --earliest 18:00 --latest 21:00

With scheduling:
    python cli.py --venue-id 25973 --date 2026-02-19 --guests 2 --best 19:00 --earliest 18:00 --latest 21:00 --run-at "2026-02-05 09:00:00"
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, date, timezone
from pathlib import Path

from api.base import BookingClientError
from api.client_factory import load_client_from_config
from api.slot_selection import select_best_slot


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
    venue_id: str,
    res_date: str,
    party_size: int,
    best: str,
    earliest: str,
    latest: str,
    platform: str = "resy",
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
    print(f"  Platform:    {platform}")
    print(f"  Venue ID:    {venue_id}")
    print(f"  Date:        {res_date}")
    print(f"  Party size:  {party_size}")
    print(f"  Time range:  {earliest} - {latest} (ideal: {best})")
    print(f"  Preferences: {len(preferred_times)} time slots")
    if table_types:
        print(f"  Table types: {', '.join(table_types)}")
    print()

    config_file = config_path or str(DEFAULT_CONFIG_PATH)
    try:
        client = load_client_from_config(platform, config_file)
    except BookingClientError as e:
        print(f"Error: {e}")
        return False

    for attempt in range(1, retry_count + 1):
        try:
            print(f"Attempt {attempt}/{retry_count}...")

            # Find available slots
            slots = client.find_slots(venue_id, res_date, party_size)

            if not slots:
                print("  No slots available.")
                if attempt < retry_count:
                    time.sleep(retry_delay)
                continue

            print(f"  Found {len(slots)} available slots")

            selected_slot = select_best_slot(slots, preferred_times, table_types)

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

            result = client.book_slot(selected_slot, res_date, party_size)

            print()
            print("=" * 50)
            print("SUCCESS! Reservation confirmed.")
            print(f"  Confirmation: {result.confirmation_id[:40]}...")
            if result.reservation_id:
                print(f"  Reservation ID: {result.reservation_id}")
            print("=" * 50)

            return True

        except BookingClientError as e:
            print(f"  Error: {e}")
            if attempt < retry_count:
                time.sleep(retry_delay)

    print()
    print("Failed to book reservation after all attempts.")
    return False


def require_booking_args(args, parser):
    """Validate that all booking-related arguments are present."""
    required = {
        "--venue-id": args.venue_id,
        "--date": args.date,
        "--guests": args.guests,
        "--best": args.best,
        "--earliest": args.earliest,
        "--latest": args.latest,
    }
    missing = [name for name, val in required.items() if val is None]
    if missing:
        parser.error(f"the following arguments are required: {', '.join(missing)}")

    if args.guests < 1:
        parser.error("Guest count must be at least 1.")


def main():
    parser = argparse.ArgumentParser(
        description="OddJob — Automated restaurant reservation booker",
        epilog="Example: python cli.py --venue-id 25973 --date 2026-02-19 --guests 2 --best 19:00 --earliest 18:00 --latest 21:00"
    )
    # Booking arguments (required for booking/scheduling, not for --list-jobs/--cancel-job)
    parser.add_argument("--platform", choices=["resy", "opentable"], default="resy",
                        help="Booking platform (default: resy)")
    parser.add_argument("--venue-id", type=str,
                        help="Venue ID (platform-specific)")
    parser.add_argument("--date",
                        help="Reservation date in YYYY-MM-DD format")
    parser.add_argument("--guests", type=int,
                        help="Number of guests")
    parser.add_argument("--best",
                        help="Ideal reservation time (e.g., '19:00')")
    parser.add_argument("--earliest",
                        help="Earliest acceptable time (e.g., '18:00')")
    parser.add_argument("--latest",
                        help="Latest acceptable time (e.g., '21:00')")
    parser.add_argument("--table-type", action="append", dest="table_types",
                        help="Preferred table type (can specify multiple, e.g., --table-type 'Indoor Dining' --table-type 'Patio')")
    parser.add_argument("--run-at",
                        help="Schedule booking locally at a specific time (format: 'YYYY-MM-DD HH:MM:SS')")
    parser.add_argument("--retries", type=int, default=3,
                        help="Number of retry attempts (default: 3)")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH),
                        help=f"Path to config.json (default: {DEFAULT_CONFIG_PATH})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Find and select a slot but don't actually book")

    # Cloud scheduling arguments
    parser.add_argument("--schedule",
                        help="Create a cloud-scheduled job via EventBridge (local time, format: 'YYYY-MM-DD HH:MM:SS')")
    parser.add_argument("--list-jobs", action="store_true",
                        help="List all cloud-scheduled jobs")
    parser.add_argument("--cancel-job",
                        help="Cancel a cloud-scheduled job by name")

    args = parser.parse_args()

    # Handle cloud scheduling commands (no booking args required)
    if args.list_jobs:
        from scheduler import list_schedules
        schedules = list_schedules()
        if not schedules:
            print("No scheduled jobs.")
        else:
            print(f"Scheduled jobs ({len(schedules)}):\n")
            for s in schedules:
                print(f"  {s['name']}")
                print(f"    State:    {s['state']}")
                print(f"    Schedule: {s['schedule']}")
                if s.get("payload"):
                    p = s["payload"]
                    print(f"    Platform: {p.get('platform', 'resy')}")
                    print(f"    Venue:    {p.get('venue_id', '?')}")
                    print(f"    Date:     {p.get('date', '?')}")
                    print(f"    Guests:   {p.get('party_size', '?')}")
                    print(f"    Time:     {p.get('earliest', '?')}-{p.get('latest', '?')} (best: {p.get('best', '?')})")
                print()
        sys.exit(0)

    if args.cancel_job:
        from scheduler import cancel_schedule
        try:
            cancel_schedule(args.cancel_job)
            print(f"Cancelled: {args.cancel_job}")
        except Exception as e:
            print(f"Error cancelling job: {e}")
            sys.exit(1)
        sys.exit(0)

    # For booking and scheduling, all booking args are required
    require_booking_args(args, parser)

    if args.schedule:
        from scheduler import schedule_booking
        # Convert local time to UTC
        try:
            local_dt = datetime.strptime(args.schedule, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            print(f"Error: Invalid --schedule format '{args.schedule}'. Use 'YYYY-MM-DD HH:MM:SS'.")
            sys.exit(1)

        local_dt = local_dt.astimezone()  # attach local timezone
        utc_dt = local_dt.astimezone(timezone.utc)
        run_at_utc = utc_dt.strftime("%Y-%m-%dT%H:%M:%S")

        if utc_dt <= datetime.now(timezone.utc):
            print(f"Error: --schedule time '{args.schedule}' is in the past.")
            sys.exit(1)

        schedule_name = schedule_booking(
            venue_id=args.venue_id,
            date=args.date,
            party_size=args.guests,
            best=args.best,
            earliest=args.earliest,
            latest=args.latest,
            run_at_utc=run_at_utc,
            table_types=args.table_types,
            retries=args.retries,
            platform=args.platform,
        )

        print(f"Cloud job scheduled!")
        print(f"  Name:      {schedule_name}")
        print(f"  Platform:  {args.platform}")
        print(f"  Fires at:  {args.schedule} local ({run_at_utc} UTC)")
        print(f"  Venue:     {args.venue_id}")
        print(f"  Date:      {args.date}")
        print(f"  Guests:    {args.guests}")
        print(f"  Time:      {args.earliest}-{args.latest} (best: {args.best})")
        print()
        print("The schedule will auto-delete after firing.")
        print("To cancel: python cli.py --cancel-job " + schedule_name)
        sys.exit(0)

    if args.run_at:
        wait_until(args.run_at)

    success = run_booking(
        venue_id=args.venue_id,
        res_date=args.date,
        party_size=args.guests,
        best=args.best,
        earliest=args.earliest,
        latest=args.latest,
        platform=args.platform,
        table_types=args.table_types,
        retry_count=args.retries,
        config_path=args.config,
        dry_run=args.dry_run,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
