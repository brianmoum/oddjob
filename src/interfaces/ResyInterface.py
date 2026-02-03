import argparse
import json
import os
import sys
from datetime import date, datetime

import ResyTimeFunctions as rtf
import ResyDaemon as rd


def validate_config():
    if not os.path.exists('config.json'):
        print("Error: config.json not found.")
        print("Create a config.json file with your Resy credentials:")
        print('  {"username": "your@email.com", "password": "your_password"}')
        sys.exit(1)

    with open('config.json') as f:
        try:
            auth = json.load(f)
        except json.JSONDecodeError:
            print("Error: config.json is not valid JSON.")
            sys.exit(1)

    if "username" not in auth or "password" not in auth:
        print("Error: config.json must contain 'username' and 'password' keys.")
        sys.exit(1)


def validate_date(date_str):
    try:
        res_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        print(f"Error: Invalid date format '{date_str}'. Use YYYY-MM-DD.")
        sys.exit(1)

    if res_date < date.today():
        print(f"Error: Date '{date_str}' is in the past.")
        sys.exit(1)

    return date_str


def validate_times(best, earliest, latest):
    n_best = rtf.timeToFloat(best)
    n_earliest = rtf.timeToFloat(earliest)
    n_latest = rtf.timeToFloat(latest)

    if n_earliest > n_best:
        print(f"Error: Earliest time ({earliest}) is after best time ({best}).")
        sys.exit(1)

    if n_best > n_latest:
        print(f"Error: Best time ({best}) is after latest time ({latest}).")
        sys.exit(1)

    if n_earliest > n_latest:
        print(f"Error: Earliest time ({earliest}) is after latest time ({latest}).")
        sys.exit(1)


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

    args = parser.parse_args()

    if args.guests < 1:
        parser.error("Guest count must be at least 1.")

    return args


def main():
    args = parse_args()

    validate_config()
    validate_date(args.date)
    validate_times(args.best, args.earliest, args.latest)

    preferred_times = rd.getPreferredTimes(args.best, args.earliest, args.latest)

    url = "https://resy.com/cities/{0}/venues/{1}?seats={2}&date={3}".format(
        args.city, args.restaurant, args.guests, args.date
    )

    print(f"Booking: {args.restaurant}")
    print(f"  Date:   {args.date}")
    print(f"  Guests: {args.guests}")
    print(f"  Time:   {args.earliest} - {args.latest} (ideal: {args.best})")
    print(f"  URL:    {url}")
    print()

    rd.getPage(url, preferred_times)


main()
