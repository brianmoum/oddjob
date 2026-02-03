import argparse
import sys
import time
from datetime import datetime

from booking import run_booking


def parse_args():
    parser = argparse.ArgumentParser(
        description="OddJob — Automated Resy reservation booker",
        epilog="Example: python ResyInterface.py --restaurant lartusi-ny --date 2025-03-15 --guests 4 --best 7:00 --earliest 6:00 --latest 9:30"
    )
    parser.add_argument("--restaurant", required=True,
                        help="Resy restaurant URL code (e.g. 'lartusi-ny')")
    parser.add_argument("--date", required=True,
                        help="Reservation date in YYYY-MM-DD format")
    parser.add_argument("--guests", required=True, type=int,
                        help="Number of guests")
    parser.add_argument("--best", required=True,
                        help="Ideal reservation time (e.g. '7:00')")
    parser.add_argument("--earliest", required=True,
                        help="Earliest acceptable time (e.g. '6:00')")
    parser.add_argument("--latest", required=True,
                        help="Latest acceptable time (e.g. '9:30')")
    parser.add_argument("--city", default="new-york-ny",
                        help="Resy city slug (default: 'new-york-ny')")
    parser.add_argument("--run-at",
                        help="Schedule booking at a specific time (format: 'YYYY-MM-DD HH:MM:SS')")

    args = parser.parse_args()

    if args.guests < 1:
        parser.error("Guest count must be at least 1.")

    return args


def wait_until(run_at_str):
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

    print("Executing booking now.                ")


def main():
    args = parse_args()

    if args.run_at:
        wait_until(args.run_at)

    run_booking(
        restaurant=args.restaurant,
        res_date=args.date,
        guests=args.guests,
        best=args.best,
        earliest=args.earliest,
        latest=args.latest,
        city=args.city,
    )


main()
